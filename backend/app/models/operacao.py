import enum
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.mixins import agora


class StatusFrequencia(str, enum.Enum):
    PRESENTE = "PRESENTE"
    FALTA = "FALTA"


class Gravidade(str, enum.Enum):
    LEVE = "LEVE"
    MEDIA = "MEDIA"
    GRAVE = "GRAVE"


class Frequencia(Base):
    __tablename__ = "frequencias"
    id: Mapped[int] = mapped_column(primary_key=True)
    aluno_id: Mapped[int] = mapped_column(ForeignKey("alunos.id"), index=True)
    data: Mapped[date] = mapped_column(Date)
    status: Mapped[StatusFrequencia] = mapped_column(
        Enum(StatusFrequencia, native_enum=False, length=20)
    )
    observacao: Mapped[str | None] = mapped_column(String(255))
    registrado_por: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)
    __table_args__ = (UniqueConstraint("aluno_id", "data"),)


class TipoOcorrencia(Base):
    __tablename__ = "tipos_ocorrencia"
    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    nome: Mapped[str] = mapped_column(String(80))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)


class Ocorrencia(Base):
    __tablename__ = "ocorrencias"
    id: Mapped[int] = mapped_column(primary_key=True)
    aluno_id: Mapped[int] = mapped_column(ForeignKey("alunos.id"), index=True)
    tipo_id: Mapped[int] = mapped_column(ForeignKey("tipos_ocorrencia.id"))
    data: Mapped[date] = mapped_column(Date)
    gravidade: Mapped[Gravidade] = mapped_column(Enum(Gravidade, native_enum=False, length=20))
    descricao: Mapped[str] = mapped_column(Text)
    consequencia: Mapped[str | None] = mapped_column(String(120))
    registrado_por: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)


class RegraReincidencia(Base):
    __tablename__ = "regras_reincidencia"
    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    numero_ocorrencia: Mapped[int]
    consequencia: Mapped[str] = mapped_column(String(120))
    __table_args__ = (UniqueConstraint("empresa_id", "numero_ocorrencia"),)
