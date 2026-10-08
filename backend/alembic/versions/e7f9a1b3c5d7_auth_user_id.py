"""auth_user_id

Revision ID: e7f9a1b3c5d7
Revises: c5d7e9f1a3b5
"""
import sqlalchemy as sa
from alembic import op

revision = "e7f9a1b3c5d7"
down_revision = "c5d7e9f1a3b5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("usuarios", sa.Column("auth_user_id", sa.String(length=36), nullable=True))
    op.create_index("ix_usuarios_auth_user_id", "usuarios", ["auth_user_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_usuarios_auth_user_id", table_name="usuarios")
    op.drop_column("usuarios", "auth_user_id")