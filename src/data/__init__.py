"""
Data layer package.
Provides database models, connection management, and repositories.
"""

from src.data.database import (
    Base,
    init_db,
    get_engine,
    get_session,
    session_scope,
    create_tables,
    drop_tables,
    check_connection,
    close_db,
)

from src.data.models import (
    Cryptocurrency,
    PriceHistory,
    Prediction,
    ChatHistory,
    QueryAuditLog,
    MarketTendency,
)

from src.data.repositories import (
    CryptoRepository,
    PriceHistoryRepository,
    PredictionRepository,
    ChatHistoryRepository,
    AuditLogRepository,
    MarketTendencyRepository,
)

__all__ = [
    # Database management
    'Base',
    'init_db',
    'get_engine',
    'get_session',
    'session_scope',
    'create_tables',
    'drop_tables',
    'check_connection',
    'close_db',
    # Models
    'Cryptocurrency',
    'PriceHistory',
    'Prediction',
    'ChatHistory',
    'QueryAuditLog',
    'MarketTendency',
    # Repositories
    'CryptoRepository',
    'PriceHistoryRepository',
    'PredictionRepository',
    'ChatHistoryRepository',
    'AuditLogRepository',
    'MarketTendencyRepository',
]
