from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Aluno, HistoricoRota, Parada, Rota, RotaAluno, StatusExecucao


def obter_rota(db: Session, empresa_id: int, rota_id: int) -> Rota:
    rota = db.scalar(select(Rota).where(Rota.id == rota_id, Rota.empresa_id == empresa_id))
    if rota is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rota não encontrada")
    return rota


def viagem_em_andamento(db: Session, rota_id: int) -> bool:
    achou = db.scalar(
        select(HistoricoRota.id)
        .where(
            HistoricoRota.rota_id == rota_id,
            HistoricoRota.status == StatusExecucao.EM_ANDAMENTO,
        )
        .limit(1)
    )
    return achou is not None


def bloquear_se_em_viagem(db: Session, rota_id: int, mensagem: str) -> None:
    if viagem_em_andamento(db, rota_id):
        raise HTTPException(status.HTTP_409_CONFLICT, mensagem)


def total_alunos(db: Session, rota_id: int) -> int:
    return db.scalar(select(func.count(RotaAluno.id)).where(RotaAluno.rota_id == rota_id)) or 0


def alunos_da_rota(db: Session, rota_id: int, aluno_id: int | None = None) -> list[dict]:
    q = (
        select(Aluno.id, Aluno.nome, Aluno.escola, RotaAluno.parada_id, Parada.nome)
        .select_from(RotaAluno)
        .join(Aluno, Aluno.id == RotaAluno.aluno_id)
        .outerjoin(Parada, Parada.id == RotaAluno.parada_id)
        .where(RotaAluno.rota_id == rota_id)
    )
    if aluno_id is not None:
        q = q.where(RotaAluno.aluno_id == aluno_id)
    q = q.order_by(Aluno.nome)
    return [
        {
            "aluno_id": a_id,
            "nome": nome,
            "escola": escola,
            "parada_id": parada_id,
            "parada_nome": parada_nome,
        }
        for a_id, nome, escola, parada_id, parada_nome in db.execute(q).all()
    ]