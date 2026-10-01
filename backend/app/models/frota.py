import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.mixins import TimestampMixin, agora


class StatusRota(str, enum.Enum):
    ATIVA = "ATIVA"
    INATIVA = "INATIVA"


class StatusExecucao(str, enum.Enum):
    EM_ANDAMENTO = "EM_ANDAMENTO"
    FINALIZADA = "FINALIZADA"


class Veiculo(TimestampMixin, Base):
    __tablename__ = "veiculos"
    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    placa: Mapped[str] = mapped_column(String(10))
    apelido: Mapped[str] = mapped_column(String(60))
    capacidade: Mapped[int] = mapped_column(default=15)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (UniqueConstraint("empresa_id", "placa"),)


class Rota(TimestampMixin, Base):
    __tablename__ = "rotas"
    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    nome: Mapped[str] = mapped_column(String(120))
    escola: Mapped[str | None] = mapped_column(String(120))
    veiculo_id: Mapped[int | None] = mapped_column(ForeignKey("veiculos.id"))
    motorista_id: Mapped[int | None] = mapped_column(ForeignKey("motoristas.id"))
    status: Mapped[StatusRota] = mapped_column(
        Enum(StatusRota, native_enum=False, length=20), default=StatusRota.ATIVA
    )


class Parada(Base):
    __tablename__ = "paradas"
    id: Mapped[int] = mapped_column(primary_key=True)
    rota_id: Mapped[int] = mapped_column(ForeignKey("rotas.id"), index=True)
    nome: Mapped[str] = mapped_column(String(120))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    ordem: Mapped[int]
    __table_args__ = (UniqueConstraint("rota_id", "ordem"),)


class RotaAluno(Base):
    __tablename__ = "rota_alunos"
    id: Mapped[int] = mapped_column(primary_key=True)
    rota_id: Mapped[int] = mapped_column(ForeignKey("rotas.id"), index=True)
    aluno_id: Mapped[int] = mapped_column(ForeignKey("alunos.id"), index=True)
    parada_id: Mapped[int | None] = mapped_column(ForeignKey("paradas.id"))
    __table_args__ = (UniqueConstraint("rota_id", "aluno_id"),)


class HistoricoRota(Base):
    __tablename__ = "historico_rotas"
    id: Mapped[int] = mapped_column(primary_key=True)
    rota_id: Mapped[int] = mapped_column(ForeignKey("rotas.id"), index=True)
    veiculo_id: Mapped[int | None] = mapped_column(ForeignKey("veiculos.id"))
    motorista_id: Mapped[int | None] = mapped_column(ForeignKey("motoristas.id"))
    iniciada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)
    finalizada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[StatusExecucao] = mapped_column(
        Enum(StatusExecucao, native_enum=False, length=20), default=StatusExecucao.EM_ANDAMENTO
    )


class Localizacao(Base):
    __tablename__ = "localizacoes"
    id: Mapped[int] = mapped_column(primary_key=True)
    veiculo_id: Mapped[int] = mapped_column(ForeignKey("veiculos.id"))
    historico_rota_id: Mapped[int | None] = mapped_column(ForeignKey("historico_rotas.id"))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    velocidade: Mapped[float | None] = mapped_column(Float)
    direcao: Mapped[float | None] = mapped_column(Float)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)
    __table_args__ = (Index("ix_localizacoes_veiculo_ts", "veiculo_id", "timestamp"),)
