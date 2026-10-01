from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.mixins import agora


class Notificacao(Base):
    __tablename__ = "notificacoes"
    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), index=True)
    tipo: Mapped[str] = mapped_column(String(40))
    titulo: Mapped[str] = mapped_column(String(120))
    mensagem: Mapped[str] = mapped_column(Text)
    lida: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)


class Configuracao(Base):
    __tablename__ = "configuracoes"
    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    chave: Mapped[str] = mapped_column(String(60))
    valor: Mapped[dict] = mapped_column(JSON)
    __table_args__ = (UniqueConstraint("empresa_id", "chave"),)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    acao: Mapped[str] = mapped_column(String(60))
    entidade: Mapped[str | None] = mapped_column(String(60))
    entidade_id: Mapped[int | None]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)
