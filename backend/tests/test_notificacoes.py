import pytest
from sqlalchemy import select

from app.core.security import hash_senha
from app.models import Empresa, Motorista, Perfil, Usuario
from app.services.geo import distancia_metros

SENHA = "senha-teste-123"
API = "/api/v1"

# Parada P1 em (-9.6000, -35.7000); P2 em (-9.7000, -35.8000)
P1 = (-9.6000, -35.7000)
P2 = (-9.7000, -35.8000)


@pytest.fixture()
def cen(db, dados, login):
    emp = db.scalar(select(Empresa).where(Empresa.nome == "Teste"))
    u = Usuario(
        empresa_id=emp.id, nome="m1", email="m1@t.com", senha_hash=hash_senha(SENHA), perfil=Perfil.MOTORISTA
    )
    db.add(u)
    db.flush()
    m1 = Motorista(empresa_id=emp.id, usuario_id=u.id)
    db.add(m1)
    db.commit()
    return {
        "m1_id": m1.id,
        "filho_a": dados["filho_a"],
        "filho_b": dados["filho_b"],
        "admin": login("admin@t.com"),
        "m1": login("m1@t.com"),
        "ra": login("a@t.com"),
        "rb": login("b@t.com"),
    }


@pytest.fixture()
def rota(client, cen):
    """Filho A na parada P1 (resp. A) e Filho B na parada P2 (resp. B)."""
    a = cen["admin"]
    van = client.post(
        f"{API}/veiculos", headers=a, json={"placa": "ABC1D23", "apelido": "Van", "capacidade": 10}
    ).json()["id"]
    rid = client.post(
        f"{API}/rotas", headers=a, json={"nome": "Manhã", "veiculo_id": van, "motorista_id": cen["m1_id"]}
    ).json()["id"]
    p1 = client.post(
        f"{API}/rotas/{rid}/paradas", headers=a, json={"nome": "P1", "latitude": P1[0], "longitude": P1[1]}
    ).json()["id"]
    p2 = client.post(
        f"{API}/rotas/{rid}/paradas", headers=a, json={"nome": "P2", "latitude": P2[0], "longitude": P2[1]}
    ).json()["id"]
    client.post(f"{API}/rotas/{rid}/alunos", headers=a, json={"aluno_id": cen["filho_a"], "parada_id": p1})
    client.post(f"{API}/rotas/{rid}/alunos", headers=a, json={"aluno_id": cen["filho_b"], "parada_id": p2})
    return {"id": rid}


def _iniciar(client, cen, rota):
    r = client.post(f"{API}/motorista/rotas/{rota['id']}/viagem/iniciar", headers=cen["m1"])
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _gps(client, cen, viagem, lat, lng):
    r = client.post(
        f"{API}/motorista/viagens/{viagem}/localizacao",
        headers=cen["m1"],
        json={"latitude": lat, "longitude": lng},
    )
    assert r.status_code == 201, r.text


def _avisos(client, cen, quem, tipo=None):
    lista = client.get(f"{API}/responsavel/avisos", headers=cen[quem]).json()
    return [a for a in lista if tipo is None or a["tipo"] == tipo]


# ---------------------------------------------------------------- geografia
def test_distancia_haversine():
    assert distancia_metros(*P1, *P1) == 0
    d = distancia_metros(-9.0, -35.0, -10.0, -35.0)  # 1 grau de latitude
    assert 111_000 < d < 111_400
    assert 50 < distancia_metros(-9.6005, -35.7, *P1) < 60


# --------------------------------------------------------- início e fim
def test_iniciar_viagem_avisa_os_responsaveis_da_rota(client, cen, rota):
    _iniciar(client, cen, rota)
    a = _avisos(client, cen, "ra", "VIAGEM_INICIADA")
    assert len(a) == 1
    assert a[0]["titulo"] == "Viagem iniciada" and a[0]["lida"] is False
    assert "Manhã" in a[0]["mensagem"] and "Filho A" in a[0]["mensagem"]
    assert "Filho B" not in a[0]["mensagem"]
    b = _avisos(client, cen, "rb", "VIAGEM_INICIADA")
    assert len(b) == 1 and "Filho B" in b[0]["mensagem"]


def test_responsavel_com_dois_filhos_na_rota_recebe_um_aviso_so(client, cen, rota, db, dados):
    # move o Filho B para o mesmo responsável A
    from app.models import Aluno

    filho_b = db.get(Aluno, cen["filho_b"])
    filho_b.responsavel_id = db.get(Aluno, cen["filho_a"]).responsavel_id
    db.commit()
    _iniciar(client, cen, rota)
    a = _avisos(client, cen, "ra", "VIAGEM_INICIADA")
    assert len(a) == 1
    assert "Filho A" in a[0]["mensagem"] and "Filho B" in a[0]["mensagem"]


def test_encerrar_viagem_avisa(client, cen, rota):
    viagem = _iniciar(client, cen, rota)
    client.post(f"{API}/motorista/viagens/{viagem}/encerrar", headers=cen["m1"])
    for quem in ("ra", "rb"):
        fim = _avisos(client, cen, quem, "VIAGEM_ENCERRADA")
        assert len(fim) == 1 and fim[0]["titulo"] == "Viagem encerrada"


def test_admin_encerrando_tambem_avisa(client, cen, rota):
    viagem = _iniciar(client, cen, rota)
    client.post(f"{API}/viagens/{viagem}/encerrar", headers=cen["admin"])
    assert len(_avisos(client, cen, "ra", "VIAGEM_ENCERRADA")) == 1


def test_aluno_inativo_nao_gera_aviso(client, cen, rota, db):
    from app.models import Aluno

    db.get(Aluno, cen["filho_b"]).ativo = False
    db.commit()
    _iniciar(client, cen, rota)
    assert _avisos(client, cen, "rb") == []
    assert len(_avisos(client, cen, "ra")) == 1


# --------------------------------------------------------------- proximidade
def test_van_longe_nao_avisa(client, cen, rota):
    viagem = _iniciar(client, cen, rota)
    _gps(client, cen, viagem, -9.0, -35.0)
    assert _avisos(client, cen, "ra", "VAN_PROXIMA") == []
    assert _avisos(client, cen, "rb", "VAN_PROXIMA") == []


def test_van_perto_avisa_so_o_responsavel_da_parada(client, cen, rota):
    client.patch(f"{API}/configuracoes", headers=cen["admin"], json={"proximidade_metros": 200})
    viagem = _iniciar(client, cen, rota)
    _gps(client, cen, viagem, -9.6005, -35.7000)  # ~55 m da P1
    a = _avisos(client, cen, "ra", "VAN_PROXIMA")
    assert len(a) == 1
    assert a[0]["titulo"] == "Van se aproximando"
    assert '"P1"' in a[0]["mensagem"] and "Filho A" in a[0]["mensagem"] and "Manhã" in a[0]["mensagem"]
    assert _avisos(client, cen, "rb", "VAN_PROXIMA") == []


def test_aviso_de_proximidade_nao_repete_na_mesma_viagem(client, cen, rota):
    viagem = _iniciar(client, cen, rota)
    for lat in (-9.6005, -9.6003, -9.6001):
        _gps(client, cen, viagem, lat, -35.7000)
    assert len(_avisos(client, cen, "ra", "VAN_PROXIMA")) == 1


def test_cada_parada_avisa_a_sua_hora(client, cen, rota):
    viagem = _iniciar(client, cen, rota)
    _gps(client, cen, viagem, -9.6005, -35.7000)
    assert len(_avisos(client, cen, "ra", "VAN_PROXIMA")) == 1
    assert _avisos(client, cen, "rb", "VAN_PROXIMA") == []
    _gps(client, cen, viagem, -9.7005, -35.8000)  # agora perto da P2
    assert len(_avisos(client, cen, "rb", "VAN_PROXIMA")) == 1
    assert len(_avisos(client, cen, "ra", "VAN_PROXIMA")) == 1


def test_nova_viagem_pode_avisar_de_novo(client, cen, rota):
    primeira = _iniciar(client, cen, rota)
    _gps(client, cen, primeira, -9.6005, -35.7000)
    client.post(f"{API}/motorista/viagens/{primeira}/encerrar", headers=cen["m1"])
    segunda = _iniciar(client, cen, rota)
    _gps(client, cen, segunda, -9.6005, -35.7000)
    assert len(_avisos(client, cen, "ra", "VAN_PROXIMA")) == 2


def test_sem_configuracao_usa_300_metros(client, cen, rota):
    viagem = _iniciar(client, cen, rota)
    _gps(client, cen, viagem, -9.5960, -35.7000)  # ~445 m: fora do padrão
    assert _avisos(client, cen, "ra", "VAN_PROXIMA") == []
    _gps(client, cen, viagem, -9.59775, -35.7000)  # ~250 m: dentro do padrão
    assert len(_avisos(client, cen, "ra", "VAN_PROXIMA")) == 1


def test_distancia_configurada_e_respeitada(client, cen, rota):
    client.patch(f"{API}/configuracoes", headers=cen["admin"], json={"proximidade_metros": 100})
    viagem = _iniciar(client, cen, rota)
    _gps(client, cen, viagem, -9.59775, -35.7000)  # ~250 m: fora de 100 m
    assert _avisos(client, cen, "ra", "VAN_PROXIMA") == []
    _gps(client, cen, viagem, -9.6005, -35.7000)  # ~55 m: dentro
    assert len(_avisos(client, cen, "ra", "VAN_PROXIMA")) == 1


def test_parada_sem_alunos_nao_avisa(client, cen, rota):
    a = cen["admin"]
    client.post(
        f"{API}/rotas/{rota['id']}/paradas", headers=a, json={"nome": "Vazia", "latitude": -9.5, "longitude": -35.5}
    )
    viagem = _iniciar(client, cen, rota)
    _gps(client, cen, viagem, -9.5, -35.5)
    assert _avisos(client, cen, "ra", "VAN_PROXIMA") == []
    assert _avisos(client, cen, "rb", "VAN_PROXIMA") == []


def test_enviar_gps_continua_funcionando_com_notificacoes(client, cen, rota):
    viagem = _iniciar(client, cen, rota)
    r = client.post(
        f"{API}/motorista/viagens/{viagem}/localizacao",
        headers=cen["m1"],
        json={"latitude": -9.6005, "longitude": -35.7000, "velocidade": 7.5},
    )
    assert r.status_code == 201 and r.json()["velocidade"] == 7.5
    resumo = client.get(f"{API}/responsavel/avisos/resumo", headers=cen["ra"]).json()
    assert resumo["nao_lidas"] == 2  # viagem iniciada + van se aproximando