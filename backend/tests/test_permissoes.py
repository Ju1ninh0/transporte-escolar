def test_responsavel_lista_so_seus_filhos(client, dados, login):
    r = client.get("/api/v1/alunos", headers=login("a@t.com"))
    assert [a["nome"] for a in r.json()] == ["Filho A"]


def test_responsavel_nao_ve_filho_de_outro(client, dados, login):
    r = client.get(f"/api/v1/alunos/{dados['filho_b']}", headers=login("a@t.com"))
    assert r.status_code == 404


def test_responsavel_nao_cria_aluno(client, dados, login):
    body = {"nome": "X Y", "data_nascimento": "2016-01-01", "escola": "E", "responsavel_id": dados["resp_b"]}
    assert client.post("/api/v1/alunos", json=body, headers=login("a@t.com")).status_code == 403


def test_admin_ve_todos(client, dados, login):
    assert len(client.get("/api/v1/alunos", headers=login("admin@t.com")).json()) == 2
