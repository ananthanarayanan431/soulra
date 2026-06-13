"""traditions per-user scoping + embedding user_id backfill

Revision ID: 0008
Revises: 0007
Create Date: 2026-06-13

"""

from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None

# Sole existing account in the dev DB — owns the existing "mahabharat"
# tradition row and its 1371 embedded chunks. One-time backfill only.
_BACKFILL_USER_ID = "user_3F2yAzuFB9vdrwZIsPNtxMQQmVV"


def upgrade() -> None:
    op.add_column("traditions", sa.Column("user_id", sa.String(length=255), nullable=True))
    op.execute(f"UPDATE traditions SET user_id = '{_BACKFILL_USER_ID}'")
    op.alter_column("traditions", "user_id", nullable=False)
    op.create_foreign_key(
        "fk_traditions_user_id", "traditions", "users", ["user_id"], ["id"], ondelete="CASCADE"
    )
    op.drop_constraint("traditions_pkey", "traditions", type_="primary")
    op.create_primary_key("traditions_pkey", "traditions", ["user_id", "slug"])

    op.execute(
        f"""
        UPDATE langchain_pg_embedding
        SET cmetadata = cmetadata || '{{"user_id": "{_BACKFILL_USER_ID}"}}'::jsonb
        WHERE cmetadata->>'tradition' = 'mahabharat'
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE langchain_pg_embedding
        SET cmetadata = cmetadata - 'user_id'
        WHERE cmetadata->>'tradition' = 'mahabharat'
        """
    )
    op.drop_constraint("traditions_pkey", "traditions", type_="primary")
    op.create_primary_key("traditions_pkey", "traditions", ["slug"])
    op.drop_constraint("fk_traditions_user_id", "traditions", type_="foreignkey")
    op.drop_column("traditions", "user_id")
