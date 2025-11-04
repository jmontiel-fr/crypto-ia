"""
Example script demonstrating GenAI engine usage.

This script shows how to:
1. Initialize the GenAI engine
2. Process user queries
3. Handle responses
4. Manage chat history
5. Track costs and statistics
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.genai import (
    PIIFilter,
    TopicValidator,
    ContextBuilder,
    GenAIEngine,
    ChatHistoryManager
)
from src.config import load_config
from src.data.database import get_session


def test_pii_filter():
    """Test PII detection and filtering."""
    print("\n=== Testing PII Filter ===")
    
    pii_filter = PIIFilter()
    
    # Test cases
    test_cases = [
        "What is the price of Bitcoin?",
        "My email is john@example.com",
        "Call me at 555-123-4567",
        "I live at 123 Main Street",
        "My name is John Doe and I want to invest",
    ]
    
    for text in test_cases:
        result = pii_filter.analyze(text)
        print(f"\nText: {text}")
        print(f"Contains PII: {result.contains_pii}")
        if result.contains_pii:
            print(f"Patterns: {result.patterns_detected}")
            print(f"Sanitized: {result.sanitized_text}")


def test_topic_validator():
    """Test topic validation."""
    print("\n=== Testing Topic Validator ===")
    
    validator = TopicValidator()
    
    # Test cases
    test_cases = [
        "What is the price of Bitcoin?",
        "Should I invest in Ethereum?",
        "What's the weather today?",
        "Who won the football game?",
        "Tell me about crypto regulations",
    ]
    
    for question in test_cases:
        result = validator.validate(question)
        print(f"\nQuestion: {question}")
        print(f"Valid: {result.is_valid}")
        if not result.is_valid:
            print(f"Reason: {result.reason}")
            print(f"Message: {result.rejection_message}")


def test_context_builder():
    """Test context building."""
    print("\n=== Testing Context Builder ===")
    
    try:
        session = get_session()
        context_builder = ContextBuilder(session)
        
        # Test cases
        questions = [
            "What is the price of Bitcoin?",
            "Should I invest in Ethereum and Solana?",
            "What are the top 20 best performing cryptos?",
        ]
        
        for question in questions:
            print(f"\nQuestion: {question}")
            
            # Extract symbols
            symbols = context_builder.extract_crypto_symbols(question)
            print(f"Extracted symbols: {symbols}")
            
            # Build context
            context = context_builder.build_context(question)
            print(f"Predictions count: {context['lstm_predictions']['count']}")
            print(f"Market tendency: {context['market_tendency']['tendency']}")
            
            # Format for prompt
            context_text = context_builder.format_context_for_prompt(context)
            print(f"Context text length: {len(context_text)} characters")
            print(f"Context preview:\n{context_text[:200]}...")
        
        session.close()
        
    except Exception as e:
        print(f"Error: {e}")
        print("Note: This test requires a configured database with data.")


def test_genai_engine():
    """Test GenAI engine (without actual OpenAI calls)."""
    print("\n=== Testing GenAI Engine ===")
    
    try:
        config = load_config()
        session = get_session()
        
        # Note: This will fail if OPENAI_API_KEY is not set
        # For testing without API key, you can mock the OpenAI client
        
        engine = GenAIEngine(config, session)
        
        print(f"Engine initialized with model: {config.openai_model}")
        print(f"Max tokens: {config.openai_max_tokens}")
        print(f"Temperature: {config.openai_temperature}")
        
        # Test validation without API call
        test_questions = [
            "What is the price of Bitcoin?",
            "My email is test@example.com",
            "What's the weather today?",
        ]
        
        for question in test_questions:
            is_valid, message = engine.validate_question(question)
            print(f"\nQuestion: {question}")
            print(f"Valid: {is_valid}")
            if not is_valid:
                print(f"Rejection: {message}")
        
        session.close()
        
    except Exception as e:
        print(f"Error: {e}")
        print("Note: This test requires OPENAI_API_KEY in environment.")


def test_chat_history_manager():
    """Test chat history management."""
    print("\n=== Testing Chat History Manager ===")
    
    try:
        session = get_session()
        history_manager = ChatHistoryManager(session)
        
        session_id = "test-session-123"
        
        # Get recent history
        history = history_manager.get_recent_history(session_id, limit=3)
        print(f"Recent history count: {len(history)}")
        
        # Get session statistics
        stats = history_manager.get_session_statistics(session_id)
        print(f"\nSession statistics:")
        print(f"  Message count: {stats.get('message_count', 0)}")
        print(f"  Total cost: ${stats.get('total_cost_usd', 0):.6f}")
        print(f"  Total tokens: {stats.get('total_tokens_input', 0)} in, {stats.get('total_tokens_output', 0)} out")
        
        # Get rejected queries (admin)
        rejected = history_manager.get_rejected_queries(limit=5)
        print(f"\nRejected queries count: {len(rejected)}")
        
        # Get PII detections (admin)
        pii_detections = history_manager.get_pii_detections(limit=5)
        print(f"PII detections count: {len(pii_detections)}")
        
        session.close()
        
    except Exception as e:
        print(f"Error: {e}")
        print("Note: This test requires a configured database.")


def main():
    """Run all tests."""
    print("=" * 60)
    print("GenAI Engine Test Suite")
    print("=" * 60)
    
    # Tests that don't require database or API
    test_pii_filter()
    test_topic_validator()
    
    # Tests that require database
    print("\n" + "=" * 60)
    print("Database-dependent tests (may fail if DB not configured)")
    print("=" * 60)
    test_context_builder()
    test_chat_history_manager()
    
    # Tests that require OpenAI API key
    print("\n" + "=" * 60)
    print("API-dependent tests (may fail if API key not set)")
    print("=" * 60)
    test_genai_engine()
    
    print("\n" + "=" * 60)
    print("Test suite completed")
    print("=" * 60)


if __name__ == "__main__":
    main()
