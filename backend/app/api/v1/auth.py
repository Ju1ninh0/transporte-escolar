from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import (
    criar_access_token,
    hash_token,
    novo_refresh_token,
    verificar_senha,
)
from app.db.session import get_db
from app.models import AuditLog, RefreshToken, Usuario
from app.schemas.auth import LoginIn, RefreshIn, TokenOut, UsuarioOut

router = APIRouter(prefix="/auth", tags=["auth"])


def _emitir(db: Session, user: Usuario) -> TokenOut:
    token, token_hash, expira = novo_refresh_token()
    db.add(RefreshToken(usuario_id=user.id, token_hash=token_hash, expira_em=expira))
    db.commit()
    return TokenOut(
        access_token=criar_access_token(user.id, user.perfil.value), refresh_token=token
    )


@router.post("/login", response_model=TokenOut)
def login(dados: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(Usuario).where(Usuario.email == dados.email.lower()))
    if not user or not user.ativo or not verificar_senha(user.senha_hash, dados.senha):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciais inválidas")
    db.add(AuditLog(usuario_id=user.id, acao="login"))
    return _emitir(db, user)


@router.post("/refresh", response_model=TokenOut)
def refresh(dados: RefreshIn, db: Session = Depends(get_db)):
    rt = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(dados.refresh_token)))
    if rt is None or rt.revogado:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token inválido")
    expira = rt.expira_em if rt.expira_em.tzinfo else rt.expira_em.replace(tzinfo=UTC)
    user = db.get(Usuario, rt.usuario_id)
    if expira < datetime.now(UTC) or user is None or not user.ativo:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token inválido")
    rt.revogado = True
    return _emitir(db, user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(dados: RefreshIn, db: Session = Depends(get_db)):
    rt = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(dados.refresh_token)))
    if rt:
        rt.revogado = True
        db.commit()


@router.get("/me", response_model=UsuarioOut)
def me(user: Usuario = Depends(get_current_user)):
    return user
