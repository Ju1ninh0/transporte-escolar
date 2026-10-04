from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import admin_only
from app.db.session import get_db
from app.models import HistoricoRota, Motorista, Rota, StatusExecucao, Usuario
from app.schemas.viagem import ViagemOut
from app.services.viagem import finalizar, viagem_dict

router = APIRouter(prefix="/viagens", tags=["viagens"])


def _consulta(user: Usuario):
    return (
        select(HistoricoRota, Rota.nome, Usuario.nome)
        .join(Rota, Rota.id == HistoricoRota.rota_id)
        .outerjoin(Motorista, Motorista.id == HistoricoRota.motorista_id)
        .outerjoin(Usuario, Usuario.id == Motorista.usuario_id)
        .where(Rota.empresa_id == user.empresa_id)
    )


@router.get("", response_model=list[ViagemOut])
def listar(
    status_filtro: StatusExecucao | None = Query(default=None, alias="status"),
    rota_id: int | None = None,
    limite: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: Usuario = Depends(admin_only),
):
    q = _consulta(user)
    if status_filtro is not None:
        q = q.where(HistoricoRota.status == status_filtro)
    if rota_id is not None:
        q = q.where(HistoricoRota.rota_id == rota_id)
    q = q.order_by(HistoricoRota.iniciada_em.desc(), HistoricoRota.id.desc()).limit(limite)
    return [viagem_dict(v, rota_nome, mot_nome) for v, rota_nome, mot_nome in db.execute(q).all()]


@router.post("/{viagem_id}/encerrar", response_model=ViagemOut)
def encerrar(viagem_id: int, db: Session = Depends(get_db), user: Usuario = Depends(admin_only)):
    linha = db.execute(_consulta(user).where(HistoricoRota.id == viagem_id)).first()
    if linha is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Viagem não encontrada")
    viagem, rota_nome, mot_nome = linha
    if viagem.status != StatusExecucao.EM_ANDAMENTO:
        raise HTTPException(status.HTTP_409_CONFLICT, "Viagem já encerrada")
    finalizar(db, viagem)
    return viagem_dict(viagem, rota_nome, mot_nome)