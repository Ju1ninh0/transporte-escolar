def test_admin_lista_responsaveis_com_nome_e_email(client, dados, login):
    r = client.get("/api/v1/responsaveis", headers=login("admin@t.com"))
    assert r.status_code == 200
    itens = r.json()
    assert sorted(x["nome"] for x in itens) == ["a@t.com", "b@t.com"]
    assert all(x["email"] and "telefone" in x for x in itens)