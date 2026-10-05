from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.api.v1.rotas import _serializar
from app.db.session import get_db
from app.models import (
    HistoricoRota,
    Motorista,
    Parada,
    Perfil,
    Rota,
    StatusExecucao,
    StatusRota,
    Usuario,
    Veiculo,
)
from app.schemas.frota import ParadaOut
from app.schemas.viagem import MotoristaRotaDetalheOut, MotoristaRotaOut, ViagemOut
from app.services.frota import alunos_da_rota, viagem_em_andamento
from app.services.notificacoes import executar_seguro, notificar_fim, notificar_inicio
from app.services.viagem import finalizar, viagem_dict, viagens_em_andamento

router = APIRouter(prefix="/motorista", tags=["motorista"])
motorista_only = require_role(Perfil.MOTORISTA)


def _motorista(db: Session, user: Usuario) -> Motorista:
    m = db.scalar(
        select(Motorista).where(
            Motorista.usuario_id == user.id, Motorista.empresa_id == user.empresa_id
        )
    )
    if m is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cadastro de motorista não encontrado")
    return m


def _rota_do_motorista(db: Session, motorista: Motorista, rota_id: int) -> Rota:
    rota = db.scalar(
        select(Rota).where(
            Rota.id == rota_id,
            Rota.empresa_id == motorista.empresa_id,
            Rota.motorista_id == motorista.id,
        )
    )
    if rota is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rota não encontrada")
    return rota


def _em_andamento(db: Session, **filtros) -> bool:
    q = select(HistoricoRota.id).where(HistoricoRota.status == StatusExecucao.EM_ANDAMENTO)
    for campo, valor in filtros.items():
        q = q.where(getattr(HistoricoRota, campo) == valor)
    return db.scalar(q.limit(1)) is not None


@router.get("/rotas", response_model=list[MotoristaRotaOut])
def minhas_rotas(db: Session = Depends(get_db), user: Usuario = Depends(motorista_only)):
    m = _motorista(db, user)
    rotas = list(
        db.scalars(
            select(Rota)
            .where(
                Rota.empresa_id == m.empresa_id,
                Rota.motorista_id == m.id,
                Rota.status == StatusRota.ATIVA,
            )
            .order_by(Rota.nome)
        ).all()
    )
    ativas = viagens_em_andamento(db, [r.id for r in rotas])
    dados = _serializar(db, rotas)
    for d in dados:
        d["viagem_em_andamento_id"] = ativas.get(d["id"])
    return dados


@router.get("/rotas/{rota_id}", response_model=MotoristaRotaDetalheOut)
def minha_rota(rota_id: int, db: Session = Depends(get_db), user: Usuario = Depends(motorista_only)):
    m = _motorista(db, user)
    rota = _rota_do_motorista(db, m, rota_id)
    dados = _serializar(db, [rota])[0]
    dados["viagem_em_andamento_id"] = viagens_em_andamento(db, [rota.id]).get(rota.id)
    paradas = db.scalars(
        select(Parada).where(Parada.rota_id == rota.id).order_by(Parada.ordem)
    ).all()
    dados["paradas"] = [ParadaOut.model_validate(p).model_dump() for p in paradas]
    dados["alunos"] = alunos_da_rota(db, rota.id)
    return dados


@router.post(
    "/rotas/{rota_id}/viagem/iniciar", response_model=ViagemOut, status_code=status.HTTP_201_CREATED
)
def iniciar_viagem(
    rota_id: int, db: Session = Depends(get_db), user: Usuario = Depends(motorista_only)
):
    m = _motorista(db, user)
    rota = _rota_do_motorista(db, m, rota_id)
    if rota.status != StatusRota.ATIVA:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Rota inativa")
    if rota.veiculo_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "A rota não tem veículo vinculado")
    veiculo = db.get(Veiculo, rota.veiculo_id)
    if veiculo is None or not veiculo.ativo:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Veículo inativo")
    if viagem_em_andamento(db, rota.id):
        raise HTTPException(status.HTTP_409_CONFLICT, "Esta rota já tem uma viagem em andamento")
    if _em_andamento(db, veiculo_id=rota.veiculo_id):
        raise HTTPException(status.HTTP_409_CONFLICT, "O veículo já está em outra viagem em andamento")
    if _em_andamento(db, motorista_id=m.id):
        raise HTTPException(status.HTTP_409_CONFLICT, "Você já tem uma viagem em andamento")
    viagem = HistoricoRota(rota_id=rota.id, veiculo_id=rota.veiculo_id, motorista_id=m.id)
    db.add(viagem)
    db.commit()
    db.refresh(viagem)
    executar_seguro(db, notificar_inicio, viagem.id, rota.id, rota.nome)
    return viagem_dict(viagem, rota.nome, user.nome)


@router.post("/viagens/{viagem_id}/encerrar", response_model=ViagemOut)
def encerrar_viagem(
    viagem_id: int, db: Session = Depends(get_db), user: Usuario = Depends(motorista_only)
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
        raise HTTPException(status.HTTP_409_CONFLICT, "Viagem já encerrada")
    finalizar(db, viagem)
    rota = db.get(Rota, viagem.rota_id)
    executar_seguro(db, notificar_fim, rota.id, rota.nome)
    return viagem_dict(viagem, rota.nome, user.nome)