from datetime import date
from decimal import Decimal

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models import (Aluno, Mensalidade, Pagamento, Responsavel,
                        StatusMensalidade, Usuario)
from app.schemas.financeiro import MensalidadeDetalhe, MensalidadeOut, PagamentoOut

PAGAMENTO_CONFIRMADO = "CONFIRMADO"
ZERO = Decimal("0.00")


def hoje() -> date:
    return date.today()


def query_base(empresa_id: int) -> Select:
    return (
        select(Mensalidade, Aluno.nome, Usuario.nome)
        .join(Aluno, Aluno.id == Mensalidade.aluno_id)
        .join(Responsavel, Responsavel.id == Mensalidade.responsavel_id)
        .join(Usuario, Usuario.id == Responsavel.usuario_id)
        .where(Mensalidade.empresa_id == empresa_id)
    )


def get_mensalidade_ou_none(db: Session, empresa_id: int, mensalidade_id: int,
                            for_update: bool = False):
    q = query_base(empresa_id).where(Mensalidade.id == mensalidade_id)
    if for_update:
        q = q.with_for_update(of=Mensalidade)
    return db.execute(q).first()


def totais_pagos(db: Session, ids: list[int]) -> dict[int, Decimal]:
    if not ids:
        return {}
    rows = db.execute(
        select(Pagamento.mensalidade_id, func.sum(Pagamento.valor))
        .where(Pagamento.mensalidade_id.in_(ids),
               Pagamento.status == PAGAMENTO_CONFIRMADO)
        .group_by(Pagamento.mensalidade_id)
    ).all()
    return {mid: total for mid, total in rows}


def total_pago(db: Session, mensalidade_id: int) -> Decimal:
    return totais_pagos(db, [mensalidade_id]).get(mensalidade_id, ZERO)


def saldo_mensalidade(m: Mensalidade, pago: Decimal) -> Decimal:
    return max(m.valor - pago, ZERO)


def status_efetivo(m: Mensalidade, pago: Decimal, ref: date) -> StatusMensalidade:
    if m.status == StatusMensalidade.CANCELADO:
        return StatusMensalidade.CANCELADO
    if pago >= m.valor:
        return StatusMensalidade.PAGO
    if m.vencimento < ref:
        return StatusMensalidade.ATRASADO
    return StatusMensalidade.PENDENTE


def sincronizar_status(m: Mensalidade, pago: Decimal) -> None:
    """Persiste apenas PENDENTE, PAGO ou CANCELADO (ATRASADO nunca e salvo)."""
    if m.status == StatusMensalidade.CANCELADO:
        return
    m.status = StatusMensalidade.PAGO if pago >= m.valor else StatusMensalidade.PENDENTE


def listar_pagamentos(db: Session, mensalidade_id: int) -> list[Pagamento]:
    return list(db.scalars(
        select(Pagamento)
        .where(Pagamento.mensalidade_id == mensalidade_id,
               Pagamento.status == PAGAMENTO_CONFIRMADO)
        .order_by(Pagamento.data_pagamento, Pagamento.id)
    ))


def to_out(m: Mensalidade, aluno_nome: str, responsavel_nome: str,
           pago: Decimal, ref: date) -> MensalidadeOut:
    return MensalidadeOut(
        id=m.id, aluno_id=m.aluno_id, aluno_nome=aluno_nome,
        responsavel_id=m.responsavel_id, responsavel_nome=responsavel_nome,
        mes_referencia=m.mes_referencia, valor=m.valor, valor_pago=pago,
        saldo=saldo_mensalidade(m, pago), vencimento=m.vencimento,
        status=status_efetivo(m, pago, ref),
        created_at=m.created_at, updated_at=m.updated_at,
    )


def to_detalhe(db: Session, m: Mensalidade, aluno_nome: str,
               responsavel_nome: str, pago: Decimal, ref: date) -> MensalidadeDetalhe:
    base = to_out(m, aluno_nome, responsavel_nome, pago, ref)
    pagamentos = [PagamentoOut.model_validate(p) for p in listar_pagamentos(db, m.id)]
    return MensalidadeDetalhe(**base.model_dump(), pagamentos=pagamentos)