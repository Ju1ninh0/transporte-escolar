from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import admin_only
from app.db.session import get_db
from app.models import Aluno, Parada, RotaAluno, Usuario, Veiculo
from app.schemas.frota import RotaAlunoCreate, RotaAlunoOut, RotaAlunoUpdate
from app.services.frota import alunos_da_rota, obter_rota, total_alunos

router = APIRouter(prefix="/rotas/{rota_id}/alunos", tags=["rota-alunos"])


def _validar_parada(db: Session, rota_id: int, parada_id: int) -> None:
    existe = db.scalar(select(Parada.id).where(Parada.id == parada_id, Parada.rota_id == rota_id))
    if existe is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Parada não pertence a esta rota")


def _obter_vinculo(db: Session, rota_id: int, aluno_id: int) -> RotaAluno:
    vinculo = db.scalar(
        select(RotaAluno).where(RotaAluno.rota_id == rota_id, RotaAluno.aluno_id == aluno_id)
    )
    if vinculo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Aluno não está nesta rota")
    return vinculo


@router.get("", response_model=list[RotaAlunoOut])
def listar(rota_id: int, db: Session = Depends(get_db), user: Usuario = Depends(admin_only)):
    rota = obter_rota(db, user.empresa_id, rota_id)
    return alunos_da_rota(db, rota.id)


@router.post("", response_model=RotaAlunoOut, status_code=status.HTTP_201_CREATED)
def vincular(
    rota_id: int,
    body: RotaAlunoCreate,
    db: Session = Depends(get_db),
    user: Usuario = Depends(admin_only),
):
    rota = obter_rota(db, user.empresa_id, rota_id)
    aluno = db.scalar(
        select(Aluno).where(Aluno.id == body.aluno_id, Aluno.empresa_id == user.empresa_id)
    )
    if aluno is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Aluno não encontrado")
    if not aluno.ativo:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Aluno inativo")
    if body.parada_id is not None:
        _validar_parada(db, rota.id, body.parada_id)

    ja_vinculado = db.scalar(
        select(RotaAluno.id).where(RotaAluno.rota_id == rota.id, RotaAluno.aluno_id == aluno.id)
    )
    if ja_vinculado is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Aluno já está nesta rota")

    if rota.veiculo_id is not None:
        veiculo = db.get(Veiculo, rota.veiculo_id)
        if veiculo is not None and total_alunos(db, rota.id) + 1 > veiculo.capacidade:
            raise HTTPException(status.HTTP_409_CONFLICT, "Capacidade do veículo excedida")

    db.add(RotaAluno(rota_id=rota.id, aluno_id=aluno.id, parada_id=body.parada_id))
    db.commit()
    return alunos_da_rota(db, rota.id, aluno.id)[0]


@router.patch("/{aluno_id}", response_model=RotaAlunoOut)
def atualizar(
    rota_id: int,
    aluno_id: int,
    body: RotaAlunoUpdate,
    db: Session = Depends(get_db),
    user: Usuario = Depends(admin_only),
):
    rota = obter_rota(db, user.empresa_id, rota_id)
    vinculo = _obter_vinculo(db, rota.id, aluno_id)
    dados = body.model_dump(exclude_unset=True)
    if "parada_id" in dados:
        if dados["parada_id"] is not None:
            _validar_parada(db, rota.id, dados["parada_id"])
        vinculo.parada_id = dados["parada_id"]
        db.commit()
    return alunos_da_rota(db, rota.id, aluno_id)[0]


@router.delete("/{aluno_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover(
    rota_id: int,
    aluno_id: int,
    db: Session = Depends(get_db),
    user: Usuario = Depends(admin_only),
):
    rota = obter_rota(db, user.empresa_id, rota_id)
    db.delete(_obter_vinculo(db, rota.id, aluno_id))
    db.commit()