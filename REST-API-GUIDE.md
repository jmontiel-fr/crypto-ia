# REST API Guide

## Overview

This guide provides comprehensive documentation for the Crypto Market Analysis REST API. The API enables programmatic access to cryptocurrency predictions, market analysis, and AI-powered chat capabilities.

**Quick Links:**
- [Detailed API Documentation](src/api/API_DOCUMENTATION.md) - Complete endpoint specifications
- [Authentication Setup](#authentication)
- [Quick Start Examples](#quick-start)
- [Rate Limits & Best Practices](#best-practices)

## Base URLs

- **Local Development**: `http://localhost:5000`
- **Local HTTPS**: `https://crypto-ai.local:10443`
- **AWS Production**: `https://crypto-ai.crypto-vision.com`

## Authentication

All API endpoints (except `/health`) require authentication using an API key.

### Getting an API Key

API keys are managed through the system configuration. Contact your system administrator or generate one using:

```bash
# Generate a new API key
python -m src.api.auth.api_key_manager generate --role user --description "My API Key"

# Generate an admin API key
python -m src.api.auth.api_key_manager generate --role admin --description "Admin Key"
```

### Using Your API Key

Include your API key in requests using one of these methods:

**1. Authorization Header (Recommended)**
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  http://localhost:5000/api/predictions/top20
```

**2. X-API-Key Header**
```bash
curl -H "X-API-Key: YOUR_API_KEY" \
  http://localhost:5000/api/predictions/top20
```

**3. Query Parameter**
```bash
curl "http://localhost:5000/api/predictions/top20?api_key=YOUR_API_KEY"
```

## Quick Start

### 1. Check API Health

```bash
curl http://localhost:5000/health
```


Response:
```json
{
  "status": "healthy",
  "timestamp": "2025-11-01T12:00:00Z",
  "service": "crypto-market-analysis-api",
  "version": "1.0.0"
}
```

### 2. Get Top 20 Predictions

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  http://localhost:5000/api/predictions/top20
```

Response:
```json
{
  "predictions": [
    {
      "symbol": "BTC",
      "name": "Bitcoin",
      "current_price": 45000.00,
      "predicted_price": 46500.00,
      "predicted_change_percent": 3.33,
      "confidence": 0.85
    }
  ],
  "prediction_time": "2025-11-01T12:00:00Z",
  "horizon_hours": 24,
  "count": 20
}
```

### 3. Get Market Tendency

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  http://localhost:5000/api/market/tendency
```

Response:
```json
{
  "tendency": "bullish",
  "confidence": 0.78,
  "metrics": {
    "avg_change_percent": 2.5,
    "volatility_index": 0.15,
    "market_cap_change": 1.8
  },
  "timestamp": "2025-11-01T12:00:00Z"
}
```

### 4. Ask a Chat Question

```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the best performing cryptocurrencies?", "session_id": "user-123"}' \
  http://localhost:5000/api/chat/query
```


Response:
```json
{
  "success": true,
  "answer": "Based on our LSTM predictions, the top performers are...",
  "session_id": "user-123",
  "timestamp": "2025-11-01T12:00:00Z",
  "metadata": {
    "tokens_input": 150,
    "tokens_output": 300,
    "cost_usd": 0.0002
  }
}
```

## API Endpoints Overview

### Predictions
- `GET /api/predictions/top20` - Get top 20 cryptocurrency predictions
- `GET /api/predictions/crypto/{symbol}` - Get prediction for specific crypto

### Market Analysis
- `GET /api/market/tendency` - Get current market tendency
- `GET /api/market/tendency/history` - Get historical tendencies
- `GET /api/market/overview` - Get comprehensive market overview

### Chat Interface
- `POST /api/chat/query` - Process a chat query
- `GET /api/chat/history/{session_id}` - Get chat history
- `POST /api/chat/validate` - Validate a question

### Admin (Requires Admin API Key)
- `POST /api/admin/collect/trigger` - Trigger data collection
- `GET /api/admin/collect/status` - Get collection status
- `GET /api/admin/system/info` - Get system information

### Health
- `GET /health` - Check API health (no auth required)

## Rate Limiting

- **Limit**: 100 requests per minute per IP address
- **Response Code**: 429 (Too Many Requests)
- **Header**: `Retry-After` indicates seconds to wait

Example rate limit response:
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Please try again later.",
    "timestamp": "2025-11-01T12:00:00Z"
  }
}
```


## Error Handling

All errors follow a standardized format:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": "Additional error details",
    "timestamp": "2025-11-01T12:00:00Z"
  }
}
```

### Common Error Codes

| Code | Status | Description |
|------|--------|-------------|
| `BAD_REQUEST` | 400 | Invalid request data or parameters |
| `UNAUTHORIZED` | 401 | Missing or invalid API key |
| `FORBIDDEN` | 403 | Insufficient permissions (admin required) |
| `NOT_FOUND` | 404 | Resource not found |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `INTERNAL_SERVER_ERROR` | 500 | Server error |

### Chat-Specific Errors

**PII Detected:**
```json
{
  "success": false,
  "rejected": true,
  "rejection_reason": "pii_detected",
  "pii_detected": true,
  "pii_warning": "Your question contained personally identifiable information...",
  "answer": "I detected personally identifiable information in your question..."
}
```

**Invalid Topic:**
```json
{
  "success": false,
  "rejected": true,
  "rejection_reason": "invalid_topic",
  "answer": "I can only answer questions about cryptocurrencies..."
}
```

## Best Practices

### 1. Use Caching

Enable caching to reduce API calls and improve performance:

```bash
# Use cached predictions (default)
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "http://localhost:5000/api/predictions/top20?use_cache=true&max_age_hours=24"

# Force fresh predictions
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "http://localhost:5000/api/predictions/top20?use_cache=false"
```


### 2. Handle Rate Limits

Implement exponential backoff when rate limited:

```python
import requests
import time

def make_request_with_retry(url, headers, max_retries=3):
    for attempt in range(max_retries):
        response = requests.get(url, headers=headers)
        
        if response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', 60))
            time.sleep(retry_after)
            continue
            
        return response
    
    raise Exception("Max retries exceeded")
```

### 3. Validate Chat Questions

Use the validation endpoint before submitting queries:

```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is Bitcoin?"}' \
  http://localhost:5000/api/chat/validate
```

### 4. Maintain Session Continuity

Use consistent session IDs for chat conversations:

```python
import uuid

session_id = str(uuid.uuid4())  # Generate once per user session

# Use same session_id for all queries in conversation
response = requests.post(
    f"{BASE_URL}/api/chat/query",
    headers=headers,
    json={
        "question": "What is Bitcoin?",
        "session_id": session_id
    }
)
```

### 5. Monitor Costs

Track OpenAI usage through metadata:

```python
response = requests.post(f"{BASE_URL}/api/chat/query", ...)
data = response.json()

if data.get("success"):
    metadata = data.get("metadata", {})
    print(f"Tokens: {metadata['tokens_input']} + {metadata['tokens_output']}")
    print(f"Cost: ${metadata['cost_usd']:.6f}")
```


## Code Examples

### Python

```python
import requests

API_KEY = "your_api_key"
BASE_URL = "http://localhost:5000"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# Get top 10 predictions
response = requests.get(
    f"{BASE_URL}/api/predictions/top20",
    headers=headers,
    params={"limit": 10}
)
predictions = response.json()

for pred in predictions["predictions"]:
    print(f"{pred['symbol']}: {pred['predicted_change_percent']:.2f}% "
          f"(confidence: {pred['confidence']:.2f})")

# Get market tendency
response = requests.get(
    f"{BASE_URL}/api/market/tendency",
    headers=headers
)
tendency = response.json()
print(f"Market is {tendency['tendency']} with {tendency['confidence']:.2f} confidence")

# Chat query
response = requests.post(
    f"{BASE_URL}/api/chat/query",
    headers=headers,
    json={
        "question": "What are the best cryptocurrencies to invest in?",
        "session_id": "user-123"
    }
)
chat_response = response.json()

if chat_response.get("success"):
    print(f"Answer: {chat_response['answer']}")
    print(f"Cost: ${chat_response['metadata']['cost_usd']:.6f}")
else:
    print(f"Error: {chat_response.get('rejection_reason')}")
```

### JavaScript (Node.js)

```javascript
const axios = require('axios');

const API_KEY = "your_api_key";
const BASE_URL = "http://localhost:5000";

const headers = {
  "Authorization": `Bearer ${API_KEY}`,
  "Content-Type": "application/json"
};

// Get predictions
async function getPredictions() {
  const response = await axios.get(
    `${BASE_URL}/api/predictions/top20`,
    { headers, params: { limit: 10 } }
  );
  return response.data;
}

// Get market tendency
async function getMarketTendency() {
  const response = await axios.get(
    `${BASE_URL}/api/market/tendency`,
    { headers }
  );
  return response.data;
}

// Chat query
async function askQuestion(question, sessionId) {
  const response = await axios.post(
    `${BASE_URL}/api/chat/query`,
    { question, session_id: sessionId },
    { headers }
  );
  return response.data;
}

// Usage
(async () => {
  const predictions = await getPredictions();
  console.log(`Top prediction: ${predictions.predictions[0].symbol}`);
  
  const tendency = await getMarketTendency();
  console.log(`Market is ${tendency.tendency}`);
  
  const chat = await askQuestion("What is Bitcoin?", "user-123");
  console.log(`Answer: ${chat.answer}`);
})();
```


### JavaScript (Browser)

```javascript
const API_KEY = "your_api_key";
const BASE_URL = "http://localhost:5000";

// Get predictions
fetch(`${BASE_URL}/api/predictions/top20?limit=10`, {
  headers: {
    "Authorization": `Bearer ${API_KEY}`
  }
})
  .then(response => response.json())
  .then(data => {
    console.log("Top predictions:", data.predictions);
  })
  .catch(error => console.error("Error:", error));

// Chat query
fetch(`${BASE_URL}/api/chat/query`, {
  method: "POST",
  headers: {
    "Authorization": `Bearer ${API_KEY}`,
    "Content-Type": "application/json"
  },
  body: JSON.stringify({
    question: "What is Ethereum?",
    session_id: "user-123"
  })
})
  .then(response => response.json())
  .then(data => {
    if (data.success) {
      console.log("Answer:", data.answer);
    } else {
      console.log("Rejected:", data.rejection_reason);
    }
  });
```

### cURL Examples

```bash
# Health check (no auth)
curl http://localhost:5000/health

# Get top 5 predictions
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "http://localhost:5000/api/predictions/top20?limit=5"

# Get specific crypto prediction
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "http://localhost:5000/api/predictions/crypto/BTC"

# Get market tendency
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "http://localhost:5000/api/market/tendency"

# Get market tendency history (last 7 days)
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "http://localhost:5000/api/market/tendency/history?hours=168"

# Get market overview
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "http://localhost:5000/api/market/overview"

# Chat query
curl -X POST \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is Bitcoin?", "session_id": "user-123"}' \
  http://localhost:5000/api/chat/query

# Get chat history
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "http://localhost:5000/api/chat/history/user-123?limit=10"

# Validate question
curl -X POST \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is Bitcoin?"}' \
  http://localhost:5000/api/chat/validate

# Admin: Trigger data collection
curl -X POST \
  -H "Authorization: Bearer ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"mode": "forward"}' \
  http://localhost:5000/api/admin/collect/trigger

# Admin: Check collection status
curl -H "Authorization: Bearer ADMIN_API_KEY" \
  "http://localhost:5000/api/admin/collect/status"

# Admin: Get system info
curl -H "Authorization: Bearer ADMIN_API_KEY" \
  "http://localhost:5000/api/admin/system/info"
```


## Advanced Usage

### Pagination

For endpoints that return large datasets, use pagination:

```bash
# Get chat history with pagination
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "http://localhost:5000/api/chat/history/user-123?limit=20"
```

### Filtering and Sorting

Customize prediction results:

```bash
# Get top 5 predictions with fresh data
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "http://localhost:5000/api/predictions/top20?limit=5&use_cache=false"

# Get market tendency with custom lookback period
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "http://localhost:5000/api/market/tendency?lookback_hours=48"
```

### Batch Operations

Process multiple queries efficiently:

```python
import requests
from concurrent.futures import ThreadPoolExecutor

API_KEY = "your_api_key"
BASE_URL = "http://localhost:5000"
headers = {"Authorization": f"Bearer {API_KEY}"}

symbols = ["BTC", "ETH", "SOL", "ADA", "DOT"]

def get_prediction(symbol):
    response = requests.get(
        f"{BASE_URL}/api/predictions/crypto/{symbol}",
        headers=headers
    )
    return response.json()

# Fetch predictions in parallel
with ThreadPoolExecutor(max_workers=5) as executor:
    results = list(executor.map(get_prediction, symbols))

for result in results:
    print(f"{result['symbol']}: {result['predicted_change_percent']:.2f}%")
```

### Webhook Integration (Future)

While not currently implemented, the API is designed to support webhooks for:
- Real-time prediction updates
- Market shift alerts
- Collection completion notifications


## Security Considerations

### API Key Management

- **Never commit API keys** to version control
- **Rotate keys regularly** (recommended: every 90 days)
- **Use environment variables** to store keys
- **Limit key permissions** (use user keys for regular access, admin keys only when needed)

```bash
# Store API key in environment variable
export CRYPTO_API_KEY="your_api_key"

# Use in scripts
curl -H "Authorization: Bearer $CRYPTO_API_KEY" \
  http://localhost:5000/api/predictions/top20
```

### HTTPS in Production

Always use HTTPS in production environments:

```python
# Production
BASE_URL = "https://crypto-ai.crypto-vision.com"

# Local development (HTTP is acceptable)
BASE_URL = "http://localhost:5000"
```

### PII Protection

The API automatically filters personally identifiable information:

- Email addresses
- Phone numbers
- Names (via NER)
- Addresses
- Financial data (credit cards, bank accounts)

Questions containing PII will be rejected with a security warning.

### Rate Limiting

Respect rate limits to avoid service disruption:

- Monitor `Retry-After` headers
- Implement exponential backoff
- Cache responses when appropriate
- Use batch operations for multiple queries


## Troubleshooting

### Common Issues

**1. 401 Unauthorized**

```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Invalid or missing API key"
  }
}
```

**Solution:**
- Verify API key is correct
- Check Authorization header format: `Bearer YOUR_API_KEY`
- Ensure API key hasn't expired

**2. 429 Rate Limit Exceeded**

```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Please try again later."
  }
}
```

**Solution:**
- Wait for the time specified in `Retry-After` header
- Implement exponential backoff
- Enable caching to reduce API calls

**3. 500 Internal Server Error**

```json
{
  "error": {
    "code": "INTERNAL_SERVER_ERROR",
    "message": "An unexpected error occurred"
  }
}
```

**Solution:**
- Check API logs for details
- Verify database connectivity
- Ensure all services are running
- Contact system administrator

**4. Chat Query Rejected (PII)**

```json
{
  "success": false,
  "rejection_reason": "pii_detected",
  "pii_warning": "Your question contained personally identifiable information..."
}
```

**Solution:**
- Remove personal information from question
- Use generic examples instead of real data
- Rephrase question without PII

**5. Chat Query Rejected (Invalid Topic)**

```json
{
  "success": false,
  "rejection_reason": "invalid_topic"
}
```

**Solution:**
- Ensure question is about cryptocurrencies, blockchain, or related topics
- Avoid questions about weather, sports, politics (unless crypto-related)


### Testing the API

**Check if API is running:**
```bash
curl http://localhost:5000/health
```

**Test authentication:**
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  http://localhost:5000/api/predictions/top20
```

**Test with invalid key:**
```bash
curl -H "Authorization: Bearer invalid_key" \
  http://localhost:5000/api/predictions/top20
# Should return 401 Unauthorized
```

**Test rate limiting:**
```bash
# Send 101 requests rapidly (exceeds 100/minute limit)
for i in {1..101}; do
  curl -H "Authorization: Bearer YOUR_API_KEY" \
    http://localhost:5000/api/predictions/top20
done
# Last request should return 429
```

## Performance Tips

### 1. Enable Caching

Predictions and market tendencies are cached by default:

```python
# Use cached data (fast, recommended for most use cases)
response = requests.get(
    f"{BASE_URL}/api/predictions/top20",
    headers=headers,
    params={"use_cache": True, "max_age_hours": 24}
)

# Force fresh data (slower, use only when needed)
response = requests.get(
    f"{BASE_URL}/api/predictions/top20",
    headers=headers,
    params={"use_cache": False}
)
```

### 2. Minimize API Calls

```python
# Good: Get all predictions at once
predictions = requests.get(f"{BASE_URL}/api/predictions/top20").json()

# Bad: Make separate calls for each crypto
for symbol in ["BTC", "ETH", "SOL"]:
    pred = requests.get(f"{BASE_URL}/api/predictions/crypto/{symbol}").json()
```

### 3. Use Appropriate Limits

```python
# Get only what you need
response = requests.get(
    f"{BASE_URL}/api/predictions/top20",
    params={"limit": 5}  # Only get top 5 instead of 20
)
```

### 4. Implement Client-Side Caching

```python
import time

cache = {}
CACHE_TTL = 3600  # 1 hour

def get_predictions_cached():
    now = time.time()
    
    if "predictions" in cache:
        data, timestamp = cache["predictions"]
        if now - timestamp < CACHE_TTL:
            return data
    
    response = requests.get(f"{BASE_URL}/api/predictions/top20", headers=headers)
    data = response.json()
    cache["predictions"] = (data, now)
    
    return data
```


## API Versioning

The current API version is **1.0.0**. Future versions will maintain backward compatibility where possible.

### Version Information

Check API version:
```bash
curl http://localhost:5000/health
```

Response includes version:
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

### Future Versioning Strategy

When breaking changes are introduced, the API will use URL versioning:

- Current: `/api/predictions/top20`
- Future: `/api/v2/predictions/top20`

Version 1.0 endpoints will remain available for at least 6 months after a new version is released.

## Cost Estimation

### OpenAI API Costs

Chat queries use OpenAI's gpt-4o-mini model:

- **Input tokens**: ~$0.15 per 1M tokens
- **Output tokens**: ~$0.60 per 1M tokens
- **Average query**: 150 input + 300 output tokens = ~$0.0002 per question

**Monthly estimates:**
- 100 queries/day: ~$6/month
- 500 queries/day: ~$30/month
- 1000 queries/day: ~$60/month

### API Rate Limits

- **Free tier**: 100 requests/minute
- **No per-request charges** for predictions and market data
- **Only OpenAI chat queries** incur external costs

Track costs via metadata:
```python
response = requests.post(f"{BASE_URL}/api/chat/query", ...)
cost = response.json()["metadata"]["cost_usd"]
print(f"This query cost: ${cost:.6f}")
```

## Support and Resources

### Documentation

- **[Complete API Reference](src/api/API_DOCUMENTATION.md)** - Detailed endpoint specifications
- **[User Guide](USER-GUIDE.md)** - System usage and features
- **[Development Guide](DEVELOPMENT-GUIDE.md)** - Setup and development
- **[Security Guide](SECURITY-CONFORMANCE-GUIDE.md)** - Security best practices

### Getting Help

1. Check this guide and the detailed API documentation
2. Review error messages and troubleshooting section
3. Check API logs for detailed error information
4. Contact your system administrator

### Reporting Issues

When reporting API issues, include:
- Endpoint URL and method
- Request headers and body
- Response status code and body
- Timestamp of the request
- API version (from `/health` endpoint)


## Quick Reference

### Endpoint Summary

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/health` | GET | No | Health check |
| `/api/predictions/top20` | GET | Yes | Top 20 predictions |
| `/api/predictions/crypto/{symbol}` | GET | Yes | Specific crypto prediction |
| `/api/market/tendency` | GET | Yes | Current market tendency |
| `/api/market/tendency/history` | GET | Yes | Historical tendencies |
| `/api/market/overview` | GET | Yes | Market overview |
| `/api/chat/query` | POST | Yes | Process chat query |
| `/api/chat/history/{session_id}` | GET | Yes | Get chat history |
| `/api/chat/validate` | POST | Yes | Validate question |
| `/api/admin/collect/trigger` | POST | Admin | Trigger data collection |
| `/api/admin/collect/status` | GET | Admin | Collection status |
| `/api/admin/system/info` | GET | Admin | System information |

### Response Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 202 | Accepted (async operation started) |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 429 | Rate Limit Exceeded |
| 500 | Internal Server Error |

### Market Tendency Types

- **bullish**: Upward momentum (>60% cryptos increasing)
- **bearish**: Downward momentum (>60% cryptos decreasing)
- **volatile**: High fluctuations, no clear direction
- **stable**: Low volatility, minimal changes
- **consolidating**: Sideways movement in tight range

### Authentication Methods

1. `Authorization: Bearer YOUR_API_KEY` (recommended)
2. `X-API-Key: YOUR_API_KEY`
3. `?api_key=YOUR_API_KEY` (query parameter)

---

**Last Updated**: November 2025  
**API Version**: 1.0.0  
**Documentation Version**: 1.0.0
