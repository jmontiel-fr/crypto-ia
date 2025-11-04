"""
GenAI module for OpenAI integration and chat functionality.

This module provides:
- PII detection and filtering
- Topic validation for crypto-related questions
- Context building from internal data sources
- OpenAI API integration
- Chat history management and audit logging
"""

from src.genai.pii_filter import PIIFilter, PIIDetectionResult
from src.genai.topic_validator import TopicValidator, TopicValidationResult
from src.genai.context_builder import ContextBuilder
from src.genai.genai_engine import GenAIEngine, ChatResponse
from src.genai.chat_history_manager import ChatHistoryManager

__all__ = [
    'PIIFilter',
    'PIIDetectionResult',
    'TopicValidator',
    'TopicValidationResult',
    'ContextBuilder',
    'GenAIEngine',
    'ChatResponse',
    'ChatHistoryManager',
]
