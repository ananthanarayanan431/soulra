"""add personal_note to journal_entries

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-09

"""

from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "journal_entries",
        sa.Column("personal_note", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("journal_entries", "personal_note")
