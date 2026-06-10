"""users, login_events, token_usage_log + user_id on existing tables

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-10

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0006'
down_revision = '0005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('role', sa.String(length=20), nullable=False, server_default='user'),
        sa.Column('token_limit', sa.BigInteger(), nullable=False, server_default='1000000'),
        sa.Column('tokens_used', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('last_login_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    op.create_table(
        'login_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.String(length=255), nullable=False),
        sa.Column('event_type', sa.String(length=20), nullable=False),
        sa.Column('ip_address', sa.String(length=64), nullable=True),
        sa.Column('user_agent', sa.String(length=512), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_login_events_user_id', 'login_events', ['user_id'])
    op.create_index('ix_login_events_created_at', 'login_events', ['created_at'])

    op.create_table(
        'token_usage_log',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.String(length=255), nullable=False),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('model', sa.String(length=255), nullable=False),
        sa.Column('prompt_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('completion_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_token_usage_log_user_id', 'token_usage_log', ['user_id'])
    op.create_index('ix_token_usage_log_created_at', 'token_usage_log', ['created_at'])

    # Scope existing tables to a user. No production data exists yet, so these
    # are added as NOT NULL directly (no backfill migration needed).
    for table in ('conversations', 'journal_entries', 'ingest_jobs'):
        op.add_column(table, sa.Column('user_id', sa.String(length=255), nullable=False))
        op.create_foreign_key(
            f'fk_{table}_user_id', table, 'users', ['user_id'], ['id'], ondelete='CASCADE'
        )
        op.create_index(f'ix_{table}_user_id', table, ['user_id'])


def downgrade() -> None:
    for table in ('conversations', 'journal_entries', 'ingest_jobs'):
        op.drop_index(f'ix_{table}_user_id', table_name=table)
        op.drop_constraint(f'fk_{table}_user_id', table, type_='foreignkey')
        op.drop_column(table, 'user_id')

    op.drop_index('ix_token_usage_log_created_at', table_name='token_usage_log')
    op.drop_index('ix_token_usage_log_user_id', table_name='token_usage_log')
    op.drop_table('token_usage_log')

    op.drop_index('ix_login_events_created_at', table_name='login_events')
    op.drop_index('ix_login_events_user_id', table_name='login_events')
    op.drop_table('login_events')

    op.drop_index('ix_users_email', table_name='users')
    op.drop_table('users')
