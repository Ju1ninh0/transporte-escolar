import pytest
from sqlalchemy import select

from app.core.security import hash_senha
from app.models import Empresa, Motorista, Perfil, Usuario

SENHA = "senha-teste-123"
API = "/api/v1"


# ---------------------------------------------------------------- fixtures
@pytest.fixture()
def cen(db, dados, login):
    """Empresa 'Teste' com 2 motoristas (+1 usuário motorista sem cadastro) e uma 2ª empresa."""
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
    novo_usuario(emp, "semcad@t.com", Perfil.MOTORISTA)
    emp2 = Empresa(nome="Outra")
    db.add(emp2)
    db.flush()
    novo_usuario(emp2, "admin2@o.com", Perfil.ADMIN)
    db.add_all([m1, m2])
    db.commit()
    return {
        "m1_id": m1.id,
        "m2_id": m2.id,
        "filho_a": dados["filho_a"],
        "admin": login("admin@t.com"),
        "m1": login("m1@t.com"),
        "m2": login("m2@t.com"),
    }


def _veiculo(client, h, placa="ABC1D23", apelido="Van 1"):
    r = client.post(
        f"{API}/veiculos", headers=h, json={"placa": placa, "apelido": apelido, "capacidade": 10}
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _rota(client, h, nome="Manhã", veiculo=None, motorista=None):
    r = client.post(
        f"{API}/rotas",
        headers=h,
        json={"nome": nome, "veiculo_id": veiculo, "motorista_id": motorista},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _iniciar(client, h, rota_id):
    return client.post(f"{API}/motorista/rotas/{rota_id}/viagem/iniciar", headers=h)


def _encerrar(client, h, viagem_id):
    return client.post(f"{API}/motorista/viagens/{viagem_id}/encerrar", headers=h)


# ------------------------------------------------------------- permissões
@pytest.mark.parametrize(
    "metodo,caminho",
    [
        ("GET", "/motorista/rotas"),
        ("GET", "/motorista/rotas/1"),
        ("POST", "/motorista/rotas/1/viagem/iniciar"),
        ("POST", "/motorista/viagens/1/encerrar"),
        ("GET", "/viagens"),
        ("POST", "/viagens/1/encerrar"),
    ],
)
def test_sem_token_401(client, metodo, caminho):
    assert client.request(metodo, f"{API}{caminho}").status_code == 401


@pytest.mark.parametrize("email", ["admin@t.com", "a@t.com"])
def test_nao_motorista_403_nas_rotas_do_motorista(client, cen, login, email):
    h = login(email)
    assert client.get(f"{API}/motorista/rotas", headers=h).status_code == 403
    assert client.post(f"{API}/motorista/rotas/1/viagem/iniciar", headers=h).status_code == 403
    assert client.post(f"{API}/motorista/viagens/1/encerrar", headers=h).status_code == 403


@pytest.mark.parametrize("email", ["m1@t.com", "a@t.com"])
def test_nao_admin_403_nas_viagens_admin(client, cen, login, email):
    h = login(email)
    assert client.get(f"{API}/viagens", headers=h).status_code == 403
    assert client.post(f"{API}/viagens/1/encerrar", headers=h).status_code == 403


def test_usuario_motorista_sem_cadastro_404(client, cen, login):
    r = client.get(f"{API}/motorista/rotas", headers=login("semcad@t.com"))
    assert r.status_code == 404


# ----------------------------------------------------- rotas do motorista
def test_motorista_lista_apenas_suas_rotas_ativas(client, cen):
    a = cen["admin"]
    _rota(client, a, nome="Minha", motorista=cen["m1_id"])
    _rota(client, a, nome="Do outro", motorista=cen["m2_id"])
    _rota(client, a, nome="Sem motorista")
    inativa = _rota(client, a, nome="Inativa", motorista=cen["m1_id"])
    client.patch(f"{API}/rotas/{inativa}", headers=a, json={"status": "INATIVA"})
    r = client.get(f"{API}/motorista/rotas", headers=cen["m1"])
    assert r.status_code == 200
    assert [x["nome"] for x in r.json()] == ["Minha"]
    assert r.json()[0]["viagem_em_andamento_id"] is None


def test_motorista_detalha_propria_rota(client, cen):
    a = cen["admin"]
    rota = _rota(client, a, motorista=cen["m1_id"])
    p = client.post(
        f"{API}/rotas/{rota}/paradas",
        headers=a,
        json={"nome": "Praça", "latitude": -9.66, "longitude": -35.73},
    ).json()
    client.post(
        f"{API}/rotas/{rota}/alunos", headers=a, json={"aluno_id": cen["filho_a"], "parada_id": p["id"]}
    )
    r = client.get(f"{API}/motorista/rotas/{rota}", headers=cen["m1"])
    assert r.status_code == 200
    det = r.json()
    assert [x["nome"] for x in det["paradas"]] == ["Praça"]
    assert [x["nome"] for x in det["alunos"]] == ["Filho A"]
    assert det["alunos"][0]["parada_nome"] == "Praça"


def test_motorista_nao_ve_rota_de_outro_404(client, cen):
    rota = _rota(client, cen["admin"], motorista=cen["m2_id"])
    assert client.get(f"{API}/motorista/rotas/{rota}", headers=cen["m1"]).status_code == 404
    assert _iniciar(client, cen["m1"], rota).status_code == 404


# ------------------------------------------------------------ iniciar viagem
def test_iniciar_viagem_ok(client, cen):
    a = cen["admin"]
    van = _veiculo(client, a)
    rota = _rota(client, a, nome="Manhã", veiculo=van, motorista=cen["m1_id"])
    r = _iniciar(client, cen["m1"], rota)
    assert r.status_code == 201, r.text
    v = r.json()
    assert v["status"] == "EM_ANDAMENTO"
    assert v["rota_id"] == rota and v["rota_nome"] == "Manhã"
    assert v["veiculo_id"] == van and v["motorista_id"] == cen["m1_id"]
    assert v["finalizada_em"] is None
    listadas = client.get(f"{API}/motorista/rotas", headers=cen["m1"]).json()
    assert listadas[0]["viagem_em_andamento_id"] == v["id"]


def test_iniciar_sem_veiculo_400(client, cen):
    rota = _rota(client, cen["admin"], motorista=cen["m1_id"])
    assert _iniciar(client, cen["m1"], rota).status_code == 400


def test_iniciar_rota_inativa_400(client, cen):
    a = cen["admin"]
    rota = _rota(client, a, veiculo=_veiculo(client, a), motorista=cen["m1_id"])
    client.patch(f"{API}/rotas/{rota}", headers=a, json={"status": "INATIVA"})
    assert _iniciar(client, cen["m1"], rota).status_code == 400


def test_iniciar_duas_vezes_409(client, cen):
    a = cen["admin"]
    rota = _rota(client, a, veiculo=_veiculo(client, a), motorista=cen["m1_id"])
    assert _iniciar(client, cen["m1"], rota).status_code == 201
    r = _iniciar(client, cen["m1"], rota)
    assert r.status_code == 409
    assert "rota" in r.json()["detail"].lower()


def test_iniciar_com_veiculo_em_outra_viagem_409(client, cen):
    a = cen["admin"]
    van = _veiculo(client, a)
    manha = _rota(client, a, nome="Manhã", veiculo=van, motorista=cen["m1_id"])
    tarde = _rota(client, a, nome="Tarde", veiculo=van, motorista=cen["m2_id"])
    assert _iniciar(client, cen["m1"], manha).status_code == 201
    r = _iniciar(client, cen["m2"], tarde)
    assert r.status_code == 409
    assert "veículo" in r.json()["detail"].lower()


def test_iniciar_com_motorista_em_outra_viagem_409(client, cen):
    a = cen["admin"]
    r1 = _rota(client, a, nome="R1", veiculo=_veiculo(client, a, "AAA1A11", "V1"), motorista=cen["m1_id"])
    r2 = _rota(client, a, nome="R2", veiculo=_veiculo(client, a, "BBB2B22", "V2"), motorista=cen["m1_id"])
    assert _iniciar(client, cen["m1"], r1).status_code == 201
    r = _iniciar(client, cen["m1"], r2)
    assert r.status_code == 409
    assert "você" in r.json()["detail"].lower()


# ----------------------------------------------------------- encerrar viagem
def test_encerrar_e_iniciar_de_novo(client, cen):
    a = cen["admin"]
    rota = _rota(client, a, veiculo=_veiculo(client, a), motorista=cen["m1_id"])
    viagem = _iniciar(client, cen["m1"], rota).json()
    r = _encerrar(client, cen["m1"], viagem["id"])
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "FINALIZADA" and r.json()["finalizada_em"] is not None
    assert client.get(f"{API}/motorista/rotas", headers=cen["m1"]).json()[0]["viagem_em_andamento_id"] is None
    nova = _iniciar(client, cen["m1"], rota)
    assert nova.status_code == 201 and nova.json()["id"] != viagem["id"]


def test_encerrar_duas_vezes_409(client, cen):
    a = cen["admin"]
    rota = _rota(client, a, veiculo=_veiculo(client, a), motorista=cen["m1_id"])
    viagem = _iniciar(client, cen["m1"], rota).json()
    assert _encerrar(client, cen["m1"], viagem["id"]).status_code == 200
    assert _encerrar(client, cen["m1"], viagem["id"]).status_code == 409


def test_encerrar_viagem_de_outro_motorista_404(client, cen):
    a = cen["admin"]
    rota = _rota(client, a, veiculo=_veiculo(client, a), motorista=cen["m1_id"])
    viagem = _iniciar(client, cen["m1"], rota).json()
    assert _encerrar(client, cen["m2"], viagem["id"]).status_code == 404
    assert _encerrar(client, cen["m1"], 99999).status_code == 404


# -------------------------------------------------------------- visão admin
def test_admin_lista_viagens_com_filtros(client, cen):
    a = cen["admin"]
    rota = _rota(client, a, nome="Manhã", veiculo=_veiculo(client, a), motorista=cen["m1_id"])
    viagem = _iniciar(client, cen["m1"], rota).json()
    todas = client.get(f"{API}/viagens", headers=a).json()
    assert len(todas) == 1
    assert todas[0]["rota_nome"] == "Manhã" and todas[0]["motorista_nome"] == "m1"
    assert len(client.get(f"{API}/viagens?status=EM_ANDAMENTO", headers=a).json()) == 1
    assert client.get(f"{API}/viagens?status=FINALIZADA", headers=a).json() == []
    assert len(client.get(f"{API}/viagens?rota_id={rota}", headers=a).json()) == 1
    assert client.get(f"{API}/viagens?rota_id=99999", headers=a).json() == []
    _encerrar(client, cen["m1"], viagem["id"])
    assert len(client.get(f"{API}/viagens?status=FINALIZADA", headers=a).json()) == 1


def test_admin_encerra_viagem_de_qualquer_motorista(client, cen):
    a = cen["admin"]
    rota = _rota(client, a, veiculo=_veiculo(client, a), motorista=cen["m1_id"])
    viagem = _iniciar(client, cen["m1"], rota).json()
    r = client.post(f"{API}/viagens/{viagem['id']}/encerrar", headers=a)
    assert r.status_code == 200 and r.json()["status"] == "FINALIZADA"
    assert client.post(f"{API}/viagens/{viagem['id']}/encerrar", headers=a).status_code == 409
    assert _iniciar(client, cen["m1"], rota).status_code == 201


def test_admin_de_outra_empresa_nao_ve_nem_encerra_404(client, cen, login):
    a = cen["admin"]
    rota = _rota(client, a, veiculo=_veiculo(client, a), motorista=cen["m1_id"])
    viagem = _iniciar(client, cen["m1"], rota).json()
    a2 = login("admin2@o.com")
    assert client.get(f"{API}/viagens", headers=a2).json() == []
    assert client.post(f"{API}/viagens/{viagem['id']}/encerrar", headers=a2).status_code == 404


# ------------------------------------------------- integração com a Etapa 1
def test_viagem_em_andamento_bloqueia_inativar_rota_e_mexer_nas_paradas(client, cen):
    a = cen["admin"]
    rota = _rota(client, a, veiculo=_veiculo(client, a), motorista=cen["m1_id"])
    viagem = _iniciar(client, cen["m1"], rota).json()
    r = client.patch(f"{API}/rotas/{rota}", headers=a, json={"status": "INATIVA"})
    assert r.status_code == 409
    r = client.post(
        f"{API}/rotas/{rota}/paradas", headers=a, json={"nome": "X", "latitude": 0, "longitude": 0}
    )
    assert r.status_code == 409
    _encerrar(client, cen["m1"], viagem["id"])
    r = client.patch(f"{API}/rotas/{rota}", headers=a, json={"status": "INATIVA"})
    assert r.status_code == 200