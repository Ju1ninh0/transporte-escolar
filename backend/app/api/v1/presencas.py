from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import admin_only
from app.api.v1.motorista import _motorista, motorista_only
from app.db.session import get_db
from app.models import HistoricoRota, PresencaViagem, Rota, RotaAluno, StatusExecucao, Usuario
from app.schemas.presenca import PresencaAlunoOut, PresencaIn, PresencasOut
from app.services.presenca import montar_presencas

router = APIRouter(tags=["presencas"])


def _viagem_do_motorista(db: Session, user: Usuario, viagem_id: int) -> HistoricoRota:
    m = _motorista(db, user)
    viagem = db.scalar(
        select(HistoricoRota).where(
            HistoricoRota.id == viagem_id, HistoricoRota.motorista_id == m.id
        )
    )
    if viagem is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Viagem não encontrada")
    return viagem


@router.get("/motorista/viagens/{viagem_id}/presencas", response_model=PresencasOut)
def checklist(
    viagem_id: int, db: Session = Depends(get_db), user: Usuario = Depends(motorista_only)
):
    return montar_presencas(db, _viagem_do_motorista(db, user, viagem_id))


@router.put(
    "/motorista/viagens/{viagem_id}/presencas/{aluno_id}", response_model=PresencaAlunoOut
)
def marcar(
    viagem_id: int,
    aluno_id: int,
    body: PresencaIn,
    db: Session = Depends(get_db),
    user: Usuario = Depends(motorista_only),
):
    viagem = _viagem_do_motorista(db, user, viagem_id)
    if viagem.status != StatusExecucao.EM_ANDAMENTO:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Viagem encerrada; não é possível alterar a presença"
        )
    na_rota = db.scalar(
        select(RotaAluno.id).where(RotaAluno.rota_id == viagem.rota_id, RotaAluno.aluno_id == aluno_id)
    )
    if na_rota is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Aluno não está nesta rota")
    presenca = db.scalar(
        select(PresencaViagem).where(
            PresencaViagem.historico_rota_id == viagem.id, PresencaViagem.aluno_id == aluno_id
        )
    )
    if presenca is None:
        presenca = PresencaViagem(
            historico_rota_id=viagem.id,
            aluno_id=aluno_id,
            status=body.status,
            observacao=body.observacao,
            registrado_por=user.id,
        )
        db.add(presenca)
    else:
        presenca.status = body.status
        presenca.observacao = body.observacao
        presenca.registrado_por = user.id
    db.commit()
    for item in montar_presencas(db, viagem)["alunos"]:
        if item["aluno_id"] == aluno_id:
            return item
    raise HTTPException(status.HTTP_404_NOT_FOUND, "Aluno não está nesta rota")


@router.delete(
    "/motorista/viagens/{viagem_id}/presencas/{aluno_id}", status_code=status.HTTP_204_NO_CONTENT
)
def desfazer(
    viagem_id: int,
    aluno_id: int,
    db: Session = Depends(get_db),
    user: Usuario = Depends(motorista_only),
):
    viagem = _viagem_do_motorista(db, user, viagem_id)
    if viagem.status != StatusExecucao.EM_ANDAMENTO:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Viagem encerrada; não é possível alterar a presença"
        )
    presenca = db.scalar(
        select(PresencaViagem).where(
            PresencaViagem.historico_rota_id == viagem.id, PresencaViagem.aluno_id == aluno_id
        )
    )
    if presenca is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Presença não registrada")
    db.delete(presenca)
    db.commit()


@router.get("/viagens/{viagem_id}/presencas", response_model=PresencasOut)
def presencas_admin(
    viagem_id: int, db: Session = Depends(get_db), user: Usuario = Depends(admin_only)
):
    viagem = db.scalar(
        select(HistoricoRota)
        .join(Rota, Rota.id == HistoricoRota.rota_id)
        .where(HistoricoRota.id == viagem_id, Rota.empresa_id == user.empresa_id)
    )
    if viagem is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Viagem não encontrada")
    return montar_presencas(db, viagem)