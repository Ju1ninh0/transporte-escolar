from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_senha
from app.models import Perfil, Usuario


def criar_usuario(
    db: Session, empresa_id: int, nome: str, email: str, telefone: str | None,
    senha: str, perfil: Perfil,
) -> Usuario:
    email = email.lower()
    if db.scalar(select(Usuario.id).where(Usuario.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "E-mail já cadastrado")
    user = Usuario(
        empresa_id=empresa_id, nome=nome, email=email, telefone=telefone,
        senha_hash=hash_senha(senha), perfil=perfil,
    )
    db.add(user)
    db.flush()
    return user
