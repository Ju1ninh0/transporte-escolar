"""Validação criptográfica de tokens emitidos pelo Supabase Auth.

O Supabase é responsável SOMENTE pela identidade: este módulo prova que o token é legítimo e
devolve o UUID do usuário (`sub`). Perfil, empresa, ativo etc. vêm do PostgreSQL do sistema.
"""
import logging
import uuid

import jwt
from jwt import PyJWKClient
from jwt.exceptions import PyJWKClientConnectionError

from app.core.auth_errors import ErroAutenticacao
from app.core.config import settings

logger = logging.getLogger(__name__)

_AUDIENCIA = "authenticated"
_clientes_jwks: dict[str, PyJWKClient] = {}


def _base_url() -> str:
    return settings.supabase_url.strip().rstrip("/")


def emissor_esperado() -> str:
    base = _base_url()
    if not base:
        logger.error("SUPABASE_URL não está configurada no backend: não dá para validar tokens.")
        raise ErroAutenticacao(
            503, "auth_nao_configurada", "O servidor de autenticação não está configurado."
        )
    return f"{base}/auth/v1"


def _cliente_jwks() -> PyJWKClient:
    url = f"{emissor_esperado()}/.well-known/jwks.json"
    if url not in _clientes_jwks:
        _clientes_jwks[url] = PyJWKClient(url, cache_keys=True, lifespan=3600, timeout=5)
    return _clientes_jwks[url]


def token_parece_do_supabase(payload_sem_verificar: dict) -> bool:
    """Apenas ROTEIA o token (Supabase x legado) olhando o `iss`. Não autentica nada:
    quem aceita ou recusa o token é `validar_token_supabase`, que verifica a assinatura."""
    return str(payload_sem_verificar.get("iss", "")).endswith("/auth/v1")


def validar_token_supabase(token: str) -> str:
    """Valida assinatura, emissor, audiência, expiração e `sub`. Devolve o UUID (minúsculo)."""
    emissor = emissor_esperado()
    try:
        algoritmo = jwt.get_unverified_header(token).get("alg")
        if algoritmo == "HS256":  # projetos com o segredo legado do Supabase
            if not settings.supabase_jwt_secret:
                logger.error(
                    "Token HS256 recebido, mas SUPABASE_JWT_SECRET não está configurado no backend."
                )
                raise ErroAutenticacao(
                    503, "auth_nao_configurada", "O servidor de autenticação não está configurado."
                )
            chave, algoritmos = settings.supabase_jwt_secret, ["HS256"]
        elif algoritmo in ("ES256", "RS256"):  # JWT Signing Keys: chave pública via JWKS
            chave = _cliente_jwks().get_signing_key_from_jwt(token).key
            algoritmos = [algoritmo]
        else:
            raise jwt.InvalidAlgorithmError("algoritmo não aceito")

        payload = jwt.decode(
            token,
            chave,
            algorithms=algoritmos,
            audience=_AUDIENCIA,
            issuer=emissor,
            options={"require": ["exp", "sub", "aud", "iss"]},
        )
    except ErroAutenticacao:
        raise
    except jwt.ExpiredSignatureError:
        raise ErroAutenticacao(
            401, "token_expirado", "Sua sessão expirou. Entre novamente para continuar."
        ) from None
    except PyJWKClientConnectionError as exc:
        logger.error("Não consegui buscar o JWKS do Supabase: %s", exc)
        raise ErroAutenticacao(
            503,
            "auth_indisponivel",
            "Não foi possível validar o seu acesso agora. Tente novamente em instantes.",
        ) from None
    except jwt.PyJWTError as exc:
        logger.warning("Token do Supabase recusado: %s", exc)
        raise ErroAutenticacao(
            401, "token_invalido", "Sessão inválida. Entre novamente para continuar."
        ) from None

    try:
        return str(uuid.UUID(str(payload["sub"])))
    except ValueError:
        logger.warning("Token do Supabase com `sub` que não é UUID")
        raise ErroAutenticacao(
            401, "token_invalido", "Sessão inválida. Entre novamente para continuar."
        ) from None