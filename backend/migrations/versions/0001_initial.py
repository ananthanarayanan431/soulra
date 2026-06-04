"""initial

Revision ID: 0001
Revises:
Create Date: 2026-06-04

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('conversations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('thread_id', sa.String(length=255), nullable=False),
        sa.Column('situation', sa.Text(), nullable=False),
        sa.Column('clarify_q', sa.Text(), nullable=True),
        sa.Column('clarify_ans', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('completed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_conversations_thread_id'), 'conversations', ['thread_id'], unique=True)

    op.create_table('action_steps',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('step_number', sa.Integer(), nullable=False),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_action_steps_conversation_id'), 'action_steps', ['conversation_id'])

    op.create_table('ingest_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('filename', sa.Text(), nullable=True),
        sa.Column('tradition', sa.String(length=100), nullable=True),
        sa.Column('chunks_created', sa.Integer(), nullable=False),
        sa.Column('tokens_used', sa.Integer(), nullable=False),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('completed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('ingest_jobs')
    op.drop_index(op.f('ix_action_steps_conversation_id'), table_name='action_steps')
    op.drop_table('action_steps')
    op.drop_index(op.f('ix_conversations_thread_id'), table_name='conversations')
    op.drop_table('conversations')
