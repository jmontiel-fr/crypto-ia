# Flask REST API

This module provides the Flask REST API for the Crypto Market Analysis SaaS.

## Structure

```
src/api/
├── __init__.py              # Package initialization
├── app.py                   # Flask application factory
├── main.py                  # Main entry point
├── utils.py                 # Utility functions
├── API_DOCUMENTATION.md     # Complete API documentation
├── middleware/              # Middleware modules
│   ├── __init__.py
│   ├── auth.py             # API key authentication
│   └── rate_limiter.py     # Rate limiting
└── routes/                  # API route blueprints
    ├── __init__.py
    ├── health.py           # Health check endpoints
    ├── predictions.py      # Prediction endpoints
    ├── market.py           # Market analysis endpoints
    ├── chat.py             # Chat interface endpoints
    └── admin.py            # Admin endpoints
```

## Features

### Middleware

1. **CORS Configuration**: Configurable cross-origin resource sharing
2. **Request Logging**: Automatic logging of all requests and responses
3. **API Key Authentication**: Token-based authentication for protected endpoints
4. **Rate Limiting**: Token bucket algorithm limiting requests per minute per IP
5. **Error Handling**: Standardized error responses with proper HTTP status codes

### Endpoints

#### Public Endpoints
- `GET /health` - Health check
- `GET /` - API information

#### Prediction Endpoints
- `GET /api/predictions/top20` - Get top 20 cryptocurrency predictions
- `GET /api/predictions/crypto/{symbol}` - Get prediction for specific crypto

#### Market Endpoints
- `GET /api/market/tendency` - Get current market tendency
- `GET /api/market/tendency/history` - Get historical tendencies
- `GET /api/market/overview` - Get comprehensive market overview

#### Chat Endpoints
- `POST /api/chat/query` - Process chat query with GenAI
- `GET /api/chat/history/{session_id}` - Get chat history
- `POST /api/chat/validate` - Validate question without processing

#### Admin Endpoints (Admin Role Required)
- `POST /api/admin/collect/trigger` - Trigger manual data collection
- `GET /api/admin/collect/status` - Get collection status
- `GET /api/admin/system/info` - Get system information

## Running the API

### Local Development

```bash
# Set up environment
cp local-env.example local-env
# Edit local-env with your configuration

# Install dependencies
pip install -r requirements.txt

# Run the API
python src/api/main.py
```

The API will be available at `http://localhost:5000`

### Production Deployment

```bash
# Set up environment
cp aws-env.example aws-env
# Edit aws-env with your configuration

# Use a production WSGI server (e.g., Gunicorn)
gunicorn -w 4 -b 0.0.0.0:5000 src.api.main:app
```

## Configuration

The API is configured via environment variables (see `local-env.example` or `aws-env.example`):

### Required Variables

- `DATABASE_URL`: PostgreSQL connection string
- `OPENAI_API_KEY`: OpenAI API key for chat functionality
- `SECRET_KEY`: Secret key for Flask sessions

### Optional Variables

- `API_HOST`: Host to bind to (default: 0.0.0.0)
- `API_PORT`: Port to bind to (default: 5000)
- `API_KEY_REQUIRED`: Enable API key authentication (default: false)
- `RATE_LIMIT_PER_MINUTE`: Rate limit per IP (default: 100)
- `ALLOWED_ORIGINS`: CORS allowed origins (default: *)
- `LOG_LEVEL`: Logging level (default: INFO)

## Authentication

### API Keys

For development, use the built-in API keys:

- **User Key**: `dev_key_12345`
- **Admin Key**: `admin_key_67890`

In production, implement proper API key management:

1. Store API keys in database with hashing
2. Implement key generation and rotation
3. Add key expiration and revocation
4. Track key usage and rate limits per key

### Using API Keys

Include the API key in requests:

**Authorization Header** (recommended):
```bash
curl -H "Authorization: Bearer dev_key_12345" \
  http://localhost:5000/api/predictions/top20
```

**X-API-Key Header**:
```bash
curl -H "X-API-Key: dev_key_12345" \
  http://localhost:5000/api/predictions/top20
```

**Query Parameter**:
```bash
curl "http://localhost:5000/api/predictions/top20?api_key=dev_key_12345"
```

## Rate Limiting

The API implements token bucket rate limiting:

- **Default Limit**: 100 requests per minute per IP address
- **Algorithm**: Token bucket with continuous refill
- **Response**: 429 status code with `Retry-After` header

### Rate Limit Headers

Responses include rate limit information:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1635782400
```

## Error Handling

All errors follow a standardized format:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message",
    "details": "Additional details",
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

## Testing

### Manual Testing

Use curl or Postman to test endpoints:

```bash
# Health check
curl http://localhost:5000/health

# Get predictions (with API key)
curl -H "Authorization: Bearer dev_key_12345" \
  http://localhost:5000/api/predictions/top20

# Chat query
curl -X POST \
  -H "Authorization: Bearer dev_key_12345" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is Bitcoin?", "session_id": "test-123"}' \
  http://localhost:5000/api/chat/query
```

### Automated Testing

Run the test suite:

```bash
pytest tests/test_api.py -v
```

## Monitoring

### Logging

All requests and errors are logged:

```
2025-11-01 12:00:00 INFO: GET /api/predictions/top20 from 192.168.1.100
2025-11-01 12:00:01 INFO: GET /api/predictions/top20 - Status: 200
```

### Health Checks

Use the `/health` endpoint for monitoring:

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

## Security Best Practices

1. **Always use HTTPS in production**
2. **Implement proper API key management**
3. **Enable rate limiting**
4. **Validate all input data**
5. **Use environment variables for secrets**
6. **Keep dependencies updated**
7. **Monitor for suspicious activity**
8. **Implement request logging and auditing**

## Performance Optimization

1. **Enable caching** for predictions and market data
2. **Use connection pooling** for database
3. **Implement response compression**
4. **Add CDN** for static assets
5. **Use async workers** for long-running tasks
6. **Monitor and optimize slow queries**

## Troubleshooting

### API Not Starting

Check:
- Database connection string is correct
- Required environment variables are set
- Port is not already in use
- Dependencies are installed

### Authentication Errors

Check:
- API key is correct
- API key authentication is enabled in config
- Authorization header format is correct

### Rate Limit Issues

Check:
- Rate limit configuration
- IP address detection
- Consider increasing limit for specific IPs

### Database Errors

Check:
- Database is running
- Connection string is correct
- Database migrations are applied
- Connection pool settings

## Development

### Adding New Endpoints

1. Create route function in appropriate blueprint
2. Add authentication/authorization decorators
3. Implement request validation
4. Add error handling
5. Update API documentation
6. Add tests

### Adding Middleware

1. Create middleware function in `middleware/` directory
2. Register in `app.py` `register_middleware()`
3. Add configuration options
4. Document behavior

## Documentation

See [API_DOCUMENTATION.md](./API_DOCUMENTATION.md) for complete API reference.

## Support

For issues or questions:
1. Check the logs for error messages
2. Review the API documentation
3. Check the main project README
4. Contact the development team
