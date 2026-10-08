import asyncio
import logging

import anyio.from_thread
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import admin_only, usuario_do_token
from app.api.v1.motorista import _motorista, motorista_only
from app.db.session import get_db
from app.models import HistoricoRota, Localizacao, Perfil, Rota, StatusExecucao, Usuario
from app.schemas.gps import (
    LocalizacaoIn,
    LocalizacaoOut,
    PontoTrilhaOut,
    ViagemAtivaOut,
)
from app.services.gps import Assinante, hub, rotas_visiveis, viagens_ativas
from app.services.notificacoes import executar_seguro, notificar_proximidade

logger = logging.getLogger(__name__)
router = APIRouter(tags=["gps"])

WS_NAO_AUTENTICADO = 4401
WS_SEM_PERMISSAO = 4403


def _publicar(evento: dict, empresa_id: int, rota_id: int) -> None:
    """Chamado de endpoints síncronos (thread do anyio). Nunca deve quebrar o envio do GPS."""
    try:
        anyio.from_thread.run(hub.publicar, evento, empresa_id, rota_id)
    except Exception:  # pragma: no cover
        logger.exception("Falha ao publicar localização no WebSocket")


# ---------------------------------------------------------------- motorista envia
@router.post(
    "/motorista/viagens/{viagem_id}/localizacao",
    response_model=LocalizacaoOut,
    status_code=status.HTTP_201_CREATED,
)
def enviar_localizacao(
    viagem_id: int,
    body: LocalizacaoIn,
    db: Session = Depends(get_db),
    user: Usuario = Depends(motorista_only),
):
    m = _motorista(db, user)
    viagem = db.scalar(
        select(HistoricoRota).where(
            HistoricoRota.id == viagem_id, HistoricoRota.motorista_id == m.id
        )
    )
    if viagem is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Viagem não encontrada")
    if viagem.status != StatusExecucao.EM_ANDAMENTO:
        raise HTTPException(status.HTTP_409_CONFLICT, "Viagem encerrada")
    if viagem.veiculo_id is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Viagem sem veículo")

    loc = Localizacao(
        veiculo_id=viagem.veiculo_id,
        historico_rota_id=viagem.id,
        latitude=body.latitude,
        longitude=body.longitude,
        velocidade=body.velocidade,
        direcao=body.direcao,
    )
    db.add(loc)
    db.commit()
    db.refresh(loc)

    saida = {
        "id": loc.id,
        "viagem_id": viagem.id,
        "latitude": loc.latitude,
        "longitude": loc.longitude,
        "velocidade": loc.velocidade,
        "direcao": loc.direcao,
        "timestamp": loc.timestamp,
    }
    _publicar(
        {"tipo": "localizacao", "rota_id": viagem.rota_id, **saida},
        user.empresa_id,
        viagem.rota_id,
    )
    rota = db.get(Rota, viagem.rota_id)
    executar_seguro(
        db,
        notificar_proximidade,
        viagem.id,
        viagem.rota_id,
        rota.nome if rota else "",
        user.empresa_id,
        body.latitude,
        body.longitude,
    )
    return saida


# ------------------------------------------------------------------ admin (HTTP)
@router.get("/viagens/ativas", response_model=list[ViagemAtivaOut])
def ativas(db: Session = Depends(get_db), user: Usuario = Depends(admin_only)):
    return viagens_ativas(db, user.empresa_id, None)


@router.get("/viagens/{viagem_id}/trilha", response_model=list[PontoTrilhaOut])
def trilha(
    viagem_id: int,
    limite: int = Query(default=200, ge=1, le=2000),
    db: Session = Depends(get_db),
    user: Usuario = Depends(admin_only),
):
    viagem = db.scalar(
        select(HistoricoRota)
        .join(Rota, Rota.id == HistoricoRota.rota_id)
        .where(HistoricoRota.id == viagem_id, Rota.empresa_id == user.empresa_id)
    )
    if viagem is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Viagem não encontrada")
    ultimos = db.scalars(
        select(Localizacao)
        .where(Localizacao.historico_rota_id == viagem.id)
        .order_by(Localizacao.id.desc())
        .limit(limite)
    ).all()
    return [
        {"latitude": p.latitude, "longitude": p.longitude, "timestamp": p.timestamp}
        for p in reversed(ultimos)
    ]


# ---------------------------------------------------------------------- WebSocket
async def _fechar(ws: WebSocket, codigo: int) -> None:
    try:
        await ws.close(code=codigo)
    except RuntimeError:
        pass


@router.websocket("/ws/viagens")
async def acompanhar_viagens(ws: WebSocket, db: Session = Depends(get_db)):
    """
    Protocolo:
      1) o cliente conecta e envia {"token": "<access token>"} em até 10 s
      2) o servidor responde {"tipo": "snapshot", "viagens": [...]} com as viagens em andamento
      3) depois chegam eventos {"tipo": "localizacao", ...}; o cliente pode enviar "ping"
    Admin vê tudo da empresa; responsável só as rotas dos filhos; motorista não acessa.
    """
    await ws.accept()
    try:
        msg = await asyncio.wait_for(ws.receive_json(), timeout=10)
    except WebSocketDisconnect:
        return
    except (asyncio.TimeoutError, ValueError, KeyError):
        await _fechar(ws, WS_NAO_AUTENTICADO)
        return

    user = usuario_do_token(db, msg.get("token") if isinstance(msg, dict) else None)
    if user is None:
        await _fechar(ws, WS_NAO_AUTENTICADO)
        return
    if user.perfil not in (Perfil.ADMIN, Perfil.RESPONSAVEL):
        await _fechar(ws, WS_SEM_PERMISSAO)
        return

    rotas = rotas_visiveis(db, user)
    snapshot = viagens_ativas(db, user.empresa_id, rotas)
    empresa_id = user.empresa_id
    db.rollback()  # libera a conexão do pool enquanto o socket fica aberto

    # Entra no hub ANTES de enviar o snapshot: assim nenhum evento se perde. Como um evento pode
    # chegar antes do snapshot, o cliente compara o timestamp e mantém a posição mais recente.
    assinante = Assinante(ws=ws, empresa_id=empresa_id, rotas=rotas)
    hub.adicionar(assinante)
    try:
        await ws.send_json(jsonable_encoder({"tipo": "snapshot", "viagens": snapshot}))
        while True:
            texto = await ws.receive_text()
            if texto == "ping":
                await ws.send_json({"tipo": "pong"})
    except WebSocketDisconnect:
        pass
    finally:
        hub.remover(assinante)