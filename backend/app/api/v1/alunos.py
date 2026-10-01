from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import admin_only, get_current_user
from app.db.session import get_db
from app.models import Aluno, Responsavel, Usuario
from app.schemas.pessoas import AlunoCreate, AlunoOut, AlunoUpdate
from app.services.alunos import alunos_visiveis

router = APIRouter(prefix="/alunos", tags=["alunos"])


def _obter(db: Session, user: Usuario, aluno_id: int) -> Aluno:
    aluno = db.scalars(alunos_visiveis(user).where(Aluno.id == aluno_id)).first()
    if aluno is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Aluno não encontrado")
    return aluno


def _validar_responsavel(db: Session, admin: Usuario, responsavel_id: int) -> None:
    resp = db.get(Responsavel, responsavel_id)
    if resp is None or resp.empresa_id != admin.empresa_id:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Responsável inválido")


@router.get("", response_model=list[AlunoOut])
def listar(user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.scalars(alunos_visiveis(user).where(Aluno.ativo.is_(True))).all()


@router.get("/{aluno_id}", response_model=AlunoOut)
def detalhar(aluno_id: int, user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    return _obter(db, user, aluno_id)


@router.post("", response_model=AlunoOut, status_code=status.HTTP_201_CREATED)
def criar(dados: AlunoCreate, admin: Usuario = Depends(admin_only), db: Session = Depends(get_db)):
    _validar_responsavel(db, admin, dados.responsavel_id)
    aluno = Aluno(empresa_id=admin.empresa_id, **dados.model_dump())
    db.add(aluno)
    db.commit()
    return aluno


@router.patch("/{aluno_id}", response_model=AlunoOut)
def atualizar(aluno_id: int, dados: AlunoUpdate, admin: Usuario = Depends(admin_only), db: Session = Depends(get_db)):
    aluno = _obter(db, admin, aluno_id)
    campos = dados.model_dump(exclude_unset=True)
    if "responsavel_id" in campos:
        _validar_responsavel(db, admin, campos["responsavel_id"])
    for k, v in campos.items():
        setattr(aluno, k, v)
    db.commit()
    return aluno


@router.delete("/{aluno_id}", status_code=status.HTTP_204_NO_CONTENT)
def desativar(aluno_id: int, admin: Usuario = Depends(admin_only), db: Session = Depends(get_db)):
    _obter(db, admin, aluno_id).ativo = False
    db.commit()
