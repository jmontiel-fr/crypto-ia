# User Guide - Crypto Market Analysis SaaS

Welcome to the Crypto Market Analysis SaaS! This guide will help you understand and use all the features of the platform.

## Table of Contents

- [Getting Started](#getting-started)
- [Accessing the System](#accessing-the-system)
- [Streamlit Dashboard](#streamlit-dashboard)
- [Chat Interface](#chat-interface)
- [API Endpoints](#api-endpoints)
- [Alert System](#alert-system)
- [Cost Information](#cost-information)
- [FAQ](#faq)
- [Support](#support)

## Getting Started

The Crypto Market Analysis SaaS provides AI-powered cryptocurrency market analysis through multiple interfaces:

- **📊 Streamlit Dashboard**: Interactive data visualization and analytics
- **💬 Chat Interface**: Natural language queries about crypto markets
- **🔌 REST API**: Programmatic access to predictions and data
- **📱 SMS Alerts**: Real-time notifications for significant market changes

### What You Can Do

- **Get AI Predictions**: View top 20 cryptocurrencies predicted to perform best in the next 24 hours
- **Market Analysis**: Understand current market trends (bullish, bearish, volatile, etc.)
- **Ask Questions**: Chat with AI about cryptocurrency markets using natural language
- **Receive Alerts**: Get SMS notifications when markets move significantly
- **Access Data**: Use REST API for custom applications and integrations

## Accessing the System

The system consists of three independent web applications accessed through a landing page:

### Landing Page

**Purpose**: Unified entry point to access all system features

**Local Development:**
- URL: `http://www.crypto-vision.com` (or `http://localhost:80`)

**AWS Production:**
- URL: `http://www.crypto-vision.com`

**Features:**
- Simple, clean interface with two primary navigation buttons:
  - **"View Dashboard"**: Opens the Streamlit dashboard for data visualization
  - **"Chat Assistant"**: Opens the AI chat interface for natural language queries
- Responsive design works on desktop, tablet, and mobile
- Quick access to both main features without complex navigation

### Application URLs

**Local Development Environment:**

If running locally:
- **Landing Page**: `http://www.crypto-vision.com` (or `http://localhost:80`)
- **Streamlit Dashboard**: `http://localhost:8501`
- **Chat Interface**: `https://crypto-ai.local:10443`
- **API Base URL**: `https://crypto-ai.local:10443/api`

**AWS Production Environment:**

If deployed to AWS:
- **Landing Page**: `http://www.crypto-vision.com`
- **Streamlit Dashboard**: `http://www.crypto-vision.com:8501` (or `http://dashboard.crypto-vision.com`)
- **Chat Interface**: `https://crypto-ai.crypto-vision.com:10443` (or `https://chat.crypto-vision.com`)
- **API Base URL**: `https://crypto-ai.crypto-vision.com/api`

### Navigation Flow

1. **Start at Landing Page**: Visit `www.crypto-vision.com`
2. **Choose Your Tool**:
   - Click **"View Dashboard"** for charts, predictions, and analytics
   - Click **"Chat Assistant"** for conversational AI queries
3. **Switch Between Tools**: Use browser tabs or return to landing page

### Architecture Notes

- All three applications (Landing Page, Dashboard, Chat) are **independent**
- Each runs on its own port with dedicated functionality
- No tight integration - navigate via links/buttons
- Can open multiple tabs for simultaneous access
- Each application can be bookmarked separately

### Browser Requirements

- **Modern Browser**: Chrome, Firefox, Safari, or Edge (latest versions)
- **JavaScript Enabled**: Required for chat interface and interactive charts
- **HTTPS Support**: All connections use SSL/TLS encryption
- **Cookies**: Session management for chat history

**Note**: Self-signed certificates will show security warnings in browsers. Click "Advanced" → "Proceed to site" to continue.

## Streamlit Dashboard

The Streamlit dashboard provides interactive data visualization and analytics.

### Navigation

The dashboard has multiple pages accessible via the sidebar:

- **🏠 Market Overview**: General market statistics and trends
- **🎯 Top Predictions**: AI predictions for best performing cryptocurrencies
- **📈 Market Tendency**: Current market sentiment and historical trends
- **⚙️ Data Collection**: System status and data collection information
- **🔍 Admin Audit**: Security and usage analytics (admin only)

### Market Overview Page

**Key Metrics:**
- Total cryptocurrencies tracked
- Market capitalization trends
- Volume analysis
- Price change distributions

**Interactive Charts:**
- Market cap over time
- Volume trends
- Top gainers and losers
- Correlation matrices

### Top Predictions Page

**AI Predictions Display:**
- Top 20 cryptocurrencies predicted to perform best
- Confidence scores for each prediction
- Current prices and predicted changes
- Historical accuracy metrics

**Features:**
- **Sortable Table**: Click column headers to sort
- **Filtering**: Filter by confidence score or predicted change
- **Export**: Download predictions as CSV
- **Refresh**: Update predictions with latest data

**Understanding Predictions:**
- **Predicted Change**: Expected price change in next 24 hours
- **Confidence Score**: AI confidence in prediction (0-1 scale)
- **Current Price**: Latest price from data collection
- **Market Cap Rank**: Cryptocurrency ranking by market capitalization

### Market Tendency Page

**Market Sentiment Analysis:**
- **Bullish**: Market showing upward momentum
- **Bearish**: Market showing downward momentum  
- **Volatile**: High price fluctuations with no clear direction
- **Stable**: Low volatility with minimal price changes
- **Consolidating**: Sideways movement within tight range

**Historical Trends:**
- Tendency changes over time
- Confidence levels
- Supporting metrics and indicators

### Data Collection Page

**System Status:**
- Real-time collection progress (per-crypto and overall)
- Collection status: Complete, Partial, Failed, Skipped
- Last update timestamps
- Coverage statistics (100 cryptos tracked)
- Detailed error reporting with retry counts

**Collection Features:**
- **Smart Resume**: Automatically continues from where it left off if interrupted
- **No Duplicates**: Only fetches missing data ranges
- **Automatic Retry**: Failed batches retry up to 3 times with exponential backoff
- **Interruption-Safe**: Can stop/restart anytime without losing progress

**Manual Controls:**
- **Trigger Collection**: Start backward, forward, or gap-fill collection
- **Monitor Progress**: Real-time status updates via API
- **View Results**: Detailed per-crypto results with status
- **Check System Health**: Verify data completeness

**Collection Modes:**
- **Backward**: Collect historical data from start date to present
- **Forward**: Update with latest data since last collection
- **Gap Fill**: Detect and fill missing data ranges

**API Usage:**
```bash
# Trigger historical collection (requires API key)
curl -X POST http://localhost:5000/api/admin/collect/trigger \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"mode": "backward", "start_date": "2024-01-01T00:00:00Z"}'

# Check collection status
curl -H "X-API-Key: YOUR_KEY" \
  http://localhost:5000/api/admin/collect/status
```

**See Also:** `docs/QUICK-START-COLLECTOR.md` for detailed collection guide

### Admin Audit Page

**Security Analytics:**
- Query audit logs
- PII detection events
- Cost tracking
- Usage statistics

**Features:**
- Filter by date range and event type
- Export audit data
- Real-time monitoring
- Compliance reporting

## Chat Interface

The chat interface allows natural language queries about cryptocurrency markets.

### Accessing the Chat

1. Navigate to the main application URL
2. You'll see a ChatGPT-like interface
3. Type your question in the input box
4. Press Enter or click Send

### What You Can Ask

**Market Analysis Questions:**
- "What are the top 20 cryptocurrencies to invest in?"
- "Should I buy Bitcoin right now?"
- "What's the current market sentiment?"
- "Which altcoins are showing bullish signals?"

**Specific Cryptocurrency Questions:**
- "What's the prediction for Ethereum?"
- "Is Solana a good investment?"
- "How is Cardano performing?"
- "What factors affect Bitcoin price?"

**General Crypto Questions:**
- "What is DeFi?"
- "How does blockchain technology work?"
- "What are the risks of crypto investing?"
- "What's the difference between Bitcoin and Ethereum?"

### Chat Features

**Conversation History:**
- Last 3 question-answer pairs are displayed
- Provides context for follow-up questions
- Automatically cleared after session ends

**AI-Powered Responses:**
- Combines internal LSTM predictions with external knowledge
- Uses OpenAI GPT-4o-mini for natural language processing
- Provides comprehensive analysis with multiple perspectives

**Safety Features:**
- **PII Protection**: Automatically detects and blocks personal information
- **Topic Validation**: Only answers cryptocurrency-related questions
- **Content Filtering**: Ensures appropriate and helpful responses

### Chat Limitations

**Restricted Topics:**
- Only cryptocurrency and blockchain-related questions
- No personal financial advice
- No weather, sports, or general topics

**Data Privacy:**
- No personal information is stored
- All queries are anonymized
- PII is automatically filtered out

**Response Time:**
- Typical response: 2-5 seconds
- Complex queries may take longer
- Timeout after 30 seconds

## API Endpoints

The REST API provides programmatic access to all system functionality.

### Base URL

- **Local**: https://crypto-ai.local:10443/api
- **AWS**: https://crypto-ai.your-domain.com/api

### Authentication

**API Key Authentication**: Enabled for admin endpoints.

**Public Endpoints** (no key required):
- `GET /api/health` - Health check
- `GET /api/predictions/top20` - Top predictions
- `GET /api/market/tendency` - Market tendency
- `POST /api/chat/query` - Chat queries

**Admin Endpoints** (API key required):
- `POST /api/admin/collect/trigger` - Trigger data collection
- `GET /api/admin/collect/status` - Collection status
- `GET /api/admin/system/info` - System information

**Generate API Key:**
```bash
python scripts/generate_admin_api_key.py
```

**Use API Key:**
```bash
# Option 1: X-API-Key header (recommended)
curl -H "X-API-Key: your-api-key" http://localhost:5000/api/admin/collect/status

# Option 2: Authorization header
curl -H "Authorization: Bearer your-api-key" http://localhost:5000/api/admin/collect/status

# Option 3: Query parameter
curl "http://localhost:5000/api/admin/collect/status?api_key=your-api-key"
```

**Security Notes:**
- API keys are stored hashed in the database (never in config files)
- Keys are shown only once when generated - save them securely!
- Admin keys have full access to all admin endpoints
- Keys can be revoked anytime via the API key manager

### Available Endpoints

#### Health Check
```bash
GET /api/health
```
**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-11-01T12:00:00Z",
  "version": "1.0.0"
}
```

#### Top Predictions
```bash
GET /api/predictions/top20
```
**Parameters:**
- `limit` (optional): Number of predictions (default: 20)
- `use_cache` (optional): Use cached results (default: true)

**Response:**
```json
{
  "predictions": [
    {
      "symbol": "BTC",
      "current_price": 45000.00,
      "predicted_price": 46500.00,
      "predicted_change_percent": 3.33,
      "confidence": 0.85,
      "market_cap_rank": 1
    }
  ],
  "prediction_time": "2025-11-01T12:00:00Z",
  "horizon_hours": 24
}
```

#### Market Tendency
```bash
GET /api/market/tendency
```
**Response:**
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

#### Chat Query
```bash
POST /api/chat/query
```
**Request:**
```json
{
  "question": "What factors influence Bitcoin price?",
  "session_id": "user-session-123"
}
```
**Response:**
```json
{
  "answer": "Bitcoin price is influenced by several factors...",
  "history": [
    {"question": "Previous question", "answer": "Previous answer"}
  ],
  "timestamp": "2025-11-01T12:00:00Z"
}
```

### API Usage Examples

**Python:**
```python
import requests

# Get top predictions
response = requests.get('https://crypto-ai.your-domain.com/api/predictions/top20')
predictions = response.json()

for pred in predictions['predictions']:
    print(f"{pred['symbol']}: {pred['predicted_change_percent']:.2f}%")
```

**JavaScript:**
```javascript
// Get market tendency
fetch('https://crypto-ai.your-domain.com/api/market/tendency')
  .then(response => response.json())
  .then(data => {
    console.log(`Market is ${data.tendency} with ${data.confidence} confidence`);
  });
```

**cURL:**
```bash
# Chat query
curl -X POST https://crypto-ai.your-domain.com/api/chat/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Should I invest in Ethereum?", "session_id": "test-session"}'
```

## Alert System

The SMS alert system monitors cryptocurrency markets and sends notifications for significant price movements.

### How It Works

1. **Monitoring**: System checks prices every hour
2. **Detection**: Identifies movements beyond threshold (default: 10%)
3. **Filtering**: Prevents spam with cooldown periods
4. **Notification**: Sends SMS with relevant information

### Alert Configuration

**Threshold Settings:**
- Default threshold: 10% price change in 1 hour
- Configurable via environment variables
- Separate thresholds for increases and decreases

**Cooldown Protection:**
- Maximum 1 alert per cryptocurrency per 4 hours
- Prevents notification spam during volatile periods
- Configurable cooldown periods

### SMS Providers

**Twilio (Recommended):**
- Reliable delivery
- Global coverage
- Detailed delivery reports

**AWS SNS:**
- Native AWS integration
- Cost-effective for high volume
- Regional availability

### Alert Message Format

```
🚨 CRYPTO ALERT 🚨
BTC: +12.5% in 1h
$45,000 → $50,625
Time: 2025-11-01 14:30 UTC
```

### Managing Alerts

**Enable/Disable:**
```bash
# In environment configuration
ALERT_ENABLED=true
```

**Adjust Threshold:**
```bash
# Set to 15% threshold
ALERT_THRESHOLD_PERCENT=15.0
```

**Change Phone Number:**
```bash
# Update SMS recipient
SMS_PHONE_NUMBER=+1234567890
```

## Cost Information

Understanding the costs associated with running the Crypto Market Analysis SaaS.

### AWS Infrastructure Costs

**EC2 Instance (t3.micro):**
- **On-Demand**: ~$7.50/month
- **Reserved Instance (1-year)**: ~$5.00/month (33% savings)
- **Free Tier**: First 12 months free for new AWS accounts

**EBS Storage:**
- **Root Volume (20 GB)**: ~$2.00/month
- **PostgreSQL Data (50 GB)**: ~$5.00/month
- **Snapshots**: ~$0.50/month (if backup enabled)

**Network:**
- **Elastic IP**: Free when attached to running instance
- **Data Transfer**: ~$1-5/month depending on usage
- **First 1 GB/month**: Free

**CloudWatch:**
- **Basic Monitoring**: Free
- **Detailed Monitoring**: ~$0.50/month
- **Log Storage**: ~$0.50/month

**Total AWS Costs: $15-20/month**

### OpenAI API Costs

**gpt-4o-mini Pricing:**
- **Input Tokens**: $0.15 per 1M tokens
- **Output Tokens**: $0.60 per 1M tokens

**Usage Estimates:**
- **Average Query**: 150 input + 300 output tokens = ~$0.0002
- **100 queries/day**: ~$0.60/month
- **1000 queries/day**: ~$6.00/month

**Cost Control:**
- Set `OPENAI_MAX_TOKENS=500` to limit response length
- Monitor usage in OpenAI dashboard
- Use audit logging to track costs

### SMS Alert Costs

**Twilio Pricing:**
- **SMS Messages**: $0.0075 per message (US)
- **International**: Varies by country

**Usage Estimates:**
- **10 alerts/month**: ~$0.08
- **100 alerts/month**: ~$0.75
- **High volatility periods**: May increase

### Total Monthly Costs

**Light Usage (100 chat queries, 10 SMS alerts):**
- AWS Infrastructure: $15-20
- OpenAI API: $0.60
- SMS Alerts: $0.08
- **Total: ~$16-21/month**

**Moderate Usage (1000 chat queries, 100 SMS alerts):**
- AWS Infrastructure: $15-20
- OpenAI API: $6.00
- SMS Alerts: $0.75
- **Total: ~$22-27/month**

**Heavy Usage (5000 chat queries, 500 SMS alerts):**
- AWS Infrastructure: $15-20
- OpenAI API: $30.00
- SMS Alerts: $3.75
- **Total: ~$49-54/month**

### Cost Optimization Tips

1. **Use Reserved Instances**: Save 30-40% on EC2 costs
2. **Monitor OpenAI Usage**: Set usage alerts in OpenAI dashboard
3. **Optimize Alert Thresholds**: Reduce unnecessary SMS alerts
4. **Schedule Data Collection**: Run during off-peak hours
5. **Use Caching**: Reduce API calls with intelligent caching

## FAQ

### General Questions

**Q: What cryptocurrencies are supported?**
A: The system tracks the top 50 cryptocurrencies by market capitalization, including Bitcoin, Ethereum, Solana, Cardano, and others. The list is automatically updated based on market rankings.

**Q: How accurate are the predictions?**
A: Predictions are generated using LSTM neural networks trained on historical data. While we strive for accuracy, cryptocurrency markets are highly volatile and unpredictable. Use predictions as one factor in your decision-making process.

**Q: How often is data updated?**
A: Price data is collected every 6 hours by default. Predictions are updated daily. Market tendency is calculated hourly.

**Q: Is my data secure?**
A: Yes. The system includes comprehensive security measures:
- All communications use HTTPS encryption
- PII is automatically detected and filtered
- No personal information is stored
- Audit logging tracks all activities
- Access is restricted to authorized users only

### Technical Questions

**Q: What happens if the system goes down?**
A: The system includes monitoring and automatic restart capabilities. If issues persist, check the status page or contact support.

**Q: Can I integrate with my own applications?**
A: Yes! Use the REST API to integrate predictions and market data into your own applications. See the API documentation above.

**Q: How do I change my alert settings?**
A: Alert settings are configured via environment variables. Contact your administrator to modify thresholds, phone numbers, or enable/disable alerts.

**Q: Why am I getting SSL certificate warnings?**
A: The system uses self-signed certificates by default. These are secure but not recognized by browsers. For production use, consider using certificates from a trusted Certificate Authority.

### Troubleshooting

**Q: The chat interface isn't responding**
A: Check your internet connection and try refreshing the page. If the issue persists, the OpenAI API may be experiencing issues.

**Q: I'm not receiving SMS alerts**
A: Verify your phone number is correctly configured and that SMS alerts are enabled. Check with your mobile provider for any SMS blocking.

**Q: Predictions seem outdated**
A: Predictions are cached for performance. If you need the latest predictions, wait for the next update cycle or contact your administrator.

**Q: The dashboard is loading slowly**
A: Dashboard performance depends on data volume and network speed. Try refreshing the page or accessing during off-peak hours.

### Billing Questions

**Q: How can I monitor my costs?**
A: Use the admin audit dashboard to track OpenAI API usage and costs. AWS costs can be monitored through the AWS Billing Dashboard.

**Q: Can I set spending limits?**
A: Yes. Set up billing alerts in AWS and OpenAI dashboards. You can also configure usage limits in the application settings.

**Q: What happens if I exceed my budget?**
A: The system will continue running, but you'll be charged for usage. Set up billing alerts to monitor spending and adjust usage as needed.

## Support

### Getting Help

**Documentation:**
- [Development Guide](DEVELOPMENT-GUIDE.md) - For developers and contributors
- [Deployment Guide](DEPLOYMENT-GUIDE.md) - For system administrators
- [Security Guide](SECURITY-CONFORMANCE-GUIDE.md) - For security and compliance

**System Status:**
- Check the health endpoint: `/api/health`
- View system logs via the admin dashboard
- Monitor AWS CloudWatch for infrastructure metrics

**Common Issues:**
1. **SSL Certificate Warnings**: Normal for self-signed certificates
2. **Slow Response Times**: May indicate high load or API rate limits
3. **Missing Predictions**: Check data collection status
4. **Chat Not Working**: Verify OpenAI API key configuration

### Contact Information

For technical support or questions about the Crypto Market Analysis SaaS:

1. **Check Documentation**: Review this guide and other documentation
2. **System Logs**: Check application logs for error messages
3. **Health Checks**: Use the `/api/health` endpoint to verify system status
4. **Admin Dashboard**: Use the audit dashboard to monitor system health

### Reporting Issues

When reporting issues, please include:

- **Error Messages**: Exact error text or screenshots
- **Steps to Reproduce**: What you were doing when the issue occurred
- **Browser/Environment**: Browser version, operating system
- **Timestamp**: When the issue occurred
- **User Session**: Session ID if available

This user guide should help you make the most of the Crypto Market Analysis SaaS platform. For technical details and development information, see the [DEVELOPMENT-GUIDE.md](DEVELOPMENT-GUIDE.md).