# Portfolio Evaluation API

## Overview

The Portfolio API uses LSTM/GRU predictions in reverse - you provide a portfolio, and it predicts the 24-hour performance using the trained models.

### Key Features

✅ **Portfolio Evaluation**: Predict 24-hour performance of any portfolio  
✅ **Portfolio Comparison**: Compare multiple portfolio strategies  
✅ **Portfolio Optimization**: Get suggestions to improve your portfolio  
✅ **Risk Assessment**: Calculate portfolio risk scores  
✅ **Best/Worst Performers**: Identify which holdings will perform best/worst  

---

## API Endpoints

### 1. Evaluate Portfolio

**Endpoint:** `POST /api/portfolio/evaluate`

**Description:** Evaluate a portfolio and predict its 24-hour performance.

**Request:**
```json
{
  "holdings": {
    "BTC": 0.5,
    "ETH": 2.0,
    "SOL": 100,
    "AVAX": 50,
    "MATIC": 500
  },
  "use_cache": true
}
```

**Response:**
```json
{
  "total_current_value": 50000.00,
  "total_predicted_value": 52500.00,
  "total_change_usd": 2500.00,
  "total_change_percent": 5.0,
  "holdings": [
    {
      "symbol": "BTC",
      "quantity": 0.5,
      "current_price": 45000.00,
      "current_value": 22500.00,
      "predicted_price": 47250.00,
      "predicted_value": 23625.00,
      "predicted_change_percent": 5.0,
      "predicted_change_usd": 1125.00
    },
    {
      "symbol": "ETH",
      "quantity": 2.0,
      "current_price": 2500.00,
      "current_value": 5000.00,
      "predicted_price": 2700.00,
      "predicted_value": 5400.00,
      "predicted_change_percent": 8.0,
      "predicted_change_usd": 400.00
    }
    // ... more holdings
  ],
  "best_performers": [
    {
      "symbol": "SOL",
      "quantity": 100,
      "current_value": 10000.00,
      "predicted_change_percent": 12.5,
      "predicted_change_usd": 1250.00
    },
    {
      "symbol": "ETH",
      "quantity": 2.0,
      "current_value": 5000.00,
      "predicted_change_percent": 8.0,
      "predicted_change_usd": 400.00
    }
  ],
  "worst_performers": [
    {
      "symbol": "MATIC",
      "quantity": 500,
      "current_value": 500.00,
      "predicted_change_percent": -2.5,
      "predicted_change_usd": -12.50
    }
  ],
  "risk_score": 4.2,
  "confidence_score": 0.82,
  "timestamp": "2025-11-12T14:30:00",
  "prediction_horizon_hours": 24
}
```

**Example:**
```bash
curl -X POST http://localhost:5000/api/portfolio/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "holdings": {
      "BTC": 0.5,
      "ETH": 2.0,
      "SOL": 100
    }
  }'
```

---

### 2. Compare Portfolios

**Endpoint:** `POST /api/portfolio/compare`

**Description:** Compare multiple portfolio strategies.

**Request:**
```json
{
  "portfolios": {
    "Conservative": {
      "BTC": 1.0,
      "ETH": 5.0
    },
    "Aggressive": {
      "SOL": 500,
      "AVAX": 200,
      "MATIC": 1000
    },
    "Balanced": {
      "BTC": 0.5,
      "ETH": 2.0,
      "SOL": 100,
      "AVAX": 50
    }
  }
}
```

**Response:**
```json
{
  "portfolios": {
    "Conservative": {
      "current_value": 60000.00,
      "predicted_value": 63000.00,
      "predicted_change_percent": 5.0,
      "predicted_change_usd": 3000.00,
      "risk_score": 2.1,
      "confidence_score": 0.88
    },
    "Aggressive": {
      "current_value": 45000.00,
      "predicted_value": 49500.00,
      "predicted_change_percent": 10.0,
      "predicted_change_usd": 4500.00,
      "risk_score": 6.8,
      "confidence_score": 0.75
    },
    "Balanced": {
      "current_value": 50000.00,
      "predicted_value": 53500.00,
      "predicted_change_percent": 7.0,
      "predicted_change_usd": 3500.00,
      "risk_score": 3.5,
      "confidence_score": 0.82
    }
  },
  "rankings": {
    "by_return": [
      {
        "rank": 1,
        "name": "Aggressive",
        "predicted_return": 10.0
      },
      {
        "rank": 2,
        "name": "Balanced",
        "predicted_return": 7.0
      },
      {
        "rank": 3,
        "name": "Conservative",
        "predicted_return": 5.0
      }
    ],
    "by_risk": [
      {
        "rank": 1,
        "name": "Conservative",
        "risk_score": 2.1
      },
      {
        "rank": 2,
        "name": "Balanced",
        "risk_score": 3.5
      },
      {
        "rank": 3,
        "name": "Aggressive",
        "risk_score": 6.8
      }
    ]
  },
  "best_portfolio": "Aggressive",
  "timestamp": "2025-11-12T14:30:00"
}
```

**Example:**
```bash
curl -X POST http://localhost:5000/api/portfolio/compare \
  -H "Content-Type: application/json" \
  -d '{
    "portfolios": {
      "Conservative": {"BTC": 1.0, "ETH": 5.0},
      "Aggressive": {"SOL": 500, "AVAX": 200}
    }
  }'
```

---

### 3. Optimize Portfolio

**Endpoint:** `POST /api/portfolio/optimize`

**Description:** Get suggestions to optimize your portfolio.

**Request:**
```json
{
  "holdings": {
    "BTC": 0.5,
    "ETH": 2.0,
    "DOGE": 1000
  },
  "target_value": 60000,
  "max_risk": 5.0
}
```

**Response:**
```json
{
  "current_portfolio": {
    "value": 50000.00,
    "predicted_value": 51500.00,
    "predicted_change_percent": 3.0,
    "risk_score": 4.5
  },
  "suggestions": [
    {
      "action": "ADD",
      "symbol": "SOL",
      "reason": "Top predicted performer (+12.5%)",
      "predicted_change": 12.5
    },
    {
      "action": "ADD",
      "symbol": "AVAX",
      "reason": "Top predicted performer (+9.8%)",
      "predicted_change": 9.8
    },
    {
      "action": "REDUCE",
      "symbol": "DOGE",
      "reason": "Predicted to decline (-3.2%)",
      "predicted_change": -3.2
    }
  ],
  "timestamp": "2025-11-12T14:30:00"
}
```

**Example:**
```bash
curl -X POST http://localhost:5000/api/portfolio/optimize \
  -H "Content-Type: application/json" \
  -d '{
    "holdings": {
      "BTC": 0.5,
      "ETH": 2.0,
      "DOGE": 1000
    }
  }'
```

---

## Use Cases

### 1. Portfolio Tracking

```python
import requests

# Your current portfolio
portfolio = {
    "BTC": 0.5,
    "ETH": 2.0,
    "SOL": 100,
    "AVAX": 50
}

# Evaluate daily
response = requests.post(
    'http://localhost:5000/api/portfolio/evaluate',
    json={'holdings': portfolio}
)

result = response.json()
print(f"Current value: ${result['total_current_value']:,.2f}")
print(f"Predicted (24h): ${result['total_predicted_value']:,.2f}")
print(f"Expected change: {result['total_change_percent']:+.2f}%")
```

### 2. Strategy Comparison

```python
# Compare different strategies
strategies = {
    "Bitcoin Maxi": {"BTC": 1.0},
    "Ethereum Focus": {"ETH": 10.0},
    "Diversified": {
        "BTC": 0.3,
        "ETH": 1.5,
        "SOL": 50,
        "AVAX": 30
    }
}

response = requests.post(
    'http://localhost:5000/api/portfolio/compare',
    json={'portfolios': strategies}
)

result = response.json()
print(f"Best strategy: {result['best_portfolio']}")
```

### 3. Daily Optimization

```python
# Get optimization suggestions
response = requests.post(
    'http://localhost:5000/api/portfolio/optimize',
    json={'holdings': portfolio}
)

suggestions = response.json()['suggestions']
for suggestion in suggestions:
    print(f"{suggestion['action']} {suggestion['symbol']}: {suggestion['reason']}")
```

---

## Response Fields

### Portfolio Evaluation

| Field | Type | Description |
|-------|------|-------------|
| `total_current_value` | float | Current portfolio value in USD |
| `total_predicted_value` | float | Predicted value in 24 hours |
| `total_change_usd` | float | Predicted change in USD |
| `total_change_percent` | float | Predicted change in percentage |
| `holdings` | array | Detailed breakdown per holding |
| `best_performers` | array | Top 3 predicted performers |
| `worst_performers` | array | Bottom 3 predicted performers |
| `risk_score` | float | Portfolio risk (0-10, higher = riskier) |
| `confidence_score` | float | Average prediction confidence (0-1) |
| `prediction_horizon_hours` | int | Prediction timeframe (24 hours) |

### Risk Score Interpretation

| Score | Risk Level | Description |
|-------|-----------|-------------|
| 0-2 | Low | Very stable, low volatility |
| 2-4 | Moderate | Balanced risk/reward |
| 4-6 | High | Significant volatility expected |
| 6-8 | Very High | Highly volatile portfolio |
| 8-10 | Extreme | Extremely risky |

---

## Error Handling

### Invalid Holdings

```json
{
  "error": {
    "code": "INVALID_PORTFOLIO",
    "message": "No valid holdings in portfolio"
  }
}
```

### Symbol Not Found

```json
{
  "error": {
    "code": "SYMBOL_NOT_FOUND",
    "message": "Cryptocurrency 'XYZ' not found"
  }
}
```

### No Predictions Available

```json
{
  "error": {
    "code": "NO_PREDICTIONS",
    "message": "No predictions available for evaluation"
  }
}
```

---

## Performance

| Operation | Response Time | Notes |
|-----------|---------------|-------|
| Evaluate (cached) | 0.5-1s | Uses cached predictions |
| Evaluate (fresh) | 2-3s | Generates predictions |
| Compare (3 portfolios) | 1-2s | Cached predictions |
| Optimize | 1-2s | Cached predictions |

---

## Limitations

1. **Prediction Horizon**: Fixed at 24 hours
2. **Maximum Holdings**: 50 cryptos per portfolio
3. **Maximum Portfolios**: 10 portfolios for comparison
4. **Prediction Availability**: Requires trained models (100 cryptos)
5. **Cache Dependency**: Best performance with cached predictions

---

## Best Practices

1. **Use Caching**: Set `use_cache: true` for faster responses
2. **Regular Evaluation**: Check portfolio daily for best results
3. **Diversification**: Include 5-10 cryptos for balanced risk
4. **Monitor Risk**: Keep risk_score < 6 for moderate portfolios
5. **Act on Suggestions**: Review optimization suggestions regularly

---

## Integration Example

```javascript
// JavaScript/Node.js example
const axios = require('axios');

async function evaluatePortfolio(holdings) {
  try {
    const response = await axios.post(
      'http://localhost:5000/api/portfolio/evaluate',
      { holdings }
    );
    
    const { data } = response;
    
    console.log(`Portfolio Value: $${data.total_current_value.toFixed(2)}`);
    console.log(`Predicted (24h): $${data.total_predicted_value.toFixed(2)}`);
    console.log(`Expected Change: ${data.total_change_percent.toFixed(2)}%`);
    
    console.log('\nBest Performers:');
    data.best_performers.forEach(p => {
      console.log(`  ${p.symbol}: ${p.predicted_change_percent.toFixed(2)}%`);
    });
    
    return data;
  } catch (error) {
    console.error('Error:', error.response?.data || error.message);
  }
}

// Usage
evaluatePortfolio({
  BTC: 0.5,
  ETH: 2.0,
  SOL: 100
});
```

---

## Summary

The Portfolio API provides a powerful way to use LSTM/GRU predictions in reverse:

✅ **Input**: Your portfolio holdings  
✅ **Output**: Predicted 24-hour performance  
✅ **Bonus**: Risk assessment, optimization suggestions, strategy comparison  

Perfect for portfolio tracking, strategy testing, and investment decisions!

---

**Last Updated:** November 12, 2025  
**Version:** 1.0.0
