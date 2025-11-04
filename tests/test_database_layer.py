"""
Tests for database layer implementation.
Tests database connection, models, and repositories.
"""

import pytest
from datetime import datetime
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.data.database import Base
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


@pytest.fixture
def engine():
    """Create in-memory SQLite database for testing."""
    engine = create_engine('sqlite:///:memory:', echo=False)
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine):
    """Create database session for testing."""
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class TestCryptoRepository:
    """Test CryptoRepository operations."""
    
    def test_create_cryptocurrency(self, session):
        """Test creating a cryptocurrency."""
        repo = CryptoRepository(session)
        crypto = repo.create('BTC', 'Bitcoin', 1)
        
        assert crypto.id is not None
        assert crypto.symbol == 'BTC'
        assert crypto.name == 'Bitcoin'
        assert crypto.market_cap_rank == 1
    
    def test_get_by_symbol(self, session):
        """Test retrieving cryptocurrency by symbol."""
        repo = CryptoRepository(session)
        repo.create('ETH', 'Ethereum', 2)
        session.commit()
        
        crypto = repo.get_by_symbol('ETH')
        assert crypto is not None
        assert crypto.symbol == 'ETH'
        assert crypto.name == 'Ethereum'
    
    def test_get_or_create(self, session):
        """Test get_or_create functionality."""
        repo = CryptoRepository(session)
        
        # First call creates
        crypto1 = repo.get_or_create('SOL', 'Solana', 5)
        session.commit()
        
        # Second call retrieves
        crypto2 = repo.get_or_create('SOL', 'Solana', 5)
        
        assert crypto1.id == crypto2.id


class TestPriceHistoryRepository:
    """Test PriceHistoryRepository operations."""
    
    def test_create_price_history(self, session):
        """Test creating price history record."""
        # Create cryptocurrency first
        crypto_repo = CryptoRepository(session)
        crypto = crypto_repo.create('BTC', 'Bitcoin', 1)
        session.commit()
        
        # Create price history
        price_repo = PriceHistoryRepository(session)
        timestamp = datetime(2024, 1, 1, 12, 0, 0)
        price = price_repo.create(
            crypto_id=crypto.id,
            timestamp=timestamp,
            price_usd=Decimal('45000.00'),
            volume_24h=Decimal('1000000.00'),
            market_cap=Decimal('900000000.00')
        )
        
        assert price.id is not None
        assert price.crypto_id == crypto.id
        assert price.price_usd == Decimal('45000.00')
    
    def test_get_latest_timestamp(self, session):
        """Test getting latest timestamp."""
        # Setup
        crypto_repo = CryptoRepository(session)
        crypto = crypto_repo.create('BTC', 'Bitcoin', 1)
        session.commit()
        
        price_repo = PriceHistoryRepository(session)
        price_repo.create(crypto.id, datetime(2024, 1, 1), Decimal('45000'))
        price_repo.create(crypto.id, datetime(2024, 1, 2), Decimal('46000'))
        session.commit()
        
        # Test
        latest = price_repo.get_latest_timestamp(crypto.id)
        assert latest == datetime(2024, 1, 2)


class TestPredictionRepository:
    """Test PredictionRepository operations."""
    
    def test_create_prediction(self, session):
        """Test creating prediction record."""
        # Setup
        crypto_repo = CryptoRepository(session)
        crypto = crypto_repo.create('BTC', 'Bitcoin', 1)
        session.commit()
        
        # Create prediction
        pred_repo = PredictionRepository(session)
        prediction = pred_repo.create(
            crypto_id=crypto.id,
            prediction_date=datetime(2024, 1, 1),
            predicted_price=Decimal('50000.00'),
            confidence_score=Decimal('0.85'),
            prediction_horizon_hours=24
        )
        
        assert prediction.id is not None
        assert prediction.predicted_price == Decimal('50000.00')
        assert prediction.confidence_score == Decimal('0.85')


class TestChatHistoryRepository:
    """Test ChatHistoryRepository operations."""
    
    def test_create_chat_history(self, session):
        """Test creating chat history record."""
        repo = ChatHistoryRepository(session)
        chat = repo.create(
            session_id='test-session-123',
            question='What is Bitcoin?',
            answer='Bitcoin is a cryptocurrency...',
            topic_valid=True,
            pii_detected=False,
            openai_tokens_input=50,
            openai_tokens_output=100,
            openai_cost_usd=Decimal('0.0001')
        )
        
        assert chat.id is not None
        assert chat.session_id == 'test-session-123'
        assert chat.question == 'What is Bitcoin?'
    
    def test_get_recent_by_session(self, session):
        """Test retrieving recent chat history."""
        repo = ChatHistoryRepository(session)
        
        # Create multiple chat records
        for i in range(5):
            repo.create(
                session_id='test-session',
                question=f'Question {i}',
                answer=f'Answer {i}'
            )
        session.commit()
        
        # Get recent 3
        recent = repo.get_recent_by_session('test-session', limit=3)
        assert len(recent) == 3
        # Should be in descending order (most recent first)
        assert recent[0].question == 'Question 4'


class TestMarketTendencyRepository:
    """Test MarketTendencyRepository operations."""
    
    def test_create_market_tendency(self, session):
        """Test creating market tendency record."""
        repo = MarketTendencyRepository(session)
        tendency = repo.create(
            tendency='bullish',
            timestamp=datetime(2024, 1, 1),
            confidence=Decimal('0.75'),
            metrics={'avg_change': 2.5, 'volatility': 0.15}
        )
        
        assert tendency.id is not None
        assert tendency.tendency == 'bullish'
        assert tendency.confidence == Decimal('0.75')
        assert tendency.metrics['avg_change'] == 2.5
    
    def test_get_latest(self, session):
        """Test getting latest market tendency."""
        repo = MarketTendencyRepository(session)
        
        repo.create('bearish', datetime(2024, 1, 1), Decimal('0.6'))
        repo.create('bullish', datetime(2024, 1, 2), Decimal('0.8'))
        session.commit()
        
        latest = repo.get_latest()
        assert latest.tendency == 'bullish'
        assert latest.timestamp == datetime(2024, 1, 2)
