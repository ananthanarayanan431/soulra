"""add index on token_usage_log.conversation_id

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-11

"""

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_token_usage_log_conversation_id", "token_usage_log", ["conversation_id"])


def downgrade() -> None:
    op.drop_index("ix_token_usage_log_conversation_id", table_name="token_usage_log")
