import hashlib
import secrets
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import settings

_hasher = PasswordHasher()


def hash_senha(senha: str) -> str:
    return _hasher.hash(senha)


def verificar_senha(senha_hash: str, senha: str) -> bool:
    try:
        return _hasher.verify(senha_hash, senha)
    except (VerificationError, InvalidHashError):
        return False


def criar_access_token(usuario_id: int, perfil: str) -> str:
    exp = datetime.now(UTC) + timedelta(minutes=settings.jwt_access_minutes)
    payload = {"sub": str(usuario_id), "role": perfil, "type": "access", "exp": exp}
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decodificar_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])


def novo_refresh_token() -> tuple[str, str, datetime]:
    token = secrets.token_urlsafe(48)
    expira = datetime.now(UTC) + timedelta(days=settings.jwt_refresh_days)
    return token, hash_token(token), expira


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
