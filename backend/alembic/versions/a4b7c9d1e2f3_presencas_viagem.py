"""presencas_viagem

Revision ID: a4b7c9d1e2f3
Revises: 788e35600694
"""
import sqlalchemy as sa
from alembic import op

revision = "a4b7c9d1e2f3"
down_revision = "788e35600694"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "presencas_viagem",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("historico_rota_id", sa.Integer(), nullable=False),
        sa.Column("aluno_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("PRESENTE", "FALTA", name="statusfrequencia", native_enum=False, length=20),
            nullable=False,
        ),
        sa.Column("observacao", sa.String(length=255), nullable=True),
        sa.Column("registrado_por", sa.Integer(), nullable=False),
        sa.Column("registrado_em", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["aluno_id"], ["alunos.id"]),
        sa.ForeignKeyConstraint(["historico_rota_id"], ["historico_rotas.id"]),
        sa.ForeignKeyConstraint(["registrado_por"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("historico_rota_id", "aluno_id"),
    )
    op.create_index(op.f("ix_presencas_viagem_aluno_id"), "presencas_viagem", ["aluno_id"])
    op.create_index(
        op.f("ix_presencas_viagem_historico_rota_id"), "presencas_viagem", ["historico_rota_id"]
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_presencas_viagem_historico_rota_id"), table_name="presencas_viagem")
    op.drop_index(op.f("ix_presencas_viagem_aluno_id"), table_name="presencas_viagem")
    op.drop_table("presencas_viagem")