from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.core.security import hash_senha
from app.models import Aluno, Empresa, Perfil, Responsavel, Usuario

SENHA = "senha-teste-123"
F = "/api/v1/financeiro"


def _mes():
    return date.today().replace(day=1).isoformat()


def _futuro():
    return (date.today() + timedelta(days=10)).isoformat()


def _passado():
    return (date.today() - timedelta(days=1)).isoformat()


@pytest.fixture()
def outra_empresa(db):
    emp = Empresa(nome="Outra")
    db.add(emp)
    db.flush()
    adm = Usuario(empresa_id=emp.id, nome="Admin 2", email="admin2@o.com",
                  senha_hash=hash_senha(SENHA), perfil=Perfil.ADMIN)
    ur = Usuario(empresa_id=emp.id, nome="Resp 2", email="resp2@o.com",
                 senha_hash=hash_senha(SENHA), perfil=Perfil.RESPONSAVEL)
    db.add_all([adm, ur])
    db.flush()
    resp = Responsavel(empresa_id=emp.id, usuario_id=ur.id)
    db.add(resp)
    db.flush()
    aluno = Aluno(empresa_id=emp.id, responsavel_id=resp.id, nome="Aluno Outra",
                  data_nascimento=date(2015, 1, 1), escola="E")
    db.add(aluno)
    db.commit()
    return {"aluno": aluno.id}


def _criar(client, headers, aluno_id, valor="200.00", vencimento=None, mes=None):
    return client.post(F + "/mensalidades", headers=headers, json={
        "aluno_id": aluno_id, "mes_referencia": mes or _mes(),
        "vencimento": vencimento or _futuro(), "valor": valor})


def _pagar(client, headers, mid, valor):
    return client.post(f"{F}/mensalidades/{mid}/pagamentos", headers=headers, json={
        "valor": valor, "data_pagamento": date.today().isoformat(), "metodo": "PIX"})


def test_admin_lista_mensalidades(client, dados, login):
    h = login("admin@t.com")
    _criar(client, h, dados["filho_a"])
    r = client.get(F + "/mensalidades", headers=h)
    assert r.status_code == 200
    assert [m["aluno_nome"] for m in r.json()] == ["Filho A"]


def test_admin_cria_mensalidade(client, dados, login):
    r = _criar(client, login("admin@t.com"), dados["filho_a"])
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "PENDENTE"
    assert Decimal(body["saldo"]) == Decimal("200")
    assert body["responsavel_nome"] == "a@t.com"


def test_duplicidade_retorna_409(client, dados, login):
    h = login("admin@t.com")
    assert _criar(client, h, dados["filho_a"]).status_code == 201
    assert _criar(client, h, dados["filho_a"]).status_code == 409


def test_detalhes_com_pagamentos(client, dados, login):
    h = login("admin@t.com")
    mid = _criar(client, h, dados["filho_a"]).json()["id"]
    _pagar(client, h, mid, "50.00")
    r = client.get(f"{F}/mensalidades/{mid}", headers=h)
    assert r.status_code == 200
    assert len(r.json()["pagamentos"]) == 1


def test_pagamento_parcial_mantem_pendente(client, dados, login):
    h = login("admin@t.com")
    mid = _criar(client, h, dados["filho_a"]).json()["id"]
    r = _pagar(client, h, mid, "50.00")
    assert r.status_code == 201
    assert r.json()["status"] == "PENDENTE"
    assert Decimal(r.json()["saldo"]) == Decimal("150")


def test_pagamento_integral_marca_pago(client, dados, login):
    h = login("admin@t.com")
    mid = _criar(client, h, dados["filho_a"]).json()["id"]
    assert _pagar(client, h, mid, "200.00").json()["status"] == "PAGO"
    lista = client.get(F + "/mensalidades", headers=h).json()
    assert lista[0]["status"] == "PAGO"
    assert _pagar(client, h, mid, "1.00").status_code == 409


def test_pagamento_acima_do_saldo_retorna_400(client, dados, login):
    h = login("admin@t.com")
    mid = _criar(client, h, dados["filho_a"], valor="250.00").json()["id"]
    assert _pagar(client, h, mid, "200.00").status_code == 201
    assert _pagar(client, h, mid, "60.00").status_code == 400
    det = client.get(f"{F}/mensalidades/{mid}", headers=h).json()
    assert len(det["pagamentos"]) == 1


@pytest.mark.parametrize("valor", ["0", "-5.00"])
def test_pagamento_zero_ou_negativo_retorna_400(client, dados, login, valor):
    h = login("admin@t.com")
    mid = _criar(client, h, dados["filho_a"]).json()["id"]
    assert _pagar(client, h, mid, valor).status_code == 400


def test_mensalidade_vencida_aparece_atrasada(client, dados, login):
    h = login("admin@t.com")
    r = _criar(client, h, dados["filho_a"], vencimento=_passado())
    assert r.json()["status"] == "ATRASADO"
    atrasadas = client.get(F + "/mensalidades?status=ATRASADO", headers=h).json()
    assert len(atrasadas) == 1


def test_patch_atrasado_nao_e_persistido(client, dados, login):
    h = login("admin@t.com")
    mid = _criar(client, h, dados["filho_a"]).json()["id"]
    r = client.patch(f"{F}/mensalidades/{mid}", headers=h, json={"status": "ATRASADO"})
    assert r.status_code == 200
    assert r.json()["status"] == "PENDENTE"


def test_cancelada_nao_vira_atrasada_nem_aceita_pagamento(client, dados, login):
    h = login("admin@t.com")
    mid = _criar(client, h, dados["filho_a"], vencimento=_passado()).json()["id"]
    r = client.patch(f"{F}/mensalidades/{mid}", headers=h, json={"status": "CANCELADO"})
    assert r.json()["status"] == "CANCELADO"
    assert client.get(f"{F}/mensalidades/{mid}", headers=h).json()["status"] == "CANCELADO"
    assert _pagar(client, h, mid, "10.00").status_code == 409


def test_resumo_financeiro(client, dados, login):
    h = login("admin@t.com")
    a = _criar(client, h, dados["filho_a"], valor="200.00").json()["id"]
    _pagar(client, h, a, "50.00")
    _criar(client, h, dados["filho_b"], valor="100.00", vencimento=_passado())
    r = client.get(F + "/resumo", headers=h)
    assert r.status_code == 200
    res = {k: Decimal(v) for k, v in r.json().items()}
    assert res == {"total_previsto": Decimal("300"), "total_recebido": Decimal("50"),
                   "total_pendente": Decimal("150"), "total_atrasado": Decimal("100")}


def test_aluno_de_outra_empresa_retorna_404(client, dados, outra_empresa, login):
    r = _criar(client, login("admin@t.com"), outra_empresa["aluno"])
    assert r.status_code == 404


def test_mensalidade_de_outra_empresa_retorna_404(client, dados, outra_empresa, login):
    h1, h2 = login("admin@t.com"), login("admin2@o.com")
    mid = _criar(client, h2, outra_empresa["aluno"]).json()["id"]
    assert client.get(f"{F}/mensalidades/{mid}", headers=h1).status_code == 404
    assert client.patch(f"{F}/mensalidades/{mid}", headers=h1, json={"valor": "1.00"}).status_code == 404
    assert client.get(F + "/mensalidades", headers=h1).json() == []


def test_pagamento_em_mensalidade_de_outra_empresa_retorna_404(client, dados, outra_empresa, login):
    h1, h2 = login("admin@t.com"), login("admin2@o.com")
    mid = _criar(client, h2, outra_empresa["aluno"]).json()["id"]
    assert _pagar(client, h1, mid, "10.00").status_code == 404


def test_nao_admin_nao_acessa_financeiro(client, dados, login):
    h = login("a@t.com")
    assert client.get(F + "/resumo", headers=h).status_code == 403
    assert client.get(F + "/mensalidades", headers=h).status_code == 403
    assert _criar(client, h, dados["filho_a"]).status_code == 403