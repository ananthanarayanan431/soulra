"""journal_entries

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-07

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'journal_entries',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('quote', sa.Text(), nullable=True),
        sa.Column('tradition', sa.String(length=100), nullable=True),
        sa.Column('author', sa.String(length=255), nullable=True),
        sa.Column('citation', sa.String(length=255), nullable=True),
        sa.Column('analysis', sa.Text(), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.Text()), nullable=False, server_default='{}'),
        sa.Column('applied', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('applied_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('saved_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_journal_entries_tradition', 'journal_entries', ['tradition'])
    op.create_index('ix_journal_entries_conversation_id', 'journal_entries', ['conversation_id'])
    op.create_index('ix_journal_entries_saved_at', 'journal_entries', ['saved_at'])


def downgrade() -> None:
    op.drop_index('ix_journal_entries_saved_at', table_name='journal_entries')
    op.drop_index('ix_journal_entries_conversation_id', table_name='journal_entries')
    op.drop_index('ix_journal_entries_tradition', table_name='journal_entries')
    op.drop_table('journal_entries')
