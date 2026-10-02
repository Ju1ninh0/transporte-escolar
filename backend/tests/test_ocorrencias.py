from datetime import date

from sqlalchemy import select

from app.core.security import hash_senha
from app.models import Aluno, Empresa, Perfil, RegraReincidencia, Responsavel, TipoOcorrencia, Usuario

SENHA = "senha-teste-123"  # mesma do conftest
URL = "/api/v1/ocorrencias"
URL_TIPOS = "/api/v1/tipos-ocorrencia"


def _ctx(db, dados):
    """Completa o `dados` do conftest: tipos, regras e uma 2ª empresa."""
    emp = db.scalar(select(Empresa).where(Empresa.nome == "Teste"))
    tipo = TipoOcorrencia(empresa_id=emp.id, nome="Comportamento")
    inativo = TipoOcorrencia(empresa_id=emp.id, nome="Antigo", ativo=False)
    db.add_all([
        tipo, inativo,
        RegraReincidencia(empresa_id=emp.id, numero_ocorrencia=1, consequencia="Advertência"),
        RegraReincidencia(empresa_id=emp.id, numero_ocorrencia=2, consequencia="Advertência formal"),
    ])
    outra = Empresa(nome="Outra")
    db.add(outra)
    db.flush()
    adm = Usuario(empresa_id=outra.id, nome="adm", email="admin@outra.com",
                  senha_hash=hash_senha(SENHA), perfil=Perfil.ADMIN)
    ur = Usuario(empresa_id=outra.id, nome="resp", email="resp@outra.com",
                 senha_hash=hash_senha(SENHA), perfil=Perfil.RESPONSAVEL)
    db.add_all([adm, ur])
    db.flush()
    resp = Responsavel(empresa_id=outra.id, usuario_id=ur.id)
    db.add(resp)
    db.flush()
    aluno_o = Aluno(empresa_id=outra.id, responsavel_id=resp.id, nome="Aluno Outra",
                    data_nascimento=date(2015, 1, 1), escola="E")
    tipo_o = TipoOcorrencia(empresa_id=outra.id, nome="Tipo da outra")
    db.add_all([aluno_o, tipo_o])
    db.commit()
    return {**dados, "tipo": tipo.id, "tipo_inativo": inativo.id,
            "aluno_outra": aluno_o.id, "tipo_outra": tipo_o.id}


def _payload(c, **kw):
    return {"aluno_id": c["filho_a"], "tipo_id": c["tipo"], "data": "2026-10-01",
            "gravidade": "LEVE", "descricao": "Levantou durante o trajeto.", **kw}


def _criar(client, h, c, **kw):
    r = client.post(URL, json=_payload(c, **kw), headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def test_admin_cria_e_consulta(client, db, dados, login):
    c, h = _ctx(db, dados), login("admin@t.com")
    oc = _criar(client, h, c, consequencia="Advertência")
    assert oc["aluno_nome"] == "Filho A"
    assert oc["tipo_nome"] == "Comportamento"
    assert oc["registrado_por_nome"] == "admin@t.com"
    r = client.get(f"{URL}/{oc['id']}", headers=h)
    assert r.status_code == 200
    assert r.json()["consequencia"] == "Advertência"


def test_admin_lista_com_filtros(client, db, dados, login):
    c, h = _ctx(db, dados), login("admin@t.com")
    _criar(client, h, c, data="2026-09-01")
    _criar(client, h, c, aluno_id=c["filho_b"], gravidade="GRAVE")
    assert len(client.get(URL, headers=h).json()) == 2
    assert len(client.get(f"{URL}?gravidade=GRAVE", headers=h).json()) == 1
    assert len(client.get(f"{URL}?aluno_id={c['filho_a']}", headers=h).json()) == 1
    assert len(client.get(f"{URL}?tipo_id={c['tipo']}", headers=h).json()) == 2
    assert len(client.get(f"{URL}?data_inicio=2026-10-01", headers=h).json()) == 1


def test_admin_atualiza(client, db, dados, login):
    c, h = _ctx(db, dados), login("admin@t.com")
    oc = _criar(client, h, c)
    r = client.patch(f"{URL}/{oc['id']}", headers=h,
                     json={"gravidade": "MEDIA", "consequencia": "Suspensão"})
    assert r.status_code == 200
    assert r.json()["gravidade"] == "MEDIA"
    assert r.json()["consequencia"] == "Suspensão"
    assert r.json()["descricao"] == oc["descricao"]


def test_atualizar_para_tipo_inativo_falha(client, db, dados, login):
    c, h = _ctx(db, dados), login("admin@t.com")
    oc = _criar(client, h, c)
    r = client.patch(f"{URL}/{oc['id']}", headers=h, json={"tipo_id": c["tipo_inativo"]})
    assert r.status_code == 400


def test_aluno_inexistente(client, db, dados, login):
    c, h = _ctx(db, dados), login("admin@t.com")
    r = client.post(URL, json=_payload(c, aluno_id=99999), headers=h)
    assert r.status_code == 404


def test_aluno_de_outra_empresa(client, db, dados, login):
    c, h = _ctx(db, dados), login("admin@t.com")
    r = client.post(URL, json=_payload(c, aluno_id=c["aluno_outra"]), headers=h)
    assert r.status_code == 404


def test_tipo_de_outra_empresa(client, db, dados, login):
    c, h = _ctx(db, dados), login("admin@t.com")
    r = client.post(URL, json=_payload(c, tipo_id=c["tipo_outra"]), headers=h)
    assert r.status_code == 404


def test_tipo_inativo(client, db, dados, login):
    c, h = _ctx(db, dados), login("admin@t.com")
    r = client.post(URL, json=_payload(c, tipo_id=c["tipo_inativo"]), headers=h)
    assert r.status_code == 400


def test_gravidade_invalida_e_descricao_vazia(client, db, dados, login):
    c, h = _ctx(db, dados), login("admin@t.com")
    assert client.post(URL, json=_payload(c, gravidade="XYZ"), headers=h).status_code == 422
    assert client.post(URL, json=_payload(c, descricao="   "), headers=h).status_code == 422


def test_admin_de_outra_empresa_nao_acessa(client, db, dados, login):
    c = _ctx(db, dados)
    oc = _criar(client, login("admin@t.com"), c)
    h2 = login("admin@outra.com")
    assert client.get(f"{URL}/{oc['id']}", headers=h2).status_code == 404
    assert client.patch(f"{URL}/{oc['id']}", headers=h2, json={"gravidade": "GRAVE"}).status_code == 404
    assert client.get(URL, headers=h2).json() == []


def test_sem_permissao(client, db, dados, login):
    c = _ctx(db, dados)
    h = login("a@t.com")  # RESPONSAVEL
    assert client.get(URL, headers=h).status_code == 403
    assert client.post(URL, json=_payload(c), headers=h).status_code == 403
    assert client.get(URL).status_code == 401


def test_sugestao_consequencia(client, db, dados, login):
    c, h = _ctx(db, dados), login("admin@t.com")
    url = f"{URL}/sugestao-consequencia?aluno_id={c['filho_a']}"
    assert client.get(url, headers=h).json()["consequencia"] == "Advertência"
    for _ in range(3):
        _criar(client, h, c)
    r = client.get(url, headers=h).json()
    assert r["numero_ocorrencia"] == 4
    assert r["consequencia"] == "Advertência formal"  # acima da última regra usa a maior


def test_sugestao_aluno_de_outra_empresa(client, db, dados, login):
    c, h = _ctx(db, dados), login("admin@t.com")
    r = client.get(f"{URL}/sugestao-consequencia?aluno_id={c['aluno_outra']}", headers=h)
    assert r.status_code == 404


def test_tipos_criar_listar_desativar(client, db, dados, login):
    c, h = _ctx(db, dados), login("admin@t.com")
    r = client.post(URL_TIPOS, json={"nome": "Atraso"}, headers=h)
    assert r.status_code == 201
    tid = r.json()["id"]
    assert client.post(URL_TIPOS, json={"nome": "atraso"}, headers=h).status_code == 409
    nomes = [t["nome"] for t in client.get(URL_TIPOS, headers=h).json()]
    assert "Atraso" in nomes and "Tipo da outra" not in nomes
    r = client.patch(f"{URL_TIPOS}/{tid}", json={"ativo": False}, headers=h)
    assert r.json()["ativo"] is False
    assert client.patch(f"{URL_TIPOS}/{c['tipo_outra']}", json={"ativo": False}, headers=h).status_code == 404
    assert client.get(URL_TIPOS, headers=login("a@t.com")).status_code == 403