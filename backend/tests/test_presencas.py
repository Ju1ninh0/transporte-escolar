import pytest
from sqlalchemy import select

from app.core.security import hash_senha
from app.models import Empresa, Motorista, Perfil, Usuario

SENHA = "senha-teste-123"
API = "/api/v1"


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
        "filho_b": dados["filho_b"],
        "admin": login("admin@t.com"),
        "m1": login("m1@t.com"),
        "m2": login("m2@t.com"),
    }


@pytest.fixture()
def viagem(client, cen):
    """Rota com 2 paradas (P1, P2), Filho B na P1, Filho A na P2, viagem iniciada pelo m1."""
    a = cen["admin"]
    van = client.post(
        f"{API}/veiculos", headers=a, json={"placa": "ABC1D23", "apelido": "Van", "capacidade": 10}
    ).json()["id"]
    rota = client.post(
        f"{API}/rotas", headers=a, json={"nome": "Manhã", "veiculo_id": van, "motorista_id": cen["m1_id"]}
    ).json()["id"]
    p1 = client.post(
        f"{API}/rotas/{rota}/paradas", headers=a, json={"nome": "P1", "latitude": -9.6, "longitude": -35.7}
    ).json()["id"]
    p2 = client.post(
        f"{API}/rotas/{rota}/paradas", headers=a, json={"nome": "P2", "latitude": -9.7, "longitude": -35.8}
    ).json()["id"]
    client.post(f"{API}/rotas/{rota}/alunos", headers=a, json={"aluno_id": cen["filho_a"], "parada_id": p2})
    client.post(f"{API}/rotas/{rota}/alunos", headers=a, json={"aluno_id": cen["filho_b"], "parada_id": p1})
    r = client.post(f"{API}/motorista/rotas/{rota}/viagem/iniciar", headers=cen["m1"])
    assert r.status_code == 201, r.text
    return {"id": r.json()["id"], "rota": rota}


def _url(viagem, aluno=None):
    base = f"{API}/motorista/viagens/{viagem['id']}/presencas"
    return base if aluno is None else f"{base}/{aluno}"


# ------------------------------------------------------------- permissões
@pytest.mark.parametrize(
    "metodo,caminho",
    [
        ("GET", "/motorista/viagens/1/presencas"),
        ("PUT", "/motorista/viagens/1/presencas/1"),
        ("DELETE", "/motorista/viagens/1/presencas/1"),
        ("GET", "/viagens/1/presencas"),
    ],
)
def test_sem_token_401(client, metodo, caminho):
    assert client.request(metodo, f"{API}{caminho}").status_code == 401


@pytest.mark.parametrize("email", ["admin@t.com", "a@t.com"])
def test_nao_motorista_403(client, cen, login, email):
    h = login(email)
    assert client.get(f"{API}/motorista/viagens/1/presencas", headers=h).status_code == 403
    r = client.put(
        f"{API}/motorista/viagens/1/presencas/1", headers=h, json={"status": "PRESENTE"}
    )
    assert r.status_code == 403
    assert client.delete(f"{API}/motorista/viagens/1/presencas/1", headers=h).status_code == 403


@pytest.mark.parametrize("email", ["m1@t.com", "a@t.com"])
def test_nao_admin_403_na_visao_admin(client, cen, login, email):
    assert client.get(f"{API}/viagens/1/presencas", headers=login(email)).status_code == 403


# ---------------------------------------------------------------- checklist
def test_checklist_inicial_tudo_pendente_na_ordem_das_paradas(client, cen, viagem):
    r = client.get(_url(viagem), headers=cen["m1"])
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["viagem_id"] == viagem["id"] and d["status_viagem"] == "EM_ANDAMENTO"
    assert (d["total"], d["presentes"], d["faltas"], d["pendentes"]) == (2, 0, 0, 2)
    # Filho B está na P1 (ordem 1) e Filho A na P2: a ordem segue as paradas, não o nome
    assert [a["nome"] for a in d["alunos"]] == ["Filho B", "Filho A"]
    assert [a["parada_nome"] for a in d["alunos"]] == ["P1", "P2"]
    assert all(a["status"] is None for a in d["alunos"])


def test_marcar_presente_e_falta(client, cen, viagem):
    r = client.put(_url(viagem, cen["filho_b"]), headers=cen["m1"], json={"status": "PRESENTE"})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "PRESENTE" and r.json()["parada_nome"] == "P1"
    r = client.put(
        _url(viagem, cen["filho_a"]),
        headers=cen["m1"],
        json={"status": "FALTA", "observacao": "  Doente  "},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "FALTA" and r.json()["observacao"] == "Doente"
    d = client.get(_url(viagem), headers=cen["m1"]).json()
    assert (d["presentes"], d["faltas"], d["pendentes"]) == (1, 1, 0)


def test_alterar_marcacao_atualiza_sem_duplicar(client, cen, viagem):
    url = _url(viagem, cen["filho_a"])
    client.put(url, headers=cen["m1"], json={"status": "PRESENTE", "observacao": "ok"})
    r = client.put(url, headers=cen["m1"], json={"status": "FALTA"})
    assert r.status_code == 200 and r.json()["status"] == "FALTA"
    assert r.json()["observacao"] is None
    d = client.get(_url(viagem), headers=cen["m1"]).json()
    assert d["total"] == 2
    assert (d["presentes"], d["faltas"], d["pendentes"]) == (0, 1, 1)


def test_observacao_em_branco_vira_nulo(client, cen, viagem):
    r = client.put(
        _url(viagem, cen["filho_a"]), headers=cen["m1"], json={"status": "PRESENTE", "observacao": "   "}
    )
    assert r.status_code == 200 and r.json()["observacao"] is None


def test_status_invalido_422(client, cen, viagem):
    r = client.put(_url(viagem, cen["filho_a"]), headers=cen["m1"], json={"status": "ATRASADO"})
    assert r.status_code == 422
    assert client.put(_url(viagem, cen["filho_a"]), headers=cen["m1"], json={}).status_code == 422


def test_aluno_fora_da_rota_404(client, cen, viagem):
    r = client.put(_url(viagem, 99999), headers=cen["m1"], json={"status": "PRESENTE"})
    assert r.status_code == 404


def test_desfazer_marcacao(client, cen, viagem):
    url = _url(viagem, cen["filho_a"])
    client.put(url, headers=cen["m1"], json={"status": "PRESENTE"})
    assert client.delete(url, headers=cen["m1"]).status_code == 204
    d = client.get(_url(viagem), headers=cen["m1"]).json()
    assert d["pendentes"] == 2
    assert client.delete(url, headers=cen["m1"]).status_code == 404


# ------------------------------------------------------- viagem encerrada
def test_viagem_encerrada_bloqueia_alteracao_mas_permite_leitura(client, cen, viagem):
    client.put(_url(viagem, cen["filho_a"]), headers=cen["m1"], json={"status": "PRESENTE"})
    r = client.post(f"{API}/motorista/viagens/{viagem['id']}/encerrar", headers=cen["m1"])
    assert r.status_code == 200
    r = client.put(_url(viagem, cen["filho_b"]), headers=cen["m1"], json={"status": "PRESENTE"})
    assert r.status_code == 409
    assert client.delete(_url(viagem, cen["filho_a"]), headers=cen["m1"]).status_code == 409
    d = client.get(_url(viagem), headers=cen["m1"]).json()
    assert d["status_viagem"] == "FINALIZADA"
    assert (d["presentes"], d["pendentes"]) == (1, 1)


def test_cada_viagem_tem_sua_propria_chamada(client, cen, viagem):
    client.put(_url(viagem, cen["filho_a"]), headers=cen["m1"], json={"status": "FALTA"})
    client.post(f"{API}/motorista/viagens/{viagem['id']}/encerrar", headers=cen["m1"])
    nova = client.post(f"{API}/motorista/rotas/{viagem['rota']}/viagem/iniciar", headers=cen["m1"]).json()
    d = client.get(f"{API}/motorista/viagens/{nova['id']}/presencas", headers=cen["m1"]).json()
    assert d["pendentes"] == 2 and d["faltas"] == 0


# --------------------------------------------------------------- isolamento
def test_outro_motorista_nao_acessa_404(client, cen, viagem):
    assert client.get(_url(viagem), headers=cen["m2"]).status_code == 404
    r = client.put(_url(viagem, cen["filho_a"]), headers=cen["m2"], json={"status": "PRESENTE"})
    assert r.status_code == 404
    assert client.delete(_url(viagem, cen["filho_a"]), headers=cen["m2"]).status_code == 404


def test_admin_ve_presencas_da_viagem(client, cen, viagem):
    client.put(_url(viagem, cen["filho_a"]), headers=cen["m1"], json={"status": "PRESENTE"})
    r = client.get(f"{API}/viagens/{viagem['id']}/presencas", headers=cen["admin"])
    assert r.status_code == 200
    assert (r.json()["presentes"], r.json()["pendentes"]) == (1, 1)


def test_admin_de_outra_empresa_404(client, cen, viagem, login):
    r = client.get(f"{API}/viagens/{viagem['id']}/presencas", headers=login("admin2@o.com"))
    assert r.status_code == 404