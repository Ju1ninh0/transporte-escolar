from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.mixins import agora
from app.models.operacao import StatusFrequencia


class PresencaViagem(Base):
    """Presença/falta de um aluno em uma viagem (chamada feita pelo motorista)."""

    __tablename__ = "presencas_viagem"
    id: Mapped[int] = mapped_column(primary_key=True)
    historico_rota_id: Mapped[int] = mapped_column(ForeignKey("historico_rotas.id"), index=True)
    aluno_id: Mapped[int] = mapped_column(ForeignKey("alunos.id"), index=True)
    status: Mapped[StatusFrequencia] = mapped_column(
        Enum(StatusFrequencia, native_enum=False, length=20)
    )
    observacao: Mapped[str | None] = mapped_column(String(255))
    registrado_por: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    registrado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=agora, onupdate=agora
    )
    __table_args__ = (UniqueConstraint("historico_rota_id", "aluno_id"),)