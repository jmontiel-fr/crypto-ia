"""
Binance API client wrapper for cryptocurrency data collection.
Provides methods for fetching price data and market information.
"""

import logging
import time
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


@dataclass
class CryptoInfo:
    """Cryptocurrency information from Binance."""
    symbol: str
    name: str
    market_cap_rank: Optional[int] = None
    current_price: Optional[Decimal] = None
    market_cap: Optional[Decimal] = None


@dataclass
class PriceData:
    """Price data point for a cryptocurrency."""
    symbol: str
    timestamp: datetime
    price_usd: Decimal
    volume_24h: Optional[Decimal] = None
    market_cap: Optional[Decimal] = None


class BinanceAPIError(Exception):
    """Exception raised for Binance API errors."""
    pass


class BinanceRateLimitError(Exception):
    """Exception raised when rate limit is exceeded."""
    pass


class BinanceClient:
    """
    Client for interacting with Binance API.
    
    Implements retry logic with exponential backoff and rate limiting
    to respect Binance API constraints.
    """
    
    # Binance API endpoints
    BASE_URL = "https://api.binance.com"
    API_V3 = f"{BASE_URL}/api/v3"
    
    # Rate limiting configuration
    MAX_REQUESTS_PER_MINUTE = 1200  # Binance limit
    REQUEST_WEIGHT_LIMIT = 6000  # Per minute
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        timeout: int = 30
    ):
        """
        Initialize Binance API client.
        
        Args:
            api_key: Binance API key (optional for public endpoints).
            api_secret: Binance API secret (optional for public endpoints).
            max_retries: Maximum number of retry attempts.
            retry_delay: Initial delay between retries in seconds.
            timeout: Request timeout in seconds.
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout
        
        # Request tracking for rate limiting
        self.request_times: List[float] = []
        self.request_weights: List[tuple] = []  # (timestamp, weight)
        
        # Configure session with retry strategy
        self.session = self._create_session()
        
        logger.info("Binance API client initialized")
    
    def _create_session(self) -> requests.Session:
        """
        Create requests session with retry configuration.
        
        Returns:
            Configured requests.Session instance.
        """
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=self.retry_delay,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def _check_rate_limit(self, weight: int = 1) -> None:
        """
        Check and enforce rate limiting.
        
        Args:
            weight: Request weight (default: 1).
        
        Raises:
            BinanceRateLimitError: If rate limit would be exceeded.
        """
        current_time = time.time()
        one_minute_ago = current_time - 60
        
        # Clean old request times
        self.request_times = [t for t in self.request_times if t > one_minute_ago]
        self.request_weights = [(t, w) for t, w in self.request_weights if t > one_minute_ago]
        
        # Check request count limit
        if len(self.request_times) >= self.MAX_REQUESTS_PER_MINUTE:
            sleep_time = 60 - (current_time - self.request_times[0])
            if sleep_time > 0:
                logger.warning(f"Rate limit approaching, sleeping for {sleep_time:.2f}s")
                time.sleep(sleep_time)
                self.request_times = []
                self.request_weights = []
        
        # Check request weight limit
        total_weight = sum(w for _, w in self.request_weights)
        if total_weight + weight > self.REQUEST_WEIGHT_LIMIT:
            sleep_time = 60 - (current_time - self.request_weights[0][0])
            if sleep_time > 0:
                logger.warning(f"Weight limit approaching, sleeping for {sleep_time:.2f}s")
                time.sleep(sleep_time)
                self.request_times = []
                self.request_weights = []
        
        # Record this request
        self.request_times.append(current_time)
        self.request_weights.append((current_time, weight))
    
    def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        weight: int = 1
    ) -> Dict[str, Any]:
        """
        Make HTTP request to Binance API with retry logic.
        
        Args:
            endpoint: API endpoint path.
            params: Query parameters.
            weight: Request weight for rate limiting.
        
        Returns:
            JSON response as dictionary.
        
        Raises:
            BinanceAPIError: If request fails after retries.
            BinanceRateLimitError: If rate limit is exceeded.
        """
        # Check rate limit before making request
        self._check_rate_limit(weight)
        
        url = f"{self.API_V3}/{endpoint}"
        headers = {}
        
        if self.api_key:
            headers["X-MBX-APIKEY"] = self.api_key
        
        retry_count = 0
        last_exception = None
        
        while retry_count <= self.max_retries:
            try:
                response = self.session.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=self.timeout
                )
                
                # Check for rate limit response
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    logger.warning(f"Rate limit hit, waiting {retry_after}s")
                    time.sleep(retry_after)
                    retry_count += 1
                    continue
                
                # Raise for other HTTP errors
                response.raise_for_status()
                
                return response.json()
                
            except requests.exceptions.RequestException as e:
                last_exception = e
                retry_count += 1
                
                if retry_count <= self.max_retries:
                    delay = self.retry_delay * (2 ** (retry_count - 1))  # Exponential backoff
                    logger.warning(
                        f"Request failed (attempt {retry_count}/{self.max_retries}), "
                        f"retrying in {delay}s: {e}"
                    )
                    time.sleep(delay)
                else:
                    logger.error(f"Request failed after {self.max_retries} retries: {e}")
        
        raise BinanceAPIError(f"Failed to fetch data from {endpoint}: {last_exception}")
    
    def get_server_time(self) -> datetime:
        """
        Get Binance server time.
        
        Returns:
            Server time as datetime.
        """
        data = self._make_request("time", weight=1)
        timestamp_ms = data.get("serverTime", 0)
        return datetime.fromtimestamp(timestamp_ms / 1000)
    
    def get_exchange_info(self) -> Dict[str, Any]:
        """
        Get exchange information including trading pairs.
        
        Returns:
            Exchange information dictionary.
        """
        return self._make_request("exchangeInfo", weight=10)
    
    def get_ticker_24h(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get 24-hour ticker price change statistics.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT'). If None, returns all symbols.
        
        Returns:
            List of ticker data dictionaries.
        """
        params = {}
        if symbol:
            params["symbol"] = symbol
            weight = 1
        else:
            weight = 40  # All symbols request has higher weight
        
        result = self._make_request("ticker/24hr", params=params, weight=weight)
        
        # Ensure result is a list
        if isinstance(result, dict):
            return [result]
        return result
    
    def get_klines(
        self,
        symbol: str,
        interval: str = "1h",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 500
    ) -> List[List]:
        """
        Get kline/candlestick data for a symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT').
            interval: Kline interval (1m, 5m, 15m, 1h, 4h, 1d, etc.).
            start_time: Start time for data.
            end_time: End time for data.
            limit: Number of records to return (max 1000).
        
        Returns:
            List of kline data arrays.
        """
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": min(limit, 1000)  # Binance max is 1000
        }
        
        if start_time:
            params["startTime"] = int(start_time.timestamp() * 1000)
        if end_time:
            params["endTime"] = int(end_time.timestamp() * 1000)
        
        return self._make_request("klines", params=params, weight=1)
    
    def get_hourly_prices(
        self,
        symbol: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[PriceData]:
        """
        Get hourly price data for a cryptocurrency.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT').
            start_time: Start time for data collection.
            end_time: End time for data collection.
        
        Returns:
            List of PriceData instances with hourly data.
        """
        all_prices = []
        current_start = start_time
        
        # Binance returns max 1000 records per request
        # For hourly data, that's about 41 days
        max_hours_per_request = 1000
        
        while current_start < end_time:
            # Calculate end time for this batch
            batch_end = min(
                current_start + timedelta(hours=max_hours_per_request),
                end_time
            )
            
            try:
                klines = self.get_klines(
                    symbol=symbol,
                    interval="1h",
                    start_time=current_start,
                    end_time=batch_end,
                    limit=1000
                )
                
                # Parse kline data
                for kline in klines:
                    timestamp = datetime.fromtimestamp(kline[0] / 1000)
                    close_price = Decimal(str(kline[4]))  # Close price
                    volume = Decimal(str(kline[5]))  # Volume
                    
                    price_data = PriceData(
                        symbol=symbol.replace("USDT", ""),  # Remove USDT suffix
                        timestamp=timestamp,
                        price_usd=close_price,
                        volume_24h=volume,
                        market_cap=None  # Not available in kline data
                    )
                    all_prices.append(price_data)
                
                logger.debug(
                    f"Fetched {len(klines)} hourly prices for {symbol} "
                    f"from {current_start} to {batch_end}"
                )
                
                # Move to next batch
                current_start = batch_end
                
                # Small delay to avoid hitting rate limits
                time.sleep(0.1)
                
            except BinanceAPIError as e:
                logger.error(f"Failed to fetch hourly prices for {symbol}: {e}")
                # Continue with next batch
                current_start = batch_end
        
        return all_prices
    
    def get_top_by_market_cap(self, limit: int = 50) -> List[CryptoInfo]:
        """
        Get top N cryptocurrencies by market capitalization.
        
        Note: Binance API doesn't directly provide market cap rankings.
        This method uses 24h ticker data and sorts by quote volume as a proxy.
        
        Args:
            limit: Number of top cryptocurrencies to retrieve.
        
        Returns:
            List of CryptoInfo instances sorted by trading volume.
        """
        try:
            # Get all USDT trading pairs
            tickers = self.get_ticker_24h()
            
            # Filter for USDT pairs and sort by quote volume
            usdt_pairs = []
            for ticker in tickers:
                symbol = ticker.get("symbol", "")
                if symbol.endswith("USDT") and symbol != "USDT":
                    try:
                        quote_volume = Decimal(str(ticker.get("quoteVolume", 0)))
                        price = Decimal(str(ticker.get("lastPrice", 0)))
                        
                        crypto_symbol = symbol.replace("USDT", "")
                        
                        usdt_pairs.append({
                            "symbol": crypto_symbol,
                            "quote_volume": quote_volume,
                            "price": price
                        })
                    except (ValueError, TypeError) as e:
                        logger.debug(f"Skipping {symbol} due to parsing error: {e}")
                        continue
            
            # Sort by quote volume (proxy for market cap)
            usdt_pairs.sort(key=lambda x: x["quote_volume"], reverse=True)
            
            # Convert to CryptoInfo objects
            result = []
            for rank, pair in enumerate(usdt_pairs[:limit], start=1):
                crypto_info = CryptoInfo(
                    symbol=pair["symbol"],
                    name=pair["symbol"],  # Binance doesn't provide full names
                    market_cap_rank=rank,
                    current_price=pair["price"],
                    market_cap=None  # Not directly available
                )
                result.append(crypto_info)
            
            logger.info(f"Retrieved top {len(result)} cryptocurrencies by volume")
            return result
            
        except BinanceAPIError as e:
            logger.error(f"Failed to get top cryptocurrencies: {e}")
            return []
    
    def test_connectivity(self) -> bool:
        """
        Test connectivity to Binance API.
        
        Returns:
            True if connection successful, False otherwise.
        """
        try:
            self.get_server_time()
            logger.info("Binance API connectivity test successful")
            return True
        except Exception as e:
            logger.error(f"Binance API connectivity test failed: {e}")
            return False
