from datetime import date

import pytest
from sqlalchemy import select

from app.core.security import hash_senha
from app.models import (
    Aluno,
    Empresa,
    HistoricoRota,
    Motorista,
    Perfil,
    Responsavel,
    StatusExecucao,
    Usuario,
)

SENHA = "senha-teste-123"
API = "/api/v1"


# ---------------------------------------------------------------- fixtures
@pytest.fixture()
def frota(db, dados):
    """Empresa 'Teste' (do conftest) + motorista, aluno inativo e uma 2ª empresa."""
    emp = db.scalar(select(Empresa).where(Empresa.nome == "Teste"))

    def novo_usuario(empresa, email, perfil):
        u = Usuario(
            empresa_id=empresa.id,
            nome=email,
            email=email,
            senha_hash=hash_senha(SENHA),
            perfil=perfil,
        )
        db.add(u)
        db.flush()
        return u

    mot = Motorista(empresa_id=emp.id, usuario_id=novo_usuario(emp, "mot@t.com", Perfil.MOTORISTA).id)

    emp2 = Empresa(nome="Outra")
    db.add(emp2)
    db.flush()
    novo_usuario(emp2, "admin2@o.com", Perfil.ADMIN)
    mot2 = Motorista(
        empresa_id=emp2.id, usuario_id=novo_usuario(emp2, "mot2@o.com", Perfil.MOTORISTA).id
    )
    resp2 = Responsavel(
        empresa_id=emp2.id, usuario_id=novo_usuario(emp2, "r2@o.com", Perfil.RESPONSAVEL).id
    )
    db.add_all([mot, mot2, resp2])
    db.flush()

    inativo = Aluno(
        empresa_id=emp.id,
        responsavel_id=dados["resp_b"],
        nome="Aluno Inativo",
        data_nascimento=date(2015, 1, 1),
        escola="E",
        ativo=False,
    )
    de_outra = Aluno(
        empresa_id=emp2.id,
        responsavel_id=resp2.id,
        nome="Aluno Outra Empresa",
        data_nascimento=date(2015, 1, 1),
        escola="E",
    )
    db.add_all([inativo, de_outra])
    db.commit()
    return {
        "motorista": mot.id,
        "motorista2": mot2.id,
        "filho_a": dados["filho_a"],
        "filho_b": dados["filho_b"],
        "inativo": inativo.id,
        "de_outra": de_outra.id,
    }


@pytest.fixture()
def admin(login, frota):
    return login("admin@t.com")


@pytest.fixture()
def admin2(login, frota):
    return login("admin2@o.com")


def _veiculo(client, h, placa="ABC1D23", cap=15, apelido="Van 1"):
    r = client.post(
        f"{API}/veiculos", headers=h, json={"placa": placa, "apelido": apelido, "capacidade": cap}
    )
    assert r.status_code == 201, r.text
    return r.json()


def _rota(client, h, **extra):
    r = client.post(f"{API}/rotas", headers=h, json={"nome": "Rota Manhã", **extra})
    assert r.status_code == 201, r.text
    return r.json()


def _parada(client, h, rota_id, nome="Parada", **extra):
    r = client.post(
        f"{API}/rotas/{rota_id}/paradas",
        headers=h,
        json={"nome": nome, "latitude": -9.66, "longitude": -35.73, **extra},
    )
    assert r.status_code == 201, r.text
    return r.json()


def _iniciar_viagem(db, rota_id):
    h = HistoricoRota(rota_id=rota_id, status=StatusExecucao.EM_ANDAMENTO)
    db.add(h)
    db.commit()
    return h


def _finalizar_viagem(db, viagem):
    viagem.status = StatusExecucao.FINALIZADA
    db.commit()


# ------------------------------------------------------------- permissões
CASOS = [
    ("GET", "/veiculos"),
    ("POST", "/veiculos"),
    ("GET", "/rotas"),
    ("POST", "/rotas"),
    ("GET", "/rotas/1"),
    ("PATCH", "/rotas/1"),
    ("GET", "/rotas/1/paradas"),
    ("POST", "/rotas/1/paradas"),
    ("PUT", "/rotas/1/paradas/ordem"),
    ("GET", "/rotas/1/alunos"),
    ("POST", "/rotas/1/alunos"),
]


@pytest.mark.parametrize("metodo,caminho", CASOS)
def test_sem_token_401(client, metodo, caminho):
    assert client.request(metodo, f"{API}{caminho}", json={}).status_code == 401


@pytest.mark.parametrize("email", ["mot@t.com", "a@t.com"])
@pytest.mark.parametrize("metodo,caminho", CASOS)
def test_nao_admin_403(client, frota, login, email, metodo, caminho):
    r = client.request(metodo, f"{API}{caminho}", headers=login(email), json={})
    assert r.status_code == 403


# --------------------------------------------------------------- veículos
def test_veiculo_normaliza_placa(client, admin):
    v = _veiculo(client, admin, placa="abc-1d23")
    assert v["placa"] == "ABC1D23"
    assert v["ativo"] is True


def test_veiculo_aceita_placa_antiga(client, admin):
    assert _veiculo(client, admin, placa="ABC 1234")["placa"] == "ABC1234"


@pytest.mark.parametrize("placa", ["XX12", "1234567", "ABCD123", ""])
def test_veiculo_placa_invalida_422(client, admin, placa):
    r = client.post(f"{API}/veiculos", headers=admin, json={"placa": placa, "apelido": "V"})
    assert r.status_code == 422


@pytest.mark.parametrize("cap", [0, -1, 101])
def test_veiculo_capacidade_invalida_422(client, admin, cap):
    r = client.post(
        f"{API}/veiculos", headers=admin, json={"placa": "ABC1D23", "apelido": "V", "capacidade": cap}
    )
    assert r.status_code == 422


def test_veiculo_apelido_vazio_422(client, admin):
    r = client.post(f"{API}/veiculos", headers=admin, json={"placa": "ABC1D23", "apelido": "  "})
    assert r.status_code == 422


def test_veiculo_placa_duplicada_409(client, admin):
    _veiculo(client, admin, placa="ABC1D23")
    r = client.post(f"{API}/veiculos", headers=admin, json={"placa": "abc 1d23", "apelido": "Outra"})
    assert r.status_code == 409


def test_veiculo_mesma_placa_em_outra_empresa_ok(client, admin, admin2):
    _veiculo(client, admin, placa="ABC1D23")
    _veiculo(client, admin2, placa="ABC1D23")


def test_veiculo_listar_com_filtro_ativo(client, admin):
    a = _veiculo(client, admin, placa="AAA1A11", apelido="A")
    _veiculo(client, admin, placa="BBB2B22", apelido="B")
    r = client.patch(f"{API}/veiculos/{a['id']}", headers=admin, json={"ativo": False})
    assert r.status_code == 200 and r.json()["ativo"] is False
    assert len(client.get(f"{API}/veiculos", headers=admin).json()) == 2
    ativos = client.get(f"{API}/veiculos?ativo=true", headers=admin).json()
    assert [v["apelido"] for v in ativos] == ["B"]
    inativos = client.get(f"{API}/veiculos?ativo=false", headers=admin).json()
    assert [v["apelido"] for v in inativos] == ["A"]


def test_veiculo_patch_placa_duplicada_409(client, admin):
    _veiculo(client, admin, placa="AAA1A11", apelido="A")
    b = _veiculo(client, admin, placa="BBB2B22", apelido="B")
    r = client.patch(f"{API}/veiculos/{b['id']}", headers=admin, json={"placa": "aaa-1a11"})
    assert r.status_code == 409


def test_veiculo_nao_desativa_em_rota_ativa(client, admin):
    v = _veiculo(client, admin)
    rota = _rota(client, admin, veiculo_id=v["id"])
    r = client.patch(f"{API}/veiculos/{v['id']}", headers=admin, json={"ativo": False})
    assert r.status_code == 409
    client.patch(f"{API}/rotas/{rota['id']}", headers=admin, json={"veiculo_id": None})
    r = client.patch(f"{API}/veiculos/{v['id']}", headers=admin, json={"ativo": False})
    assert r.status_code == 200


def test_veiculo_desativa_se_rota_so_inativa(client, admin):
    v = _veiculo(client, admin)
    rota = _rota(client, admin, veiculo_id=v["id"])
    client.patch(f"{API}/rotas/{rota['id']}", headers=admin, json={"status": "INATIVA"})
    r = client.patch(f"{API}/veiculos/{v['id']}", headers=admin, json={"ativo": False})
    assert r.status_code == 200


def test_veiculo_reduzir_capacidade_abaixo_dos_alunos_409(client, admin, frota):
    v = _veiculo(client, admin, cap=5)
    rota = _rota(client, admin, veiculo_id=v["id"])
    for aluno in (frota["filho_a"], frota["filho_b"]):
        client.post(f"{API}/rotas/{rota['id']}/alunos", headers=admin, json={"aluno_id": aluno})
    r = client.patch(f"{API}/veiculos/{v['id']}", headers=admin, json={"capacidade": 1})
    assert r.status_code == 409
    r = client.patch(f"{API}/veiculos/{v['id']}", headers=admin, json={"capacidade": 2})
    assert r.status_code == 200


def test_veiculo_isolamento_entre_empresas(client, admin, admin2):
    v = _veiculo(client, admin)
    assert client.get(f"{API}/veiculos/{v['id']}", headers=admin2).status_code == 404
    r = client.patch(f"{API}/veiculos/{v['id']}", headers=admin2, json={"apelido": "X"})
    assert r.status_code == 404
    assert client.get(f"{API}/veiculos", headers=admin2).json() == []


# ------------------------------------------------------------------ rotas
def test_rota_criar_listar_e_detalhar(client, admin, frota):
    v = _veiculo(client, admin)
    rota = _rota(
        client, admin, escola="Escola X", veiculo_id=v["id"], motorista_id=frota["motorista"]
    )
    assert rota["status"] == "ATIVA"
    assert rota["veiculo"]["placa"] == "ABC1D23"
    assert rota["motorista"]["id"] == frota["motorista"]
    assert rota["total_paradas"] == 0 and rota["total_alunos"] == 0

    _parada(client, admin, rota["id"], nome="P1")
    client.post(
        f"{API}/rotas/{rota['id']}/alunos", headers=admin, json={"aluno_id": frota["filho_a"]}
    )

    lista = client.get(f"{API}/rotas", headers=admin).json()
    assert len(lista) == 1
    assert lista[0]["total_paradas"] == 1 and lista[0]["total_alunos"] == 1

    det = client.get(f"{API}/rotas/{rota['id']}", headers=admin).json()
    assert det["nome"] == "Rota Manhã"
    assert [p["nome"] for p in det["paradas"]] == ["P1"]
    assert [a["nome"] for a in det["alunos"]] == ["Filho A"]


def test_rota_sem_vinculos(client, admin):
    rota = _rota(client, admin)
    assert rota["veiculo"] is None and rota["motorista"] is None


def test_rota_nome_vazio_422(client, admin):
    r = client.post(f"{API}/rotas", headers=admin, json={"nome": "   "})
    assert r.status_code == 422


def test_rota_veiculo_de_outra_empresa_404(client, admin, admin2):
    v2 = _veiculo(client, admin2)
    r = client.post(f"{API}/rotas", headers=admin, json={"nome": "R", "veiculo_id": v2["id"]})
    assert r.status_code == 404


def test_rota_motorista_de_outra_empresa_404(client, admin, frota):
    r = client.post(
        f"{API}/rotas", headers=admin, json={"nome": "R", "motorista_id": frota["motorista2"]}
    )
    assert r.status_code == 404


def test_rota_veiculo_inativo_400(client, admin):
    v = _veiculo(client, admin)
    client.patch(f"{API}/veiculos/{v['id']}", headers=admin, json={"ativo": False})
    r = client.post(f"{API}/rotas", headers=admin, json={"nome": "R", "veiculo_id": v["id"]})
    assert r.status_code == 400


def test_rota_desvincular_com_null(client, admin, frota):
    v = _veiculo(client, admin)
    rota = _rota(client, admin, veiculo_id=v["id"], motorista_id=frota["motorista"])
    r = client.patch(
        f"{API}/rotas/{rota['id']}", headers=admin, json={"veiculo_id": None, "motorista_id": None}
    )
    assert r.status_code == 200
    assert r.json()["veiculo"] is None and r.json()["motorista"] is None


def test_rota_patch_sem_enviar_mantem_vinculos(client, admin, frota):
    v = _veiculo(client, admin)
    rota = _rota(client, admin, veiculo_id=v["id"], motorista_id=frota["motorista"])
    r = client.patch(f"{API}/rotas/{rota['id']}", headers=admin, json={"nome": "Novo nome"})
    assert r.status_code == 200
    assert r.json()["nome"] == "Novo nome"
    assert r.json()["veiculo"]["id"] == v["id"]
    assert r.json()["motorista"]["id"] == frota["motorista"]


def test_rota_van_pode_atender_duas_rotas(client, admin):
    v = _veiculo(client, admin)
    _rota(client, admin, nome="Manhã", veiculo_id=v["id"])
    _rota(client, admin, nome="Tarde", veiculo_id=v["id"])


def test_rota_filtros(client, admin, frota):
    _rota(client, admin, nome="A", motorista_id=frota["motorista"])
    b = _rota(client, admin, nome="B")
    client.patch(f"{API}/rotas/{b['id']}", headers=admin, json={"status": "INATIVA"})
    assert [r["nome"] for r in client.get(f"{API}/rotas?status=INATIVA", headers=admin).json()] == ["B"]
    assert [r["nome"] for r in client.get(f"{API}/rotas?status=ATIVA", headers=admin).json()] == ["A"]
    por_mot = client.get(f"{API}/rotas?motorista_id={frota['motorista']}", headers=admin).json()
    assert [r["nome"] for r in por_mot] == ["A"]


def test_rota_inativar_com_viagem_em_andamento_409(client, admin, db):
    rota = _rota(client, admin)
    viagem = _iniciar_viagem(db, rota["id"])
    r = client.patch(f"{API}/rotas/{rota['id']}", headers=admin, json={"status": "INATIVA"})
    assert r.status_code == 409
    _finalizar_viagem(db, viagem)
    r = client.patch(f"{API}/rotas/{rota['id']}", headers=admin, json={"status": "INATIVA"})
    assert r.status_code == 200 and r.json()["status"] == "INATIVA"


def test_rota_trocar_para_veiculo_de_capacidade_menor_409(client, admin, frota):
    grande = _veiculo(client, admin, placa="AAA1A11", cap=10, apelido="Grande")
    pequeno = _veiculo(client, admin, placa="BBB2B22", cap=1, apelido="Pequeno")
    rota = _rota(client, admin, veiculo_id=grande["id"])
    for aluno in (frota["filho_a"], frota["filho_b"]):
        client.post(f"{API}/rotas/{rota['id']}/alunos", headers=admin, json={"aluno_id": aluno})
    r = client.patch(f"{API}/rotas/{rota['id']}", headers=admin, json={"veiculo_id": pequeno["id"]})
    assert r.status_code == 409


def test_rota_isolamento_entre_empresas(client, admin, admin2):
    rota = _rota(client, admin)
    assert client.get(f"{API}/rotas/{rota['id']}", headers=admin2).status_code == 404
    r = client.patch(f"{API}/rotas/{rota['id']}", headers=admin2, json={"nome": "X"})
    assert r.status_code == 404
    assert client.get(f"{API}/rotas", headers=admin2).json() == []


# ---------------------------------------------------------------- paradas
def test_parada_ordem_automatica(client, admin):
    rota = _rota(client, admin)
    ordens = [_parada(client, admin, rota["id"], nome=f"P{i}")["ordem"] for i in range(3)]
    assert ordens == [1, 2, 3]


def test_parada_ordem_explicita_duplicada_409(client, admin):
    rota = _rota(client, admin)
    _parada(client, admin, rota["id"], ordem=1)
    r = client.post(
        f"{API}/rotas/{rota['id']}/paradas",
        headers=admin,
        json={"nome": "Dup", "latitude": 0, "longitude": 0, "ordem": 1},
    )
    assert r.status_code == 409


@pytest.mark.parametrize(
    "lat,lng", [(91, 0), (-91, 0), (0, 181), (0, -181)]
)
def test_parada_coordenadas_invalidas_422(client, admin, lat, lng):
    rota = _rota(client, admin)
    r = client.post(
        f"{API}/rotas/{rota['id']}/paradas",
        headers=admin,
        json={"nome": "P", "latitude": lat, "longitude": lng},
    )
    assert r.status_code == 422


def test_parada_listagem_ordenada_e_patch(client, admin):
    rota = _rota(client, admin)
    _parada(client, admin, rota["id"], nome="Segunda", ordem=2)
    p1 = _parada(client, admin, rota["id"], nome="Primeira", ordem=1)
    nomes = [p["nome"] for p in client.get(f"{API}/rotas/{rota['id']}/paradas", headers=admin).json()]
    assert nomes == ["Primeira", "Segunda"]
    r = client.patch(
        f"{API}/rotas/{rota['id']}/paradas/{p1['id']}",
        headers=admin,
        json={"nome": "Renomeada", "latitude": -9.7},
    )
    assert r.status_code == 200
    assert r.json()["nome"] == "Renomeada" and r.json()["latitude"] == -9.7
    assert r.json()["ordem"] == 1


def test_parada_reordenar(client, admin):
    rota = _rota(client, admin)
    ids = [_parada(client, admin, rota["id"], nome=f"P{i}")["id"] for i in range(1, 4)]
    r = client.put(
        f"{API}/rotas/{rota['id']}/paradas/ordem", headers=admin, json={"ids": list(reversed(ids))}
    )
    assert r.status_code == 200
    assert [p["id"] for p in r.json()] == list(reversed(ids))
    assert [p["ordem"] for p in r.json()] == [1, 2, 3]
    listadas = client.get(f"{API}/rotas/{rota['id']}/paradas", headers=admin).json()
    assert [p["id"] for p in listadas] == list(reversed(ids))


def test_parada_reordenar_ids_invalidos_400(client, admin):
    rota = _rota(client, admin)
    outra = _rota(client, admin, nome="Outra")
    a = _parada(client, admin, rota["id"], nome="A")["id"]
    b = _parada(client, admin, rota["id"], nome="B")["id"]
    estranha = _parada(client, admin, outra["id"], nome="X")["id"]
    url = f"{API}/rotas/{rota['id']}/paradas/ordem"
    assert client.put(url, headers=admin, json={"ids": [a]}).status_code == 400  # falta
    assert client.put(url, headers=admin, json={"ids": [a, b, b]}).status_code == 400  # repetida
    assert client.put(url, headers=admin, json={"ids": [a, estranha]}).status_code == 400  # de outra rota
    assert client.put(url, headers=admin, json={"ids": [a, b, estranha]}).status_code == 400  # sobra


def test_parada_excluir_mantem_aluno_sem_parada(client, admin, frota):
    rota = _rota(client, admin)
    p1 = _parada(client, admin, rota["id"], nome="P1")
    p2 = _parada(client, admin, rota["id"], nome="P2")
    client.post(
        f"{API}/rotas/{rota['id']}/alunos",
        headers=admin,
        json={"aluno_id": frota["filho_a"], "parada_id": p1["id"]},
    )
    r = client.delete(f"{API}/rotas/{rota['id']}/paradas/{p1['id']}", headers=admin)
    assert r.status_code == 204
    alunos = client.get(f"{API}/rotas/{rota['id']}/alunos", headers=admin).json()
    assert len(alunos) == 1
    assert alunos[0]["parada_id"] is None and alunos[0]["parada_nome"] is None
    restantes = client.get(f"{API}/rotas/{rota['id']}/paradas", headers=admin).json()
    assert [(p["id"], p["ordem"]) for p in restantes] == [(p2["id"], 2)]  # sem renumerar


def test_parada_bloqueada_com_viagem_em_andamento(client, admin, db):
    rota = _rota(client, admin)
    p = _parada(client, admin, rota["id"])
    viagem = _iniciar_viagem(db, rota["id"])
    base = f"{API}/rotas/{rota['id']}/paradas"
    novo = {"nome": "N", "latitude": 0, "longitude": 0}
    assert client.post(base, headers=admin, json=novo).status_code == 409
    assert client.patch(f"{base}/{p['id']}", headers=admin, json={"nome": "X"}).status_code == 409
    assert client.put(f"{base}/ordem", headers=admin, json={"ids": [p["id"]]}).status_code == 409
    assert client.delete(f"{base}/{p['id']}", headers=admin).status_code == 409
    _finalizar_viagem(db, viagem)
    assert client.post(base, headers=admin, json=novo).status_code == 201


def test_parada_de_outra_rota_404(client, admin):
    r1 = _rota(client, admin, nome="R1")
    r2 = _rota(client, admin, nome="R2")
    p = _parada(client, admin, r1["id"])
    r = client.patch(f"{API}/rotas/{r2['id']}/paradas/{p['id']}", headers=admin, json={"nome": "X"})
    assert r.status_code == 404
    assert client.delete(f"{API}/rotas/{r2['id']}/paradas/{p['id']}", headers=admin).status_code == 404


def test_parada_isolamento_entre_empresas(client, admin, admin2):
    rota = _rota(client, admin)
    _parada(client, admin, rota["id"])
    assert client.get(f"{API}/rotas/{rota['id']}/paradas", headers=admin2).status_code == 404
    r = client.post(
        f"{API}/rotas/{rota['id']}/paradas",
        headers=admin2,
        json={"nome": "X", "latitude": 0, "longitude": 0},
    )
    assert r.status_code == 404


# ----------------------------------------------------------------- alunos
def test_vincular_aluno_e_listar(client, admin, frota):
    rota = _rota(client, admin)
    p = _parada(client, admin, rota["id"], nome="Praça")
    r = client.post(
        f"{API}/rotas/{rota['id']}/alunos",
        headers=admin,
        json={"aluno_id": frota["filho_a"], "parada_id": p["id"]},
    )
    assert r.status_code == 201
    assert r.json()["nome"] == "Filho A" and r.json()["parada_nome"] == "Praça"
    lista = client.get(f"{API}/rotas/{rota['id']}/alunos", headers=admin).json()
    assert [a["aluno_id"] for a in lista] == [frota["filho_a"]]


def test_vincular_sem_parada_ok(client, admin, frota):
    rota = _rota(client, admin)
    r = client.post(
        f"{API}/rotas/{rota['id']}/alunos", headers=admin, json={"aluno_id": frota["filho_a"]}
    )
    assert r.status_code == 201 and r.json()["parada_id"] is None


def test_vincular_duplicado_409(client, admin, frota):
    rota = _rota(client, admin)
    url = f"{API}/rotas/{rota['id']}/alunos"
    assert client.post(url, headers=admin, json={"aluno_id": frota["filho_a"]}).status_code == 201
    assert client.post(url, headers=admin, json={"aluno_id": frota["filho_a"]}).status_code == 409


def test_vincular_parada_de_outra_rota_400(client, admin, frota):
    r1 = _rota(client, admin, nome="R1")
    r2 = _rota(client, admin, nome="R2")
    p = _parada(client, admin, r2["id"])
    r = client.post(
        f"{API}/rotas/{r1['id']}/alunos",
        headers=admin,
        json={"aluno_id": frota["filho_a"], "parada_id": p["id"]},
    )
    assert r.status_code == 400


def test_vincular_aluno_inativo_400(client, admin, frota):
    rota = _rota(client, admin)
    r = client.post(
        f"{API}/rotas/{rota['id']}/alunos", headers=admin, json={"aluno_id": frota["inativo"]}
    )
    assert r.status_code == 400


def test_vincular_aluno_de_outra_empresa_404(client, admin, frota):
    rota = _rota(client, admin)
    r = client.post(
        f"{API}/rotas/{rota['id']}/alunos", headers=admin, json={"aluno_id": frota["de_outra"]}
    )
    assert r.status_code == 404


def test_aluno_pode_estar_em_duas_rotas(client, admin, frota):
    r1 = _rota(client, admin, nome="Ida")
    r2 = _rota(client, admin, nome="Volta")
    for rota in (r1, r2):
        r = client.post(
            f"{API}/rotas/{rota['id']}/alunos", headers=admin, json={"aluno_id": frota["filho_a"]}
        )
        assert r.status_code == 201


def test_capacidade_do_veiculo_excedida_409(client, admin, frota):
    v = _veiculo(client, admin, cap=1)
    rota = _rota(client, admin, veiculo_id=v["id"])
    url = f"{API}/rotas/{rota['id']}/alunos"
    assert client.post(url, headers=admin, json={"aluno_id": frota["filho_a"]}).status_code == 201
    r = client.post(url, headers=admin, json={"aluno_id": frota["filho_b"]})
    assert r.status_code == 409
    assert "Capacidade" in r.json()["detail"]


def test_rota_sem_veiculo_nao_limita_alunos(client, admin, frota):
    rota = _rota(client, admin)
    url = f"{API}/rotas/{rota['id']}/alunos"
    assert client.post(url, headers=admin, json={"aluno_id": frota["filho_a"]}).status_code == 201
    assert client.post(url, headers=admin, json={"aluno_id": frota["filho_b"]}).status_code == 201


def test_trocar_parada_do_aluno_e_remover(client, admin, frota):
    rota = _rota(client, admin)
    p1 = _parada(client, admin, rota["id"], nome="P1")
    p2 = _parada(client, admin, rota["id"], nome="P2")
    base = f"{API}/rotas/{rota['id']}/alunos"
    client.post(base, headers=admin, json={"aluno_id": frota["filho_a"], "parada_id": p1["id"]})

    r = client.patch(f"{base}/{frota['filho_a']}", headers=admin, json={"parada_id": p2["id"]})
    assert r.status_code == 200 and r.json()["parada_nome"] == "P2"
    r = client.patch(f"{base}/{frota['filho_a']}", headers=admin, json={"parada_id": None})
    assert r.status_code == 200 and r.json()["parada_id"] is None

    assert client.delete(f"{base}/{frota['filho_a']}", headers=admin).status_code == 204
    assert client.get(base, headers=admin).json() == []
    assert client.delete(f"{base}/{frota['filho_a']}", headers=admin).status_code == 404


def test_patch_aluno_que_nao_esta_na_rota_404(client, admin, frota):
    rota = _rota(client, admin)
    r = client.patch(
        f"{API}/rotas/{rota['id']}/alunos/{frota['filho_a']}", headers=admin, json={"parada_id": None}
    )
    assert r.status_code == 404


def test_alunos_isolamento_entre_empresas(client, admin, admin2, frota):
    rota = _rota(client, admin)
    assert client.get(f"{API}/rotas/{rota['id']}/alunos", headers=admin2).status_code == 404
    r = client.post(
        f"{API}/rotas/{rota['id']}/alunos", headers=admin2, json={"aluno_id": frota["de_outra"]}
    )
    assert r.status_code == 404