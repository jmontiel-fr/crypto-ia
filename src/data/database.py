"""
Database connection and session management module.
Provides SQLAlchemy engine, session factory, and database initialization.
"""

import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event, pool
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.exc import SQLAlchemyError

from src.config.config_loader import Config

logger = logging.getLogger(__name__)

# Base class for all SQLAlchemy models
Base = declarative_base()

# Global engine and session factory (initialized by init_db)
_engine = None
_SessionFactory = None


def init_db(config: Config) -> None:
    """
    Initialize database connection and session factory.
    
    Args:
        config: Configuration object with database settings.
    
    Raises:
        SQLAlchemyError: If database connection fails.
    """
    global _engine, _SessionFactory
    
    try:
        # Create engine with connection pooling
        _engine = create_engine(
            config.database_url,
            poolclass=pool.QueuePool,
            pool_size=config.db_pool_size,
            max_overflow=config.db_max_overflow,
            pool_pre_ping=True,  # Verify connections before using
            pool_recycle=3600,   # Recycle connections after 1 hour
            echo=config.log_level == 'DEBUG',  # Log SQL in debug mode
        )
        
        # Add connection event listeners for logging
        @event.listens_for(_engine, "connect")
        def receive_connect(dbapi_conn, connection_record):
            logger.debug("Database connection established")
        
        @event.listens_for(_engine, "close")
        def receive_close(dbapi_conn, connection_record):
            logger.debug("Database connection closed")
        
        # Create session factory
        _SessionFactory = sessionmaker(
            bind=_engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
        
        logger.info(f"Database initialized successfully: {config.database_url.split('@')[1]}")
        
    except SQLAlchemyError as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


def get_engine():
    """
    Get the SQLAlchemy engine instance.
    
    Returns:
        SQLAlchemy Engine instance.
    
    Raises:
        RuntimeError: If database is not initialized.
    """
    if _engine is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _engine


def get_session() -> Session:
    """
    Get a new database session.
    
    Returns:
        SQLAlchemy Session instance.
    
    Raises:
        RuntimeError: If database is not initialized.
    """
    if _SessionFactory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _SessionFactory()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """
    Provide a transactional scope for database operations.
    
    Usage:
        with session_scope() as session:
            session.add(obj)
            # Changes are automatically committed
    
    Yields:
        SQLAlchemy Session instance.
    
    Raises:
        SQLAlchemyError: If database operation fails.
    """
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database transaction failed: {e}")
        raise
    finally:
        session.close()


def create_tables() -> None:
    """
    Create all database tables defined in models.
    
    This should be called after all models are imported.
    For production, use Alembic migrations instead.
    
    Raises:
        SQLAlchemyError: If table creation fails.
    """
    try:
        engine = get_engine()
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except SQLAlchemyError as e:
        logger.error(f"Failed to create database tables: {e}")
        raise


def drop_tables() -> None:
    """
    Drop all database tables.
    
    WARNING: This will delete all data. Use with caution!
    
    Raises:
        SQLAlchemyError: If table drop fails.
    """
    try:
        engine = get_engine()
        Base.metadata.drop_all(bind=engine)
        logger.warning("All database tables dropped")
    except SQLAlchemyError as e:
        logger.error(f"Failed to drop database tables: {e}")
        raise


def check_connection() -> bool:
    """
    Check if database connection is working.
    
    Returns:
        True if connection is successful, False otherwise.
    """
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        logger.info("Database connection check successful")
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False


def close_db() -> None:
    """
    Close database connections and dispose of the engine.
    
    Should be called when shutting down the application.
    """
    global _engine, _SessionFactory
    
    if _engine is not None:
        _engine.dispose()
        _engine = None
        _SessionFactory = None
        logger.info("Database connections closed")
