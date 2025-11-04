"""
Topic Validator module.
Ensures user questions are related to cryptocurrency and blockchain topics.
"""

import re
import logging
from typing import Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TopicValidationResult:
    """Result of topic validation."""
    is_valid: bool
    reason: str
    rejection_message: str = ""


class TopicValidator:
    """
    Topic validation class.
    Validates that questions are crypto-related and rejects off-topic queries.
    """
    
    def __init__(self):
        """Initialize topic validator with allowed and rejected topic keywords."""
        # Allowed crypto-related topics
        self.allowed_keywords = {
            # Cryptocurrencies
            'bitcoin', 'btc', 'ethereum', 'eth', 'crypto', 'cryptocurrency', 'cryptocurrencies',
            'altcoin', 'altcoins', 'coin', 'coins', 'token', 'tokens',
            'solana', 'sol', 'cardano', 'ada', 'ripple', 'xrp', 'dogecoin', 'doge',
            'litecoin', 'ltc', 'polkadot', 'dot', 'chainlink', 'link', 'stellar', 'xlm',
            'binance', 'bnb', 'polygon', 'matic', 'avalanche', 'avax', 'shiba', 'shib',
            
            # Blockchain technology
            'blockchain', 'block chain', 'distributed ledger', 'ledger',
            'consensus', 'proof of work', 'pow', 'proof of stake', 'pos',
            'mining', 'miner', 'miners', 'hash', 'hashing', 'hashrate',
            'node', 'nodes', 'validator', 'validators',
            
            # DeFi and Web3
            'defi', 'decentralized finance', 'dex', 'decentralized exchange',
            'liquidity', 'yield', 'staking', 'stake', 'farming', 'yield farming',
            'smart contract', 'smart contracts', 'dapp', 'dapps',
            'web3', 'web 3', 'metaverse',
            
            # NFTs
            'nft', 'nfts', 'non-fungible', 'collectible', 'collectibles',
            
            # Trading and markets
            'trading', 'trade', 'market', 'markets', 'exchange', 'exchanges',
            'price', 'prices', 'volume', 'market cap', 'marketcap', 'capitalization',
            'bull', 'bullish', 'bear', 'bearish', 'volatile', 'volatility',
            'trend', 'trends', 'analysis', 'technical analysis', 'fundamental analysis',
            'chart', 'charts', 'candlestick', 'support', 'resistance',
            'buy', 'sell', 'hold', 'hodl', 'investment', 'invest', 'portfolio',
            
            # Wallets and security
            'wallet', 'wallets', 'private key', 'public key', 'seed phrase',
            'cold storage', 'hot wallet', 'hardware wallet',
            
            # Regulations and legal
            'regulation', 'regulations', 'sec', 'regulatory', 'legal',
            'compliance', 'kyc', 'aml', 'tax', 'taxes',
            
            # Technology
            'layer 1', 'layer 2', 'l1', 'l2', 'scaling', 'scalability',
            'transaction', 'transactions', 'tx', 'gas', 'gas fee', 'fees',
            'fork', 'hard fork', 'soft fork', 'upgrade', 'protocol',
        }
        
        # Rejected topics (non-crypto)
        self.rejected_keywords = {
            # Weather
            'weather', 'temperature', 'rain', 'snow', 'forecast', 'climate',
            'sunny', 'cloudy', 'storm', 'hurricane', 'tornado',
            
            # Sports
            'football', 'soccer', 'basketball', 'baseball', 'tennis', 'golf',
            'nfl', 'nba', 'mlb', 'nhl', 'fifa', 'olympics',
            'game', 'match', 'score', 'team', 'player', 'athlete',
            
            # Politics (unless crypto-related)
            'election', 'vote', 'voting', 'president', 'senator', 'congress',
            'democrat', 'republican', 'liberal', 'conservative',
            'government policy', 'foreign policy',
            
            # Entertainment
            'movie', 'movies', 'film', 'actor', 'actress', 'director',
            'tv show', 'series', 'netflix', 'streaming',
            'music', 'song', 'album', 'concert', 'band', 'singer',
            
            # General news (unless crypto-related)
            'celebrity', 'celebrities', 'gossip',
            
            # Personal advice (non-crypto)
            'relationship', 'dating', 'marriage', 'divorce',
            'health', 'medical', 'doctor', 'medicine', 'disease',
            'diet', 'exercise', 'fitness', 'workout',
            
            # Other
            'recipe', 'cooking', 'food', 'restaurant',
            'travel', 'vacation', 'hotel', 'flight',
            'car', 'automobile', 'vehicle',
        }
        
        # Rejection messages for different scenarios
        self.rejection_messages = {
            'off_topic': (
                "I'm a cryptocurrency market analysis assistant. "
                "I can only answer questions related to cryptocurrencies, blockchain technology, "
                "crypto markets, trading, DeFi, NFTs, and related topics. "
                "Please ask a crypto-related question."
            ),
            'too_vague': (
                "Your question seems too vague or general. "
                "Please ask a specific question about cryptocurrencies or blockchain technology."
            ),
        }
    
    def validate(self, question: str) -> TopicValidationResult:
        """
        Validate if question is crypto-related.
        
        Args:
            question: User question to validate.
        
        Returns:
            TopicValidationResult with validation status and reason.
        """
        if not question or not question.strip():
            return TopicValidationResult(
                is_valid=False,
                reason='empty_question',
                rejection_message="Please provide a question."
            )
        
        question_lower = question.lower()
        
        # Check if question is too short (likely not meaningful)
        if len(question.split()) < 3:
            return TopicValidationResult(
                is_valid=False,
                reason='too_short',
                rejection_message=self.rejection_messages['too_vague']
            )
        
        # Check for rejected topics first
        for keyword in self.rejected_keywords:
            if self._contains_keyword(question_lower, keyword):
                # Check if it's crypto-related despite containing rejected keyword
                # (e.g., "crypto regulation" contains "regulation" but is valid)
                if not self._contains_crypto_keyword(question_lower):
                    logger.info(f"Question rejected: contains non-crypto keyword '{keyword}'")
                    return TopicValidationResult(
                        is_valid=False,
                        reason='off_topic',
                        rejection_message=self.rejection_messages['off_topic']
                    )
        
        # Check for allowed crypto keywords
        if self._contains_crypto_keyword(question_lower):
            return TopicValidationResult(
                is_valid=True,
                reason='crypto_related'
            )
        
        # If no crypto keywords found, reject
        logger.info("Question rejected: no crypto-related keywords found")
        return TopicValidationResult(
            is_valid=False,
            reason='off_topic',
            rejection_message=self.rejection_messages['off_topic']
        )
    
    def _contains_keyword(self, text: str, keyword: str) -> bool:
        """
        Check if text contains keyword (word boundary aware).
        
        Args:
            text: Text to search in (lowercase).
            keyword: Keyword to search for (lowercase).
        
        Returns:
            True if keyword found, False otherwise.
        """
        # Use word boundaries for single words, simple contains for phrases
        if ' ' in keyword:
            return keyword in text
        else:
            # Use regex with word boundaries
            pattern = r'\b' + re.escape(keyword) + r'\b'
            return bool(re.search(pattern, text))
    
    def _contains_crypto_keyword(self, text: str) -> bool:
        """
        Check if text contains any crypto-related keyword.
        
        Args:
            text: Text to search in (lowercase).
        
        Returns:
            True if any crypto keyword found, False otherwise.
        """
        for keyword in self.allowed_keywords:
            if self._contains_keyword(text, keyword):
                return True
        return False
    
    def is_valid_topic(self, question: str) -> bool:
        """
        Simple boolean check if question is valid.
        
        Args:
            question: User question to validate.
        
        Returns:
            True if valid crypto topic, False otherwise.
        """
        result = self.validate(question)
        return result.is_valid
    
    def get_rejection_message(self, question: str) -> str:
        """
        Get rejection message for invalid question.
        
        Args:
            question: User question that was rejected.
        
        Returns:
            User-friendly rejection message.
        """
        result = self.validate(question)
        return result.rejection_message if not result.is_valid else ""
