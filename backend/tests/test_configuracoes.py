from sqlalchemy import select

from app.core.security import hash_senha
from app.models import Configuracao, Empresa, Perfil, RegraReincidencia, Usuario

SENHA = "senha-teste-123"  # mesma do conftest
URL = "/api/v1/configuracoes"


def _ctx(db):
    """Completa o conftest: configs/regras da empresa 'Teste' e uma 2ª empresa com as suas."""
    emp = db.scalar(select(Empresa).where(Empresa.nome == "Teste"))
    outra = Empresa(nome="Outra")
    db.add(outra)
    db.flush()
    db.add(Usuario(empresa_id=outra.id, nome="adm", email="admin@outra.com",
                   senha_hash=hash_senha(SENHA), perfil=Perfil.ADMIN))
    for e, nome, metros in ((emp, "Teste", 500), (outra, "Outra", 900)):
        db.add_all([
            Configuracao(empresa_id=e.id, chave="pix", valor={
                "recebedor": nome, "tipo_chave": "EMAIL",
                "chave": f"pix@{nome.lower()}.com", "mensagem": "Mensalidade"}),
            Configuracao(empresa_id=e.id, chave="proximidade_metros", valor={"metros": metros}),
            RegraReincidencia(empresa_id=e.id, numero_ocorrencia=1, consequencia=f"Adv {nome}"),
            RegraReincidencia(empresa_id=e.id, numero_ocorrencia=2, consequencia=f"Formal {nome}"),
        ])
    db.commit()


def test_admin_visualiza(client, db, dados, login):
    _ctx(db)
    r = client.get(URL, headers=login("admin@t.com"))
    assert r.status_code == 200
    j = r.json()
    assert j["pix"]["recebedor"] == "Teste"
    assert j["proximidade_metros"] == 500
    assert [x["consequencia"] for x in j["regras_reincidencia"]] == ["Adv Teste", "Formal Teste"]


def test_admin_altera(client, db, dados, login):
    _ctx(db)
    h = login("admin@t.com")
    pix = {"recebedor": "Novo", "tipo_chave": "CPF", "chave": "12345678900", "mensagem": "Msg"}
    r = client.patch(URL, headers=h, json={"pix": pix, "proximidade_metros": 300})
    assert r.status_code == 200
    j = client.get(URL, headers=h).json()
    assert j["pix"] == pix
    assert j["proximidade_metros"] == 300
    r = client.patch(f"{URL}/regras-reincidencia/2", headers=h, json={"consequencia": "Suspensão"})
    assert r.status_code == 200
    assert client.get(URL, headers=h).json()["regras_reincidencia"][1]["consequencia"] == "Suspensão"


def test_altera_so_proximidade_preserva_pix(client, db, dados, login):
    _ctx(db)
    h = login("admin@t.com")
    client.patch(URL, headers=h, json={"proximidade_metros": 700})
    j = client.get(URL, headers=h).json()
    assert j["proximidade_metros"] == 700
    assert j["pix"]["recebedor"] == "Teste"


def test_isolamento_entre_empresas(client, db, dados, login):
    _ctx(db)
    h1, h2 = login("admin@t.com"), login("admin@outra.com")
    client.patch(URL, headers=h1, json={"proximidade_metros": 111,
                                        "pix": {"recebedor": "X", "tipo_chave": "EMAIL", "chave": "x@x.com"}})
    client.patch(f"{URL}/regras-reincidencia/1", headers=h1, json={"consequencia": "Alterada"})
    j = client.get(URL, headers=h2).json()
    assert j["proximidade_metros"] == 900
    assert j["pix"]["recebedor"] == "Outra"
    assert j["regras_reincidencia"][0]["consequencia"] == "Adv Outra"
    assert client.patch(f"{URL}/regras-reincidencia/99", headers=h2,
                        json={"consequencia": "x"}).status_code == 404


def test_sem_permissao(client, db, dados, login):
    _ctx(db)
    h = login("a@t.com")  # RESPONSAVEL
    assert client.get(URL, headers=h).status_code == 403
    assert client.patch(URL, headers=h, json={"proximidade_metros": 1}).status_code == 403
    assert client.patch(f"{URL}/regras-reincidencia/1", headers=h,
                        json={"consequencia": "x"}).status_code == 403
    assert client.get(URL).status_code == 401


def test_validacao(client, db, dados, login):
    _ctx(db)
    h = login("admin@t.com")
    assert client.patch(URL, headers=h, json={"proximidade_metros": 0}).status_code == 422
    assert client.patch(URL, headers=h, json={"pix": {"recebedor": "A", "tipo_chave": "EMAIL", "chave": "  "}}).status_code == 422
    assert client.patch(f"{URL}/regras-reincidencia/1", headers=h, json={"consequencia": " "}).status_code == 422