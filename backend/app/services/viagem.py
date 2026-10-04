from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import HistoricoRota, StatusExecucao
from app.models.mixins import agora


def viagem_dict(v: HistoricoRota, rota_nome: str, motorista_nome: str | None) -> dict:
    return {
        "id": v.id,
        "rota_id": v.rota_id,
        "rota_nome": rota_nome,
        "veiculo_id": v.veiculo_id,
        "motorista_id": v.motorista_id,
        "motorista_nome": motorista_nome,
        "iniciada_em": v.iniciada_em,
        "finalizada_em": v.finalizada_em,
        "status": v.status,
    }


def viagens_em_andamento(db: Session, rota_ids: list[int]) -> dict[int, int]:
    """rota_id -> id da viagem em andamento."""
    if not rota_ids:
        return {}
    linhas = db.execute(
        select(HistoricoRota.rota_id, HistoricoRota.id).where(
            HistoricoRota.rota_id.in_(rota_ids),
            HistoricoRota.status == StatusExecucao.EM_ANDAMENTO,
        )
    ).all()
    return {rota_id: viagem_id for rota_id, viagem_id in linhas}


def finalizar(db: Session, viagem: HistoricoRota) -> None:
    viagem.status = StatusExecucao.FINALIZADA
    viagem.finalizada_em = agora()
    db.commit()
    db.refresh(viagem)