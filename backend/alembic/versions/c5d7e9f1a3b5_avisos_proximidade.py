"""avisos_proximidade

Revision ID: c5d7e9f1a3b5
Revises: a4b7c9d1e2f3
"""
import sqlalchemy as sa
from alembic import op

revision = "c5d7e9f1a3b5"
down_revision = "a4b7c9d1e2f3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "avisos_proximidade",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("historico_rota_id", sa.Integer(), nullable=False),
        sa.Column("parada_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["historico_rota_id"], ["historico_rotas.id"]),
        sa.ForeignKeyConstraint(["parada_id"], ["paradas.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("historico_rota_id", "parada_id"),
    )
    op.create_index(
        op.f("ix_avisos_proximidade_historico_rota_id"), "avisos_proximidade", ["historico_rota_id"]
    )
    op.create_index(op.f("ix_avisos_proximidade_parada_id"), "avisos_proximidade", ["parada_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_avisos_proximidade_parada_id"), table_name="avisos_proximidade")
    op.drop_index(op.f("ix_avisos_proximidade_historico_rota_id"), table_name="avisos_proximidade")
    op.drop_table("avisos_proximidade")