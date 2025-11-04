# GenAI Module

This module provides the GenAI engine for OpenAI integration with comprehensive security, validation, and context enrichment features.

## Components

### 1. PIIFilter (`pii_filter.py`)

Detects and filters personally identifiable information (PII) from user input.

**Features:**
- Email detection
- Phone number detection (multiple formats)
- Credit card detection
- SSN detection
- Bank account detection
- Street address detection
- IP address detection
- Personal URL detection
- Name detection (regex + spaCy NER)

**Usage:**
```python
from src.genai import PIIFilter

pii_filter = PIIFilter()

# Check for PII
contains_pii, patterns = pii_filter.contains_pii("My email is john@example.com")
# Returns: (True, ['email'])

# Sanitize text
sanitized = pii_filter.sanitize_text("My email is john@example.com")
# Returns: "My email is [EMAIL]"

# Full analysis
result = pii_filter.analyze("Contact me at 555-1234")
# Returns: PIIDetectionResult(contains_pii=True, patterns_detected=['phone'], sanitized_text="Contact me at [PHONE]")
```

**Note:** For name detection using spaCy NER, install the model:
```bash
python -m spacy download en_core_web_sm
```

### 2. TopicValidator (`topic_validator.py`)

Validates that user questions are related to cryptocurrency and blockchain topics.

**Features:**
- Keyword-based validation for crypto topics
- Rejection of off-topic questions (weather, sports, politics, etc.)
- User-friendly rejection messages

**Usage:**
```python
from src.genai import TopicValidator

validator = TopicValidator()

# Validate question
result = validator.validate("What is the price of Bitcoin?")
# Returns: TopicValidationResult(is_valid=True, reason='crypto_related')

result = validator.validate("What's the weather today?")
# Returns: TopicValidationResult(is_valid=False, reason='off_topic', rejection_message='...')

# Simple boolean check
is_valid = validator.is_valid_topic("Should I invest in Ethereum?")
# Returns: True
```

### 3. ContextBuilder (`context_builder.py`)

Builds context from internal data sources to enrich OpenAI prompts.

**Features:**
- Extract cryptocurrency symbols from questions
- Fetch LSTM predictions for relevant cryptos
- Retrieve current market tendency
- Get recent price data and trends
- Format context as text for prompts

**Usage:**
```python
from src.genai import ContextBuilder
from src.data.database import get_session

session = get_session()
context_builder = ContextBuilder(session)

# Build context for a question
context = context_builder.build_context("What are the top 20 best performing cryptos?")
# Returns: Dictionary with predictions, market tendency, and price data

# Format context for OpenAI prompt
context_text = context_builder.format_context_for_prompt(context)
# Returns: Formatted text string ready for OpenAI
```

### 4. GenAIEngine (`genai_engine.py`)

Main interface for OpenAI API integration with full workflow.

**Features:**
- Topic validation
- PII filtering
- Context building
- OpenAI API calls
- Token counting and cost tracking
- Error handling with fallback responses

**Usage:**
```python
from src.genai import GenAIEngine
from src.config import load_config
from src.data.database import get_session

config = load_config()
session = get_session()

engine = GenAIEngine(config, session)

# Process a query
response = engine.process_query(
    question="Should I invest in Bitcoin right now?",
    session_id="user-session-123",
    ip_address="192.168.1.100",
    user_agent="Mozilla/5.0..."
)

# Check response
if response.success:
    print(f"Answer: {response.answer}")
    print(f"Cost: ${response.cost_usd:.6f}")
    print(f"Tokens: {response.tokens_input} in, {response.tokens_output} out")
else:
    print(f"Rejected: {response.rejection_reason}")
    print(f"Message: {response.answer}")
```

**Response Object:**
```python
@dataclass
class ChatResponse:
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
```

### 5. ChatHistoryManager (`chat_history_manager.py`)

Manages conversation tracking, history retrieval, and audit logging.

**Features:**
- Store chat messages with full tracing
- Retrieve conversation history (last N Q&A pairs)
- Audit logging for security and compliance
- Cost tracking per session
- PII detection logging
- Rejected query tracking

**Usage:**
```python
from src.genai import ChatHistoryManager, GenAIEngine
from src.data.database import get_session

session = get_session()
history_manager = ChatHistoryManager(session)

# After processing a query with GenAIEngine
response = engine.process_query(...)

# Store the chat message
chat_id = history_manager.store_chat_message(
    response=response,
    ip_address="192.168.1.100",
    user_agent="Mozilla/5.0..."
)

# Get recent history (last 3 Q&A pairs)
history = history_manager.get_recent_history("user-session-123", limit=3)
# Returns: [{'question': '...', 'answer': '...', 'timestamp': '...'}, ...]

# Get session statistics
stats = history_manager.get_session_statistics("user-session-123")
# Returns: {'message_count': 5, 'total_cost_usd': 0.001234, ...}

# Get rejected queries (admin)
rejected = history_manager.get_rejected_queries(limit=10)

# Get PII detections (admin)
pii_detections = history_manager.get_pii_detections(limit=10)
```

## Complete Workflow Example

```python
from src.genai import GenAIEngine, ChatHistoryManager
from src.config import load_config
from src.data.database import get_session

# Initialize
config = load_config()
session = get_session()

engine = GenAIEngine(config, session)
history_manager = ChatHistoryManager(session)

# Process user query
session_id = "user-session-123"
question = "What are the top 20 cryptocurrencies predicted to perform best?"

# Get recent history for context (optional - for UI display)
recent_history = history_manager.get_recent_history(session_id, limit=3)

# Process the query
response = engine.process_query(
    question=question,
    session_id=session_id,
    ip_address="192.168.1.100",
    user_agent="Mozilla/5.0..."
)

# Store the response
if response.success or response.rejected:
    history_manager.store_chat_message(
        response=response,
        ip_address="192.168.1.100",
        user_agent="Mozilla/5.0..."
    )

# Return to user
if response.success:
    return {
        'answer': response.answer,
        'history': recent_history,
        'cost': float(response.cost_usd),
        'response_time_ms': response.response_time_ms
    }
else:
    return {
        'error': response.answer,
        'rejected': True,
        'reason': response.rejection_reason
    }
```

## Security Features

### PII Protection
- Multi-layer detection (regex + NER)
- Automatic rejection of queries with PII
- Sanitization for audit logs
- Pattern tracking for compliance

### Topic Validation
- Crypto-only question enforcement
- Rejection of off-topic queries
- User-friendly error messages

### Audit Logging
- All queries logged (accepted and rejected)
- PII detection events tracked
- IP address and user agent logging
- Cost tracking per session
- Rejection reason tracking

## Cost Tracking

The GenAI engine automatically tracks OpenAI API costs:

**Pricing (per 1M tokens):**
- gpt-4o-mini: $0.15 input, $0.60 output
- gpt-4o: $5.00 input, $15.00 output
- gpt-3.5-turbo: $0.50 input, $1.50 output

**Average costs:**
- Simple question: ~$0.0002 (200 tokens in, 300 tokens out)
- Complex question with context: ~$0.0005 (500 tokens in, 400 tokens out)
- 1000 questions/day: ~$0.20-0.50/day = ~$6-15/month

## Configuration

Required environment variables:

```bash
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o-mini
OPENAI_MAX_TOKENS=500
OPENAI_TEMPERATURE=0.7
```

## Error Handling

The GenAI engine provides graceful error handling:

1. **Topic Validation Failure**: Returns user-friendly rejection message
2. **PII Detection**: Returns security warning and rejects query
3. **OpenAI API Error**: Returns fallback message suggesting dashboard access
4. **Context Building Error**: Continues with empty context
5. **Database Error**: Logs error and continues (for audit logs)

## Testing

See `examples/test_genai.py` for comprehensive test cases covering:
- PII detection accuracy
- Topic validation
- Context building
- OpenAI integration (mocked)
- Chat history management
- Cost calculation

## Dependencies

- `openai`: OpenAI API client
- `spacy`: NER for name detection (optional)
- `sqlalchemy`: Database operations
- `python-dotenv`: Configuration loading

Install spaCy model for name detection:
```bash
python -m spacy download en_core_web_sm
```
