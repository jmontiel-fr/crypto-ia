# Streamlit Dashboard Guide

## Overview

The Streamlit dashboard provides a comprehensive web interface for visualizing cryptocurrency market data, predictions, and managing data collection. It connects to the Flask API backend to retrieve and display real-time market insights.

## Features

### 🏠 Market Overview
- **Current Market Tendency**: Visual indicator showing bullish, bearish, volatile, stable, or consolidating market conditions
- **Top Gainers & Losers**: Real-time tracking of best and worst performing cryptocurrencies in the last 24 hours
- **Market Statistics**: Key metrics including average price change, volatility index, and positive ratio
- **Auto-refresh**: Optional automatic data refresh every 30 seconds

### 🎯 Top Predictions
- **Top 20 Predictions**: AI-powered predictions for the best performing cryptocurrencies in the next 24 hours
- **Interactive Visualizations**:
  - Horizontal bar chart showing predicted price changes
  - Scatter plot analyzing confidence vs expected change
  - Grouped bar chart comparing current vs predicted prices
  - Sortable and filterable data table
- **Confidence Analysis**: Distribution of predictions by confidence level (high/medium/low)
- **Export Functionality**: Download predictions as CSV for further analysis
- **Customizable Display**: Adjust number of predictions shown (10-50) and caching options

### 📈 Market Tendency
- **Current Tendency**: Large visual display of current market classification with confidence score
- **Detailed Metrics**: Average change, volatility index, market cap change, and positive ratio
- **Historical Analysis**:
  - Tendency timeline showing market classification changes over time
  - Confidence score tracking with threshold indicators
  - Key metrics evolution (price change, volatility, market cap)
  - Tendency distribution pie chart
- **Flexible Time Ranges**: View historical data from 24 hours to 30 days
- **Summary Statistics**: Most common tendency, average confidence, and number of changes

### ⚙️ Data Collection (Admin)
- **Real-time Status Monitoring**: Track active collection operations
- **Manual Collection Trigger**: Start data collection with three modes:
  - **Backward**: Collect historical data from yesterday to a start date
  - **Forward**: Update from last recorded date to present
  - **Gap Fill**: Detect and fill missing data ranges
- **Collection Results**: View detailed results including success/failure counts and records collected
- **System Information**: Database statistics and service status
- **Best Practices Guide**: Built-in tips for optimal data collection

## Getting Started

### Prerequisites

1. **Flask API Running**: The dashboard requires the Flask API to be running on `http://localhost:5000`
   ```bash
   python run_api.py
   ```

2. **Database Initialized**: Ensure the PostgreSQL database is set up and migrations have run
   ```bash
   python scripts/init_database.py
   ```

3. **Data Collection**: Run at least one data collection cycle to populate the database
   - Use the Data Collection page in the dashboard, or
   - Trigger collection via API

### Starting the Dashboard

**Option 1: Using the run script (Recommended)**
```bash
python run_dashboard.py
```

**Option 2: Direct Streamlit command**
```bash
streamlit run dashboard.py
```

The dashboard will be available at: **http://localhost:8501**

## Usage Guide

### Navigating the Dashboard

1. **Sidebar Navigation**: Use the radio buttons in the left sidebar to switch between pages
2. **Refresh Data**: Each page has a refresh button (🔄) to reload data
3. **Auto-refresh**: Enable auto-refresh on pages that support it for real-time monitoring

### Market Overview Page

1. View the current market tendency at the top
2. Scroll down to see top gainers and losers
3. Check market statistics at the bottom
4. Enable auto-refresh for continuous monitoring

### Predictions Page

1. Select the number of predictions to display (10-50)
2. Choose whether to use cached predictions
3. Explore different visualization tabs:
   - **Bar Chart**: Quick overview of all predictions
   - **Confidence Analysis**: Understand prediction reliability
   - **Price Comparison**: See current vs predicted prices
   - **Data Table**: Sort, filter, and export data
4. Download predictions as CSV for offline analysis

### Market Tendency Page

1. View current market tendency with detailed metrics
2. Select a historical period (24h to 30 days)
3. Explore different analysis tabs:
   - **Tendency Timeline**: See how market classification changed
   - **Confidence**: Track prediction confidence over time
   - **Key Metrics**: Analyze underlying market indicators
   - **Distribution**: Understand tendency frequency
4. Use insights to understand market patterns

### Data Collection Page (Admin)

1. **Monitor Status**: Check if collection is running
2. **View Results**: See results from the last collection run
3. **Trigger Collection**:
   - Select collection mode (backward/forward/gap_fill)
   - Choose start date if applicable
   - Click "Start Collection"
4. **Enable Auto-refresh**: Monitor collection progress in real-time
5. **Check System Info**: Verify database statistics

## Configuration

### API Endpoint

The dashboard connects to the Flask API at `http://localhost:5000` by default. To change this:

1. Open each page file in `src/dashboard/pages/`
2. Modify the `APIClient` initialization:
   ```python
   api_client = APIClient(base_url="http://your-api-url:port")
   ```

### Port Configuration

To run the dashboard on a different port:

```bash
streamlit run dashboard.py --server.port=8502
```

Or modify `run_dashboard.py` to change the default port.

### Styling

Custom CSS is defined in `dashboard.py`. To customize:

1. Open `dashboard.py`
2. Modify the CSS in the `st.markdown()` call
3. Restart the dashboard to see changes

## Troubleshooting

### Dashboard Won't Start

**Error**: `ModuleNotFoundError: No module named 'streamlit'`
- **Solution**: Install dependencies: `pip install -r requirements.txt`

**Error**: `Address already in use`
- **Solution**: Another process is using port 8501. Either stop that process or use a different port:
  ```bash
  streamlit run dashboard.py --server.port=8502
  ```

### No Data Displayed

**Issue**: "Failed to load data" errors
- **Check**: Is the Flask API running? Visit http://localhost:5000/health
- **Check**: Has data collection run? Go to Data Collection page and trigger collection
- **Check**: Is the database initialized? Run `python scripts/init_database.py`

**Issue**: Empty charts or tables
- **Solution**: Run data collection from the Data Collection page
- **Solution**: Wait for predictions to be generated (may take a few minutes after first collection)

### API Connection Errors

**Error**: `Connection refused` or `Failed to connect`
- **Check**: Flask API is running on http://localhost:5000
- **Check**: No firewall blocking localhost connections
- **Check**: API is not configured to listen on 127.0.0.1 only

### Performance Issues

**Issue**: Dashboard is slow or unresponsive
- **Solution**: Reduce the number of predictions displayed
- **Solution**: Use shorter historical lookback periods
- **Solution**: Enable caching options
- **Solution**: Disable auto-refresh when not needed

### Auto-refresh Not Working

**Issue**: Auto-refresh checkbox doesn't update data
- **Note**: Streamlit's rerun mechanism has limitations
- **Workaround**: Use the manual refresh button
- **Alternative**: Refresh the browser page

## Best Practices

### For Regular Users

1. **Start with Market Overview**: Get a quick sense of overall market conditions
2. **Check Predictions**: Review top performers before making decisions
3. **Analyze Trends**: Use Market Tendency page to understand market patterns
4. **Export Data**: Download predictions for offline analysis and record-keeping

### For Administrators

1. **Initial Setup**:
   - Run backward collection with a start date (e.g., 30 days ago)
   - Wait for collection to complete
   - Verify data in System Information

2. **Regular Maintenance**:
   - Schedule forward collection every 6-24 hours
   - Run gap_fill weekly to ensure data completeness
   - Monitor collection status for failures

3. **Monitoring**:
   - Enable auto-refresh on Data Collection page during active collection
   - Check system info regularly to verify data freshness
   - Review collection results for any failures

## Architecture

```
Dashboard Architecture:

┌─────────────────────────────────────┐
│     Streamlit Dashboard (8501)      │
│  ┌───────────────────────────────┐  │
│  │  dashboard.py (Main Entry)    │  │
│  └───────────────┬───────────────┘  │
│                  │                   │
│  ┌───────────────▼───────────────┐  │
│  │  src/dashboard/pages/         │  │
│  │  - market_overview.py         │  │
│  │  - predictions.py             │  │
│  │  - market_tendency.py         │  │
│  │  - data_collection.py         │  │
│  └───────────────┬───────────────┘  │
│                  │                   │
│  ┌───────────────▼───────────────┐  │
│  │  src/dashboard/utils.py       │  │
│  │  - APIClient                  │  │
│  │  - Formatting utilities       │  │
│  └───────────────┬───────────────┘  │
└──────────────────┼───────────────────┘
                   │ HTTP Requests
┌──────────────────▼───────────────────┐
│      Flask API (5000)                │
│  - /api/predictions/top20            │
│  - /api/market/tendency              │
│  - /api/market/overview              │
│  - /api/admin/collect/*              │
└──────────────────┬───────────────────┘
                   │
┌──────────────────▼───────────────────┐
│      PostgreSQL Database             │
│  - Price history                     │
│  - Predictions                       │
│  - Market tendencies                 │
└──────────────────────────────────────┘
```

## API Endpoints Used

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/market/overview` | GET | Market overview data |
| `/api/predictions/top20` | GET | Top cryptocurrency predictions |
| `/api/market/tendency` | GET | Current market tendency |
| `/api/market/tendency/history` | GET | Historical market tendencies |
| `/api/admin/collect/trigger` | POST | Trigger data collection |
| `/api/admin/collect/status` | GET | Collection status |
| `/api/admin/system/info` | GET | System information |

## Development

### Adding New Pages

1. Create a new file in `src/dashboard/pages/your_page.py`
2. Implement a `show()` function:
   ```python
   def show():
       st.markdown('<h1 class="main-header">Your Page</h1>', unsafe_allow_html=True)
       # Your page content
   ```
3. Add to navigation in `dashboard.py`:
   ```python
   elif page == "🆕 Your Page":
       from src.dashboard.pages import your_page
       your_page.show()
   ```

### Customizing Charts

All chart creation functions use Plotly. To customize:

1. Locate the chart function (e.g., `create_predictions_bar_chart`)
2. Modify the Plotly figure configuration
3. Update layout, colors, or data as needed

### Testing

To test the dashboard without the API:

1. Mock the `APIClient` class in `utils.py`
2. Return sample data from mock methods
3. Run the dashboard to verify UI behavior

## Support

For issues or questions:

1. Check this guide for common solutions
2. Review the API documentation
3. Check application logs for error details
4. Verify all prerequisites are met

## Future Enhancements

Potential improvements for the dashboard:

- Real-time WebSocket updates for live data
- User authentication and personalization
- Custom alert configuration
- Portfolio tracking and management
- Advanced filtering and search
- Mobile-responsive design improvements
- Dark mode theme option
- Export to PDF reports
- Comparison tools for multiple cryptocurrencies
- Technical indicator overlays on charts
