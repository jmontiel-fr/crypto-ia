# GenAI Engine Quick Start Guide

## Prerequisites

1. **Python 3.10+** installed
2. **PostgreSQL database** configured with schema
3. **OpenAI API key** (get from https://platform.openai.com/api-keys)
4. **Environment variables** configured

## Installation

### 1. Install Dependencies

```bash
# Install Python packages
pip install -r requirements.txt

# Install spaCy model for name detection (optional but recommended)
python -m spacy download en_core_web_sm
```

### 2. Configure Environment

Create a `.env` file or use `local-env`:

```bash
# OpenAI Configuration
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_MODEL=gpt-4o-mini
OPENAI_MAX_TOKENS=500
OPENAI_TEMPERATURE=0.7

# Database Configuration
DATABASE_URL=postgresql://crypto_user:crypto_pass@localhost:5432/crypto_db

# Other required configs...
```

### 3. Initialize Database

```bash
# Run database migrations
python scripts/init_database.py
```

## Basic Usage

### Example 1: Simple Query Processing

```python
from src.genai import GenAIEngine, ChatHistoryManager
from src.config import load_config
from src.data.database import get_session

# Initialize
config = load_config()
session = get_session()

engine = GenAIEngine(config, session)
history_manager = ChatHistoryManager(session)

# Process a query
response = engine.process_query(
    question="What is the current price of Bitcoin?",
    session_id="user-session-123"
)

# Check response
if response.success:
    print(f"Answer: {response.answer}")
    print(f"Cost: ${response.cost_usd:.6f}")
else:
    print(f"Rejected: {response.rejection_reason}")

# Store in history
history_manager.store_chat_message(response)

# Clean up
session.close()
```

### Example 2: With Chat History

```python
from src.genai import GenAIEngine, ChatHistoryManager
from src.config import load_config
from src.data.database import get_session

config = load_config()
session = get_session()

engine = GenAIEngine(config, session)
history_manager = ChatHistoryManager(session)

session_id = "user-session-123"

# Get recent history (for UI display)
history = history_manager.get_recent_history(session_id, limit=3)
print(f"Previous {len(history)} messages:")
for msg in history:
    print(f"Q: {msg['question']}")
    print(f"A: {msg['answer']}\n")

# Process new query
response = engine.process_query(
    question="Should I invest in Ethereum?",
    session_id=session_id
)

# Store and display
if response.success:
    history_manager.store_chat_message(response)
    print(f"New Answer: {response.answer}")

session.close()
```

### Example 3: PII Detection

```python
from src.genai import PIIFilter

pii_filter = PIIFilter()

# Test for PII
questions = [
    "What is Bitcoin?",
    "My email is john@example.com",
    "Call me at 555-1234"
]

for question in questions:
    result = pii_filter.analyze(question)
    print(f"\nQuestion: {question}")
    print(f"Contains PII: {result.contains_pii}")
    if result.contains_pii:
        print(f"Patterns: {result.patterns_detected}")
        print(f"Sanitized: {result.sanitized_text}")
```

### Example 4: Topic Validation

```python
from src.genai import TopicValidator

validator = TopicValidator()

questions = [
    "What is the price of Bitcoin?",  # Valid
    "What's the weather today?",      # Invalid
    "Should I invest in crypto?"      # Valid
]

for question in questions:
    result = validator.validate(question)
    print(f"\nQuestion: {question}")
    print(f"Valid: {result.is_valid}")
    if not result.is_valid:
        print(f"Rejection: {result.rejection_message}")
```

### Example 5: Context Building

```python
from src.genai import ContextBuilder
from src.data.database import get_session

session = get_session()
context_builder = ContextBuilder(session)

# Build context for a question
question = "What are the top 20 best performing cryptos?"
context = context_builder.build_context(question)

print(f"Predictions: {context['lstm_predictions']['count']}")
print(f"Market Tendency: {context['market_tendency']['tendency']}")

# Format for OpenAI
context_text = context_builder.format_context_for_prompt(context)
print(f"\nContext for OpenAI:\n{context_text}")

session.close()
```

### Example 6: Admin Monitoring

```python
from src.genai import ChatHistoryManager
from src.data.database import get_session

session = get_session()
history_manager = ChatHistoryManager(session)

# Get session statistics
stats = history_manager.get_session_statistics("user-session-123")
print(f"Session Statistics:")
print(f"  Messages: {stats['message_count']}")
print(f"  Total Cost: ${stats['total_cost_usd']:.6f}")
print(f"  Avg Response Time: {stats['avg_response_time_ms']}ms")

# Get rejected queries
rejected = history_manager.get_rejected_queries(limit=10)
print(f"\nRejected Queries: {len(rejected)}")
for query in rejected:
    print(f"  - {query['rejection_reason']}: {query['question_sanitized'][:50]}...")

# Get PII detections
pii_detections = history_manager.get_pii_detections(limit=10)
print(f"\nPII Detections: {len(pii_detections)}")
for detection in pii_detections:
    print(f"  - Patterns: {detection['pii_patterns']}")

session.close()
```

## Testing

Run the test suite:

```bash
python examples/test_genai_engine.py
```

This will test:
- PII detection
- Topic validation
- Context building (requires database)
- GenAI engine (requires API key)
- Chat history management (requires database)

## Common Issues

### Issue 1: OpenAI API Key Not Found

**Error:** `ValueError: Required environment variable OPENAI_API_KEY is not set`

**Solution:**
```bash
# Add to your .env file
OPENAI_API_KEY=sk-your-api-key-here
```

### Issue 2: spaCy Model Not Found

**Warning:** `spaCy model 'en_core_web_sm' not found`

**Solution:**
```bash
python -m spacy download en_core_web_sm
```

**Note:** The system will work without spaCy, but name detection will be limited to regex patterns.

### Issue 3: Database Connection Error

**Error:** `sqlalchemy.exc.OperationalError: could not connect to server`

**Solution:**
1. Ensure PostgreSQL is running
2. Check DATABASE_URL in .env
3. Verify database exists and user has permissions

### Issue 4: No Predictions Available

**Warning:** `No cached predictions found`

**Solution:**
1. Run the prediction engine first to generate predictions
2. Or use the data collector to gather historical data
3. The GenAI engine will work with empty context, but responses will be less informed

## Cost Management

### Monitoring Costs

```python
from src.genai import ChatHistoryManager
from src.data.database import get_session

session = get_session()
history_manager = ChatHistoryManager(session)

# Get cost for a session
cost = history_manager.get_session_cost("user-session-123")
print(f"Session cost: ${cost:.6f}")

# Get statistics for all sessions
# (You would need to query all unique session_ids)
```

### Cost Estimates

- **gpt-4o-mini** (recommended):
  - Simple query: ~$0.0002
  - Complex query with context: ~$0.0005
  - 1000 queries/day: ~$0.20-0.50/day = ~$6-15/month

- **gpt-4o** (more expensive):
  - Simple query: ~$0.005
  - Complex query: ~$0.015
  - 1000 queries/day: ~$5-15/day = ~$150-450/month

### Reducing Costs

1. Use `gpt-4o-mini` instead of `gpt-4o`
2. Reduce `OPENAI_MAX_TOKENS` (default: 500)
3. Cache predictions to reduce context size
4. Implement rate limiting per user
5. Use cached predictions when available

## Security Best Practices

1. **Never log API keys**
   - Use environment variables
   - Don't commit .env files to git

2. **Validate all inputs**
   - PII detection is automatic
   - Topic validation is automatic

3. **Monitor audit logs**
   - Check rejected queries regularly
   - Review PII detections
   - Track unusual patterns

4. **Implement rate limiting**
   - Prevent abuse
   - Control costs
   - Protect API quota

5. **Secure database access**
   - Use strong passwords
   - Limit database permissions
   - Enable SSL for connections

## Next Steps

1. **Integrate with Flask API** (Task 6)
   - Create REST endpoints
   - Add authentication
   - Implement rate limiting

2. **Build Chat UI** (Task 9)
   - Bootstrap5 interface
   - Real-time updates
   - History display

3. **Add to Streamlit Dashboard** (Task 8)
   - Admin monitoring
   - Cost tracking
   - Query analytics

## Support

For issues or questions:
1. Check the README.md in src/genai/
2. Review the IMPLEMENTATION_SUMMARY.md
3. Run the test suite to verify setup
4. Check logs for detailed error messages

## Resources

- OpenAI API Documentation: https://platform.openai.com/docs
- spaCy Documentation: https://spacy.io/usage
- SQLAlchemy Documentation: https://docs.sqlalchemy.org/
