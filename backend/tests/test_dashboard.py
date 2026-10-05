import pytest
from sqlalchemy import select

from app.core.security import hash_senha
from app.models import Empresa, Motorista, Perfil, Usuario

SENHA = "senha-teste-123"
API = "/api/v1"


@pytest.fixture()
def cen(db, dados, login):
    emp = db.scalar(select(Empresa).where(Empresa.nome == "Teste"))
    u = Usuario(
        empresa_id=emp.id, nome="m1", email="m1@t.com", senha_hash=hash_senha(SENHA), perfil=Perfil.MOTORISTA
    )
    db.add(u)
    db.flush()
    m1 = Motorista(empresa_id=emp.id, usuario_id=u.id)
    emp2 = Empresa(nome="Outra")
    db.add_all([m1, emp2])
    db.flush()
    admin2 = Usuario(
        empresa_id=emp2.id, nome="a2", email="admin2@o.com", senha_hash=hash_senha(SENHA), perfil=Perfil.ADMIN
    )
    db.add(admin2)
    db.commit()
    return {
        "m1_id": m1.id,
        "filho_a": dados["filho_a"],
        "admin": login("admin@t.com"),
        "admin2": login("admin2@o.com"),
        "m1": login("m1@t.com"),
        "ra": login("a@t.com"),
    }


def test_sem_token_401(client):
    assert client.get(f"{API}/dashboard").status_code == 401


@pytest.mark.parametrize("quem", ["m1", "ra"])
def test_so_admin_403(client, cen, quem):
    assert client.get(f"{API}/dashboard", headers=cen[quem]).status_code == 403


def test_contagens_iniciais(client, cen):
    d = client.get(f"{API}/dashboard", headers=cen["admin"]).json()
    assert d["alunos_ativos"] == 2 and d["responsaveis"] == 2 and d["motoristas"] == 1
    assert d["veiculos_ativos"] == 0 and d["rotas_ativas"] == 0 and d["viagens_em_andamento"] == 0
    assert d["ocorrencias_30_dias"] == 0 and d["ocorrencias_recentes"] == []


def test_contagens_acompanham_os_cadastros_e_a_viagem(client, cen):
    a = cen["admin"]
    van = client.post(
        f"{API}/veiculos", headers=a, json={"placa": "ABC1D23", "apelido": "Van", "capacidade": 10}
    ).json()["id"]
    inativa = client.post(
        f"{API}/veiculos", headers=a, json={"placa": "BBB2B22", "apelido": "Reserva", "capacidade": 10}
    ).json()["id"]
    client.patch(f"{API}/veiculos/{inativa}", headers=a, json={"ativo": False})
    rota = client.post(
        f"{API}/rotas", headers=a, json={"nome": "Manhã", "veiculo_id": van, "motorista_id": cen["m1_id"]}
    ).json()["id"]
    outra = client.post(f"{API}/rotas", headers=a, json={"nome": "Parada"}).json()["id"]
    client.patch(f"{API}/rotas/{outra}", headers=a, json={"status": "INATIVA"})

    d = client.get(f"{API}/dashboard", headers=a).json()
    assert (d["veiculos_ativos"], d["rotas_ativas"], d["viagens_em_andamento"]) == (1, 1, 0)

    viagem = client.post(f"{API}/motorista/rotas/{rota}/viagem/iniciar", headers=cen["m1"]).json()["id"]
    assert client.get(f"{API}/dashboard", headers=a).json()["viagens_em_andamento"] == 1
    client.post(f"{API}/motorista/viagens/{viagem}/encerrar", headers=cen["m1"])
    assert client.get(f"{API}/dashboard", headers=a).json()["viagens_em_andamento"] == 0


def test_aluno_inativo_nao_conta(client, cen, db):
    from app.models import Aluno

    db.get(Aluno, cen["filho_a"]).ativo = False
    db.commit()
    assert client.get(f"{API}/dashboard", headers=cen["admin"]).json()["alunos_ativos"] == 1


def test_ocorrencias_recentes_e_contagem(client, cen):
    a = cen["admin"]
    for i in range(6):
        tipo = client.post(f"{API}/tipos-ocorrencia", headers=a, json={"nome": f"Tipo {i}"}).json()["id"]
        r = client.post(
            f"{API}/ocorrencias",
            headers=a,
            json={
                "aluno_id": cen["filho_a"],
                "tipo_id": tipo,
                "data": f"2099-01-0{i + 1}",
                "gravidade": "LEVE",
                "descricao": f"Ocorrência {i}",
            },
        )
        assert r.status_code == 201, r.text
    d = client.get(f"{API}/dashboard", headers=a).json()
    assert len(d["ocorrencias_recentes"]) == 5  # só as 5 mais recentes
    assert d["ocorrencias_recentes"][0]["tipo_nome"] == "Tipo 5"  # a mais nova primeiro
    assert d["ocorrencias_recentes"][0]["aluno_nome"] == "Filho A"
    assert d["ocorrencias_30_dias"] == 0  # datas futuras não entram na contagem dos últimos 30 dias


def test_ocorrencia_de_hoje_entra_nos_30_dias(client, cen):
    from datetime import date

    a = cen["admin"]
    tipo = client.post(f"{API}/tipos-ocorrencia", headers=a, json={"nome": "Atraso"}).json()["id"]
    client.post(
        f"{API}/ocorrencias",
        headers=a,
        json={
            "aluno_id": cen["filho_a"],
            "tipo_id": tipo,
            "data": date.today().isoformat(),
            "gravidade": "MEDIA",
            "descricao": "Chegou tarde",
        },
    )
    d = client.get(f"{API}/dashboard", headers=a).json()
    assert d["ocorrencias_30_dias"] == 1 and d["ocorrencias_recentes"][0]["gravidade"] == "MEDIA"


def test_isolamento_entre_empresas(client, cen):
    a = cen["admin"]
    client.post(f"{API}/veiculos", headers=a, json={"placa": "ABC1D23", "apelido": "Van", "capacidade": 10})
    d = client.get(f"{API}/dashboard", headers=cen["admin2"]).json()
    assert d["alunos_ativos"] == 0 and d["veiculos_ativos"] == 0 and d["motoristas"] == 0
    assert d["ocorrencias_recentes"] == []