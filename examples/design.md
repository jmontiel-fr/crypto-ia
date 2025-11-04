# Design Document

## Overview

The Crypto Market Analysis SaaS is a comprehensive system for collecting, analyzing, and predicting cryptocurrency market trends. The architecture follows a modular design with five main components:

1. **Data Collection Layer**: Automated cryptocurrency data gathering from Binance API
2. **Storage Layer**: PostgreSQL database with SQLAlchemy ORM
3. **Analysis Layer**: Deep learning prediction engine using LSTM/GRU networks
4. **API Layer**: Flask REST API exposing prediction and analysis endpoints
5. **Presentation Layer**: Dual interface with Streamlit dashboards and Bootstrap5 chat UI
6. **Alert Layer**: Automated SMS notification system for market shifts

The system is designed for AWS deployment with scalability and security as primary concerns.

## Architecture

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         Presentation Layer                       │
│  ┌──────────────────────┐      ┌──────────────────────────┐    │
│  │  Streamlit Dashboard │      │ Bootstrap5 Chat UI       │    │
│  │  - Market Overview   │      │ - GenAI Chat Interface   │    │
│  │  - Predictions View  │      │ - Topic Validation       │    │
│  └──────────┬───────────┘      └──────────┬───────────────┘    │
└─────────────┼──────────────────────────────┼────────────────────┘
              │                              │
              └──────────────┬───────────────┘
                             │
┌─────────────────────────────┼────────────────────────────────────┐
│                        API Layer (Flask)                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  REST Endpoints:                                          │   │
│  │  - /api/predictions/top20                                 │   │
│  │  - /api/market/tendency                                   │   │
│  │  - /api/chat/query                                        │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────┬────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────────┐
              │               │                   │
┌─────────────▼─────┐  ┌──────▼──────┐  ┌────────▼──────────────┐
│  Crypto Collector │  │  Prediction │  │  GenAI Engine         │
│  - Binance API    │  │  Engine     │  │  ┌─────────────────┐  │
│  - Scheduler      │  │  - LSTM/GRU │  │  │ Context Builder │  │
│  - Gap Detection  │  │  - Training │  │  │ - LSTM Data     │  │
└─────────┬─────────┘  └──────┬──────┘  │  │ - Market Data   │  │
          │                   │          │  └────────┬────────┘  │
          │                   │          │           │           │
          │                   │◄─────────┼───────────┘           │
          │                   │          │  ┌─────────────────┐  │
          │                   │          │  │ OpenAI API      │  │
          │                   │          │  │ - Internal +    │  │
          │                   │          │  │   External Info │  │
          │                   │          │  └─────────────────┘  │
          │                   │          │  ┌─────────────────┐  │
          │                   │          │  │ PII Filter      │  │
          │                   │          │  │ Topic Validator │  │
          │                   │          │  └─────────────────┘  │
          │                   │          └───────────────────────┘
          │                   │
          └─────────┬─────────┘
                    │
┌───────────────────▼────────────────────┐
│      Storage Layer (PostgreSQL)        │
│  - Cryptocurrency Price History        │
│  - Market Capitalization Data          │
│  - Prediction Results Cache            │
│  - Chat History                        │
└────────────────────────────────────────┘

┌────────────────────────────────────────┐
│         Alert System                   │
│  - Hourly Market Monitor               │
│  - SMS Gateway Integration             │
│  - Threshold Detection                 │
└────────────────────────────────────────┘
```

### Component Interaction Flow

1. **Data Collection Flow**:
   - Scheduler triggers Crypto_Collector (manual or automated)
   - Collector queries Data_Store for latest timestamp and gaps
   - Collector fetches data from Binance API (backward then forward)
   - Data persisted to PostgreSQL via SQLAlchemy

2. **Prediction Flow**:
   - API receives prediction request
   - Prediction_Engine loads historical data from Data_Store
   - LSTM/GRU model processes data and generates predictions
   - Results returned via API and cached

3. **Chat Flow**:
   - User submits question via Bootstrap5 UI
   - TopicValidator ensures question is crypto-related
   - PII_Filter analyzes question for sensitive data
   - If valid and clean, ContextBuilder gathers relevant data:
     - LSTM predictions for mentioned cryptocurrencies
     - Recent market data from Data_Store
     - Current market tendency
   - GenAI_Interface sends enriched prompt to OpenAI API with internal context
   - OpenAI combines internal data with external knowledge to generate response
   - Response displayed in chat UI with history (max 3)

4. **Alert Flow**:
   - Scheduler triggers Alert_System hourly
   - System analyzes recent market data for shifts
   - If threshold exceeded, SMS sent via gateway

## Components and Interfaces

### 1. Crypto Collector

**Purpose**: Gather and persist cryptocurrency price data from Binance API

**Key Classes**:
- `CryptoCollector`: Main orchestrator
- `BinanceClient`: API wrapper for Binance
- `DataGapDetector`: Identifies missing data ranges
- `CollectorScheduler`: Manages automated execution

**Interfaces**:
```python
class CryptoCollector:
    def collect_historical(self, start_date: datetime, end_date: datetime) -> None
    def collect_backward(self, from_date: datetime, to_date: datetime) -> None
    def collect_forward(self, from_date: datetime, to_date: datetime) -> None
    def get_top_n_cryptos(self, n: int) -> List[str]
    
class BinanceClient:
    def get_hourly_prices(self, symbol: str, start: datetime, end: datetime) -> List[PriceData]
    def get_top_by_market_cap(self, limit: int) -> List[CryptoInfo]
```

**Configuration** (.env):
- `COLLECTION_START_DATE`: Start date for historical collection
- `TOP_N_CRYPTOS`: Number of top cryptocurrencies to track
- `COLLECTION_SCHEDULE`: Cron expression for automated collection
- `BINANCE_API_KEY`: Binance API key (if required)
- `BINANCE_API_SECRET`: Binance API secret (if required)

### 2. Data Store (PostgreSQL)

**Purpose**: Persist cryptocurrency data with efficient querying

**Schema Design**:

```sql
-- Cryptocurrency metadata
CREATE TABLE cryptocurrencies (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    market_cap_rank INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Hourly price data
CREATE TABLE price_history (
    id SERIAL PRIMARY KEY,
    crypto_id INTEGER REFERENCES cryptocurrencies(id),
    timestamp TIMESTAMP NOT NULL,
    price_usd DECIMAL(20, 8) NOT NULL,
    volume_24h DECIMAL(20, 2),
    market_cap DECIMAL(20, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(crypto_id, timestamp)
);

CREATE INDEX idx_price_history_crypto_timestamp ON price_history(crypto_id, timestamp DESC);
CREATE INDEX idx_price_history_timestamp ON price_history(timestamp DESC);

-- Prediction cache
CREATE TABLE predictions (
    id SERIAL PRIMARY KEY,
    crypto_id INTEGER REFERENCES cryptocurrencies(id),
    prediction_date TIMESTAMP NOT NULL,
    predicted_price DECIMAL(20, 8),
    confidence_score DECIMAL(5, 4),
    prediction_horizon_hours INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Chat history with full tracing
CREATE TABLE chat_history (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    question_hash VARCHAR(64),  -- SHA256 hash for deduplication
    topic_valid BOOLEAN DEFAULT true,
    pii_detected BOOLEAN DEFAULT false,
    context_used JSONB,  -- LSTM predictions and data used
    openai_tokens_input INTEGER,
    openai_tokens_output INTEGER,
    openai_cost_usd DECIMAL(10, 6),
    response_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_chat_history_session ON chat_history(session_id, created_at DESC);
CREATE INDEX idx_chat_history_created ON chat_history(created_at DESC);

-- Query audit log for security and compliance
CREATE TABLE query_audit_log (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL,
    chat_history_id INTEGER REFERENCES chat_history(id),
    question_sanitized TEXT,  -- Question with any PII removed
    pii_patterns_detected TEXT[],  -- Array of PII types found
    topic_validation_result VARCHAR(50),
    ip_address VARCHAR(45),  -- IPv4 or IPv6
    user_agent TEXT,
    rejected BOOLEAN DEFAULT false,
    rejection_reason VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_log_session ON query_audit_log(session_id, created_at DESC);
CREATE INDEX idx_audit_log_rejected ON query_audit_log(rejected, created_at DESC);

-- Market tendency tracking
CREATE TABLE market_tendencies (
    id SERIAL PRIMARY KEY,
    tendency VARCHAR(50) NOT NULL,
    confidence DECIMAL(5, 4),
    metrics JSONB,
    timestamp TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**SQLAlchemy Models**:
```python
class Cryptocurrency(Base):
    __tablename__ = 'cryptocurrencies'
    id: int
    symbol: str
    name: str
    market_cap_rank: int
    
class PriceHistory(Base):
    __tablename__ = 'price_history'
    id: int
    crypto_id: int
    timestamp: datetime
    price_usd: Decimal
    volume_24h: Decimal
    market_cap: Decimal
    
class Prediction(Base):
    __tablename__ = 'predictions'
    id: int
    crypto_id: int
    prediction_date: datetime
    predicted_price: Decimal
    confidence_score: Decimal
    prediction_horizon_hours: int
```

### 3. Prediction Engine

**Purpose**: Generate cryptocurrency performance predictions using deep learning

**Key Classes**:
- `PredictionEngine`: Main prediction orchestrator
- `LSTMModel`: LSTM-based prediction model
- `GRUModel`: GRU-based prediction model (alternative)
- `DataPreprocessor`: Feature engineering and normalization
- `ModelTrainer`: Training pipeline management

**Architecture**:
```python
class PredictionEngine:
    def predict_top_performers(self, horizon_hours: int = 24) -> List[PredictionResult]
    def predict_market_tendency(self) -> MarketTendency
    def train_models(self, cryptos: List[str]) -> None
    def evaluate_model_performance(self) -> Dict[str, float]
```

**Model Architecture**:
- Input: Historical price sequences (e.g., 168 hours = 7 days)
- Features: Price, volume, market cap, technical indicators (RSI, MACD, Bollinger Bands)
- LSTM/GRU layers: 2-3 layers with 64-128 units
- Dropout: 0.2-0.3 for regularization
- Output: Price prediction for next 24 hours

**Market Tendency Classification**:
- **Bullish**: Overall market showing upward momentum (>60% of top cryptos increasing)
- **Bearish**: Overall market showing downward momentum (>60% of top cryptos decreasing)
- **Volatile**: High price fluctuations with no clear direction (std dev > threshold)
- **Stable**: Low volatility with minimal price changes
- **Consolidating**: Sideways movement within tight range

### 4. GenAI Engine

**Purpose**: Provide natural language interface for market analysis by combining LSTM predictions, stored data, and external real-time information

**Key Classes**:
- `GenAIEngine`: OpenAI API integration with context enrichment
- `ContextBuilder`: Aggregates data from LSTM predictions and database
- `PIIFilter`: Personal data detection and blocking
- `ChatHistoryManager`: Conversation history management
- `TopicValidator`: Ensure questions are crypto-related (not weather, sports, etc.)

**Interfaces**:
```python
class GenAIEngine:
    def process_query(self, question: str, session_id: str) -> ChatResponse
    def validate_topic(self, question: str) -> bool
    def build_context(self, question: str) -> Dict[str, Any]
    
class ContextBuilder:
    def get_lstm_predictions(self, relevant_cryptos: List[str]) -> Dict[str, PredictionResult]
    def get_market_tendency(self) -> MarketTendency
    def get_recent_price_data(self, cryptos: List[str], hours: int = 24) -> Dict[str, List[PriceData]]
    
class PIIFilter:
    def contains_pii(self, text: str) -> Tuple[bool, List[str]]
    def sanitize_text(self, text: str) -> str
```

**Context Enrichment Strategy**:

The GenAI Engine operates as an intelligent orchestrator that:

1. **Analyzes the question** to identify relevant cryptocurrencies and topics
2. **Gathers internal context** from:
   - LSTM prediction results for mentioned cryptocurrencies
   - Recent price history from the database
   - Current market tendency classification
   - Historical performance data
3. **Sends enriched prompt to OpenAI** that includes:
   - User's original question
   - Relevant LSTM predictions as context
   - Recent market data as context
   - System instructions to use both internal data AND external knowledge
4. **OpenAI provides response** using:
   - Internal context (LSTM predictions, stored data)
   - External real-time information (news, trends, general crypto knowledge)
   - Its own intelligence to synthesize comprehensive answers

**Example Context Flow**:
```
User Question: "Should I invest in Bitcoin right now?"

Step 1 - Context Builder gathers LOCAL data (NO OpenAI cost):
- Queries PostgreSQL for recent BTC prices
- Calls LSTM Prediction Engine for BTC forecast
- Gets market tendency from database
Result:
- LSTM prediction: BTC predicted +3.5% in 24h (confidence: 0.82)
- Market tendency: Bullish (confidence: 0.75)
- Recent price: $45,000 (up 2% in last hour)

Step 2 - GenAI Engine creates enriched TEXT prompt:
"Context: Our LSTM model predicts Bitcoin will increase 3.5% in the next 24 hours 
with 82% confidence. Current market tendency is bullish. Bitcoin is currently at 
$45,000, up 2% in the last hour.

User question: Should I invest in Bitcoin right now?

Please provide analysis considering both our internal predictions and current 
external market conditions, news, and broader cryptocurrency trends."

Step 3 - Send TEXT to OpenAI API (THIS is where OpenAI cost occurs):
- Input tokens: ~150 tokens (system prompt + context + question)
- Output tokens: ~300 tokens (response)
- Cost: ~$0.0001 per query with gpt-4o-mini

Step 4 - OpenAI Response combines:
- Internal LSTM prediction data (from our prompt)
- External market news and sentiment (from OpenAI's knowledge)
- General investment considerations
- Risk factors and disclaimers
```

**Important Cost Clarification**:

OpenAI does NOT have direct access to:
- Your PostgreSQL database
- Your LSTM models
- Your local servers or AWS resources

OpenAI only receives:
- Text prompts we send via API
- Text responses we receive back

**Cost Structure**:
- OpenAI charges per token (text unit) sent and received
- gpt-4o-mini pricing: ~$0.15 per 1M input tokens, ~$0.60 per 1M output tokens
- Average query: 150 input + 300 output tokens = ~$0.0002 per question
- 1000 questions/day = ~$0.20/day = ~$6/month for OpenAI

**Data Flow Summary**:
```
[User Question] 
    ↓
[Topic Validator] → Validates crypto-related (local, free)
    ↓
[PII Filter] → Checks for sensitive data (local, free)
    ↓
[Context Builder] → Queries DB + LSTM (local, free)
    ↓
[GenAI Engine] → Creates text prompt with context
    ↓
[OpenAI API] → Sends TEXT prompt (COST: ~$0.0002)
    ↓
[OpenAI Response] → Returns TEXT answer (included in cost)
    ↓
[User sees answer in UI]
```

The key insight: We do all the heavy lifting locally (database queries, LSTM predictions), then send only a small text summary to OpenAI. This keeps costs minimal while leveraging both our internal intelligence and OpenAI's external knowledge.

**Detailed Example: "What are the 20 best performing cryptos for next cycle?"**

```
Step 1: Topic Validation (Local - FREE)
- Question analyzed: Contains "cryptos" → Valid crypto topic ✓
- No PII detected ✓

Step 2: Context Builder (Local - FREE)
- Calls Prediction Engine API: GET /api/predictions/top20
- LSTM model runs predictions on all tracked cryptos (e.g., top 50)
- Returns top 20 with predictions:
  1. BTC: +3.5% (confidence: 0.82)
  2. ETH: +4.2% (confidence: 0.78)
  3. SOL: +5.1% (confidence: 0.75)
  ... (17 more)
- Also gets market tendency: "Bullish"
- Total local processing time: ~2-3 seconds

Step 3: Create Enriched Prompt (Local - FREE)
GenAI Engine builds text prompt:
"
System: You are a crypto market analyst. Use our LSTM predictions and your 
knowledge of current market conditions.

Context from our LSTM model (next 24 hours):
1. Bitcoin (BTC): Predicted +3.5% (confidence 82%)
2. Ethereum (ETH): Predicted +4.2% (confidence 78%)
3. Solana (SOL): Predicted +5.1% (confidence 75%)
... [all 20 predictions listed]

Current market tendency: Bullish

User question: What are the 20 best performing cryptos for next cycle?

Provide analysis of these predictions considering current market conditions, 
recent news, and any relevant external factors.
"

Step 4: Send to OpenAI (COST: ~$0.0003)
- Input tokens: ~400 tokens (system + 20 predictions + question)
- OpenAI processes with its knowledge of:
  - Recent crypto news
  - Market sentiment
  - Regulatory developments
  - Technical analysis principles
  - General market trends

Step 5: OpenAI Response (COST: included above)
- Output tokens: ~400 tokens
- Response example:
"Based on the LSTM predictions, here are the top 20 performers for the next 
24 hours:

1. Solana (SOL) - Predicted +5.1%: Strong momentum due to recent network 
   upgrades and increased DeFi activity...
2. Ethereum (ETH) - Predicted +4.2%: Upcoming Shanghai upgrade creating 
   positive sentiment...
3. Bitcoin (BTC) - Predicted +3.5%: Institutional buying pressure continues...

[Continues with analysis of all 20, incorporating both LSTM predictions 
and external market context]

Note: These are short-term predictions. Consider market volatility and 
your risk tolerance..."

Step 6: Display to User (Local - FREE)
- Response shown in chat UI
- Saved to chat history (last 3 Q&A pairs)

Total Cost: ~$0.0003 (less than 1 cent)
Total Time: ~5 seconds
```

**Key Points**:

1. **LSTM does the prediction work** (locally, free) - this is the computationally expensive part
2. **OpenAI adds context and explanation** (via API, minimal cost) - it doesn't do predictions, just interprets them
3. **User gets best of both worlds**:
   - Accurate predictions from your trained LSTM model
   - Contextual analysis from OpenAI's knowledge of current events
   
**Alternative: Without OpenAI**

If you wanted to skip OpenAI entirely for this question:
- User calls: GET /api/predictions/top20
- Gets raw JSON with predictions
- Displays in Streamlit dashboard
- Cost: $0 (no OpenAI)
- But: No natural language explanation, no external context

**When OpenAI Adds Most Value**:
- Questions like: "Why is Bitcoin rising?" (needs external news context)
- Questions like: "Should I diversify into altcoins?" (needs general advice)
- Questions like: "What's the impact of recent regulations?" (needs current events)

**When OpenAI Adds Less Value**:
- "What are the top 20 predictions?" (could just show raw data)
- "What's the current price of BTC?" (just database query)

The design allows flexibility: critical predictions come from your LSTM, OpenAI enhances with explanation and context.

**Query Tracing and Logging**:

Every query is fully traced and logged for:
- **Security auditing**: Track PII detection attempts
- **Cost monitoring**: Track OpenAI token usage and costs
- **Performance analysis**: Response time tracking
- **Compliance**: Maintain audit trail of all interactions
- **Debugging**: Understand what context was used for each response

**What Gets Logged**:

1. **Chat History Table** (for user experience):
   - Full question and answer
   - Context used (LSTM predictions, market data)
   - OpenAI token counts and cost
   - Response time
   - Session tracking

2. **Query Audit Log** (for security/compliance):
   - Sanitized question (PII removed if any was detected)
   - PII patterns detected (email, phone, etc.)
   - Topic validation result
   - IP address and user agent
   - Rejection status and reason
   - Timestamp

**Example Trace for "What are the 20 best performing cryptos?"**:

```sql
-- chat_history table
INSERT INTO chat_history (
    session_id: 'user-abc-123',
    question: 'What are the 20 best performing cryptos for next cycle?',
    answer: 'Based on the LSTM predictions, here are...',
    question_hash: 'a3f5b2c...',
    topic_valid: true,
    pii_detected: false,
    context_used: {
        "predictions": [
            {"symbol": "BTC", "predicted_change": 3.5, "confidence": 0.82},
            {"symbol": "ETH", "predicted_change": 4.2, "confidence": 0.78},
            ...
        ],
        "market_tendency": "bullish"
    },
    openai_tokens_input: 412,
    openai_tokens_output: 387,
    openai_cost_usd: 0.000294,
    response_time_ms: 4823,
    created_at: '2025-11-01 14:23:45'
)

-- query_audit_log table
INSERT INTO query_audit_log (
    session_id: 'user-abc-123',
    chat_history_id: 1234,
    question_sanitized: 'What are the 20 best performing cryptos for next cycle?',
    pii_patterns_detected: [],
    topic_validation_result: 'valid_crypto_topic',
    ip_address: '192.168.1.100',
    user_agent: 'Mozilla/5.0...',
    rejected: false,
    rejection_reason: null,
    created_at: '2025-11-01 14:23:45'
)
```

**Admin Dashboard Queries**:

Administrators can query:
- Total OpenAI costs per day/month
- Most common questions
- PII detection rate
- Rejected queries and reasons
- Average response times
- Token usage trends

**Privacy Considerations**:
- PII is never stored in logs (sanitized first)
- Audit logs can be configured with retention policies
- Sensitive fields can be encrypted at rest
- Access to audit logs requires admin privileges

**Topic Validation**:
- **Allowed topics**: Cryptocurrencies, blockchain technology, market analysis, trading strategies, crypto regulations, DeFi, NFTs, mining
- **Rejected topics**: Weather forecasts, sports, politics (unless crypto-related), personal advice unrelated to crypto, general news
- Implementation: Use OpenAI function calling or classification to validate topic before processing

**PII Detection Patterns**:
- Email addresses: regex pattern matching
- Phone numbers: international format detection
- Names: NER (Named Entity Recognition) using spaCy
- Addresses: pattern matching for street addresses
- Financial data: credit card, bank account patterns
- IP addresses and URLs with personal domains

**OpenAI Integration**:
- Model: gpt-4o-mini (configurable via .env)
- System prompt: "You are a cryptocurrency market analysis assistant. Use provided LSTM predictions and market data along with your knowledge of current crypto markets to provide comprehensive analysis. Only answer questions related to cryptocurrencies, blockchain technology, and crypto markets. Politely decline questions about other topics."
- Temperature: 0.7 for balanced creativity
- Max tokens: 500 for concise responses
- Context: Include last 3 Q&A pairs for continuity
- Function calling: Enable for structured data extraction and topic validation

### 5. Flask API Service

**Purpose**: Expose system functionality via REST endpoints

**Endpoints**:

```python
# Prediction endpoints
GET /api/predictions/top20
Response: {
    "predictions": [
        {
            "symbol": "BTC",
            "current_price": 45000.00,
            "predicted_price": 46500.00,
            "predicted_change_percent": 3.33,
            "confidence": 0.85
        },
        ...
    ],
    "prediction_time": "2025-11-01T12:00:00Z",
    "horizon_hours": 24
}

GET /api/market/tendency
Response: {
    "tendency": "bullish",
    "confidence": 0.78,
    "metrics": {
        "avg_change_percent": 2.5,
        "volatility_index": 0.15,
        "market_cap_change": 1.8
    },
    "timestamp": "2025-11-01T12:00:00Z"
}

# Chat endpoints
POST /api/chat/query
Request: {
    "question": "What factors influence Bitcoin price?",
    "session_id": "user-session-123"
}
Response: {
    "answer": "Bitcoin price is influenced by...",
    "history": [
        {"question": "...", "answer": "..."},
        ...
    ],
    "timestamp": "2025-11-01T12:00:00Z"
}

# Data collection endpoints (admin)
POST /api/admin/collect/trigger
Request: {
    "mode": "manual",
    "start_date": "2025-10-01",
    "end_date": "2025-11-01"
}

GET /api/admin/collect/status
Response: {
    "status": "running",
    "progress": 65,
    "current_crypto": "ETH",
    "last_update": "2025-11-01T12:00:00Z"
}
```

**Authentication & Authorization**:
- API key-based authentication for all endpoints
- Admin endpoints require elevated privileges
- Rate limiting: 100 requests per minute per API key

### 6. Web UI

**Purpose**: Provide user-friendly interfaces for visualization and interaction

**Streamlit Dashboard** (`dashboard.py`):
- Market overview with real-time data
- Top 20 predictions visualization (charts, tables)
- Market tendency indicator with historical trends
- Data collection status and statistics

**Bootstrap5 Chat Interface** (`templates/chat.html`):
- ChatGPT-like conversation interface
- Message history display (last 3 Q&A pairs)
- Input validation and PII warning messages
- Responsive design for mobile and desktop

**Technology Stack**:
- Streamlit: Data visualization and dashboards
- HTML5/CSS3: Structure and styling
- Bootstrap 5: Responsive UI components
- JavaScript: Client-side interactivity
- Chart.js or Plotly: Interactive charts

### 7. Alert System

**Purpose**: Monitor market and send SMS notifications for significant shifts

**Key Classes**:
- `AlertSystem`: Main monitoring orchestrator
- `MarketMonitor`: Analyze market data for shifts
- `SMSGateway`: SMS sending integration
- `AlertScheduler`: Hourly execution management

**Interfaces**:
```python
class AlertSystem:
    def check_market_shifts(self) -> List[MarketShift]
    def send_alert(self, shift: MarketShift) -> bool
    
class MarketMonitor:
    def detect_massive_shift(self, threshold_percent: float) -> Optional[MarketShift]
    def analyze_hourly_changes(self) -> Dict[str, float]
```

**Market Shift Detection**:
- Threshold: Configurable percentage change (e.g., 10% in 1 hour)
- Metrics: Individual crypto price change, overall market cap change
- Frequency: Hourly checks
- Cooldown: Prevent alert spam (e.g., max 1 alert per crypto per 4 hours)

**SMS Integration Options**:
- Twilio API (recommended for AWS deployment)
- AWS SNS (native AWS service)
- Configuration in .env: `SMS_PHONE_NUMBER`, `SMS_PROVIDER`, `SMS_API_KEY`

## Data Models

### Core Data Entities

**CryptoData**:
```python
@dataclass
class CryptoData:
    symbol: str
    name: str
    timestamp: datetime
    price_usd: Decimal
    volume_24h: Decimal
    market_cap: Decimal
    market_cap_rank: int
```

**PredictionResult**:
```python
@dataclass
class PredictionResult:
    symbol: str
    current_price: Decimal
    predicted_price: Decimal
    predicted_change_percent: float
    confidence_score: float
    prediction_horizon_hours: int
    timestamp: datetime
```

**MarketTendency**:
```python
@dataclass
class MarketTendency:
    tendency: str  # bullish, bearish, volatile, stable, consolidating
    confidence: float
    metrics: Dict[str, float]
    timestamp: datetime
```

**ChatMessage**:
```python
@dataclass
class ChatMessage:
    session_id: str
    question: str
    answer: str
    timestamp: datetime
    contains_pii: bool = False
    topic_valid: bool = True
    context_used: Dict[str, Any] = None  # LSTM predictions, market data
    openai_tokens_input: int = 0
    openai_tokens_output: int = 0
    openai_cost_usd: Decimal = Decimal('0')
    response_time_ms: int = 0

@dataclass
class QueryAuditEntry:
    session_id: str
    chat_history_id: Optional[int]
    question_sanitized: str
    pii_patterns_detected: List[str]
    topic_validation_result: str
    ip_address: str
    user_agent: str
    rejected: bool
    rejection_reason: Optional[str]
    timestamp: datetime
```

**MarketShift**:
```python
@dataclass
class MarketShift:
    crypto_symbol: str
    shift_type: str  # increase, decrease
    change_percent: float
    previous_price: Decimal
    current_price: Decimal
    timestamp: datetime
```

## Error Handling

### Error Categories and Strategies

**1. External API Errors**:
- Binance API failures: Retry with exponential backoff (max 3 attempts)
- OpenAI API failures: Return cached response or error message
- Rate limiting: Queue requests and throttle
- Network timeouts: Log and retry after delay

**2. Database Errors**:
- Connection failures: Implement connection pooling with retry logic
- Constraint violations: Log and skip duplicate records
- Query timeouts: Optimize queries and add appropriate indexes
- Transaction failures: Rollback and retry with isolation

**3. Model Errors**:
- Prediction failures: Return last known good prediction with warning
- Training failures: Alert admin and use previous model version
- Data quality issues: Skip problematic data points and log

**4. Security Errors**:
- PII detection: Reject request with user-friendly message
- Authentication failures: Return 401 with clear error
- Authorization failures: Return 403 with minimal information

**5. Data Collection Errors**:
- Missing data: Log gaps and continue with available data
- Invalid data format: Skip and log for manual review
- Partial collection failure: Resume from last successful point

### Error Response Format

```python
{
    "error": {
        "code": "PREDICTION_FAILED",
        "message": "Unable to generate prediction at this time",
        "details": "Insufficient historical data for BTC",
        "timestamp": "2025-11-01T12:00:00Z",
        "request_id": "req-123456"
    }
}
```

### Logging Strategy

- Use Python `logging` module with structured logging
- Log levels: DEBUG (development), INFO (production), ERROR (always)
- Log rotation: Daily rotation with 30-day retention
- Sensitive data: Never log API keys, PII, or credentials
- AWS CloudWatch integration for centralized logging

## Testing Strategy

### Unit Testing

**Coverage Target**: 80% code coverage

**Key Test Areas**:
- Data collection logic (mocked Binance API)
- PII detection patterns (comprehensive test cases)
- Database operations (in-memory SQLite for tests)
- Prediction model inference (with sample data)
- API endpoint responses (Flask test client)

**Testing Framework**: pytest with fixtures

### Integration Testing

**Test Scenarios**:
- End-to-end data collection flow
- Prediction generation with real database
- Chat flow with mocked OpenAI API
- Alert system with mocked SMS gateway
- API authentication and authorization

### Performance Testing

**Metrics**:
- API response time: < 500ms for predictions
- Data collection throughput: > 100 records/second
- Database query performance: < 100ms for common queries
- Model inference time: < 2 seconds per prediction

**Tools**: locust for load testing, pytest-benchmark for benchmarks

### Security Testing

**Test Areas**:
- PII detection accuracy (false positives/negatives)
- SQL injection prevention
- API authentication bypass attempts
- XSS and CSRF protection in web UI
- Environment variable exposure

## Deployment Architecture

### Local Development Environment

**Infrastructure**:
- Local PostgreSQL database (external installation)
- Python virtual environment
- Self-signed SSL certificate for HTTPS
- Access URL: https://crypto-ai.local:10443

**Configuration**:
- Use `local-env` file for environment variables
- Database connection: localhost PostgreSQL
- All services run on local machine
- Development mode with debug logging

**Components**:
- Flask API server (port 5000)
- Streamlit dashboard (port 8501)
- Bootstrap5 chat UI (port 10443 with HTTPS)
- PostgreSQL database (port 5432)

### AWS Deployment Architecture (Initial - Single EC2)

**Infrastructure Overview**:
- Single Amazon Linux 2023 t3.micro EC2 instance
- PostgreSQL installed directly on EC2
- Public subnet with Elastic IP
- Self-signed SSL certificate for HTTPS
- Access URL: https://crypto-ai.crypto-vision.com:10443
- Domain points to Elastic IP address

**Terraform Configuration** (terraform/ folder):

The Terraform configuration provisions infrastructure in an **existing AWS account**:

1. **VPC and Networking**:
   - Uses existing VPC (referenced via data source, not created)
   - Uses existing public subnet (referenced via data source)
   - Uses existing Internet Gateway
   - No new VPC resources created

2. **EC2 Instance**:
   - AMI: Amazon Linux 2023 (latest)
   - Instance Type: t3.micro
   - Elastic IP (EIP) attached for static public IP
   - IAM instance profile with SSM and CloudWatch permissions
   - User data script for initial system setup
   - Tags for identification and cost tracking

3. **Security Group** (crypto-ai-sg):
   - **Inbound Rules**:
     - SSH (port 22) from developer workstation IP only (variable: `dev_workstation_ip`)
     - HTTPS (port 10443) from developer workstation IP only
     - All other inbound traffic blocked
   - **Outbound Rules**:
     - All traffic allowed (for package installation, Binance API, OpenAI API calls)

4. **IAM Role and Instance Profile**:
   - Role name: `crypto-ai-ec2-role`
   - Attached policies:
     - `AmazonSSMManagedInstanceCore` (for SSM Session Manager)
     - `CloudWatchAgentServerPolicy` (for CloudWatch logs and metrics)
   - Allows EC2 instance to be managed via SSM without SSH

5. **Access Methods**:
   - **Primary**: AWS Systems Manager (SSM) Session Manager (no SSH key required)
   - **Secondary**: EC2 Instance Connect (browser-based SSH)
   - **Fallback**: Direct SSH with key pair (restricted to dev workstation IP)

6. **Storage**:
   - Root EBS volume: 20 GB gp3 (general purpose SSD)
   - Additional EBS volume: 50 GB gp3 (mounted at /data for PostgreSQL)
   - Both volumes encrypted at rest

**Terraform File Structure**:

```
terraform/
├── main.tf                      # Main configuration and EC2 instance
├── variables.tf                 # Input variables (dev IP, region, etc.)
├── outputs.tf                   # Outputs (EIP, instance ID, DNS)
├── security-groups.tf           # Security group definitions
├── iam.tf                       # IAM role and instance profile
├── data.tf                      # Data sources (existing VPC, subnet)
├── user-data.sh                 # EC2 initialization script
├── terraform.tfvars.example     # Example variable values
└── README.md                    # Terraform usage instructions
```

**Key Terraform Variables**:

```hcl
# terraform/variables.tf
variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "dev_workstation_ip" {
  description = "Developer workstation IP for SSH/HTTPS access (CIDR format)"
  type        = string
  # Example: "203.0.113.42/32"
}

variable "vpc_id" {
  description = "Existing VPC ID"
  type        = string
}

variable "subnet_id" {
  description = "Existing public subnet ID"
  type        = string
}

variable "key_pair_name" {
  description = "EC2 key pair name for SSH access"
  type        = string
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.micro"
}

variable "domain_name" {
  description = "Domain name for the application"
  type        = string
  default     = "crypto-ai.crypto-vision.com"
}
```

**Script Organization**:

```
project/
├── terraform/                    # AWS infrastructure as code
│   ├── main.tf                  # Main Terraform configuration
│   ├── variables.tf             # Input variables
│   ├── outputs.tf               # Output values (EIP, instance ID, DNS)
│   ├── security-groups.tf       # Security group definitions
│   ├── iam.tf                   # IAM role and policies
│   ├── data.tf                  # Data sources for existing resources
│   ├── user-data.sh             # EC2 initialization script
│   ├── terraform.tfvars.example # Example variable values
│   └── README.md                # Terraform usage guide
│
├── local-scripts/               # Scripts run from LOCAL workstation
│   ├── deploy-to-aws.sh        # Full deployment to AWS EC2
│   ├── sync-code.sh            # Sync application code to remote
│   ├── setup-local-env.sh      # Setup local development environment
│   ├── generate-ssl-cert.sh    # Generate self-signed SSL certificates
│   ├── control-remote.sh       # Control remote services (start/stop/status)
│   ├── ssh-to-aws.sh           # SSH to AWS instance
│   ├── ssm-connect.sh          # Connect via SSM Session Manager
│   └── backup-remote-db.sh     # Trigger remote database backup
│
├── remote-scripts/              # Scripts run ON AWS EC2 instance
│   ├── install-dependencies.sh  # Install system packages and Python
│   ├── setup-postgresql.sh      # Install and configure PostgreSQL
│   ├── setup-application.sh     # Configure application services
│   ├── configure-ssl.sh         # Setup SSL certificates
│   ├── start-services.sh        # Start all application services
│   ├── stop-services.sh         # Stop all application services
│   ├── restart-services.sh      # Restart all services
│   ├── status-services.sh       # Check service status
│   ├── backup-database.sh       # Backup PostgreSQL database
│   └── update-application.sh    # Update application code
│
├── src/                         # Application source code
├── local-env.example            # Local environment configuration
├── aws-env.example              # AWS environment configuration
└── README.md
```

**Clear Separation: Local vs Remote Scripts**:

**Local Scripts** (run from developer workstation):
- Manage infrastructure provisioning (Terraform)
- Deploy code to AWS
- Control remote services via SSH/SSM
- Monitor remote system status
- Trigger remote operations

**Remote Scripts** (run on AWS EC2 instance):
- Install and configure system components
- Manage application lifecycle
- Perform database operations
- Handle service management
- Execute maintenance tasks

**Deployment Flow**:

1. **Provision Infrastructure** (from local workstation):
   ```bash
   cd terraform/
   
   # Copy and edit variables
   cp terraform.tfvars.example terraform.tfvars
   # Edit terraform.tfvars with your values:
   # - dev_workstation_ip
   # - vpc_id
   # - subnet_id
   # - key_pair_name
   
   # Initialize Terraform
   terraform init
   
   # Preview changes
   terraform plan
   
   # Apply infrastructure
   terraform apply
   
   # Note the outputs: elastic_ip, instance_id
   ```

2. **Configure DNS** (manual step):
   - Point crypto-ai.crypto-vision.com to the Elastic IP from Terraform output
   - Wait for DNS propagation

3. **Deploy Application** (from local workstation):
   ```bash
   # Full deployment
   ./local-scripts/deploy-to-aws.sh
   ```
   
   This script performs:
   - Syncs application code to EC2 instance
   - Connects via SSM and runs remote-scripts/install-dependencies.sh
   - Runs remote-scripts/setup-postgresql.sh
   - Runs remote-scripts/setup-application.sh
   - Runs remote-scripts/configure-ssl.sh
   - Starts services via remote-scripts/start-services.sh

4. **Control Remote Services** (from local workstation):
   ```bash
   # Start all services
   ./local-scripts/control-remote.sh start
   
   # Stop all services
   ./local-scripts/control-remote.sh stop
   
   # Check service status
   ./local-scripts/control-remote.sh status
   
   # Restart services
   ./local-scripts/control-remote.sh restart
   ```

5. **Access Methods** (from local workstation):
   ```bash
   # Connect via SSM (recommended, no SSH key needed)
   ./local-scripts/ssm-connect.sh
   
   # Connect via SSH (requires key pair)
   ./local-scripts/ssh-to-aws.sh
   
   # Access application
   # https://crypto-ai.crypto-vision.com:10443
   ```

6. **Update Application** (from local workstation):
   ```bash
   # Sync code changes
   ./local-scripts/sync-code.sh
   
   # Restart services to apply changes
   ./local-scripts/control-remote.sh restart
   ```

**Security Configuration**:

- Security group restricts access to single developer IP
- SSM Session Manager provides secure access without exposing SSH publicly
- All connections encrypted (HTTPS, SSH, SSM)
- IAM role follows least privilege principle
- EBS volumes encrypted at rest
- Self-signed SSL certificate for HTTPS (can be replaced with Let's Encrypt)

**Monitoring and Logs**:

- CloudWatch Logs: Application logs streamed to CloudWatch
- CloudWatch Metrics: CPU, memory, disk usage
- SSM Session Manager logs: All session activity logged
- Application logs: Available via `./local-scripts/control-remote.sh logs`

### AWS Deployment Architecture (Future - RDS Evolution)

**Evolution Path**:
- Migrate from EC2-hosted PostgreSQL to RDS PostgreSQL
- Add Application Load Balancer for HTTPS termination
- Implement Auto Scaling Group for multiple EC2 instances
- Move to private subnet with NAT Gateway
- Use AWS Certificate Manager for SSL certificates

**Future Services**:
- RDS PostgreSQL (db.t3.micro with Multi-AZ)
- Application Load Balancer
- Auto Scaling Group
- NAT Gateway
- CloudWatch for monitoring
- SNS for SMS alerts
- Secrets Manager for credentials
- S3 for model artifacts and backups

### Initial Deployment Diagram (Single EC2)

```
┌─────────────────────────────────────────────────────────────┐
│                         AWS Cloud                            │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │                    VPC                              │    │
│  │                                                     │    │
│  │  ┌──────────────────────────────────────────┐     │    │
│  │  │         Public Subnet                     │     │    │
│  │  │                                           │     │    │
│  │  │  ┌─────────────────────────────────┐    │     │    │
│  │  │  │  EC2 Instance (t3.micro)        │    │     │    │
│  │  │  │  Amazon Linux 2023              │    │     │    │
│  │  │  │                                 │    │     │    │
│  │  │  │  ┌──────────────────────┐      │    │     │    │
│  │  │  │  │ Flask API (port 5000)│      │    │     │    │
│  │  │  │  └──────────────────────┘      │    │     │    │
│  │  │  │  ┌──────────────────────┐      │    │     │    │
│  │  │  │  │ Streamlit (port 8501)│      │    │     │    │
│  │  │  │  └──────────────────────┘      │    │     │    │
│  │  │  │  ┌──────────────────────┐      │    │     │    │
│  │  │  │  │ Web UI (port 443)    │      │    │     │    │
│  │  │  │  └──────────────────────┘      │    │     │    │
│  │  │  │  ┌──────────────────────┐      │    │     │    │
│  │  │  │  │ PostgreSQL (port 5432)│     │    │     │    │
│  │  │  │  └──────────────────────┘      │    │     │    │
│  │  │  │                                 │    │     │    │
│  │  │  │  Elastic IP: X.X.X.X           │    │     │    │
│  │  │  └─────────────────────────────────┘    │     │    │
│  │  │                                           │     │    │
│  │  │  Security Group:                          │     │    │
│  │  │  - SSH (22) from Dev IP only             │     │    │
│  │  │  - HTTPS (443) from Dev IP only          │     │    │
│  │  │                                           │     │    │
│  │  └──────────────────────────────────────────┘     │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  Access Methods:                                             │
│  - EC2 Instance Connect                                      │
│  - AWS Systems Manager (SSM)                                 │
│  - SSH with key pair (IP restricted)                         │
│                                                              │
│  URL: https://crypto-ai.crypto-vision.com                   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    Local Development                         │
│                                                              │
│  Developer Workstation                                       │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Local Scripts (deployment & control)              │    │
│  │  - deploy-to-aws.sh                                │    │
│  │  - sync-code.sh                                    │    │
│  │  - control-remote.sh                               │    │
│  │  - setup-local-env.sh                              │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Local PostgreSQL Database                         │    │
│  │  Flask API + Streamlit + Web UI                    │    │
│  │  URL: https://crypto-ai.local:10443                │    │
│  └────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### Future Deployment Diagram (RDS Evolution)

```
┌─────────────────────────────────────────────────────────────┐
│                         AWS Cloud                            │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │                    VPC                              │    │
│  │                                                     │    │
│  │  ┌──────────────────────────────────────────┐     │    │
│  │  │         Public Subnet                     │     │    │
│  │  │  ┌─────────────┐    ┌─────────────┐     │     │    │
│  │  │  │     ALB     │    │   NAT GW    │     │     │    │
│  │  │  └──────┬──────┘    └─────────────┘     │     │    │
│  │  └─────────┼──────────────────────────────┘     │    │
│  │            │                                      │    │
│  │  ┌─────────▼──────────────────────────────┐     │    │
│  │  │         Private Subnet                  │     │    │
│  │  │  ┌──────────┐  ┌──────────┐           │     │    │
│  │  │  │ EC2 App  │  │ EC2 App  │           │     │    │
│  │  │  │ Instance │  │ Instance │           │     │    │
│  │  │  │(Auto Scale)│ │(Auto Scale)│        │     │    │
│  │  │  └──────────┘  └──────────┘           │     │    │
│  │  └─────────┬──────────────────────────────┘     │    │
│  │            │                                      │    │
│  │  ┌─────────▼──────────────────────────────┐     │    │
│  │  │         Data Subnet                     │     │    │
│  │  │  ┌──────────────────────┐              │     │    │
│  │  │  │  RDS PostgreSQL      │              │     │    │
│  │  │  │  (Multi-AZ)          │              │     │    │
│  │  │  └──────────────────────┘              │     │    │
│  │  └─────────────────────────────────────────┘     │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────┐     │
│  │  S3 Buckets    │  │ Secrets Mgr    │  │ SNS      │     │
│  │  - Models      │  │ - API Keys     │  │ - Alerts │     │
│  │  - Backups     │  │ - DB Creds     │  │          │     │
│  └────────────────┘  └────────────────┘  └──────────┘     │
└─────────────────────────────────────────────────────────────┘
```

### Cost Optimization

**Initial Deployment (t3.micro)**:
- EC2 t3.micro: ~$7.50/month (on-demand)
- EBS storage (70 GB): ~$7/month
- Elastic IP: Free (when attached)
- Data transfer: ~$1-5/month (depending on usage)
- **Total: ~$15-20/month**

**Future Deployment (with RDS)**:
- EC2 instances: ~$15-30/month
- RDS PostgreSQL: ~$15-30/month
- ALB: ~$16/month
- NAT Gateway: ~$32/month
- **Total: ~$80-110/month**

**Optimization Strategies**:
- Use Reserved Instances for 1-year commitment (save 30-40%)
- Schedule ML training during off-peak hours
- Implement auto-scaling to match demand
- Use S3 lifecycle policies for log archival
- Monitor and right-size instances based on actual usage

## Configuration Management

### Environment Variables

**local-env (Local Development)**:

```bash
# Environment
ENVIRONMENT=local

# Database (Local PostgreSQL)
DATABASE_URL=postgresql://crypto_user:crypto_pass@localhost:5432/crypto_db
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10

# Web UI
WEB_UI_HOST=crypto-ai.local
WEB_UI_PORT=10443
WEB_UI_PROTOCOL=https

# SSL Certificate
SSL_CERT_PATH=./certs/local/cert.pem
SSL_KEY_PATH=./certs/local/key.pem

# Data Collection
COLLECTION_START_DATE=2024-01-01
TOP_N_CRYPTOS=50
COLLECTION_SCHEDULE=0 */6 * * *  # Every 6 hours
BINANCE_API_KEY=your_binance_key
BINANCE_API_SECRET=your_binance_secret

# Prediction Engine
MODEL_TYPE=LSTM  # or GRU
PREDICTION_HORIZON_HOURS=24
MODEL_RETRAIN_SCHEDULE=0 2 * * 0  # Weekly on Sunday at 2 AM
SEQUENCE_LENGTH=168  # 7 days of hourly data

# GenAI
OPENAI_API_KEY=your_openai_key
OPENAI_MODEL=gpt-4o-mini
OPENAI_MAX_TOKENS=500
OPENAI_TEMPERATURE=0.7

# Alert System
ALERT_ENABLED=true
ALERT_THRESHOLD_PERCENT=10.0
ALERT_COOLDOWN_HOURS=4
SMS_PROVIDER=twilio  # or aws_sns
SMS_PHONE_NUMBER=+1234567890
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
TWILIO_FROM_NUMBER=+1234567890

# API
API_HOST=0.0.0.0
API_PORT=5000
API_KEY_REQUIRED=false  # Disabled for local dev
RATE_LIMIT_PER_MINUTE=100

# Streamlit
STREAMLIT_PORT=8501

# Security
SECRET_KEY=local_dev_secret_key_change_in_production
ALLOWED_ORIGINS=https://crypto-ai.local:10443

# Logging
LOG_LEVEL=DEBUG
LOG_FILE=logs/crypto_saas.log
```

**aws-env (AWS Production)**:

```bash
# Environment
ENVIRONMENT=production

# Database (PostgreSQL on EC2)
DATABASE_URL=postgresql://crypto_user:CHANGE_ME@localhost:5432/crypto_db
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20

# Web UI
WEB_UI_HOST=crypto-ai.crypto-vision.com
WEB_UI_PORT=443
WEB_UI_PROTOCOL=https

# SSL Certificate
SSL_CERT_PATH=/etc/ssl/certs/crypto-ai-cert.pem
SSL_KEY_PATH=/etc/ssl/private/crypto-ai-key.pem

# Data Collection
COLLECTION_START_DATE=2024-01-01
TOP_N_CRYPTOS=50
COLLECTION_SCHEDULE=0 */6 * * *  # Every 6 hours
BINANCE_API_KEY=your_binance_key
BINANCE_API_SECRET=your_binance_secret

# Prediction Engine
MODEL_TYPE=LSTM
PREDICTION_HORIZON_HOURS=24
MODEL_RETRAIN_SCHEDULE=0 2 * * 0  # Weekly on Sunday at 2 AM
SEQUENCE_LENGTH=168

# GenAI
OPENAI_API_KEY=your_openai_key
OPENAI_MODEL=gpt-4o-mini
OPENAI_MAX_TOKENS=500
OPENAI_TEMPERATURE=0.7

# Alert System
ALERT_ENABLED=true
ALERT_THRESHOLD_PERCENT=10.0
ALERT_COOLDOWN_HOURS=4
SMS_PROVIDER=aws_sns
SMS_PHONE_NUMBER=+1234567890
AWS_SNS_TOPIC_ARN=arn:aws:sns:us-east-1:123456789012:crypto-alerts

# API
API_HOST=0.0.0.0
API_PORT=5000
API_KEY_REQUIRED=true
RATE_LIMIT_PER_MINUTE=100

# Streamlit
STREAMLIT_PORT=8501

# AWS
AWS_REGION=us-east-1

# Security
SECRET_KEY=CHANGE_ME_TO_RANDOM_SECRET_KEY
ALLOWED_ORIGINS=https://crypto-ai.crypto-vision.com

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/crypto-saas/app.log
```

## Security Considerations

### Data Protection

- Encrypt database connections (SSL/TLS)
- Encrypt data at rest (RDS encryption)
- Use AWS Secrets Manager for sensitive credentials
- Implement API key rotation policy

### PII Protection

- Multi-layer PII detection (regex + NER)
- Audit log for PII detection events
- Never store PII in logs or database
- Sanitize all data before external API calls

### API Security

- API key authentication for all endpoints
- Rate limiting to prevent abuse
- Input validation and sanitization
- CORS configuration for web UI
- HTTPS only in production

### Network Security

- VPC isolation for database
- Security groups with least privilege
- WAF rules for common attacks
- DDoS protection via AWS Shield

### Compliance

- GDPR considerations for EU users
- Data retention policies
- User consent for data processing
- Right to deletion implementation

## Monitoring and Observability

### Key Metrics

**System Health**:
- API response times (p50, p95, p99)
- Error rates by endpoint
- Database connection pool utilization
- CPU and memory usage

**Business Metrics**:
- Number of predictions generated
- Chat queries processed
- Alerts sent
- Data collection success rate

**ML Metrics**:
- Model prediction accuracy
- Training time and frequency
- Inference latency
- Model drift detection

### Dashboards

- CloudWatch dashboard for infrastructure
- Custom Grafana dashboard for business metrics
- Streamlit admin dashboard for system status

### Alerting

- High error rate alerts
- Database connection failures
- API latency degradation
- Model prediction failures
- Data collection gaps

## Development Workflow

### Local Development Setup

1. Install Python 3.10+
2. Create virtual environment
3. Install dependencies from requirements.txt
4. Set up local PostgreSQL database
5. Configure .env file
6. Run database migrations
7. Start Flask API and Streamlit UI

### CI/CD Pipeline

- GitHub Actions or AWS CodePipeline
- Automated testing on pull requests
- Staging deployment for testing
- Production deployment with approval
- Automated rollback on failures

### Version Control

- Git with feature branch workflow
- Semantic versioning for releases
- Tag releases for deployment tracking
- Maintain CHANGELOG.md

## Future Enhancements

- Multi-exchange data aggregation (Coinbase, Kraken)
- Real-time WebSocket data streaming
- Advanced technical indicators
- Portfolio optimization recommendations
- Mobile app for alerts and monitoring
- Multi-language support for chat interface
- Sentiment analysis from social media
- Backtesting framework for strategies
