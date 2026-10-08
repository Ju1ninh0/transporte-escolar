import logging

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth_errors import ErroAutenticacao
from app.core.security import decodificar_token
from app.core.supabase_auth import token_parece_do_supabase, validar_token_supabase
from app.db.session import get_db
from app.models import Perfil, Usuario

logger = logging.getLogger(__name__)
_bearer = HTTPBearer(auto_error=False)


def _http(erro: ErroAutenticacao) -> HTTPException:
    return HTTPException(
        erro.status_code,
        detail={"code": erro.code, "message": erro.message},
        headers={"WWW-Authenticate": "Bearer"} if erro.status_code == 401 else None,
    )


def _nao_autenticado() -> ErroAutenticacao:
    return ErroAutenticacao(
        401, "nao_autenticado", "Você não está autenticado. Entre para continuar."
    )


def _token_invalido() -> ErroAutenticacao:
    return ErroAutenticacao(
        401, "token_invalido", "Sessão inválida. Entre novamente para continuar."
    )


def _usuario_legado(db: Session, token: str) -> Usuario:
    """Token emitido pelo próprio backend (POST /auth/login). Não é usado pelo frontend, que
    autentica pelo Supabase; segue disponível para a suíte de testes e scripts internos."""
    try:
        payload = decodificar_token(token)
    except jwt.ExpiredSignatureError:
        raise ErroAutenticacao(
            401, "token_expirado", "Sua sessão expirou. Entre novamente para continuar."
        ) from None
    except jwt.PyJWTError:
        raise _token_invalido() from None
    if payload.get("type") != "access":
        raise _token_invalido()
    user = db.get(Usuario, int(payload["sub"]))
    if user is None or not user.ativo:
        raise _token_invalido()
    return user


def _usuario_supabase(db: Session, token: str) -> Usuario:
    """Identidade = UUID (`sub`) do token já validado criptograficamente. O cadastro vem
    EXCLUSIVAMENTE do PostgreSQL local (`usuarios.auth_user_id`). Nada que o cliente envie
    (e-mail, perfil, usuario_id, claims de metadata) é usado para decidir quem é o usuário.

    Não existe vínculo automático por e-mail aqui: o primeiro vínculo de um usuário já existente
    é feito de forma explícita e auditada por `python -m app.scripts.vincular_auth_user`."""
    auth_id = validar_token_supabase(token)
    user = db.scalar(select(Usuario).where(Usuario.auth_user_id == auth_id))
    if user is None:
        logger.warning(
            "Token Supabase válido (sub=%s) sem cadastro em usuarios.auth_user_id", auth_id
        )
        raise ErroAutenticacao(
            403,
            "usuario_nao_cadastrado",
            "Sua conta de acesso existe, mas ainda não está vinculada a um cadastro do sistema. "
            "Fale com a administração.",
        )
    if not user.ativo:
        raise ErroAutenticacao(
            403, "usuario_inativo", "O seu cadastro está inativo. Fale com a administração."
        )
    return user


def resolver_usuario(db: Session, token: object) -> Usuario:
    """Token Bearer -> Usuario do PostgreSQL. Levanta ErroAutenticacao com o motivo exato."""
    if not isinstance(token, str) or not token:
        raise _nao_autenticado()
    try:
        # Sem verificar assinatura: serve só para decidir qual validador usar (veja
        # token_parece_do_supabase). A confiança vem da validação feita depois.
        bruto = jwt.decode(token, options={"verify_signature": False})
    except jwt.PyJWTError:
        raise _token_invalido() from None
    if token_parece_do_supabase(bruto):
        return _usuario_supabase(db, token)
    return _usuario_legado(db, token)


def usuario_do_token(db: Session, token: object) -> Usuario | None:
    """Versão sem exceção, para o WebSocket (que responde com código de fechamento)."""
    try:
        return resolver_usuario(db, token)
    except ErroAutenticacao:
        return None


def get_current_user(
    cred: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> Usuario:
    if cred is None:
        raise _http(_nao_autenticado())
    try:
        return resolver_usuario(db, cred.credentials)
    except ErroAutenticacao as erro:
        raise _http(erro) from None


def require_role(*perfis: Perfil):
    def checker(user: Usuario = Depends(get_current_user)) -> Usuario:
        if user.perfil not in perfis:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "sem_permissao",
                    "message": "Você não tem permissão para acessar este recurso.",
                },
            )
        return user

    return checker


admin_only = require_role(Perfil.ADMIN)