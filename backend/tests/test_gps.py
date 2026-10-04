import asyncio
import queue
import threading

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from starlette.websockets import WebSocketDisconnect

from app.core.security import hash_senha
from app.main import app
from app.models import Empresa, Motorista, Perfil, Usuario
from app.services.gps import Assinante, Hub

SENHA = "senha-teste-123"
API = "/api/v1"
WS = f"{API}/ws/viagens"


# ---------------------------------------------------------------- fixtures
@pytest.fixture()
def cen(db, dados, login):
    emp = db.scalar(select(Empresa).where(Empresa.nome == "Teste"))

    def novo_usuario(empresa, email, perfil):
        u = Usuario(
            empresa_id=empresa.id,
            nome=email.split("@")[0],
            email=email,
            senha_hash=hash_senha(SENHA),
            perfil=perfil,
        )
        db.add(u)
        db.flush()
        return u

    m1 = Motorista(empresa_id=emp.id, usuario_id=novo_usuario(emp, "m1@t.com", Perfil.MOTORISTA).id)
    m2 = Motorista(empresa_id=emp.id, usuario_id=novo_usuario(emp, "m2@t.com", Perfil.MOTORISTA).id)
    emp2 = Empresa(nome="Outra")
    db.add(emp2)
    db.flush()
    novo_usuario(emp2, "admin2@o.com", Perfil.ADMIN)
    db.add_all([m1, m2])
    db.commit()
    return {
        "m1_id": m1.id,
        "filho_a": dados["filho_a"],
        "admin": login("admin@t.com"),
        "admin2": login("admin2@o.com"),
        "m1": login("m1@t.com"),
        "m2": login("m2@t.com"),
        "resp_a": login("a@t.com"),
        "resp_b": login("b@t.com"),
    }


@pytest.fixture()
def viagem(client, cen):
    """Rota com o Filho A (responsável A), viagem iniciada pelo m1."""
    a = cen["admin"]
    van = client.post(
        f"{API}/veiculos", headers=a, json={"placa": "ABC1D23", "apelido": "Van 1", "capacidade": 10}
    ).json()["id"]
    rota = client.post(
        f"{API}/rotas", headers=a, json={"nome": "Manhã", "veiculo_id": van, "motorista_id": cen["m1_id"]}
    ).json()["id"]
    client.post(f"{API}/rotas/{rota}/alunos", headers=a, json={"aluno_id": cen["filho_a"]})
    r = client.post(f"{API}/motorista/rotas/{rota}/viagem/iniciar", headers=cen["m1"])
    assert r.status_code == 201, r.text
    return {"id": r.json()["id"], "rota": rota}


def _enviar(client, headers, viagem_id, lat=-9.66, lng=-35.73, **extra):
    return client.post(
        f"{API}/motorista/viagens/{viagem_id}/localizacao",
        headers=headers,
        json={"latitude": lat, "longitude": lng, **extra},
    )


def _token(headers):
    return headers["Authorization"].split(" ", 1)[1]


# ------------------------------------------------------------ envio (HTTP)
@pytest.mark.parametrize("email", ["admin@t.com", "a@t.com"])
def test_nao_motorista_nao_envia_localizacao_403(client, cen, login, email):
    r = client.post(
        f"{API}/motorista/viagens/1/localizacao",
        headers=login(email),
        json={"latitude": 0, "longitude": 0},
    )
    assert r.status_code == 403


def test_sem_token_401(client):
    assert client.post(f"{API}/motorista/viagens/1/localizacao", json={}).status_code == 401
    assert client.get(f"{API}/viagens/ativas").status_code == 401
    assert client.get(f"{API}/viagens/1/trilha").status_code == 401


@pytest.mark.parametrize("email", ["m1@t.com", "a@t.com"])
def test_nao_admin_nao_ve_ativas_nem_trilha_403(client, cen, login, email):
    h = login(email)
    assert client.get(f"{API}/viagens/ativas", headers=h).status_code == 403
    assert client.get(f"{API}/viagens/1/trilha", headers=h).status_code == 403


def test_enviar_localizacao_ok(client, cen, viagem):
    r = _enviar(client, cen["m1"], viagem["id"], velocidade=8.5, direcao=90)
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["viagem_id"] == viagem["id"]
    assert (d["latitude"], d["longitude"]) == (-9.66, -35.73)
    assert d["velocidade"] == 8.5 and d["direcao"] == 90
    assert d["timestamp"]


@pytest.mark.parametrize(
    "extra",
    [{"lat": 91}, {"lat": -91}, {"lng": 181}, {"lng": -181}, {"velocidade": -1}, {"direcao": 361}],
)
def test_localizacao_invalida_422(client, cen, viagem, extra):
    assert _enviar(client, cen["m1"], viagem["id"], **extra).status_code == 422


def test_localizacao_de_viagem_encerrada_409(client, cen, viagem):
    client.post(f"{API}/motorista/viagens/{viagem['id']}/encerrar", headers=cen["m1"])
    assert _enviar(client, cen["m1"], viagem["id"]).status_code == 409


def test_outro_motorista_nao_envia_404(client, cen, viagem):
    assert _enviar(client, cen["m2"], viagem["id"]).status_code == 404
    assert _enviar(client, cen["m1"], 99999).status_code == 404


# ------------------------------------------------------------ admin (HTTP)
def test_ativas_mostra_ultima_posicao(client, cen, viagem):
    a = client.get(f"{API}/viagens/ativas", headers=cen["admin"]).json()
    assert len(a) == 1
    assert a[0]["viagem_id"] == viagem["id"] and a[0]["rota_nome"] == "Manhã"
    assert a[0]["veiculo_placa"] == "ABC1D23" and a[0]["motorista_nome"] == "m1"
    assert a[0]["posicao"] is None

    _enviar(client, cen["m1"], viagem["id"], lat=-9.60, lng=-35.70)
    _enviar(client, cen["m1"], viagem["id"], lat=-9.61, lng=-35.71)
    a = client.get(f"{API}/viagens/ativas", headers=cen["admin"]).json()
    assert (a[0]["posicao"]["latitude"], a[0]["posicao"]["longitude"]) == (-9.61, -35.71)


def test_ativas_nao_lista_viagem_encerrada(client, cen, viagem):
    client.post(f"{API}/motorista/viagens/{viagem['id']}/encerrar", headers=cen["m1"])
    assert client.get(f"{API}/viagens/ativas", headers=cen["admin"]).json() == []


def test_ativas_isolamento_entre_empresas(client, cen, viagem):
    assert client.get(f"{API}/viagens/ativas", headers=cen["admin2"]).json() == []


def test_trilha_em_ordem_e_com_limite(client, cen, viagem):
    for i in range(5):
        _enviar(client, cen["m1"], viagem["id"], lat=round(-9.0 - i / 100, 2), lng=-35.0)
    t = client.get(f"{API}/viagens/{viagem['id']}/trilha", headers=cen["admin"]).json()
    assert [p["latitude"] for p in t] == [-9.0, -9.01, -9.02, -9.03, -9.04]
    t = client.get(f"{API}/viagens/{viagem['id']}/trilha?limite=2", headers=cen["admin"]).json()
    assert [p["latitude"] for p in t] == [-9.03, -9.04]  # os 2 mais recentes, em ordem cronológica


def test_trilha_de_outra_empresa_404(client, cen, viagem):
    r = client.get(f"{API}/viagens/{viagem['id']}/trilha", headers=cen["admin2"])
    assert r.status_code == 404


# ---------------------------------------------------------------------- hub
class FakeWS:
    def __init__(self, falha=False):
        self.msgs = []
        self.falha = falha

    async def send_json(self, dados):
        if self.falha:
            raise RuntimeError("socket fechado")
        self.msgs.append(dados)


def test_hub_entrega_so_para_quem_pode_ver():
    from datetime import datetime

    hub = Hub()
    admin, resp_rota1, resp_rota2, outra_empresa = FakeWS(), FakeWS(), FakeWS(), FakeWS()
    hub.adicionar(Assinante(admin, 1, None))
    hub.adicionar(Assinante(resp_rota1, 1, {1}))
    hub.adicionar(Assinante(resp_rota2, 1, {2}))
    hub.adicionar(Assinante(outra_empresa, 2, None))

    asyncio.run(hub.publicar({"tipo": "localizacao", "timestamp": datetime(2026, 1, 1)}, 1, 1))

    assert len(admin.msgs) == 1 and len(resp_rota1.msgs) == 1
    assert resp_rota2.msgs == [] and outra_empresa.msgs == []
    assert isinstance(admin.msgs[0]["timestamp"], str)  # datetime virou texto JSON


def test_hub_remove_socket_com_falha_sem_afetar_os_outros():
    hub = Hub()
    ruim, bom = FakeWS(falha=True), FakeWS()
    hub.adicionar(Assinante(ruim, 1, None))
    hub.adicionar(Assinante(bom, 1, None))
    asyncio.run(hub.publicar({"tipo": "x"}, 1, 1))
    assert len(bom.msgs) == 1
    assert hub.total() == 1


# --------------------------------------------------------------- WebSocket
def test_ws_admin_recebe_snapshot(client, cen, viagem):
    _enviar(client, cen["m1"], viagem["id"], lat=-9.5, lng=-35.5)
    with client.websocket_connect(WS) as ws:
        ws.send_json({"token": _token(cen["admin"])})
        msg = ws.receive_json()
    assert msg["tipo"] == "snapshot"
    assert [v["viagem_id"] for v in msg["viagens"]] == [viagem["id"]]
    assert msg["viagens"][0]["posicao"]["latitude"] == -9.5


def test_ws_responsavel_so_ve_a_rota_do_proprio_filho(client, cen, viagem):
    with client.websocket_connect(WS) as ws:
        ws.send_json({"token": _token(cen["resp_a"])})
        assert [v["viagem_id"] for v in ws.receive_json()["viagens"]] == [viagem["id"]]
    with client.websocket_connect(WS) as ws:
        ws.send_json({"token": _token(cen["resp_b"])})
        assert ws.receive_json()["viagens"] == []


@pytest.mark.parametrize("mensagem", [{"token": "lixo"}, {"token": 123}, {}, {"outra": "coisa"}])
def test_ws_token_invalido_fecha_com_4401(client, cen, mensagem):
    with client.websocket_connect(WS) as ws:
        ws.send_json(mensagem)
        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_json()
    assert exc.value.code == 4401


def test_ws_refresh_token_nao_vale_4401(client, cen):
    r = client.post(f"{API}/auth/login", json={"email": "admin@t.com", "senha": SENHA})
    with client.websocket_connect(WS) as ws:
        ws.send_json({"token": r.json()["refresh_token"]})
        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_json()
    assert exc.value.code == 4401


def test_ws_motorista_nao_pode_4403(client, cen):
    with client.websocket_connect(WS) as ws:
        ws.send_json({"token": _token(cen["m1"])})
        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_json()
    assert exc.value.code == 4403


def test_ws_responde_ping(client, cen):
    with client.websocket_connect(WS) as ws:
        ws.send_json({"token": _token(cen["admin"])})
        assert ws.receive_json()["tipo"] == "snapshot"
        ws.send_text("ping")
        assert ws.receive_json() == {"tipo": "pong"}


def _receber(ws, segundos=5):
    """receive_json com limite de tempo, para o teste falhar em vez de travar."""
    fila: queue.Queue = queue.Queue()

    def alvo():
        try:
            fila.put(("ok", ws.receive_json()))
        except Exception as e:  # noqa: BLE001
            fila.put(("erro", e))

    threading.Thread(target=alvo, daemon=True).start()
    try:
        tipo, valor = fila.get(timeout=segundos)
    except queue.Empty:
        pytest.fail("O evento do WebSocket não chegou a tempo")
    if tipo == "erro":
        raise valor
    return valor


def test_ws_recebe_localizacao_em_tempo_real(cen, viagem):
    # TestClient dentro de "with" compartilha o mesmo event loop entre HTTP e WebSocket,
    # como acontece no servidor de verdade.
    with TestClient(app) as c:
        with c.websocket_connect(WS) as ws:
            ws.send_json({"token": _token(cen["admin"])})
            assert _receber(ws)["tipo"] == "snapshot"
            r = c.post(
                f"{API}/motorista/viagens/{viagem['id']}/localizacao",
                headers=cen["m1"],
                json={"latitude": -9.6, "longitude": -35.7, "velocidade": 5},
            )
            assert r.status_code == 201, r.text
            ev = _receber(ws)
    assert ev["tipo"] == "localizacao"
    assert ev["viagem_id"] == viagem["id"] and ev["rota_id"] == viagem["rota"]
    assert (ev["latitude"], ev["longitude"], ev["velocidade"]) == (-9.6, -35.7, 5)
    assert isinstance(ev["timestamp"], str)


def test_ws_responsavel_de_outra_rota_nao_recebe_evento(cen, viagem):
    with TestClient(app) as c:
        with c.websocket_connect(WS) as ws_b, c.websocket_connect(WS) as ws_a:
            ws_b.send_json({"token": _token(cen["resp_b"])})
            ws_a.send_json({"token": _token(cen["resp_a"])})
            assert _receber(ws_b)["tipo"] == "snapshot"
            assert _receber(ws_a)["tipo"] == "snapshot"
            c.post(
                f"{API}/motorista/viagens/{viagem['id']}/localizacao",
                headers=cen["m1"],
                json={"latitude": -9.6, "longitude": -35.7},
            )
            assert _receber(ws_a)["tipo"] == "localizacao"  # responsável do Filho A recebe
            # o responsável B não deve receber nada: o próximo "ping" é respondido antes de qualquer evento
            ws_b.send_text("ping")
            assert _receber(ws_b) == {"tipo": "pong"}