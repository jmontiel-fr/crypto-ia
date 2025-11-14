"""
Admin endpoints.
Provides administrative functions for data collection and system management.
"""

import logging
from flask import Blueprint, jsonify, request, current_app
from datetime import datetime
from threading import Thread

from src.api.middleware.auth import admin_required
from src.data.database import session_scope
from src.collectors.crypto_collector import CryptoCollector
from src.collectors.binance_client import BinanceClient
from src.config.config_loader import load_config

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__)

# Global collection status
collection_status = {
    'is_running': False,
    'current_operation': None,
    'progress': 0,
    'current_crypto': None,
    'start_time': None,
    'results': []
}


def run_collection_task(mode: str, start_date: datetime = None, end_date: datetime = None):
    """
    Run data collection task in background.
    
    Args:
        mode: Collection mode ('backward', 'forward', 'gap_fill')
        start_date: Start date for collection
        end_date: End date for collection
    """
    global collection_status
    
    try:
        collection_status['is_running'] = True
        collection_status['current_operation'] = mode
        collection_status['start_time'] = datetime.now()
        collection_status['results'] = []
        
        logger.info(f"Starting {mode} collection task")
        
        # Load config
        config = load_config()
        
        # Initialize Binance client
        binance_client = BinanceClient(
            api_key=config.binance_api_key,
            api_secret=config.binance_api_secret
        )
        
        # Initialize collector
        collector = CryptoCollector(
            binance_client=binance_client,
            top_n_cryptos=config.top_n_cryptos
        )
        
        # Run collection based on mode
        if mode == 'backward':
            results = collector.collect_backward(
                start_date=start_date,
                end_date=end_date
            )
        elif mode == 'forward':
            results = collector.collect_forward(end_date=end_date)
        elif mode == 'gap_fill':
            results = collector.detect_and_fill_gaps(start_date=start_date)
        else:
            raise ValueError(f"Invalid collection mode: {mode}")
        
        collection_status['results'] = [
            {
                'crypto_symbol': r.crypto_symbol,
                'success': r.success,
                'status': r.status,
                'records_collected': r.records_collected,
                'duration_seconds': r.duration_seconds,
                'error_message': r.error_message,
                'retry_count': r.retry_count,
                'missing_ranges_count': len(r.missing_ranges) if r.missing_ranges else 0
            }
            for r in results
        ]
        
        logger.info(f"Completed {mode} collection task: {len(results)} cryptos processed")
        
    except Exception as e:
        logger.error(f"Error in collection task: {e}", exc_info=True)
        collection_status['results'] = [{'error': str(e)}]
    
    finally:
        collection_status['is_running'] = False
        collection_status['current_operation'] = None


@admin_bp.route('/collect/trigger', methods=['POST'])
@admin_required
def trigger_collection():
    """
    Trigger manual data collection.
    
    Request Body:
        {
            "mode": "backward|forward|gap_fill",
            "start_date": "2024-01-01T00:00:00Z" (optional, for backward/gap_fill),
            "end_date": "2024-12-31T23:59:59Z" (optional)
        }
    
    Returns:
        JSON response with collection task status
    """
    try:
        global collection_status
        
        # Check if collection is already running
        if collection_status['is_running']:
            return jsonify({
                'error': {
                    'code': 'COLLECTION_IN_PROGRESS',
                    'message': 'Data collection is already in progress',
                    'details': f"Current operation: {collection_status['current_operation']}"
                }
            }), 409
        
        # Parse request data
        data = request.get_json()
        
        if not data or 'mode' not in data:
            return jsonify({
                'error': {
                    'code': 'INVALID_REQUEST',
                    'message': 'Field "mode" is required',
                    'details': 'Valid modes: backward, forward, gap_fill'
                }
            }), 400
        
        mode = data['mode']
        
        if mode not in ['backward', 'forward', 'gap_fill']:
            return jsonify({
                'error': {
                    'code': 'INVALID_MODE',
                    'message': f'Invalid collection mode: {mode}',
                    'details': 'Valid modes: backward, forward, gap_fill'
                }
            }), 400
        
        # Parse dates
        start_date = None
        end_date = None
        
        if 'start_date' in data:
            try:
                start_date = datetime.fromisoformat(data['start_date'].replace('Z', '+00:00'))
            except ValueError:
                return jsonify({
                    'error': {
                        'code': 'INVALID_DATE',
                        'message': 'Invalid start_date format',
                        'details': 'Use ISO 8601 format: YYYY-MM-DDTHH:MM:SSZ'
                    }
                }), 400
        
        if 'end_date' in data:
            try:
                end_date = datetime.fromisoformat(data['end_date'].replace('Z', '+00:00'))
            except ValueError:
                return jsonify({
                    'error': {
                        'code': 'INVALID_DATE',
                        'message': 'Invalid end_date format',
                        'details': 'Use ISO 8601 format: YYYY-MM-DDTHH:MM:SSZ'
                    }
                }), 400
        
        # Start collection in background thread
        thread = Thread(
            target=run_collection_task,
            args=(mode, start_date, end_date)
        )
        thread.daemon = True
        thread.start()
        
        logger.info(f"Triggered {mode} collection task")
        
        return jsonify({
            'success': True,
            'message': f'Collection task started: {mode}',
            'mode': mode,
            'start_date': start_date.isoformat() if start_date else None,
            'end_date': end_date.isoformat() if end_date else None,
            'status_endpoint': '/api/admin/collect/status'
        }), 202
        
    except Exception as e:
        logger.error(f"Error triggering collection: {e}", exc_info=True)
        return jsonify({
            'error': {
                'code': 'TRIGGER_ERROR',
                'message': 'Failed to trigger collection',
                'details': str(e)
            }
        }), 500


@admin_bp.route('/collect/status', methods=['GET'])
@admin_required
def get_collection_status():
    """
    Get current data collection status.
    
    Returns:
        JSON response with collection progress and status
    """
    try:
        global collection_status
        
        response = {
            'is_running': collection_status['is_running'],
            'current_operation': collection_status['current_operation'],
            'start_time': collection_status['start_time'].isoformat() if collection_status['start_time'] else None,
            'timestamp': datetime.now().isoformat()
        }
        
        if collection_status['is_running']:
            # Calculate elapsed time
            elapsed = (datetime.now() - collection_status['start_time']).total_seconds()
            response['elapsed_seconds'] = int(elapsed)
            response['status'] = 'running'
        else:
            response['status'] = 'idle'
        
        # Add results if available
        if collection_status['results']:
            response['last_results'] = {
                'total_cryptos': len(collection_status['results']),
                'complete': sum(1 for r in collection_status['results'] if r.get('status') == 'complete'),
                'partial': sum(1 for r in collection_status['results'] if r.get('status') == 'partial'),
                'failed': sum(1 for r in collection_status['results'] if r.get('status') == 'failed'),
                'skipped': sum(1 for r in collection_status['results'] if r.get('status') == 'skipped'),
                'total_records': sum(r.get('records_collected', 0) for r in collection_status['results']),
                'details': collection_status['results'][-20:]  # Last 20 for brevity
            }
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Error getting collection status: {e}", exc_info=True)
        return jsonify({
            'error': {
                'code': 'STATUS_ERROR',
                'message': 'Failed to get collection status',
                'details': str(e)
            }
        }), 500


@admin_bp.route('/system/info', methods=['GET'])
@admin_required
def get_system_info():
    """
    Get system information and statistics.
    
    Returns:
        JSON response with system info
    """
    try:
        with session_scope() as session:
            from src.data.repositories import (
                CryptoRepository,
                PriceHistoryRepository,
                PredictionRepository,
                ChatHistoryRepository
            )
            
            crypto_repo = CryptoRepository(session)
            price_repo = PriceHistoryRepository(session)
            prediction_repo = PredictionRepository(session)
            chat_repo = ChatHistoryRepository(session)
            
            # Get counts
            total_cryptos = len(crypto_repo.get_all())
            
            # Get latest price timestamp
            latest_price = None
            if total_cryptos > 0:
                first_crypto = crypto_repo.get_all()[0]
                latest_prices = price_repo.get_latest_by_crypto(first_crypto.id, limit=1)
                if latest_prices:
                    latest_price = latest_prices[0].timestamp
            
            # Get prediction count
            total_predictions = prediction_repo.count_all()
            
            # Get chat history count
            total_chats = chat_repo.count_all()
            
            response = {
                'system': {
                    'service': 'Crypto Market Analysis API',
                    'version': '1.0.0',
                    'timestamp': datetime.now().isoformat()
                },
                'database': {
                    'total_cryptocurrencies': total_cryptos,
                    'latest_price_data': latest_price.isoformat() if latest_price else None,
                    'total_predictions': total_predictions,
                    'total_chat_messages': total_chats
                },
                'collection': {
                    'is_running': collection_status['is_running'],
                    'current_operation': collection_status['current_operation']
                }
            }
            
            return jsonify(response), 200
            
    except Exception as e:
        logger.error(f"Error getting system info: {e}", exc_info=True)
        return jsonify({
            'error': {
                'code': 'SYSTEM_INFO_ERROR',
                'message': 'Failed to get system info',
                'details': str(e)
            }
        }), 500


@admin_bp.route('/logs/recent', methods=['GET'])
@admin_required
def get_recent_logs():
    """
    Get recent application logs.
    
    Query Parameters:
        - lines: Number of log lines to return (default: 100, max: 1000)
    
    Returns:
        JSON response with recent log entries
    """
    try:
        lines = request.args.get('lines', 100, type=int)
        lines = min(lines, 1000)  # Cap at 1000
        
        # This is a placeholder - in production, you'd read from log files
        # or a centralized logging system
        
        response = {
            'message': 'Log retrieval not implemented',
            'details': 'Configure log file path and implement log reading',
            'requested_lines': lines
        }
        
        return jsonify(response), 501  # Not Implemented
        
    except Exception as e:
        logger.error(f"Error getting logs: {e}", exc_info=True)
        return jsonify({
            'error': {
                'code': 'LOGS_ERROR',
                'message': 'Failed to get logs',
                'details': str(e)
            }
        }), 500
