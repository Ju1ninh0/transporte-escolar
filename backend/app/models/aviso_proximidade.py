from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.mixins import agora


class AvisoProximidade(Base):
    """Registra que os responsáveis de uma parada já foram avisados nesta viagem (evita repetir)."""

    __tablename__ = "avisos_proximidade"
    id: Mapped[int] = mapped_column(primary_key=True)
    historico_rota_id: Mapped[int] = mapped_column(ForeignKey("historico_rotas.id"), index=True)
    parada_id: Mapped[int] = mapped_column(ForeignKey("paradas.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)
    __table_args__ = (UniqueConstraint("historico_rota_id", "parada_id"),)