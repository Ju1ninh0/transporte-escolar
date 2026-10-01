from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import admin_only
from app.db.session import get_db
from app.models import Perfil, Responsavel, Usuario
from app.schemas.pessoas import ResponsavelCreate, ResponsavelOut
from app.services.usuarios import criar_usuario

router = APIRouter(prefix="/responsaveis", tags=["responsaveis"])


def _out(resp: Responsavel, user: Usuario) -> dict:
    return {
        "id": resp.id,
        "usuario_id": user.id,
        "nome": user.nome,
        "email": user.email,
        "telefone": user.telefone,
        "endereco": resp.endereco,
    }


@router.post("", response_model=ResponsavelOut, status_code=status.HTTP_201_CREATED)
def criar(
    dados: ResponsavelCreate,
    admin: Usuario = Depends(admin_only),
    db: Session = Depends(get_db),
):
    user = criar_usuario(
        db, admin.empresa_id, dados.nome, dados.email, dados.telefone, dados.senha,
        Perfil.RESPONSAVEL,
    )
    resp = Responsavel(empresa_id=admin.empresa_id, usuario_id=user.id, endereco=dados.endereco)
    db.add(resp)
    db.commit()
    db.refresh(resp)
    return _out(resp, user)


@router.get("", response_model=list[ResponsavelOut])
def listar(admin: Usuario = Depends(admin_only), db: Session = Depends(get_db)):
    stmt = (
        select(Responsavel, Usuario)
        .join(Usuario, Usuario.id == Responsavel.usuario_id)
        .where(Responsavel.empresa_id == admin.empresa_id)
    )
    return [_out(resp, user) for resp, user in db.execute(stmt).all()]