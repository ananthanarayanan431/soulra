"""practice_daily

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-07

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tradition_cards",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("card_order", sa.Integer(), nullable=False),
        sa.Column("tradition", sa.Text(), nullable=False),
        sa.Column("author", sa.Text(), nullable=False),
        sa.Column("quote", sa.Text(), nullable=False),
        sa.Column("citation", sa.Text(), nullable=False),
        sa.Column("analysis", sa.Text(), nullable=False),
        sa.Column("source_passage", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tradition_cards_conversation_id", "tradition_cards", ["conversation_id"])

    op.create_table(
        "practice_arcs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("theme", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("current_day", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("conversation_id", name="uq_practice_arcs_conversation_id"),
    )
    op.create_index("ix_practice_arcs_conversation_id", "practice_arcs", ["conversation_id"])

    op.create_table(
        "practice_days",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("arc_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("day_number", sa.Integer(), nullable=False),
        sa.Column("day_label", sa.String(10), nullable=False),
        sa.Column("task_title", sa.Text(), nullable=False),
        sa.Column("task_body", sa.Text(), nullable=False),
        sa.Column("morning_quote", sa.Text(), nullable=False),
        sa.Column("morning_author", sa.Text(), nullable=False),
        sa.Column("morning_citation", sa.Text(), nullable=False),
        sa.Column("morning_analysis", sa.Text(), nullable=False),
        sa.Column("evening_prompt", sa.Text(), nullable=False),
        sa.Column("reflection_text", sa.Text(), nullable=True),
        sa.Column("reflection_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("completed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(["arc_id"], ["practice_arcs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_practice_days_arc_id", "practice_days", ["arc_id"])


def downgrade() -> None:
    op.drop_index("ix_practice_days_arc_id", table_name="practice_days")
    op.drop_table("practice_days")
    op.drop_index("ix_practice_arcs_conversation_id", table_name="practice_arcs")
    op.drop_table("practice_arcs")
    op.drop_index("ix_tradition_cards_conversation_id", table_name="tradition_cards")
    op.drop_table("tradition_cards")
