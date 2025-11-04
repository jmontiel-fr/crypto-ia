"""
Chat endpoints.
Provides GenAI-powered chat interface for cryptocurrency market queries.
"""

import logging
from flask import Blueprint, jsonify, request, render_template
from datetime import datetime

from src.data.database import session_scope
from src.genai.genai_engine import GenAIEngine, ChatResponse
from src.genai.chat_history_manager import ChatHistoryManager
from src.config.config_loader import load_config

logger = logging.getLogger(__name__)

chat_bp = Blueprint('chat', __name__, template_folder='../templates', static_folder='../static')


@chat_bp.route('/', methods=['GET'])
@chat_bp.route('/ui', methods=['GET'])
def chat_ui():
    """
    Serve the chat UI interface.
    
    Returns:
        Rendered HTML template for chat interface
    """
    from src.api.middleware.csrf import generate_csrf_token
    
    # Generate CSRF token for the session
    csrf_token = generate_csrf_token()
    
    return render_template('chat.html', csrf_token=csrf_token)


@chat_bp.route('/csrf-token', methods=['GET'])
def get_csrf_token():
    """
    Get CSRF token for the current session.
    
    Returns:
        JSON response with CSRF token
    """
    from src.api.middleware.csrf import generate_csrf_token
    
    token = generate_csrf_token()
    
    return jsonify({
        'csrf_token': token
    }), 200


def validate_chat_request(data: dict) -> tuple[bool, str]:
    """
    Validate chat request data.
    
    Args:
        data: Request data dictionary
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not data:
        return False, "Request body is required"
    
    if 'question' not in data:
        return False, "Field 'question' is required"
    
    if not isinstance(data['question'], str):
        return False, "Field 'question' must be a string"
    
    if not data['question'].strip():
        return False, "Field 'question' cannot be empty"
    
    if len(data['question']) > 1000:
        return False, "Field 'question' exceeds maximum length of 1000 characters"
    
    if 'session_id' not in data:
        return False, "Field 'session_id' is required"
    
    if not isinstance(data['session_id'], str):
        return False, "Field 'session_id' must be a string"
    
    return True, ""


def format_chat_response(chat_response: ChatResponse, history: list = None) -> dict:
    """
    Format chat response for API.
    
    Args:
        chat_response: ChatResponse object
        history: Optional chat history
    
    Returns:
        Formatted response dictionary
    """
    response = {
        'success': chat_response.success,
        'answer': chat_response.answer,
        'session_id': chat_response.session_id,
        'timestamp': datetime.now().isoformat()
    }
    
    if chat_response.rejected:
        response['rejected'] = True
        response['rejection_reason'] = chat_response.rejection_reason
    
    if chat_response.pii_detected:
        response['pii_detected'] = True
        response['pii_warning'] = (
            "Your question contained personally identifiable information. "
            "Please rephrase without including personal data."
        )
    
    if history:
        response['history'] = history
    
    # Add metadata for successful queries
    if chat_response.success and not chat_response.rejected:
        response['metadata'] = {
            'tokens_input': chat_response.tokens_input,
            'tokens_output': chat_response.tokens_output,
            'cost_usd': float(chat_response.cost_usd) if chat_response.cost_usd else 0.0,
            'response_time_ms': chat_response.response_time_ms
        }
    
    return response


@chat_bp.route('/query', methods=['POST'])
def process_chat_query():
    """
    Process chat query.
    
    Request Body:
        {
            "question": "What are the top performing cryptocurrencies?",
            "session_id": "user-session-123"
        }
    
    Returns:
        JSON response with answer and chat history
    """
    try:
        # Parse request data
        data = request.get_json()
        
        # Validate request
        is_valid, error_message = validate_chat_request(data)
        if not is_valid:
            return jsonify({
                'error': {
                    'code': 'INVALID_REQUEST',
                    'message': 'Invalid request data',
                    'details': error_message
                }
            }), 400
        
        question = data['question'].strip()
        session_id = data['session_id']
        
        # Get client info
        ip_address = request.remote_addr
        user_agent = request.headers.get('User-Agent', 'Unknown')
        
        logger.info(f"Processing chat query for session {session_id}")
        
        with session_scope() as session:
            # Load config
            config = load_config()
            
            # Initialize GenAI engine
            genai_engine = GenAIEngine(config=config, session=session)
            
            # Process query
            chat_response = genai_engine.process_query(
                question=question,
                session_id=session_id,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            # Get chat history (last 3 Q&A pairs)
            history_manager = ChatHistoryManager(session)
            
            # Store chat interaction if successful
            if chat_response.success and not chat_response.rejected:
                history_manager.store_chat(
                    session_id=session_id,
                    question=question,
                    answer=chat_response.answer,
                    question_hash=genai_engine.generate_question_hash(question),
                    topic_valid=True,
                    pii_detected=False,
                    context_used=chat_response.context_used,
                    openai_tokens_input=chat_response.tokens_input,
                    openai_tokens_output=chat_response.tokens_output,
                    openai_cost_usd=chat_response.cost_usd,
                    response_time_ms=chat_response.response_time_ms
                )
                
                # Store audit log
                history_manager.store_audit_log(
                    session_id=session_id,
                    question_sanitized=question,
                    pii_patterns_detected=[],
                    topic_validation_result='valid',
                    ip_address=ip_address,
                    user_agent=user_agent,
                    rejected=False
                )
            else:
                # Store audit log for rejected queries
                history_manager.store_audit_log(
                    session_id=session_id,
                    question_sanitized=question,
                    pii_patterns_detected=chat_response.pii_patterns,
                    topic_validation_result='invalid' if chat_response.rejection_reason else 'valid',
                    ip_address=ip_address,
                    user_agent=user_agent,
                    rejected=True,
                    rejection_reason=chat_response.rejection_reason
                )
            
            session.commit()
            
            # Get chat history
            history = history_manager.get_recent_history(session_id, limit=3)
            
            # Format history for response
            formatted_history = [
                {
                    'question': h.question,
                    'answer': h.answer,
                    'timestamp': h.created_at.isoformat()
                }
                for h in history
            ]
            
            # Format response
            response = format_chat_response(chat_response, formatted_history)
            
            # Return appropriate status code
            if chat_response.rejected:
                if chat_response.pii_detected:
                    return jsonify(response), 400  # Bad request for PII
                else:
                    return jsonify(response), 422  # Unprocessable entity for invalid topic
            
            return jsonify(response), 200
            
    except Exception as e:
        logger.error(f"Error processing chat query: {e}", exc_info=True)
        return jsonify({
            'error': {
                'code': 'CHAT_ERROR',
                'message': 'Failed to process chat query',
                'details': str(e)
            }
        }), 500


@chat_bp.route('/history/<session_id>', methods=['GET'])
def get_chat_history(session_id: str):
    """
    Get chat history for a session.
    
    Args:
        session_id: User session ID
    
    Query Parameters:
        - limit: Number of messages to return (default: 10, max: 50)
    
    Returns:
        JSON response with chat history
    """
    try:
        limit = request.args.get('limit', 10, type=int)
        limit = min(limit, 50)  # Cap at 50
        
        logger.info(f"Fetching chat history for session {session_id}")
        
        with session_scope() as session:
            history_manager = ChatHistoryManager(session)
            
            history = history_manager.get_recent_history(session_id, limit=limit)
            
            formatted_history = [
                {
                    'question': h.question,
                    'answer': h.answer,
                    'timestamp': h.created_at.isoformat(),
                    'tokens_input': h.openai_tokens_input,
                    'tokens_output': h.openai_tokens_output,
                    'cost_usd': float(h.openai_cost_usd) if h.openai_cost_usd else 0.0
                }
                for h in history
            ]
            
            response = {
                'session_id': session_id,
                'history': formatted_history,
                'count': len(formatted_history)
            }
            
            return jsonify(response), 200
            
    except Exception as e:
        logger.error(f"Error fetching chat history: {e}", exc_info=True)
        return jsonify({
            'error': {
                'code': 'HISTORY_ERROR',
                'message': 'Failed to fetch chat history',
                'details': str(e)
            }
        }), 500


@chat_bp.route('/validate', methods=['POST'])
def validate_question():
    """
    Validate a question without processing it.
    
    Useful for client-side validation before submitting.
    
    Request Body:
        {
            "question": "What is Bitcoin?"
        }
    
    Returns:
        JSON response with validation result
    """
    try:
        data = request.get_json()
        
        if not data or 'question' not in data:
            return jsonify({
                'error': {
                    'code': 'INVALID_REQUEST',
                    'message': 'Field "question" is required'
                }
            }), 400
        
        question = data['question'].strip()
        
        with session_scope() as session:
            config = load_config()
            genai_engine = GenAIEngine(config=config, session=session)
            
            is_valid, rejection_message = genai_engine.validate_question(question)
            
            response = {
                'valid': is_valid,
                'question': question
            }
            
            if not is_valid:
                response['rejection_message'] = rejection_message
            
            return jsonify(response), 200
            
    except Exception as e:
        logger.error(f"Error validating question: {e}", exc_info=True)
        return jsonify({
            'error': {
                'code': 'VALIDATION_ERROR',
                'message': 'Failed to validate question',
                'details': str(e)
            }
        }), 500
