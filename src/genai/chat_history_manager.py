"""
Chat History Manager module.
Manages conversation tracking, history retrieval, and audit logging.
"""

import logging
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from src.data.repositories import ChatHistoryRepository, AuditLogRepository
from src.data.models import ChatHistory, QueryAuditLog
from src.genai.genai_engine import ChatResponse

logger = logging.getLogger(__name__)


class ChatHistoryManager:
    """
    Manages chat history and audit logging.
    
    Features:
    - Store chat messages with full tracing
    - Retrieve conversation history (last N Q&A pairs)
    - Audit logging for security and compliance
    - Cost tracking per session
    """
    
    def __init__(self, session: Session):
        """
        Initialize chat history manager.
        
        Args:
            session: Database session
        """
        self.session = session
        
        # Initialize repositories
        self.chat_repo = ChatHistoryRepository(session)
        self.audit_repo = AuditLogRepository(session)
        
        logger.info("Initialized ChatHistoryManager")
    
    def store_chat_message(
        self,
        response: ChatResponse,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Optional[int]:
        """
        Store chat message with full tracing data.
        
        Args:
            response: ChatResponse from GenAI engine
            ip_address: User IP address (optional)
            user_agent: User agent string (optional)
        
        Returns:
            Chat history ID or None if rejected
        """
        logger.debug(f"Storing chat message for session {response.session_id}")
        
        # Generate question hash
        question_hash = self._generate_hash(response.question)
        
        # Store chat history only if not rejected
        chat_history_id = None
        if not response.rejected:
            try:
                chat = self.chat_repo.create(
                    session_id=response.session_id,
                    question=response.question,
                    answer=response.answer,
                    question_hash=question_hash,
                    topic_valid=True,
                    pii_detected=response.pii_detected,
                    context_used=response.context_used,
                    openai_tokens_input=response.tokens_input,
                    openai_tokens_output=response.tokens_output,
                    openai_cost_usd=response.cost_usd,
                    response_time_ms=response.response_time_ms
                )
                self.session.commit()
                chat_history_id = chat.id
                
                logger.info(f"Stored chat message: id={chat.id}, session={response.session_id}")
            except Exception as e:
                logger.error(f"Error storing chat message: {e}", exc_info=True)
                self.session.rollback()
        
        # Always store audit log
        try:
            # Sanitize question if PII was detected
            question_sanitized = response.question
            if response.pii_detected:
                # Replace with placeholder (actual sanitization done by PII filter)
                question_sanitized = "[QUESTION WITH PII REMOVED]"
            
            audit = self.audit_repo.create(
                session_id=response.session_id,
                chat_history_id=chat_history_id,
                question_sanitized=question_sanitized,
                pii_patterns_detected=response.pii_patterns if response.pii_detected else None,
                topic_validation_result='valid' if not response.rejected else response.rejection_reason,
                ip_address=ip_address,
                user_agent=user_agent,
                rejected=response.rejected,
                rejection_reason=response.rejection_reason
            )
            self.session.commit()
            
            logger.debug(f"Stored audit log: id={audit.id}")
        except Exception as e:
            logger.error(f"Error storing audit log: {e}", exc_info=True)
            self.session.rollback()
        
        return chat_history_id
    
    def get_recent_history(
        self,
        session_id: str,
        limit: int = 3
    ) -> List[Dict[str, str]]:
        """
        Retrieve last N Q&A pairs for session.
        
        Args:
            session_id: User session ID
            limit: Number of recent messages to retrieve (default: 3)
        
        Returns:
            List of dictionaries with question and answer
        """
        logger.debug(f"Retrieving recent history for session {session_id}")
        
        try:
            # Get recent chat history
            history = self.chat_repo.get_recent_by_session(session_id, limit=limit)
            
            # Reverse to chronological order (oldest first)
            history = list(reversed(history))
            
            # Format as list of Q&A pairs
            qa_pairs = []
            for chat in history:
                qa_pairs.append({
                    'question': chat.question,
                    'answer': chat.answer,
                    'timestamp': chat.created_at.isoformat()
                })
            
            logger.debug(f"Retrieved {len(qa_pairs)} Q&A pairs")
            return qa_pairs
            
        except Exception as e:
            logger.error(f"Error retrieving chat history: {e}", exc_info=True)
            return []
    
    def get_all_history(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get all chat history for a session.
        
        Args:
            session_id: User session ID
        
        Returns:
            List of dictionaries with full chat data
        """
        logger.debug(f"Retrieving all history for session {session_id}")
        
        try:
            history = self.chat_repo.get_all_by_session(session_id)
            
            result = []
            for chat in history:
                result.append({
                    'id': chat.id,
                    'question': chat.question,
                    'answer': chat.answer,
                    'timestamp': chat.created_at.isoformat(),
                    'pii_detected': chat.pii_detected,
                    'tokens_input': chat.openai_tokens_input,
                    'tokens_output': chat.openai_tokens_output,
                    'cost_usd': float(chat.openai_cost_usd) if chat.openai_cost_usd else 0.0,
                    'response_time_ms': chat.response_time_ms
                })
            
            logger.debug(f"Retrieved {len(result)} chat messages")
            return result
            
        except Exception as e:
            logger.error(f"Error retrieving all chat history: {e}", exc_info=True)
            return []
    
    def get_session_cost(self, session_id: str) -> Decimal:
        """
        Calculate total OpenAI cost for a session.
        
        Args:
            session_id: User session ID
        
        Returns:
            Total cost in USD
        """
        try:
            total_cost = self.chat_repo.get_total_cost_by_session(session_id)
            logger.debug(f"Session {session_id} total cost: ${total_cost:.6f}")
            return total_cost
        except Exception as e:
            logger.error(f"Error calculating session cost: {e}", exc_info=True)
            return Decimal('0')
    
    def get_rejected_queries(
        self,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get rejected queries for admin review.
        
        Args:
            limit: Maximum number of results
        
        Returns:
            List of rejected query data
        """
        logger.debug("Retrieving rejected queries")
        
        try:
            rejected = self.audit_repo.get_rejected_queries(limit=limit)
            
            result = []
            for audit in rejected:
                result.append({
                    'id': audit.id,
                    'session_id': audit.session_id,
                    'question_sanitized': audit.question_sanitized,
                    'rejection_reason': audit.rejection_reason,
                    'pii_patterns': audit.pii_patterns_detected,
                    'timestamp': audit.created_at.isoformat(),
                    'ip_address': audit.ip_address
                })
            
            logger.debug(f"Retrieved {len(result)} rejected queries")
            return result
            
        except Exception as e:
            logger.error(f"Error retrieving rejected queries: {e}", exc_info=True)
            return []
    
    def get_pii_detections(
        self,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get queries where PII was detected.
        
        Args:
            limit: Maximum number of results
        
        Returns:
            List of PII detection data
        """
        logger.debug("Retrieving PII detections")
        
        try:
            detections = self.audit_repo.get_pii_detections(limit=limit)
            
            result = []
            for audit in detections:
                result.append({
                    'id': audit.id,
                    'session_id': audit.session_id,
                    'pii_patterns': audit.pii_patterns_detected,
                    'timestamp': audit.created_at.isoformat(),
                    'ip_address': audit.ip_address,
                    'rejected': audit.rejected
                })
            
            logger.debug(f"Retrieved {len(result)} PII detections")
            return result
            
        except Exception as e:
            logger.error(f"Error retrieving PII detections: {e}", exc_info=True)
            return []
    
    def get_session_statistics(self, session_id: str) -> Dict[str, Any]:
        """
        Get statistics for a session.
        
        Args:
            session_id: User session ID
        
        Returns:
            Dictionary with session statistics
        """
        logger.debug(f"Calculating statistics for session {session_id}")
        
        try:
            history = self.chat_repo.get_all_by_session(session_id)
            
            if not history:
                return {
                    'session_id': session_id,
                    'message_count': 0,
                    'total_cost_usd': 0.0,
                    'total_tokens_input': 0,
                    'total_tokens_output': 0,
                    'avg_response_time_ms': 0,
                    'first_message': None,
                    'last_message': None
                }
            
            total_cost = sum(
                float(chat.openai_cost_usd) if chat.openai_cost_usd else 0.0
                for chat in history
            )
            
            total_tokens_input = sum(
                chat.openai_tokens_input if chat.openai_tokens_input else 0
                for chat in history
            )
            
            total_tokens_output = sum(
                chat.openai_tokens_output if chat.openai_tokens_output else 0
                for chat in history
            )
            
            response_times = [
                chat.response_time_ms for chat in history
                if chat.response_time_ms is not None
            ]
            avg_response_time = (
                sum(response_times) / len(response_times)
                if response_times else 0
            )
            
            return {
                'session_id': session_id,
                'message_count': len(history),
                'total_cost_usd': total_cost,
                'total_tokens_input': total_tokens_input,
                'total_tokens_output': total_tokens_output,
                'avg_response_time_ms': int(avg_response_time),
                'first_message': history[0].created_at.isoformat(),
                'last_message': history[-1].created_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error calculating session statistics: {e}", exc_info=True)
            return {
                'session_id': session_id,
                'error': str(e)
            }
    
    def _generate_hash(self, text: str) -> str:
        """
        Generate SHA256 hash of text.
        
        Args:
            text: Text to hash
        
        Returns:
            SHA256 hash as hex string
        """
        return hashlib.sha256(text.encode('utf-8')).hexdigest()
