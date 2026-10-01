import os

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["JWT_SECRET"] = "test-secret"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402
from datetime import date

import app.models  # noqa: E402, F401
from app.core.security import hash_senha  # noqa: E402
from app.db.session import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Aluno, Empresa, Perfil, Responsavel, Usuario  # noqa: E402

SENHA = "senha-teste-123"


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False)()
    yield session
    session.close()


@pytest.fixture()
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app)
    app.dependency_overrides.clear()


def _user(db, emp, email, perfil):
    u = Usuario(empresa_id=emp.id, nome=email, email=email, senha_hash=hash_senha(SENHA), perfil=perfil)
    db.add(u)
    db.flush()
    return u


@pytest.fixture()
def dados(db):
    emp = Empresa(nome="Teste")
    db.add(emp)
    db.flush()
    _user(db, emp, "admin@t.com", Perfil.ADMIN)
    ra, rb = _user(db, emp, "a@t.com", Perfil.RESPONSAVEL), _user(db, emp, "b@t.com", Perfil.RESPONSAVEL)
    resp_a, resp_b = Responsavel(empresa_id=emp.id, usuario_id=ra.id), Responsavel(empresa_id=emp.id, usuario_id=rb.id)
    db.add_all([resp_a, resp_b])
    db.flush()
    filho_a = Aluno(empresa_id=emp.id, responsavel_id=resp_a.id, nome="Filho A", data_nascimento=date(2015, 1, 1), escola="E")
    filho_b = Aluno(empresa_id=emp.id, responsavel_id=resp_b.id, nome="Filho B", data_nascimento=date(2015, 1, 1), escola="E")
    db.add_all([filho_a, filho_b])
    db.commit()
    return {"filho_a": filho_a.id, "filho_b": filho_b.id, "resp_b": resp_b.id}


@pytest.fixture()
def login(client):
    def _login(email):
        r = client.post("/api/v1/auth/login", json={"email": email, "senha": SENHA})
        assert r.status_code == 200
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    return _login
