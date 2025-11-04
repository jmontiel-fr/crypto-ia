# Crypto Market Analysis API Documentation

## Overview

The Crypto Market Analysis API provides endpoints for cryptocurrency price predictions, market analysis, and AI-powered chat queries.

**Base URL**: `http://localhost:5000` (local) or `https://crypto-ai.crypto-vision.com` (production)

**API Version**: 1.0.0

## Authentication

Most endpoints require API key authentication. Provide your API key in one of the following ways:

1. **Authorization Header** (recommended):
   ```
   Authorization: Bearer YOUR_API_KEY
   ```

2. **X-API-Key Header**:
   ```
   X-API-Key: YOUR_API_KEY
   ```

3. **Query Parameter**:
   ```
   ?api_key=YOUR_API_KEY
   ```

### Admin Endpoints

Admin endpoints require an API key with admin role.

## Rate Limiting

- **Rate Limit**: 100 requests per minute per IP address
- **Response Header**: `Retry-After` (seconds to wait before retrying)
- **Status Code**: 429 (Too Many Requests)

## Error Responses

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

- `BAD_REQUEST` (400): Invalid request data
- `UNAUTHORIZED` (401): Missing or invalid API key
- `FORBIDDEN` (403): Insufficient permissions
- `NOT_FOUND` (404): Resource not found
- `RATE_LIMIT_EXCEEDED` (429): Too many requests
- `INTERNAL_SERVER_ERROR` (500): Server error

## Endpoints

### Health Check

#### GET /health

Check API health status.

**Authentication**: Not required

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2025-11-01T12:00:00Z",
  "service": "crypto-market-analysis-api",
  "version": "1.0.0"
}
```

---

### Predictions

#### GET /api/predictions/top20

Get top 20 cryptocurrency predictions for the next 24 hours.

**Authentication**: Required

**Query Parameters**:
- `limit` (integer, optional): Number of predictions to return (default: 20, max: 50)
- `use_cache` (boolean, optional): Use cached predictions (default: true)
- `max_age_hours` (integer, optional): Maximum age of cached predictions in hours (default: 24)

**Response**:
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
  "count": 20,
  "cached": true
}
```

**Example**:
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "http://localhost:5000/api/predictions/top20?limit=10"
```

---

#### GET /api/predictions/crypto/{symbol}

Get prediction for a specific cryptocurrency.

**Authentication**: Required

**Path Parameters**:
- `symbol` (string): Cryptocurrency symbol (e.g., BTC, ETH)

**Response**:
```json
{
  "symbol": "BTC",
  "name": "Bitcoin",
  "current_price": 45000.00,
  "predicted_price": 46500.00,
  "predicted_change_percent": 3.33,
  "confidence": 0.85,
  "prediction_time": "2025-11-01T12:00:00Z",
  "horizon_hours": 24
}
```

**Example**:
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "http://localhost:5000/api/predictions/crypto/BTC"
```

---

### Market Analysis

#### GET /api/market/tendency

Get current market tendency classification.

**Authentication**: Required

**Query Parameters**:
- `use_cache` (boolean, optional): Use cached tendency (default: true)
- `max_age_hours` (integer, optional): Maximum age of cached tendency in hours (default: 1)
- `lookback_hours` (integer, optional): Hours to look back for analysis (default: 24)

**Response**:
```json
{
  "tendency": "bullish",
  "confidence": 0.78,
  "metrics": {
    "avg_change_percent": 2.5,
    "volatility_index": 0.15,
    "market_cap_change": 1.8,
    "positive_count": 35,
    "negative_count": 15,
    "positive_ratio": 0.70,
    "total_count": 50
  },
  "timestamp": "2025-11-01T12:00:00Z",
  "cached": true
}
```

**Tendency Types**:
- `bullish`: Overall upward momentum (>60% of cryptos increasing)
- `bearish`: Overall downward momentum (>60% of cryptos decreasing)
- `volatile`: High price fluctuations with no clear direction
- `stable`: Low volatility with minimal price changes
- `consolidating`: Sideways movement within tight range

**Example**:
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "http://localhost:5000/api/market/tendency"
```

---

#### GET /api/market/tendency/history

Get historical market tendencies.

**Authentication**: Required

**Query Parameters**:
- `hours` (integer, optional): Number of hours to look back (default: 168 = 1 week, max: 720)

**Response**:
```json
{
  "tendencies": [
    {
      "tendency": "bullish",
      "confidence": 0.78,
      "metrics": { ... },
      "timestamp": "2025-11-01T12:00:00Z"
    }
  ],
  "count": 24,
  "hours": 168,
  "start_time": "2025-10-25T12:00:00Z",
  "end_time": "2025-11-01T12:00:00Z"
}
```

---

#### GET /api/market/overview

Get comprehensive market overview.

**Authentication**: Required

**Response**:
```json
{
  "tendency": { ... },
  "top_gainers": [
    {
      "symbol": "SOL",
      "change_percent": 5.2
    }
  ],
  "top_losers": [
    {
      "symbol": "DOGE",
      "change_percent": -3.1
    }
  ],
  "total_cryptos_analyzed": 50,
  "timestamp": "2025-11-01T12:00:00Z"
}
```

---

### Chat Interface

#### POST /api/chat/query

Process a chat query using GenAI.

**Authentication**: Required

**Request Body**:
```json
{
  "question": "What are the top performing cryptocurrencies?",
  "session_id": "user-session-123"
}
```

**Response** (Success):
```json
{
  "success": true,
  "answer": "Based on our LSTM predictions, the top performers are...",
  "session_id": "user-session-123",
  "timestamp": "2025-11-01T12:00:00Z",
  "history": [
    {
      "question": "Previous question",
      "answer": "Previous answer",
      "timestamp": "2025-11-01T11:55:00Z"
    }
  ],
  "metadata": {
    "tokens_input": 150,
    "tokens_output": 300,
    "cost_usd": 0.0002,
    "response_time_ms": 1500
  }
}
```

**Response** (PII Detected):
```json
{
  "success": false,
  "answer": "I detected personally identifiable information...",
  "session_id": "user-session-123",
  "rejected": true,
  "rejection_reason": "pii_detected",
  "pii_detected": true,
  "pii_warning": "Your question contained personally identifiable information...",
  "timestamp": "2025-11-01T12:00:00Z"
}
```

**Response** (Invalid Topic):
```json
{
  "success": false,
  "answer": "I can only answer questions about cryptocurrencies...",
  "session_id": "user-session-123",
  "rejected": true,
  "rejection_reason": "invalid_topic",
  "timestamp": "2025-11-01T12:00:00Z"
}
```

**Example**:
```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is Bitcoin?", "session_id": "user-123"}' \
  "http://localhost:5000/api/chat/query"
```

---

#### GET /api/chat/history/{session_id}

Get chat history for a session.

**Authentication**: Required

**Path Parameters**:
- `session_id` (string): User session ID

**Query Parameters**:
- `limit` (integer, optional): Number of messages to return (default: 10, max: 50)

**Response**:
```json
{
  "session_id": "user-session-123",
  "history": [
    {
      "question": "What is Bitcoin?",
      "answer": "Bitcoin is...",
      "timestamp": "2025-11-01T12:00:00Z",
      "tokens_input": 50,
      "tokens_output": 100,
      "cost_usd": 0.0001
    }
  ],
  "count": 10
}
```

---

#### POST /api/chat/validate

Validate a question without processing it.

**Authentication**: Required

**Request Body**:
```json
{
  "question": "What is Bitcoin?"
}
```

**Response**:
```json
{
  "valid": true,
  "question": "What is Bitcoin?"
}
```

Or if invalid:
```json
{
  "valid": false,
  "question": "What's the weather?",
  "rejection_message": "I can only answer questions about cryptocurrencies..."
}
```

---

### Admin Endpoints

#### POST /api/admin/collect/trigger

Trigger manual data collection.

**Authentication**: Admin required

**Request Body**:
```json
{
  "mode": "backward",
  "start_date": "2024-01-01T00:00:00Z",
  "end_date": "2024-12-31T23:59:59Z"
}
```

**Modes**:
- `backward`: Collect historical data from end_date to start_date
- `forward`: Collect recent data from last recorded date to present
- `gap_fill`: Detect and fill gaps in existing data

**Response**:
```json
{
  "success": true,
  "message": "Collection task started: backward",
  "mode": "backward",
  "start_date": "2024-01-01T00:00:00Z",
  "end_date": "2024-12-31T23:59:59Z",
  "status_endpoint": "/api/admin/collect/status"
}
```

**Status Code**: 202 (Accepted)

---

#### GET /api/admin/collect/status

Get current data collection status.

**Authentication**: Admin required

**Response** (Running):
```json
{
  "is_running": true,
  "current_operation": "backward",
  "start_time": "2025-11-01T12:00:00Z",
  "elapsed_seconds": 120,
  "status": "running",
  "timestamp": "2025-11-01T12:02:00Z"
}
```

**Response** (Idle with results):
```json
{
  "is_running": false,
  "current_operation": null,
  "start_time": null,
  "status": "idle",
  "timestamp": "2025-11-01T12:05:00Z",
  "last_results": {
    "total_cryptos": 50,
    "successful": 48,
    "failed": 2,
    "total_records": 12000,
    "details": [...]
  }
}
```

---

#### GET /api/admin/system/info

Get system information and statistics.

**Authentication**: Admin required

**Response**:
```json
{
  "system": {
    "service": "Crypto Market Analysis API",
    "version": "1.0.0",
    "timestamp": "2025-11-01T12:00:00Z"
  },
  "database": {
    "total_cryptocurrencies": 50,
    "latest_price_data": "2025-11-01T11:00:00Z",
    "total_predictions": 1000,
    "total_chat_messages": 500
  },
  "collection": {
    "is_running": false,
    "current_operation": null
  }
}
```

---

## Response Headers

### Cache-Control

Prediction and market tendency endpoints include cache headers:

```
Cache-Control: public, max-age=3600
```

### Retry-After

Rate limit responses include retry-after header:

```
Retry-After: 60
```

## Best Practices

1. **Use Caching**: Enable caching for predictions and market tendency to reduce API calls
2. **Handle Rate Limits**: Implement exponential backoff when rate limited
3. **Validate Input**: Use the `/api/chat/validate` endpoint before submitting queries
4. **Session Management**: Use consistent session IDs for chat continuity
5. **Error Handling**: Always check for error responses and handle appropriately

## Examples

### Python

```python
import requests

API_KEY = "your_api_key"
BASE_URL = "http://localhost:5000"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# Get top predictions
response = requests.get(
    f"{BASE_URL}/api/predictions/top20",
    headers=headers,
    params={"limit": 10}
)
predictions = response.json()

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
```

### JavaScript

```javascript
const API_KEY = "your_api_key";
const BASE_URL = "http://localhost:5000";

// Get market tendency
fetch(`${BASE_URL}/api/market/tendency`, {
  headers: {
    "Authorization": `Bearer ${API_KEY}`
  }
})
  .then(response => response.json())
  .then(data => console.log(data));

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
  .then(data => console.log(data));
```

### cURL

```bash
# Get predictions
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "http://localhost:5000/api/predictions/top20?limit=5"

# Get market tendency
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "http://localhost:5000/api/market/tendency"

# Chat query
curl -X POST \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is Bitcoin?", "session_id": "user-123"}' \
  "http://localhost:5000/api/chat/query"

# Admin: Trigger collection
curl -X POST \
  -H "Authorization: Bearer ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"mode": "forward"}' \
  "http://localhost:5000/api/admin/collect/trigger"
```

## Support

For issues or questions, please refer to the main README.md or contact the development team.
