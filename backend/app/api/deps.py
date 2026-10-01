import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decodificar_token
from app.db.session import get_db
from app.models import Perfil, Usuario

_bearer = HTTPBearer(auto_error=False)
_401 = HTTPException(status.HTTP_401_UNAUTHORIZED, "Não autenticado")


def get_current_user(
    cred: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> Usuario:
    if cred is None:
        raise _401
    try:
        payload = decodificar_token(cred.credentials)
    except jwt.PyJWTError:
        raise _401 from None
    if payload.get("type") != "access":
        raise _401
    user = db.get(Usuario, int(payload["sub"]))
    if user is None or not user.ativo:
        raise _401
    return user


def require_role(*perfis: Perfil):
    def checker(user: Usuario = Depends(get_current_user)) -> Usuario:
        if user.perfil not in perfis:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Sem permissão")
        return user

    return checker


admin_only = require_role(Perfil.ADMIN)
