"""Autenticação: Supabase prova QUEM é (token + UUID `sub`); o PostgreSQL local diz O QUE a pessoa é
(`usuarios.auth_user_id` -> perfil, empresa, ativo). Nada enviado pelo cliente decide a identidade."""
import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from jwt.exceptions import PyJWKClientConnectionError
from sqlalchemy import select

from app.core import supabase_auth
from app.core.config import settings
from app.core.security import hash_senha
from app.models import AuditLog, Perfil, Usuario
from app.scripts.vincular_auth_user import ErroVinculo, listar, vincular
from tests.conftest import SENHA

SEGREDO = "segredo-supabase-de-teste-com-tamanho-ok"
URL = "https://projeto.supabase.co"
ID_ADMIN = "11111111-1111-1111-1111-111111111111"
ID_RESP = "22222222-2222-2222-2222-222222222222"
ID_MOTORISTA = "44444444-4444-4444-4444-444444444444"
ID_DESCONHECIDO = "99999999-9999-9999-9999-999999999999"
DASHBOARD = "/api/v1/dashboard"  # somente ADMIN


@pytest.fixture(autouse=True)
def config_supabase(monkeypatch):
    monkeypatch.setattr(settings, "supabase_url", URL)
    monkeypatch.setattr(settings, "supabase_jwt_secret", SEGREDO)


@pytest.fixture()
def contas(db, dados):
    """Cadastros do PostgreSQL já vinculados ao UUID do Supabase (estado normal do sistema)."""
    admin = db.scalar(select(Usuario).where(Usuario.email == "admin@t.com"))
    resp = db.scalar(select(Usuario).where(Usuario.email == "a@t.com"))
    motorista = Usuario(
        empresa_id=admin.empresa_id, nome="Mot", email="mot@t.com",
        senha_hash=hash_senha(SENHA), perfil=Perfil.MOTORISTA,
    )
    db.add(motorista)
    admin.auth_user_id, resp.auth_user_id, motorista.auth_user_id = ID_ADMIN, ID_RESP, ID_MOTORISTA
    db.commit()
    return {"admin": admin, "resp": resp, "motorista": motorista}


def _token(sub=ID_ADMIN, segredo=SEGREDO, **extra):
    payload = {
        "sub": sub, "aud": "authenticated", "iss": f"{URL}/auth/v1",
        "exp": int(time.time()) + 600, **extra,
    }
    return jwt.encode(payload, segredo, algorithm="HS256")


def _h(token):
    return {"Authorization": f"Bearer {token}"}


def _me(client, token):
    return client.get("/api/v1/auth/me", headers=_h(token))


def _codigo(resposta):
    return resposta.json()["detail"]["code"]


# 1. token válido + auth_user_id correto -> 200
def test_token_valido_com_auth_user_id_correto(client, contas):
    r = _me(client, _token(ID_ADMIN))
    assert r.status_code == 200
    assert r.json()["email"] == "admin@t.com"
    assert r.json()["empresa_id"] == contas["admin"].empresa_id


# 2. token inválido -> 401
def test_assinatura_invalida_401(client, contas):
    r = _me(client, _token(segredo="segredo-errado-com-tamanho-suficiente-ok"))
    assert r.status_code == 401
    assert _codigo(r) == "token_invalido"
    assert r.headers["www-authenticate"] == "Bearer"


def test_lixo_no_lugar_do_token_401(client, contas):
    assert _me(client, "isto-nao-e-um-jwt").status_code == 401


def test_sem_token_401(client, contas):
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 401
    assert _codigo(r) == "nao_autenticado"


def test_audiencia_errada_401(client, contas):
    assert _me(client, _token(aud="anon")).status_code == 401


def test_emissor_errado_401(client, contas):
    # parece Supabase (termina em /auth/v1), mas é de outro projeto
    assert _me(client, _token(iss="https://outro.supabase.co/auth/v1")).status_code == 401


def test_sub_que_nao_e_uuid_401(client, contas):
    assert _me(client, _token(sub="1")).status_code == 401


def test_algoritmo_none_401(client, contas):
    sem_assinatura = jwt.encode(
        {"sub": ID_ADMIN, "aud": "authenticated", "iss": f"{URL}/auth/v1", "exp": int(time.time()) + 600},
        None, algorithm="none",
    )
    assert _me(client, sem_assinatura).status_code == 401


# 3. token expirado -> 401
def test_token_expirado_401(client, contas):
    r = _me(client, _token(exp=int(time.time()) - 10))
    assert r.status_code == 401
    assert _codigo(r) == "token_expirado"


# 4. usuário autenticado no Supabase mas sem cadastro -> 403 específico (não 401)
def test_usuario_sem_cadastro_403_especifico(client, contas):
    r = _me(client, _token(ID_DESCONHECIDO))
    assert r.status_code == 403
    assert _codigo(r) == "usuario_nao_cadastrado"


# 5/6/7. o perfil vem do PostgreSQL
@pytest.mark.parametrize(
    "auth_id,perfil",
    [(ID_ADMIN, "ADMIN"), (ID_MOTORISTA, "MOTORISTA"), (ID_RESP, "RESPONSAVEL")],
)
def test_perfil_vem_do_postgres(client, contas, auth_id, perfil):
    r = _me(client, _token(auth_id))
    assert r.status_code == 200
    assert r.json()["perfil"] == perfil


def test_claims_enviadas_pelo_cliente_nao_mudam_identidade_nem_perfil(client, contas):
    token = _token(
        ID_RESP, email="admin@t.com", role="service_role",
        user_metadata={"perfil": "ADMIN", "email": "admin@t.com", "usuario_id": 1},
        app_metadata={"perfil": "ADMIN", "role": "ADMIN"}, perfil="ADMIN", usuario_id=1,
    )
    r = _me(client, token)
    assert r.status_code == 200
    assert r.json()["perfil"] == "RESPONSAVEL"
    assert r.json()["email"] == "a@t.com"
    assert client.get(DASHBOARD, headers=_h(token)).status_code == 403


def test_responsavel_nao_acessa_rota_de_admin_403(client, contas):
    r = client.get(DASHBOARD, headers=_h(_token(ID_RESP)))
    assert r.status_code == 403
    assert _codigo(r) == "sem_permissao"


def test_admin_acessa_rota_de_admin(client, contas):
    assert client.get(DASHBOARD, headers=_h(_token(ID_ADMIN))).status_code == 200


# 8. usuário inativo é bloqueado
def test_usuario_inativo_bloqueado(client, db, contas):
    contas["admin"].ativo = False
    db.commit()
    r = _me(client, _token(ID_ADMIN))
    assert r.status_code == 403
    assert _codigo(r) == "usuario_inativo"


# 9. UUID diferente não assume outro cadastro
def test_uuid_diferente_nao_assume_cadastro_de_outro(client, db, contas):
    r = _me(client, _token(ID_DESCONHECIDO, email="admin@t.com"))
    assert r.status_code == 403
    db.refresh(contas["admin"])
    assert contas["admin"].auth_user_id == ID_ADMIN


def test_nao_ha_vinculo_automatico_por_email(client, db, dados):
    # cadastro existe, e-mail igual ao do token, mas auth_user_id ainda é NULL
    r = _me(client, _token(ID_DESCONHECIDO, email="admin@t.com", user_metadata={"email_verified": True}))
    assert r.status_code == 403
    assert _codigo(r) == "usuario_nao_cadastrado"
    admin = db.scalar(select(Usuario).where(Usuario.email == "admin@t.com"))
    assert admin.auth_user_id is None


# configuração e infraestrutura -> 5xx apropriado, nunca um 401 enganoso
def test_sem_supabase_url_503(client, contas, monkeypatch):
    monkeypatch.setattr(settings, "supabase_url", "")
    r = _me(client, _token())
    assert r.status_code == 503
    assert _codigo(r) == "auth_nao_configurada"


def test_hs256_sem_segredo_configurado_503(client, contas, monkeypatch):
    monkeypatch.setattr(settings, "supabase_jwt_secret", "")
    assert _me(client, _token()).status_code == 503


# ES256 via JWKS (projetos com JWT Signing Keys)
class _ChaveJwks:
    def __init__(self, chave):
        self.key = chave


class _ClienteJwksFalso:
    def __init__(self, publica=None, erro=None):
        self._publica, self._erro = publica, erro

    def get_signing_key_from_jwt(self, token):
        if self._erro:
            raise self._erro
        return _ChaveJwks(self._publica)


def _par_es256():
    privada = ec.generate_private_key(ec.SECP256R1())
    pem = privada.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    )
    return pem, privada.public_key()


def _token_es256(pem, sub=ID_ADMIN):
    payload = {"sub": sub, "aud": "authenticated", "iss": f"{URL}/auth/v1", "exp": int(time.time()) + 600}
    return jwt.encode(payload, pem, algorithm="ES256", headers={"kid": "chave-1"})


def test_es256_com_jwks_valido_200(client, contas, monkeypatch):
    pem, publica = _par_es256()
    monkeypatch.setattr(supabase_auth, "_cliente_jwks", lambda: _ClienteJwksFalso(publica))
    assert _me(client, _token_es256(pem)).status_code == 200


def test_es256_assinado_por_outra_chave_401(client, contas, monkeypatch):
    pem_atacante, _ = _par_es256()
    _, publica_real = _par_es256()
    monkeypatch.setattr(supabase_auth, "_cliente_jwks", lambda: _ClienteJwksFalso(publica_real))
    assert _me(client, _token_es256(pem_atacante)).status_code == 401


def test_jwks_fora_do_ar_503(client, contas, monkeypatch):
    pem, _ = _par_es256()
    falso = _ClienteJwksFalso(erro=PyJWKClientConnectionError("sem rede"))
    monkeypatch.setattr(supabase_auth, "_cliente_jwks", lambda: falso)
    r = _me(client, _token_es256(pem))
    assert r.status_code == 503
    assert _codigo(r) == "auth_indisponivel"


# o token emitido pelo próprio backend (testes/scripts) segue funcionando
def test_token_do_backend_continua_funcionando(client, dados, login):
    assert client.get("/api/v1/auth/me", headers=login("admin@t.com")).status_code == 200


# script administrativo de vínculo
def test_script_vincula_usuario_existente_e_audita(db, dados):
    msg = vincular(db, "ADMIN@t.com", ID_ADMIN.upper())
    assert "vinculado" in msg
    admin = db.scalar(select(Usuario).where(Usuario.email == "admin@t.com"))
    assert admin.auth_user_id == ID_ADMIN
    assert db.scalar(select(AuditLog).where(AuditLog.acao == "vincular_auth_user_id")) is not None


def test_script_dry_run_nao_grava(db, dados):
    assert "dry-run" in vincular(db, "admin@t.com", ID_ADMIN, dry_run=True)
    assert db.scalar(select(Usuario).where(Usuario.email == "admin@t.com")).auth_user_id is None


def test_script_e_idempotente(db, dados):
    vincular(db, "admin@t.com", ID_ADMIN)
    assert "Nada a fazer" in vincular(db, "admin@t.com", ID_ADMIN)


def test_script_recusa_uuid_de_outro_cadastro(db, dados):
    vincular(db, "admin@t.com", ID_ADMIN)
    with pytest.raises(ErroVinculo, match="outro cadastro"):
        vincular(db, "a@t.com", ID_ADMIN, substituir=True)


def test_script_nao_troca_vinculo_existente_sem_substituir(db, dados):
    vincular(db, "admin@t.com", ID_ADMIN)
    with pytest.raises(ErroVinculo, match="--substituir"):
        vincular(db, "admin@t.com", ID_RESP)
    vincular(db, "admin@t.com", ID_RESP, substituir=True)
    assert db.scalar(select(Usuario).where(Usuario.email == "admin@t.com")).auth_user_id == ID_RESP


def test_script_nao_cria_usuario_e_valida_entrada(db, dados):
    with pytest.raises(ErroVinculo, match="Não existe"):
        vincular(db, "ninguem@t.com", ID_ADMIN)
    with pytest.raises(ErroVinculo, match="UUID válido"):
        vincular(db, "admin@t.com", "nao-e-uuid")
    assert db.scalar(select(Usuario).where(Usuario.email == "ninguem@t.com")) is None


def test_script_listar_mostra_quem_nao_tem_vinculo(db, dados):
    vincular(db, "admin@t.com", ID_ADMIN)
    saida = "\n".join(listar(db))
    assert ID_ADMIN in saida and "(sem vínculo)" in saida