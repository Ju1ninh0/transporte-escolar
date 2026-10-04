from decimal import Decimal

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
    emp2 = Empresa(nome="Outra")
    db.add(emp2)
    db.flush()
    novo_usuario(emp2, "admin2@o.com", Perfil.ADMIN)
    db.add(m1)
    db.commit()
    return {
        "m1_id": m1.id,
        "filho_a": dados["filho_a"],
        "filho_b": dados["filho_b"],
        "admin": login("admin@t.com"),
        "admin2": login("admin2@o.com"),
        "m1": login("m1@t.com"),
        "ra": login("a@t.com"),
        "rb": login("b@t.com"),
    }


@pytest.fixture()
def rota(client, cen):
    """Rota Manhã (m1, van) com 2 paradas; só o Filho A está nela (na P1). Filho B fica sem rota."""
    a = cen["admin"]
    van = client.post(
        f"{API}/veiculos", headers=a, json={"placa": "ABC1D23", "apelido": "Van 1", "capacidade": 10}
    ).json()["id"]
    rid = client.post(
        f"{API}/rotas", headers=a, json={"nome": "Manhã", "veiculo_id": van, "motorista_id": cen["m1_id"]}
    ).json()["id"]
    p1 = client.post(
        f"{API}/rotas/{rid}/paradas", headers=a, json={"nome": "P1", "latitude": -9.6, "longitude": -35.7}
    ).json()["id"]
    client.post(
        f"{API}/rotas/{rid}/paradas", headers=a, json={"nome": "P2", "latitude": -9.7, "longitude": -35.8}
    )
    client.post(f"{API}/rotas/{rid}/alunos", headers=a, json={"aluno_id": cen["filho_a"], "parada_id": p1})
    return {"id": rid, "p1": p1}


def _iniciar(client, cen, rota):
    r = client.post(f"{API}/motorista/rotas/{rota['id']}/viagem/iniciar", headers=cen["m1"])
    assert r.status_code == 201, r.text
    return r.json()["id"]


# ------------------------------------------------------------- permissões
CAMINHOS = [
    "/responsavel/filhos",
    "/responsavel/filhos/1/acompanhamento",
    "/responsavel/filhos/1/presencas",
    "/responsavel/viagens/ativas",
    "/responsavel/mensalidades",
    "/responsavel/mensalidades/1",
    "/responsavel/pix",
    "/responsavel/ocorrencias",
    "/responsavel/avisos",
    "/responsavel/avisos/resumo",
]


@pytest.mark.parametrize("caminho", CAMINHOS)
def test_sem_token_401(client, caminho):
    assert client.get(f"{API}{caminho}").status_code == 401


@pytest.mark.parametrize("quem", ["admin", "m1"])
@pytest.mark.parametrize("caminho", CAMINHOS)
def test_so_responsavel_acessa_403(client, cen, quem, caminho):
    assert client.get(f"{API}{caminho}", headers=cen[quem]).status_code == 403


def test_responsavel_nao_envia_comunicado_403(client, cen):
    r = client.post(f"{API}/comunicados", headers=cen["ra"], json={"titulo": "x", "mensagem": "y"})
    assert r.status_code == 403
    assert client.post(f"{API}/comunicados", json={}).status_code == 401


# ------------------------------------------------------------------- filhos
def test_cada_responsavel_ve_so_os_proprios_filhos(client, cen, rota):
    fa = client.get(f"{API}/responsavel/filhos", headers=cen["ra"]).json()
    assert [f["nome"] for f in fa] == ["Filho A"]
    assert fa[0]["rotas"] == [
        {
            "rota_id": rota["id"],
            "rota_nome": "Manhã",
            "parada_id": rota["p1"],
            "parada_nome": "P1",
            "viagem_em_andamento_id": None,
        }
    ]
    fb = client.get(f"{API}/responsavel/filhos", headers=cen["rb"]).json()
    assert [f["nome"] for f in fb] == ["Filho B"]
    assert fb[0]["rotas"] == []


def test_filho_mostra_viagem_em_andamento(client, cen, rota):
    viagem = _iniciar(client, cen, rota)
    f = client.get(f"{API}/responsavel/filhos", headers=cen["ra"]).json()[0]
    assert f["rotas"][0]["viagem_em_andamento_id"] == viagem


# ------------------------------------------------------------ acompanhamento
def test_acompanhamento_sem_viagem(client, cen, rota):
    r = client.get(f"{API}/responsavel/filhos/{cen['filho_a']}/acompanhamento", headers=cen["ra"])
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["aluno_nome"] == "Filho A" and len(d["rotas"]) == 1
    rt = d["rotas"][0]
    assert rt["rota_nome"] == "Manhã" and rt["parada_nome"] == "P1"
    assert rt["veiculo_placa"] == "ABC1D23" and rt["motorista_nome"] == "m1"
    assert [p["nome"] for p in rt["paradas"]] == ["P1", "P2"]
    assert rt["viagem"] is None


def test_acompanhamento_com_viagem_posicao_e_chamada(client, cen, rota):
    viagem = _iniciar(client, cen, rota)
    url = f"{API}/responsavel/filhos/{cen['filho_a']}/acompanhamento"
    v = client.get(url, headers=cen["ra"]).json()["rotas"][0]["viagem"]
    assert v["viagem_id"] == viagem and v["posicao"] is None and v["status_chamada"] is None

    client.post(
        f"{API}/motorista/viagens/{viagem}/localizacao",
        headers=cen["m1"],
        json={"latitude": -9.61, "longitude": -35.71},
    )
    client.put(
        f"{API}/motorista/viagens/{viagem}/presencas/{cen['filho_a']}",
        headers=cen["m1"],
        json={"status": "PRESENTE"},
    )
    v = client.get(url, headers=cen["ra"]).json()["rotas"][0]["viagem"]
    assert v["posicao"]["latitude"] == -9.61
    assert v["status_chamada"] == "PRESENTE"


def test_acompanhamento_de_filho_alheio_404(client, cen, rota):
    r = client.get(f"{API}/responsavel/filhos/{cen['filho_a']}/acompanhamento", headers=cen["rb"])
    assert r.status_code == 404
    assert client.get(f"{API}/responsavel/filhos/99999/acompanhamento", headers=cen["ra"]).status_code == 404


def test_viagens_ativas_so_das_rotas_dos_filhos(client, cen, rota):
    assert client.get(f"{API}/responsavel/viagens/ativas", headers=cen["ra"]).json() == []
    viagem = _iniciar(client, cen, rota)
    a = client.get(f"{API}/responsavel/viagens/ativas", headers=cen["ra"]).json()
    assert [v["viagem_id"] for v in a] == [viagem]
    assert client.get(f"{API}/responsavel/viagens/ativas", headers=cen["rb"]).json() == []


# ----------------------------------------------------------------- presenças
def test_historico_de_presencas(client, cen, rota):
    primeira = _iniciar(client, cen, rota)
    client.put(
        f"{API}/motorista/viagens/{primeira}/presencas/{cen['filho_a']}",
        headers=cen["m1"],
        json={"status": "PRESENTE"},
    )
    client.post(f"{API}/motorista/viagens/{primeira}/encerrar", headers=cen["m1"])
    segunda = _iniciar(client, cen, rota)
    client.put(
        f"{API}/motorista/viagens/{segunda}/presencas/{cen['filho_a']}",
        headers=cen["m1"],
        json={"status": "FALTA", "observacao": "Doente"},
    )
    r = client.get(f"{API}/responsavel/filhos/{cen['filho_a']}/presencas", headers=cen["ra"])
    assert r.status_code == 200, r.text
    d = r.json()
    assert (d["presentes"], d["faltas"], d["dias"]) == (1, 1, 30)
    assert len(d["registros"]) == 2
    assert d["registros"][0]["viagem_id"] == segunda  # mais recente primeiro
    assert d["registros"][0]["status"] == "FALTA" and d["registros"][0]["observacao"] == "Doente"
    assert d["registros"][0]["rota_nome"] == "Manhã"


def test_historico_dias_invalido_e_filho_alheio(client, cen, rota):
    url = f"{API}/responsavel/filhos/{cen['filho_a']}/presencas"
    assert client.get(f"{url}?dias=0", headers=cen["ra"]).status_code == 422
    assert client.get(f"{url}?dias=1", headers=cen["ra"]).status_code == 200
    assert client.get(url, headers=cen["rb"]).status_code == 404


# --------------------------------------------------------------- financeiro
def _mensalidade(client, cen, aluno, valor="150.00"):
    r = client.post(
        f"{API}/financeiro/mensalidades",
        headers=cen["admin"],
        json={"aluno_id": aluno, "mes_referencia": "2099-10", "vencimento": "2099-10-10", "valor": valor},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_mensalidades_so_do_proprio_responsavel(client, cen):
    ma = _mensalidade(client, cen, cen["filho_a"])
    mb = _mensalidade(client, cen, cen["filho_b"], "200.00")
    la = client.get(f"{API}/responsavel/mensalidades", headers=cen["ra"]).json()
    assert [m["id"] for m in la] == [ma] and la[0]["status"] == "PENDENTE"
    lb = client.get(f"{API}/responsavel/mensalidades", headers=cen["rb"]).json()
    assert [m["id"] for m in lb] == [mb]


def test_mensalidade_detalhe_com_pagamentos(client, cen):
    m = _mensalidade(client, cen, cen["filho_a"])
    client.post(
        f"{API}/financeiro/mensalidades/{m}/pagamentos",
        headers=cen["admin"],
        json={"valor": "50.00", "data_pagamento": "2099-10-05", "metodo": "PIX"},
    )
    d = client.get(f"{API}/responsavel/mensalidades/{m}", headers=cen["ra"]).json()
    assert Decimal(d["valor_pago"]) == Decimal("50") and Decimal(d["saldo"]) == Decimal("100")
    assert [Decimal(p["valor"]) for p in d["pagamentos"]] == [Decimal("50")]
    assert client.get(f"{API}/responsavel/mensalidades/{m}", headers=cen["rb"]).status_code == 404
    assert client.get(f"{API}/responsavel/mensalidades/99999", headers=cen["ra"]).status_code == 404


def test_mensalidades_filtros(client, cen):
    m = _mensalidade(client, cen, cen["filho_a"])
    client.post(
        f"{API}/financeiro/mensalidades/{m}/pagamentos",
        headers=cen["admin"],
        json={"valor": "150.00", "data_pagamento": "2099-10-05", "metodo": "PIX"},
    )
    base = f"{API}/responsavel/mensalidades"
    assert [x["status"] for x in client.get(f"{base}?status=PAGO", headers=cen["ra"]).json()] == ["PAGO"]
    assert client.get(f"{base}?status=PENDENTE", headers=cen["ra"]).json() == []
    assert len(client.get(f"{base}?aluno_id={cen['filho_a']}", headers=cen["ra"]).json()) == 1
    assert client.get(f"{base}?aluno_id={cen['filho_b']}", headers=cen["ra"]).status_code == 404


def test_pix_para_pagamento(client, cen):
    assert client.get(f"{API}/responsavel/pix", headers=cen["ra"]).json() is None
    client.patch(
        f"{API}/configuracoes",
        headers=cen["admin"],
        json={"pix": {"recebedor": "Transporte X", "tipo_chave": "CNPJ", "chave": "12.345.678/0001-90", "mensagem": ""}},
    )
    d = client.get(f"{API}/responsavel/pix", headers=cen["ra"]).json()
    assert d == {
        "recebedor": "Transporte X",
        "tipo_chave": "CNPJ",
        "chave": "12.345.678/0001-90",
        "mensagem": None,
    }


# -------------------------------------------------------------- ocorrências
def _ocorrencia(client, cen, aluno, descricao):
    tipo = client.post(f"{API}/tipos-ocorrencia", headers=cen["admin"], json={"nome": f"Tipo {descricao}"})
    assert tipo.status_code == 201, tipo.text
    r = client.post(
        f"{API}/ocorrencias",
        headers=cen["admin"],
        json={
            "aluno_id": aluno,
            "tipo_id": tipo.json()["id"],
            "data": "2026-10-01",
            "gravidade": "LEVE",
            "descricao": descricao,
        },
    )
    assert r.status_code == 201, r.text


def test_ocorrencias_so_dos_proprios_filhos(client, cen):
    _ocorrencia(client, cen, cen["filho_a"], "Brigou")
    _ocorrencia(client, cen, cen["filho_b"], "Esqueceu o cinto")
    la = client.get(f"{API}/responsavel/ocorrencias", headers=cen["ra"]).json()
    assert [o["descricao"] for o in la] == ["Brigou"]
    assert la[0]["aluno_nome"] == "Filho A" and la[0]["gravidade"] == "LEVE"
    assert "registrado_por" not in la[0]
    assert [o["descricao"] for o in client.get(f"{API}/responsavel/ocorrencias", headers=cen["rb"]).json()] == [
        "Esqueceu o cinto"
    ]


def test_ocorrencias_filtro_por_filho_alheio_404(client, cen):
    r = client.get(f"{API}/responsavel/ocorrencias?aluno_id={cen['filho_b']}", headers=cen["ra"])
    assert r.status_code == 404


# ------------------------------------------------------------ avisos/comunicados
def test_comunicado_para_todos_chega_a_cada_responsavel(client, cen):
    r = client.post(
        f"{API}/comunicados",
        headers=cen["admin"],
        json={"titulo": "  Reunião  ", "mensagem": "Sábado às 9h"},
    )
    assert r.status_code == 201, r.text
    assert r.json() == {"destinatarios": 2}
    for quem in ("ra", "rb"):
        avisos = client.get(f"{API}/responsavel/avisos", headers=cen[quem]).json()
        assert len(avisos) == 1
        assert avisos[0]["titulo"] == "Reunião" and avisos[0]["tipo"] == "COMUNICADO"
        assert avisos[0]["lida"] is False
        assert client.get(f"{API}/responsavel/avisos/resumo", headers=cen[quem]).json() == {"nao_lidas": 1}


def test_comunicado_por_rota_so_chega_a_quem_tem_filho_nela(client, cen, rota):
    r = client.post(
        f"{API}/comunicados",
        headers=cen["admin"],
        json={"titulo": "Atraso", "mensagem": "Van atrasada", "rota_id": rota["id"]},
    )
    assert r.json() == {"destinatarios": 1}
    assert len(client.get(f"{API}/responsavel/avisos", headers=cen["ra"]).json()) == 1
    assert client.get(f"{API}/responsavel/avisos", headers=cen["rb"]).json() == []


def test_comunicado_rota_inexistente_ou_sem_alunos(client, cen):
    a = cen["admin"]
    r = client.post(f"{API}/comunicados", headers=a, json={"titulo": "x", "mensagem": "y", "rota_id": 99999})
    assert r.status_code == 404
    vazia = client.post(f"{API}/rotas", headers=a, json={"nome": "Vazia"}).json()["id"]
    r = client.post(f"{API}/comunicados", headers=a, json={"titulo": "x", "mensagem": "y", "rota_id": vazia})
    assert r.status_code == 400


def test_comunicado_de_outra_empresa_nao_alcanca_ninguem(client, cen):
    r = client.post(f"{API}/comunicados", headers=cen["admin2"], json={"titulo": "x", "mensagem": "y"})
    assert r.status_code == 400  # a outra empresa não tem responsáveis
    assert client.get(f"{API}/responsavel/avisos", headers=cen["ra"]).json() == []


@pytest.mark.parametrize(
    "corpo",
    [{"titulo": "", "mensagem": "y"}, {"titulo": "x", "mensagem": "   "}, {"titulo": "x" * 121, "mensagem": "y"}, {}],
)
def test_comunicado_invalido_422(client, cen, corpo):
    assert client.post(f"{API}/comunicados", headers=cen["admin"], json=corpo).status_code == 422


def test_marcar_aviso_como_lido(client, cen):
    client.post(f"{API}/comunicados", headers=cen["admin"], json={"titulo": "A", "mensagem": "a"})
    client.post(f"{API}/comunicados", headers=cen["admin"], json={"titulo": "B", "mensagem": "b"})
    avisos = client.get(f"{API}/responsavel/avisos", headers=cen["ra"]).json()
    assert [a["titulo"] for a in avisos] == ["B", "A"]  # mais recente primeiro

    r = client.post(f"{API}/responsavel/avisos/{avisos[0]['id']}/lida", headers=cen["ra"])
    assert r.status_code == 204
    assert client.get(f"{API}/responsavel/avisos/resumo", headers=cen["ra"]).json() == {"nao_lidas": 1}
    nao_lidas = client.get(f"{API}/responsavel/avisos?somente_nao_lidas=true", headers=cen["ra"]).json()
    assert [a["titulo"] for a in nao_lidas] == ["A"]

    # o aviso do outro responsável não pode ser marcado
    do_outro = client.get(f"{API}/responsavel/avisos", headers=cen["rb"]).json()[0]["id"]
    assert client.post(f"{API}/responsavel/avisos/{do_outro}/lida", headers=cen["ra"]).status_code == 404
    assert client.get(f"{API}/responsavel/avisos/resumo", headers=cen["rb"]).json() == {"nao_lidas": 2}


def test_marcar_todos_como_lidos(client, cen):
    for t in ("A", "B", "C"):
        client.post(f"{API}/comunicados", headers=cen["admin"], json={"titulo": t, "mensagem": t})
    assert client.post(f"{API}/responsavel/avisos/lidas", headers=cen["ra"]).status_code == 204
    assert client.get(f"{API}/responsavel/avisos/resumo", headers=cen["ra"]).json() == {"nao_lidas": 0}
    assert client.get(f"{API}/responsavel/avisos/resumo", headers=cen["rb"]).json() == {"nao_lidas": 3}