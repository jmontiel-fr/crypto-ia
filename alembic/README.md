# Database Migrations with Alembic

This directory contains database migration scripts for the Crypto Market Analysis SaaS application.

## Overview

We use Alembic for database schema migrations. Migrations allow you to:
- Version control your database schema
- Apply incremental changes to the database
- Rollback changes if needed
- Keep development, staging, and production databases in sync

## Prerequisites

- PostgreSQL database running
- DATABASE_URL environment variable set
- Python dependencies installed (including alembic)

## Quick Start

### 1. Set Database URL

```bash
# For local development
export DATABASE_URL=postgresql://crypto_user:crypto_pass@localhost:5432/crypto_db

# Or load from env file
export $(cat local-env | xargs)
```

### 2. Run Migrations

```bash
# Upgrade to latest version
python scripts/migrate_upgrade.py

# Check current version
python scripts/migrate_current.py

# View migration history
python scripts/migrate_history.py
```

## Migration Scripts

### Upgrade Database
```bash
python scripts/migrate_upgrade.py
```
Applies all pending migrations to bring the database to the latest version.

### Downgrade Database
```bash
# Downgrade one version
python scripts/migrate_downgrade.py -1

# Downgrade to specific revision
python scripts/migrate_downgrade.py 001_initial

# Downgrade to base (removes all migrations)
python scripts/migrate_downgrade.py base
```

### Check Current Version
```bash
python scripts/migrate_current.py
```
Shows the current migration version of the database.

### View Migration History
```bash
python scripts/migrate_history.py
```
Shows all available migrations and their status.

## Creating New Migrations

### Auto-generate Migration
```bash
# Make changes to models in src/data/models.py
# Then generate migration
alembic revision --autogenerate -m "Description of changes"
```

### Manual Migration
```bash
# Create empty migration file
alembic revision -m "Description of changes"

# Edit the generated file in alembic/versions/
```

## Migration Files

Migration files are located in `alembic/versions/` and follow the naming pattern:
```
YYYYMMDD_HHMM-revision_description.py
```

Each migration file contains:
- `upgrade()`: Function to apply the migration
- `downgrade()`: Function to rollback the migration

## Initial Migration

The initial migration (`20241111_initial_schema.py`) creates all tables:
- `cryptocurrencies` - Cryptocurrency metadata
- `price_history` - Historical price data
- `predictions` - ML model predictions
- `chat_history` - Chat conversation history
- `query_audit_log` - Security and compliance audit log
- `market_tendencies` - Market tendency classifications
- `alert_logs` - SMS alert tracking

## Best Practices

1. **Always backup before migrations**: Especially in production
   ```bash
   python remote-scripts/backup-database.sh
   ```

2. **Test migrations locally first**: Run on local database before production

3. **Review auto-generated migrations**: Always check the generated SQL

4. **Write reversible migrations**: Ensure `downgrade()` properly reverses `upgrade()`

5. **Use descriptive messages**: Make migration purposes clear

6. **Don't modify existing migrations**: Create new ones instead

## Troubleshooting

### Migration fails with "relation already exists"
The table might already exist. Check current schema:
```sql
\dt  -- List tables in psql
```

### Can't connect to database
Verify DATABASE_URL is set correctly:
```bash
echo $DATABASE_URL
```

### Migration history out of sync
Check Alembic version table:
```sql
SELECT * FROM alembic_version;
```

### Reset database (CAUTION: Destroys all data)
```bash
# Downgrade to base
python scripts/migrate_downgrade.py base

# Upgrade to latest
python scripts/migrate_upgrade.py
```

## Integration with Application

The application automatically runs migrations on startup if configured:
```python
from alembic.config import Config
from alembic import command

# In your startup code
alembic_cfg = Config("alembic.ini")
command.upgrade(alembic_cfg, "head")
```

## Environment-Specific Migrations

The migration system works with both local and AWS environments:

**Local Development:**
```bash
export $(cat local-env | xargs)
python scripts/migrate_upgrade.py
```

**AWS Production:**
```bash
export $(cat aws-env | xargs)
python scripts/migrate_upgrade.py
```

## Further Reading

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- Project DEVELOPMENT-GUIDE.md for more details
