"""
Context Builder module.
Aggregates internal data (LSTM predictions, market data) to enrich OpenAI prompts.
"""

import logging
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from src.data.repositories import (
    CryptoRepository,
    PriceHistoryRepository,
    PredictionRepository,
    MarketTendencyRepository
)
from src.data.models import Cryptocurrency, PriceHistory, Prediction

logger = logging.getLogger(__name__)


class ContextBuilder:
    """
    Builds context from internal data sources for enriched OpenAI prompts.
    
    Aggregates:
    - LSTM predictions for relevant cryptocurrencies
    - Recent price data and trends
    - Current market tendency
    - Historical performance data
    """
    
    def __init__(self, session: Session):
        """
        Initialize context builder.
        
        Args:
            session: Database session
        """
        self.session = session
        
        # Initialize repositories
        self.crypto_repo = CryptoRepository(session)
        self.price_repo = PriceHistoryRepository(session)
        self.prediction_repo = PredictionRepository(session)
        self.tendency_repo = MarketTendencyRepository(session)
        
        logger.info("Initialized ContextBuilder")
    
    def extract_crypto_symbols(self, question: str) -> List[str]:
        """
        Extract cryptocurrency symbols mentioned in question.
        
        Args:
            question: User question
        
        Returns:
            List of cryptocurrency symbols found
        """
        # Common crypto symbols and names
        crypto_patterns = {
            'BTC': ['bitcoin', 'btc'],
            'ETH': ['ethereum', 'eth', 'ether'],
            'SOL': ['solana', 'sol'],
            'ADA': ['cardano', 'ada'],
            'XRP': ['ripple', 'xrp'],
            'DOGE': ['dogecoin', 'doge'],
            'DOT': ['polkadot', 'dot'],
            'MATIC': ['polygon', 'matic'],
            'LINK': ['chainlink', 'link'],
            'AVAX': ['avalanche', 'avax'],
            'UNI': ['uniswap', 'uni'],
            'LTC': ['litecoin', 'ltc'],
            'ATOM': ['cosmos', 'atom'],
            'XLM': ['stellar', 'xlm'],
            'BNB': ['binance', 'bnb'],
        }
        
        question_lower = question.lower()
        found_symbols = []
        
        for symbol, patterns in crypto_patterns.items():
            for pattern in patterns:
                # Use word boundaries to avoid false matches
                if re.search(r'\b' + re.escape(pattern) + r'\b', question_lower):
                    found_symbols.append(symbol)
                    break
        
        # Remove duplicates
        found_symbols = list(set(found_symbols))
        
        logger.debug(f"Extracted crypto symbols from question: {found_symbols}")
        return found_symbols
    
    def get_lstm_predictions(
        self,
        symbols: Optional[List[str]] = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Get LSTM predictions for specified cryptocurrencies or top performers.
        
        Args:
            symbols: List of crypto symbols (None = top performers)
            limit: Number of predictions to retrieve
        
        Returns:
            Dictionary with prediction data
        """
        predictions_data = {
            'predictions': [],
            'timestamp': None,
            'count': 0
        }
        
        if symbols:
            # Get predictions for specific cryptocurrencies
            for symbol in symbols:
                crypto = self.crypto_repo.get_by_symbol(symbol)
                if not crypto:
                    continue
                
                # Get latest prediction
                predictions = self.prediction_repo.get_by_crypto(crypto.id, limit=1)
                if predictions:
                    pred = predictions[0]
                    
                    # Get current price
                    latest_price = self.price_repo.get_latest_by_crypto(crypto.id, limit=1)
                    current_price = latest_price[0].price_usd if latest_price else pred.predicted_price
                    
                    # Calculate predicted change
                    predicted_change = (
                        (float(pred.predicted_price) - float(current_price)) / float(current_price)
                    ) * 100
                    
                    predictions_data['predictions'].append({
                        'symbol': crypto.symbol,
                        'name': crypto.name,
                        'current_price': float(current_price),
                        'predicted_price': float(pred.predicted_price),
                        'predicted_change_percent': predicted_change,
                        'confidence': float(pred.confidence_score) if pred.confidence_score else 0.0,
                        'horizon_hours': pred.prediction_horizon_hours
                    })
                    
                    if predictions_data['timestamp'] is None:
                        predictions_data['timestamp'] = pred.prediction_date
        else:
            # Get top performers
            top_predictions = self.prediction_repo.get_top_performers(limit=limit)
            
            for pred in top_predictions:
                crypto = self.crypto_repo.get_by_id(pred.crypto_id)
                if not crypto:
                    continue
                
                # Get current price
                latest_price = self.price_repo.get_latest_by_crypto(crypto.id, limit=1)
                current_price = latest_price[0].price_usd if latest_price else pred.predicted_price
                
                # Calculate predicted change
                predicted_change = (
                    (float(pred.predicted_price) - float(current_price)) / float(current_price)
                ) * 100
                
                predictions_data['predictions'].append({
                    'symbol': crypto.symbol,
                    'name': crypto.name,
                    'current_price': float(current_price),
                    'predicted_price': float(pred.predicted_price),
                    'predicted_change_percent': predicted_change,
                    'confidence': float(pred.confidence_score) if pred.confidence_score else 0.0,
                    'horizon_hours': pred.prediction_horizon_hours
                })
                
                if predictions_data['timestamp'] is None:
                    predictions_data['timestamp'] = pred.prediction_date
        
        predictions_data['count'] = len(predictions_data['predictions'])
        
        logger.debug(f"Retrieved {predictions_data['count']} LSTM predictions")
        return predictions_data
    
    def get_market_tendency(self) -> Dict[str, Any]:
        """
        Get current market tendency classification.
        
        Returns:
            Dictionary with market tendency data
        """
        tendency_data = {
            'tendency': 'unknown',
            'confidence': 0.0,
            'metrics': {},
            'timestamp': None
        }
        
        # Get latest tendency
        latest = self.tendency_repo.get_latest()
        
        if latest:
            tendency_data['tendency'] = latest.tendency
            tendency_data['confidence'] = float(latest.confidence) if latest.confidence else 0.0
            tendency_data['metrics'] = latest.metrics or {}
            tendency_data['timestamp'] = latest.timestamp
        
        logger.debug(f"Retrieved market tendency: {tendency_data['tendency']}")
        return tendency_data
    
    def get_recent_price_data(
        self,
        symbols: List[str],
        hours: int = 24
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get recent price data for specified cryptocurrencies.
        
        Args:
            symbols: List of crypto symbols
            hours: Number of hours to look back
        
        Returns:
            Dictionary mapping symbols to price data
        """
        price_data = {}
        
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        for symbol in symbols:
            crypto = self.crypto_repo.get_by_symbol(symbol)
            if not crypto:
                continue
            
            # Get price history
            prices = self.price_repo.get_by_crypto_and_time_range(
                crypto.id,
                start_time,
                end_time
            )
            
            if prices:
                price_data[symbol] = [
                    {
                        'timestamp': p.timestamp.isoformat(),
                        'price': float(p.price_usd),
                        'volume_24h': float(p.volume_24h) if p.volume_24h else 0.0,
                        'market_cap': float(p.market_cap) if p.market_cap else 0.0
                    }
                    for p in prices
                ]
        
        logger.debug(f"Retrieved recent price data for {len(price_data)} cryptocurrencies")
        return price_data
    
    def build_context(self, question: str) -> Dict[str, Any]:
        """
        Build comprehensive context for a question.
        
        Args:
            question: User question
        
        Returns:
            Dictionary with all relevant context data
        """
        logger.info("Building context for question")
        
        # Extract mentioned cryptocurrencies
        mentioned_symbols = self.extract_crypto_symbols(question)
        
        # Build context
        context = {
            'question': question,
            'mentioned_cryptos': mentioned_symbols,
            'lstm_predictions': {},
            'market_tendency': {},
            'recent_prices': {},
            'timestamp': datetime.now().isoformat()
        }
        
        # Get LSTM predictions
        if mentioned_symbols:
            # Get predictions for mentioned cryptos
            context['lstm_predictions'] = self.get_lstm_predictions(symbols=mentioned_symbols)
        else:
            # Get top performers if no specific cryptos mentioned
            context['lstm_predictions'] = self.get_lstm_predictions(limit=20)
        
        # Get market tendency
        context['market_tendency'] = self.get_market_tendency()
        
        # Get recent price data for mentioned cryptos
        if mentioned_symbols:
            context['recent_prices'] = self.get_recent_price_data(mentioned_symbols, hours=24)
        
        logger.info(
            f"Built context: {len(context['lstm_predictions']['predictions'])} predictions, "
            f"tendency={context['market_tendency']['tendency']}, "
            f"{len(context['recent_prices'])} price histories"
        )
        
        return context
    
    def format_context_for_prompt(self, context: Dict[str, Any]) -> str:
        """
        Format context data as text for OpenAI prompt.
        
        Args:
            context: Context dictionary from build_context()
        
        Returns:
            Formatted text string for prompt
        """
        lines = []
        
        # Market tendency
        if context['market_tendency']['tendency'] != 'unknown':
            tendency = context['market_tendency']
            lines.append(f"Current Market Tendency: {tendency['tendency'].upper()}")
            lines.append(f"Confidence: {tendency['confidence']:.2f}")
            
            if tendency['metrics']:
                metrics = tendency['metrics']
                if 'avg_change_percent' in metrics:
                    lines.append(f"Average Price Change: {metrics['avg_change_percent']:.2f}%")
                if 'positive_ratio' in metrics:
                    lines.append(f"Positive Movers: {metrics['positive_ratio']*100:.1f}%")
            lines.append("")
        
        # LSTM predictions
        if context['lstm_predictions']['predictions']:
            lines.append("LSTM Model Predictions (Next 24 Hours):")
            
            for pred in context['lstm_predictions']['predictions'][:10]:  # Limit to top 10 for prompt
                lines.append(
                    f"- {pred['symbol']} ({pred['name']}): "
                    f"Current ${pred['current_price']:.2f}, "
                    f"Predicted ${pred['predicted_price']:.2f} "
                    f"({pred['predicted_change_percent']:+.2f}%), "
                    f"Confidence: {pred['confidence']:.2f}"
                )
            
            if len(context['lstm_predictions']['predictions']) > 10:
                lines.append(f"... and {len(context['lstm_predictions']['predictions']) - 10} more")
            lines.append("")
        
        # Recent price trends for mentioned cryptos
        if context['recent_prices']:
            lines.append("Recent Price Trends:")
            
            for symbol, prices in context['recent_prices'].items():
                if len(prices) >= 2:
                    start_price = prices[0]['price']
                    end_price = prices[-1]['price']
                    change_percent = ((end_price - start_price) / start_price) * 100
                    
                    lines.append(
                        f"- {symbol}: ${start_price:.2f} → ${end_price:.2f} "
                        f"({change_percent:+.2f}% over {len(prices)} hours)"
                    )
            lines.append("")
        
        formatted_text = "\n".join(lines)
        
        logger.debug(f"Formatted context: {len(formatted_text)} characters")
        return formatted_text
