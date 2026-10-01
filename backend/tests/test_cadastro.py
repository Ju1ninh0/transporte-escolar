def test_admin_cadastra_responsavel_e_aluno(client, dados, login):
    h = login("admin@t.com")
    r = client.post("/api/v1/responsaveis", headers=h, json={
        "nome": "Novo Resp", "email": "novo@t.com", "senha": "outra-senha-123"})
    assert r.status_code == 201
    a = client.post("/api/v1/alunos", headers=h, json={
        "nome": "Aluno Novo", "data_nascimento": "2016-05-05", "escola": "Escola", "responsavel_id": r.json()["id"]})
    assert a.status_code == 201


def test_email_duplicado(client, dados, login):
    r = client.post("/api/v1/responsaveis", headers=login("admin@t.com"), json={
        "nome": "Dup Resp", "email": "a@t.com", "senha": "outra-senha-123"})
    assert r.status_code == 409


def test_desativar_aluno(client, dados, login):
    h = login("admin@t.com")
    assert client.delete(f"/api/v1/alunos/{dados['filho_a']}", headers=h).status_code == 204
    assert len(client.get("/api/v1/alunos", headers=h).json()) == 1
