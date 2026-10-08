import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.mixins import TimestampMixin


class Perfil(str, enum.Enum):
    ADMIN = "ADMIN"
    MOTORISTA = "MOTORISTA"
    RESPONSAVEL = "RESPONSAVEL"


class Empresa(TimestampMixin, Base):
    __tablename__ = "empresas"
    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(120))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)


class Usuario(TimestampMixin, Base):
    __tablename__ = "usuarios"
    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    nome: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    telefone: Mapped[str | None] = mapped_column(String(20))
    auth_user_id: Mapped[str | None] = mapped_column(String(36), unique=True, index=True)
    senha_hash: Mapped[str] = mapped_column(String(255))
    perfil: Mapped[Perfil] = mapped_column(Enum(Perfil, native_enum=False, length=20))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revogado: Mapped[bool] = mapped_column(Boolean, default=False)