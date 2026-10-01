from tests.conftest import SENHA


def test_login_invalido(client, dados):
    r = client.post("/api/v1/auth/login", json={"email": "admin@t.com", "senha": "errada"})
    assert r.status_code == 401


def test_me_requer_token(client, dados):
    assert client.get("/api/v1/auth/me").status_code == 401


def test_me_com_token(client, dados, login):
    r = client.get("/api/v1/auth/me", headers=login("admin@t.com"))
    assert r.json()["perfil"] == "ADMIN"


def test_refresh_rotaciona_e_logout_revoga(client, dados):
    tokens = client.post("/api/v1/auth/login", json={"email": "a@t.com", "senha": SENHA}).json()
    novo = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert novo.status_code == 200
    reuso = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert reuso.status_code == 401
    rt = novo.json()["refresh_token"]
    assert client.post("/api/v1/auth/logout", json={"refresh_token": rt}).status_code == 204
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": rt}).status_code == 401
