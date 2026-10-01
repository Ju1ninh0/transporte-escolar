from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.mixins import TimestampMixin


class Responsavel(TimestampMixin, Base):
    __tablename__ = "responsaveis"
    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), unique=True)
    endereco: Mapped[str | None] = mapped_column(String(255))


class Motorista(TimestampMixin, Base):
    __tablename__ = "motoristas"
    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), unique=True)


class Aluno(TimestampMixin, Base):
    __tablename__ = "alunos"
    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    responsavel_id: Mapped[int] = mapped_column(ForeignKey("responsaveis.id"), index=True)
    nome: Mapped[str] = mapped_column(String(120))
    data_nascimento: Mapped[date] = mapped_column(Date)
    escola: Mapped[str] = mapped_column(String(120))
    serie: Mapped[str | None] = mapped_column(String(40))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
