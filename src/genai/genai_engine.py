"""
GenAI Engine module.
Main interface for OpenAI API integration with full workflow:
- Topic validation
- PII filtering
- Context building
- OpenAI API calls
- Response handling
"""

import logging
import hashlib
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime

from openai import OpenAI, OpenAIError
from sqlalchemy.orm import Session

from src.genai.pii_filter import PIIFilter, PIIDetectionResult
from src.genai.topic_validator import TopicValidator, TopicValidationResult
from src.genai.context_builder import ContextBuilder
from src.config.config_loader import Config

logger = logging.getLogger(__name__)


@dataclass
class ChatResponse:
    """Response from GenAI engine."""
    success: bool
    answer: str
    question: str
    session_id: str
    rejected: bool = False
    rejection_reason: Optional[str] = None
    pii_detected: bool = False
    pii_patterns: List[str] = None
    context_used: Optional[Dict[str, Any]] = None
    tokens_input: Optional[int] = None
    tokens_output: Optional[int] = None
    cost_usd: Optional[Decimal] = None
    response_time_ms: Optional[int] = None
    
    def __post_init__(self):
        if self.pii_patterns is None:
            self.pii_patterns = []


class GenAIEngine:
    """
    GenAI Engine for OpenAI integration.
    
    Workflow:
    1. Validate topic (crypto-related)
    2. Filter PII (detect and reject if found)
    3. Build context (LSTM predictions, market data)
    4. Call OpenAI API with enriched prompt
    5. Track tokens and costs
    6. Return response
    """
    
    # OpenAI pricing (per 1M tokens) - gpt-4o-mini
    PRICING = {
        'gpt-4o-mini': {
            'input': 0.15,   # $0.15 per 1M input tokens
            'output': 0.60   # $0.60 per 1M output tokens
        },
        'gpt-4o': {
            'input': 5.00,   # $5.00 per 1M input tokens
            'output': 15.00  # $15.00 per 1M output tokens
        },
        'gpt-3.5-turbo': {
            'input': 0.50,   # $0.50 per 1M input tokens
            'output': 1.50   # $1.50 per 1M output tokens
        }
    }
    
    def __init__(
        self,
        config: Config,
        session: Session
    ):
        """
        Initialize GenAI engine.
        
        Args:
            config: Application configuration
            session: Database session
        """
        self.config = config
        self.session = session
        
        # Initialize OpenAI client
        self.client = OpenAI(api_key=config.openai_api_key)
        
        # Initialize components
        self.pii_filter = PIIFilter()
        self.topic_validator = TopicValidator()
        self.context_builder = ContextBuilder(session)
        
        # System prompt for crypto assistant
        self.system_prompt = (
            "You are a cryptocurrency market analysis assistant. "
            "You have access to internal LSTM model predictions and real-time market data. "
            "Use the provided context (LSTM predictions, market tendency, price data) along with "
            "your knowledge of current crypto markets to provide comprehensive analysis. "
            "Only answer questions related to cryptocurrencies, blockchain technology, and crypto markets. "
            "Be concise, accurate, and helpful. "
            "Always consider both the internal predictions and external market factors. "
            "If you don't have enough information, say so clearly."
        )
        
        logger.info(
            f"Initialized GenAIEngine: "
            f"model={config.openai_model}, "
            f"max_tokens={config.openai_max_tokens}, "
            f"temperature={config.openai_temperature}"
        )
    
    def process_query(
        self,
        question: str,
        session_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> ChatResponse:
        """
        Process user query with full workflow.
        
        Args:
            question: User question
            session_id: User session ID
            ip_address: User IP address (optional)
            user_agent: User agent string (optional)
        
        Returns:
            ChatResponse with answer or rejection
        """
        start_time = time.time()
        
        logger.info(f"Processing query for session {session_id}")
        
        # Step 1: Validate topic
        topic_result = self.topic_validator.validate(question)
        if not topic_result.is_valid:
            logger.info(f"Query rejected: {topic_result.reason}")
            return ChatResponse(
                success=False,
                answer=topic_result.rejection_message,
                question=question,
                session_id=session_id,
                rejected=True,
                rejection_reason=topic_result.reason,
                response_time_ms=int((time.time() - start_time) * 1000)
            )
        
        # Step 2: Filter PII
        pii_result = self.pii_filter.analyze(question)
        if pii_result.contains_pii:
            logger.warning(f"PII detected in query: {pii_result.patterns_detected}")
            return ChatResponse(
                success=False,
                answer=(
                    "I detected personally identifiable information (PII) in your question. "
                    "For your privacy and security, please rephrase your question without "
                    "including personal information such as names, email addresses, phone numbers, "
                    "or other sensitive data."
                ),
                question=question,
                session_id=session_id,
                rejected=True,
                rejection_reason='pii_detected',
                pii_detected=True,
                pii_patterns=pii_result.patterns_detected,
                response_time_ms=int((time.time() - start_time) * 1000)
            )
        
        # Step 3: Build context
        try:
            context = self.context_builder.build_context(question)
            context_text = self.context_builder.format_context_for_prompt(context)
        except Exception as e:
            logger.error(f"Error building context: {e}", exc_info=True)
            context = {}
            context_text = ""
        
        # Step 4: Call OpenAI API
        try:
            answer, tokens_input, tokens_output = self._call_openai(
                question,
                context_text
            )
            
            # Calculate cost
            cost_usd = self._calculate_cost(
                tokens_input,
                tokens_output,
                self.config.openai_model
            )
            
            response_time_ms = int((time.time() - start_time) * 1000)
            
            logger.info(
                f"Query processed successfully: "
                f"tokens_in={tokens_input}, tokens_out={tokens_output}, "
                f"cost=${cost_usd:.6f}, time={response_time_ms}ms"
            )
            
            return ChatResponse(
                success=True,
                answer=answer,
                question=question,
                session_id=session_id,
                context_used=context,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                cost_usd=cost_usd,
                response_time_ms=response_time_ms
            )
            
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {e}", exc_info=True)
            
            # Return fallback response
            return ChatResponse(
                success=False,
                answer=(
                    "I'm sorry, I'm having trouble processing your request right now. "
                    "Please try again in a moment. If the problem persists, "
                    "you can check our predictions and market data directly through the dashboard."
                ),
                question=question,
                session_id=session_id,
                rejected=True,
                rejection_reason='api_error',
                response_time_ms=int((time.time() - start_time) * 1000)
            )
    
    def _call_openai(
        self,
        question: str,
        context_text: str
    ) -> tuple[str, int, int]:
        """
        Call OpenAI API with question and context.
        
        Args:
            question: User question
            context_text: Formatted context text
        
        Returns:
            Tuple of (answer, input_tokens, output_tokens)
        
        Raises:
            OpenAIError: If API call fails
        """
        # Build messages
        messages = [
            {"role": "system", "content": self.system_prompt}
        ]
        
        # Add context if available
        if context_text:
            messages.append({
                "role": "system",
                "content": f"Internal Data Context:\n{context_text}"
            })
        
        # Add user question
        messages.append({
            "role": "user",
            "content": question
        })
        
        # Call OpenAI API
        logger.debug(f"Calling OpenAI API: model={self.config.openai_model}")
        
        response = self.client.chat.completions.create(
            model=self.config.openai_model,
            messages=messages,
            max_tokens=self.config.openai_max_tokens,
            temperature=self.config.openai_temperature
        )
        
        # Extract response
        answer = response.choices[0].message.content
        tokens_input = response.usage.prompt_tokens
        tokens_output = response.usage.completion_tokens
        
        logger.debug(
            f"OpenAI response: {len(answer)} chars, "
            f"tokens_in={tokens_input}, tokens_out={tokens_output}"
        )
        
        return answer, tokens_input, tokens_output
    
    def _calculate_cost(
        self,
        tokens_input: int,
        tokens_output: int,
        model: str
    ) -> Decimal:
        """
        Calculate cost of OpenAI API call.
        
        Args:
            tokens_input: Number of input tokens
            tokens_output: Number of output tokens
            model: Model name
        
        Returns:
            Cost in USD as Decimal
        """
        # Get pricing for model (default to gpt-4o-mini if not found)
        pricing = self.PRICING.get(model, self.PRICING['gpt-4o-mini'])
        
        # Calculate cost (pricing is per 1M tokens)
        input_cost = (tokens_input / 1_000_000) * pricing['input']
        output_cost = (tokens_output / 1_000_000) * pricing['output']
        total_cost = input_cost + output_cost
        
        return Decimal(str(total_cost))
    
    def generate_question_hash(self, question: str) -> str:
        """
        Generate SHA256 hash of question for deduplication.
        
        Args:
            question: User question
        
        Returns:
            SHA256 hash as hex string
        """
        return hashlib.sha256(question.encode('utf-8')).hexdigest()
    
    def validate_question(self, question: str) -> tuple[bool, str]:
        """
        Validate question (topic and PII).
        
        Args:
            question: User question
        
        Returns:
            Tuple of (is_valid, rejection_message)
        """
        # Validate topic
        topic_result = self.topic_validator.validate(question)
        if not topic_result.is_valid:
            return False, topic_result.rejection_message
        
        # Check PII
        pii_result = self.pii_filter.analyze(question)
        if pii_result.contains_pii:
            return False, (
                "I detected personally identifiable information (PII) in your question. "
                "Please rephrase without including personal information."
            )
        
        return True, ""
    
    def get_system_prompt(self) -> str:
        """
        Get the system prompt used for OpenAI.
        
        Returns:
            System prompt string
        """
        return self.system_prompt
    
    def set_system_prompt(self, prompt: str) -> None:
        """
        Set custom system prompt.
        
        Args:
            prompt: New system prompt
        """
        self.system_prompt = prompt
        logger.info("Updated system prompt")
