"""traditions

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-07

"""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "traditions",
        sa.Column("slug", sa.String(80), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("origin", sa.String(120), nullable=False),
        sa.Column("era", sa.String(40), nullable=False),
        sa.Column("user_selected", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("description", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("slug"),
    )


def downgrade() -> None:
    op.drop_table("traditions")
