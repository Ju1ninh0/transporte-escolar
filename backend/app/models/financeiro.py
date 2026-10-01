import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.mixins import TimestampMixin, agora


class StatusMensalidade(str, enum.Enum):
    PENDENTE = "PENDENTE"
    PAGO = "PAGO"
    ATRASADO = "ATRASADO"
    CANCELADO = "CANCELADO"


class Mensalidade(TimestampMixin, Base):
    __tablename__ = "mensalidades"
    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    aluno_id: Mapped[int] = mapped_column(ForeignKey("alunos.id"), index=True)
    responsavel_id: Mapped[int] = mapped_column(ForeignKey("responsaveis.id"), index=True)
    valor: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    mes_referencia: Mapped[date] = mapped_column(Date)
    vencimento: Mapped[date] = mapped_column(Date)
    status: Mapped[StatusMensalidade] = mapped_column(
        Enum(StatusMensalidade, native_enum=False, length=20), default=StatusMensalidade.PENDENTE
    )


class Pagamento(Base):
    __tablename__ = "pagamentos"
    id: Mapped[int] = mapped_column(primary_key=True)
    mensalidade_id: Mapped[int] = mapped_column(ForeignKey("mensalidades.id"), index=True)
    valor: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    data_pagamento: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="PENDENTE")
    metodo: Mapped[str] = mapped_column(String(20), default="PIX")
    comprovante: Mapped[str | None] = mapped_column(String(255))
    provider_ref: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)
