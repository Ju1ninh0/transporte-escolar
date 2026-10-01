from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select

from app.models import Aluno, Mensalidade, Pagamento, StatusMensalidade

VALOR = Decimal("250.00")


def _ultimo_dia(mes: date) -> date:
    return (mes + timedelta(days=32)).replace(day=1) - timedelta(days=1)


def seed_financeiro(db, empresa) -> None:
    """Dados financeiros de DESENVOLVIMENTO. Idempotente."""
    if empresa is None:
        return
    db.flush()
    hoje = date.today()
    mes = hoje.replace(day=1)
    anterior = (mes - timedelta(days=1)).replace(day=1)
    alunos = {a.nome: a for a in db.scalars(select(Aluno).where(Aluno.empresa_id == empresa.id))}

    def obter(aluno, ref, vencimento):
        m = db.scalar(select(Mensalidade).where(
            Mensalidade.empresa_id == empresa.id,
            Mensalidade.aluno_id == aluno.id,
            Mensalidade.mes_referencia == ref))
        if m is None:
            m = Mensalidade(empresa_id=empresa.id, aluno_id=aluno.id,
                            responsavel_id=aluno.responsavel_id, valor=VALOR,
                            mes_referencia=ref, vencimento=vencimento,
                            status=StatusMensalidade.PENDENTE)
            db.add(m)
            db.flush()
        return m

    ana, bruno, carla = (alunos.get(n) for n in ("Ana Demo", "Bruno Demo", "Carla Demo"))

    if ana:  # PENDENTE no mes atual
        obter(ana, mes, _ultimo_dia(mes))

    if bruno:  # PAGO no mes atual, com pagamento PIX
        m = obter(bruno, mes, mes.replace(day=5))
        if not db.scalar(select(Pagamento.id).where(Pagamento.mensalidade_id == m.id)):
            db.add(Pagamento(mensalidade_id=m.id, valor=m.valor, data_pagamento=hoje,
                             metodo="PIX", status="CONFIRMADO"))
            m.status = StatusMensalidade.PAGO

    if carla:  # mes anterior PENDENTE vencido -> aparece como ATRASADO
        obter(carla, anterior, anterior.replace(day=10))
    db.flush()