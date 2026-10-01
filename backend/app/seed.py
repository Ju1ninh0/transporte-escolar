"""Dados de DESENVOLVIMENTO. Senhas abaixo são SOMENTE DESENVOLVIMENTO."""
import os
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select

from app.core.security import hash_senha
from app.db.session import SessionLocal
from app.seed_financeiro import seed_financeiro
from app.models import (
    Aluno, Configuracao, Empresa, Frequencia, Gravidade, Mensalidade, Motorista,
    Ocorrencia, Parada, Perfil, RegraReincidencia, Responsavel, Rota, RotaAluno,
    StatusFrequencia, StatusMensalidade, TipoOcorrencia, Usuario, Veiculo,
)

SENHA_DEV = "dev-only-123"  # SOMENTE DESENVOLVIMENTO


def _usuario(db, empresa, nome, email, perfil):
    u = Usuario(
        empresa_id=empresa.id, nome=nome, email=email,
        senha_hash=hash_senha(SENHA_DEV), perfil=perfil,
    )
    db.add(u)
    db.flush()
    return u


def seed() -> None:
    if os.getenv("APP_ENV", "development") == "production":
        raise SystemExit("Seed bloqueado em produção.")
    with SessionLocal() as db:
        if db.scalar(select(Usuario.id).where(Usuario.email == "admin@demo.com")):
            seed_financeiro(db, db.scalar(select(Empresa).where(Empresa.nome == "Transporte Demo")))
            db.commit()
            print("Seed já aplicado.")
            return
        emp = Empresa(nome="Transporte Demo")
        db.add(emp)
        db.flush()
        _usuario(db, emp, "Admin Demo", "admin@demo.com", Perfil.ADMIN)
        um = _usuario(db, emp, "Motorista Demo", "motorista@demo.com", Perfil.MOTORISTA)
        ur = _usuario(db, emp, "Responsável Demo", "responsavel@demo.com", Perfil.RESPONSAVEL)
        mot = Motorista(empresa_id=emp.id, usuario_id=um.id)
        resp = Responsavel(empresa_id=emp.id, usuario_id=ur.id)
        van = Veiculo(empresa_id=emp.id, placa="ABC1D23", apelido="Van 01")
        db.add_all([mot, resp, van])
        db.flush()
        alunos = [
            Aluno(empresa_id=emp.id, responsavel_id=resp.id, nome=n,
                  data_nascimento=date(2015, 3, 10), escola="Escola Modelo", serie=s)
            for n, s in [("Ana Demo", "4º ano"), ("Bruno Demo", "2º ano"), ("Carla Demo", "5º ano")]
        ]
        rota = Rota(empresa_id=emp.id, nome="Rota Manhã", escola="Escola Modelo",
                    veiculo_id=van.id, motorista_id=mot.id)
        db.add_all([*alunos, rota])
        db.flush()
        paradas = [
            Parada(rota_id=rota.id, nome=f"Parada {i}", ordem=i,
                   latitude=-9.6658 + i * 0.002, longitude=-35.7353 + i * 0.002)
            for i in (1, 2, 3)
        ]
        db.add_all(paradas)
        db.flush()
        db.add_all(RotaAluno(rota_id=rota.id, aluno_id=a.id, parada_id=paradas[i].id)
                   for i, a in enumerate(alunos))
        hoje = date.today()
        for a in alunos:
            for d in range(1, 8):
                dia = hoje - timedelta(days=d)
                if dia.weekday() < 5:
                    st = StatusFrequencia.FALTA if d == 3 else StatusFrequencia.PRESENTE
                    db.add(Frequencia(aluno_id=a.id, data=dia, status=st, registrado_por=um.id))
            db.add(Mensalidade(
                empresa_id=emp.id, aluno_id=a.id, responsavel_id=resp.id, valor=Decimal("250.00"),
                mes_referencia=hoje.replace(day=1), vencimento=hoje.replace(day=10),
                status=StatusMensalidade.PENDENTE,
            ))
        tipos = [TipoOcorrencia(empresa_id=emp.id, nome=n)
                 for n in ("Comportamento", "Segurança", "Desrespeito", "Dano ao veículo", "Outro")]
        db.add_all(tipos)
        db.flush()
        db.add(Ocorrencia(aluno_id=alunos[1].id, tipo_id=tipos[0].id, data=hoje,
                          gravidade=Gravidade.LEVE, descricao="Levantou durante o trajeto.",
                          consequencia="Advertência", registrado_por=um.id))
        db.add_all(RegraReincidencia(empresa_id=emp.id, numero_ocorrencia=n, consequencia=c)
                   for n, c in [(1, "Advertência"), (2, "Advertência formal"),
                                (3, "Suspensão"), (4, "Avaliação administrativa")])
        db.add_all([
            Configuracao(empresa_id=emp.id, chave="proximidade_metros", valor={"metros": 500}),
            Configuracao(empresa_id=emp.id, chave="pix", valor={
                "recebedor": "Transporte Demo", "tipo_chave": "EMAIL",
                "chave": "pix@demo.com", "mensagem": "Mensalidade"}),
        ])
        seed_financeiro(db, emp)
        db.commit()
        print("Seed aplicado. Senha de todos (SOMENTE DESENVOLVIMENTO):", SENHA_DEV)


if __name__ == "__main__":
    seed()
