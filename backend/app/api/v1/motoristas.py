from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import admin_only
from app.db.session import get_db
from app.models import Motorista, Perfil, Usuario
from app.schemas.pessoas import MotoristaOut, PessoaCreate
from app.services.usuarios import criar_usuario

router = APIRouter(prefix="/motoristas", tags=["motoristas"])


@router.post("", response_model=MotoristaOut, status_code=status.HTTP_201_CREATED)
def criar(dados: PessoaCreate, admin: Usuario = Depends(admin_only), db: Session = Depends(get_db)):
    user = criar_usuario(
        db, admin.empresa_id, dados.nome, dados.email, dados.telefone, dados.senha,
        Perfil.MOTORISTA,
    )
    mot = Motorista(empresa_id=admin.empresa_id, usuario_id=user.id)
    db.add(mot)
    db.commit()
    return mot


@router.get("", response_model=list[MotoristaOut])
def listar(admin: Usuario = Depends(admin_only), db: Session = Depends(get_db)):
    return db.scalars(select(Motorista).where(Motorista.empresa_id == admin.empresa_id)).all()
