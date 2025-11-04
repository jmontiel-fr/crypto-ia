# Database Layer

This module provides the complete database layer for the Crypto Market Analysis SaaS application.

## Components

### 1. Database Connection (`database.py`)

Manages SQLAlchemy engine, session factory, and connection pooling.

**Key Functions:**
- `init_db(config)` - Initialize database with configuration
- `get_engine()` - Get SQLAlchemy engine instance
- `get_session()` - Get new database session
- `session_scope()` - Context manager for transactional operations
- `create_tables()` - Create all database tables
- `check_connection()` - Verify database connectivity
- `close_db()` - Close all database connections

**Usage Example:**
```python
from src.config.config_loader import load_config
from src.data import init_db, session_scope, CryptoRepository

# Initialize database
config = load_config()
init_db(config)

# Use session scope for transactions
with session_scope() as session:
    repo = CryptoRepository(session)
    crypto = repo.create('BTC', 'Bitcoin', 1)
    # Changes are automatically committed
```

### 2. Models (`models.py`)

SQLAlchemy ORM models for all database entities.

**Models:**
- `Cryptocurrency` - Cryptocurrency metadata (symbol, name, market cap rank)
- `PriceHistory` - Historical price data (hourly prices, volume, market cap)
- `Prediction` - ML model predictions (predicted prices, confidence scores)
- `ChatHistory` - Chat conversation history with full tracing
- `QueryAuditLog` - Security and compliance audit logs
- `MarketTendency` - Market tendency classifications over time

**Features:**
- Automatic timestamps (created_at, updated_at)
- Optimized indexes for common queries
- Foreign key relationships with cascade delete
- JSON fields for flexible data storage

### 3. Repositories (`repositories.py`)

Repository pattern implementation for clean data access.

**Repositories:**
- `CryptoRepository` - CRUD operations for cryptocurrencies
- `PriceHistoryRepository` - Historical price data queries
- `PredictionRepository` - Prediction storage and retrieval
- `ChatHistoryRepository` - Chat history with session management
- `AuditLogRepository` - Security audit logging
- `MarketTendencyRepository` - Market tendency tracking

**Usage Example:**
```python
from src.data import session_scope, CryptoRepository, PriceHistoryRepository
from datetime import datetime
from decimal import Decimal

with session_scope() as session:
    # Create cryptocurrency
    crypto_repo = CryptoRepository(session)
    btc = crypto_repo.get_or_create('BTC', 'Bitcoin', 1)
    
    # Add price history
    price_repo = PriceHistoryRepository(session)
    price_repo.create(
        crypto_id=btc.id,
        timestamp=datetime.now(),
        price_usd=Decimal('45000.00'),
        volume_24h=Decimal('1000000.00')
    )
    
    # Query latest prices
    latest = price_repo.get_latest_by_crypto(btc.id, limit=10)
```

## Database Schema

### Cryptocurrencies Table
```sql
CREATE TABLE cryptocurrencies (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    market_cap_rank INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Price History Table
```sql
CREATE TABLE price_history (
    id SERIAL PRIMARY KEY,
    crypto_id INTEGER REFERENCES cryptocurrencies(id),
    timestamp TIMESTAMP NOT NULL,
    price_usd NUMERIC(20, 8) NOT NULL,
    volume_24h NUMERIC(20, 2),
    market_cap NUMERIC(20, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(crypto_id, timestamp)
);
CREATE INDEX idx_price_history_crypto_timestamp ON price_history(crypto_id, timestamp);
```

### Predictions Table
```sql
CREATE TABLE predictions (
    id SERIAL PRIMARY KEY,
    crypto_id INTEGER REFERENCES cryptocurrencies(id),
    prediction_date TIMESTAMP NOT NULL,
    predicted_price NUMERIC(20, 8),
    confidence_score NUMERIC(5, 4),
    prediction_horizon_hours INTEGER DEFAULT 24,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_predictions_crypto_date ON predictions(crypto_id, prediction_date);
```

### Chat History Table
```sql
CREATE TABLE chat_history (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    question_hash VARCHAR(64),
    topic_valid BOOLEAN DEFAULT true,
    pii_detected BOOLEAN DEFAULT false,
    context_used JSON,
    openai_tokens_input INTEGER,
    openai_tokens_output INTEGER,
    openai_cost_usd NUMERIC(10, 6),
    response_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_chat_history_session_created ON chat_history(session_id, created_at);
```

### Query Audit Log Table
```sql
CREATE TABLE query_audit_log (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL,
    chat_history_id INTEGER REFERENCES chat_history(id),
    question_sanitized TEXT,
    pii_patterns_detected JSON,
    topic_validation_result VARCHAR(50),
    ip_address VARCHAR(45),
    user_agent TEXT,
    rejected BOOLEAN DEFAULT false,
    rejection_reason VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_audit_log_session_created ON query_audit_log(session_id, created_at);
CREATE INDEX idx_audit_log_rejected_created ON query_audit_log(rejected, created_at);
```

### Market Tendencies Table
```sql
CREATE TABLE market_tendencies (
    id SERIAL PRIMARY KEY,
    tendency VARCHAR(50) NOT NULL,
    confidence NUMERIC(5, 4),
    metrics JSON,
    timestamp TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_market_tendency_timestamp ON market_tendencies(timestamp);
```

## Initialization

### Using the Initialization Script

```bash
# Make sure you have a .env file or local-env configured
python scripts/init_database.py
```

This script will:
1. Load configuration from environment
2. Initialize database connection
3. Create all tables with indexes
4. Verify connectivity

### Manual Initialization

```python
from src.config.config_loader import load_config
from src.data import init_db, create_tables

config = load_config()
init_db(config)
create_tables()
```

## Testing

Run the database layer tests:

```bash
pytest tests/test_database_layer.py -v
```

The tests use an in-memory SQLite database for fast, isolated testing.

## Best Practices

1. **Always use session_scope()** for transactional operations
2. **Use repositories** instead of direct model access
3. **Handle exceptions** appropriately (IntegrityError for duplicates)
4. **Close connections** when shutting down the application
5. **Use bulk operations** for large data inserts
6. **Index optimization** - indexes are already configured for common queries

## Connection Pooling

The database layer uses SQLAlchemy's QueuePool with:
- Pool size: Configurable via `DB_POOL_SIZE` (default: 5)
- Max overflow: Configurable via `DB_MAX_OVERFLOW` (default: 10)
- Pre-ping: Enabled (verifies connections before use)
- Pool recycle: 3600 seconds (1 hour)

## Error Handling

Common errors and how to handle them:

```python
from sqlalchemy.exc import IntegrityError

try:
    with session_scope() as session:
        repo = CryptoRepository(session)
        crypto = repo.create('BTC', 'Bitcoin', 1)
except IntegrityError:
    # Handle duplicate symbol
    print("Cryptocurrency already exists")
```

## Migration Support

For production deployments, use Alembic for database migrations:

```bash
# Initialize Alembic (already configured)
alembic init alembic

# Create migration
alembic revision --autogenerate -m "Initial schema"

# Apply migration
alembic upgrade head
```

## Requirements Met

This implementation satisfies:
- **Requirement 4.1**: PostgreSQL database with SQLAlchemy ORM
- **Requirement 4.2**: Complete data models for all entities
- **Requirement 4.3**: Repository pattern for data access
- **Requirement 4.4**: Connection pooling and session management

## Next Steps

After the database layer is set up, you can:
1. Implement data collectors (Task 3)
2. Build prediction engine (Task 4)
3. Create GenAI integration (Task 5)
4. Develop REST API (Task 6)
