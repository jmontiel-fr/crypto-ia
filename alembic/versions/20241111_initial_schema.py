"""Initial schema with all tables

Revision ID: 001_initial
Revises: 
Create Date: 2024-11-11 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create cryptocurrencies table
    op.create_table(
        'cryptocurrencies',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('market_cap_rank', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('symbol')
    )
    op.create_index('ix_cryptocurrencies_symbol', 'cryptocurrencies', ['symbol'])
    
    # Create price_history table
    op.create_table(
        'price_history',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('crypto_id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('price_usd', sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column('volume_24h', sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column('market_cap', sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['crypto_id'], ['cryptocurrencies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_price_history_crypto_timestamp', 'price_history', ['crypto_id', 'timestamp'])
    op.create_index('idx_price_history_timestamp', 'price_history', ['timestamp'])
    op.create_index('uq_price_history_crypto_timestamp', 'price_history', ['crypto_id', 'timestamp'], unique=True)
    
    # Create predictions table
    op.create_table(
        'predictions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('crypto_id', sa.Integer(), nullable=False),
        sa.Column('prediction_date', sa.DateTime(), nullable=False),
        sa.Column('predicted_price', sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column('confidence_score', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('prediction_horizon_hours', sa.Integer(), nullable=False, server_default='24'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['crypto_id'], ['cryptocurrencies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_predictions_crypto_date', 'predictions', ['crypto_id', 'prediction_date'])
    op.create_index('idx_predictions_date', 'predictions', ['prediction_date'])
    
    # Create chat_history table
    op.create_table(
        'chat_history',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('session_id', sa.String(length=100), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('answer', sa.Text(), nullable=False),
        sa.Column('question_hash', sa.String(length=64), nullable=True),
        sa.Column('topic_valid', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('pii_detected', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('context_used', sa.JSON(), nullable=True),
        sa.Column('openai_tokens_input', sa.Integer(), nullable=True),
        sa.Column('openai_tokens_output', sa.Integer(), nullable=True),
        sa.Column('openai_cost_usd', sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column('response_time_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_chat_history_session_created', 'chat_history', ['session_id', 'created_at'])
    op.create_index('idx_chat_history_created', 'chat_history', ['created_at'])
    op.create_index('ix_chat_history_session_id', 'chat_history', ['session_id'])
    
    # Create query_audit_log table
    op.create_table(
        'query_audit_log',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('session_id', sa.String(length=100), nullable=False),
        sa.Column('chat_history_id', sa.Integer(), nullable=True),
        sa.Column('question_sanitized', sa.Text(), nullable=True),
        sa.Column('pii_patterns_detected', sa.JSON(), nullable=True),
        sa.Column('topic_validation_result', sa.String(length=50), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('rejected', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('rejection_reason', sa.String(length=200), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['chat_history_id'], ['chat_history.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_audit_log_session_created', 'query_audit_log', ['session_id', 'created_at'])
    op.create_index('idx_audit_log_rejected_created', 'query_audit_log', ['rejected', 'created_at'])
    op.create_index('ix_query_audit_log_session_id', 'query_audit_log', ['session_id'])
    
    # Create market_tendencies table
    op.create_table(
        'market_tendencies',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tendency', sa.String(length=50), nullable=False),
        sa.Column('confidence', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('metrics', sa.JSON(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_market_tendency_timestamp', 'market_tendencies', ['timestamp'])
    op.create_index('idx_market_tendency_created', 'market_tendencies', ['created_at'])
    
    # Create alert_logs table
    op.create_table(
        'alert_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('crypto_id', sa.Integer(), nullable=False),
        sa.Column('shift_type', sa.String(length=20), nullable=False),
        sa.Column('change_percent', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('previous_price', sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column('current_price', sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column('alert_message', sa.Text(), nullable=False),
        sa.Column('recipient_number', sa.String(length=20), nullable=False),
        sa.Column('sms_provider', sa.String(length=20), nullable=False),
        sa.Column('sms_message_id', sa.String(length=100), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['crypto_id'], ['cryptocurrencies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_alert_log_crypto_timestamp', 'alert_logs', ['crypto_id', 'timestamp'])
    op.create_index('idx_alert_log_timestamp', 'alert_logs', ['timestamp'])
    op.create_index('idx_alert_log_success', 'alert_logs', ['success', 'created_at'])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('alert_logs')
    op.drop_table('market_tendencies')
    op.drop_table('query_audit_log')
    op.drop_table('chat_history')
    op.drop_table('predictions')
    op.drop_table('price_history')
    op.drop_table('cryptocurrencies')
