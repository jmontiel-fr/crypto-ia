# Streamlit Dashboard

This directory contains the Streamlit dashboard for the Crypto Market Analysis SaaS.

## Features

### 1. Market Overview (🏠)
- Current market tendency with confidence indicator
- Top gainers and losers (24h)
- Market statistics and key metrics
- Real-time data refresh

### 2. Top Predictions (🎯)
- Top 20 cryptocurrency predictions
- Interactive visualizations:
  - Bar chart of predicted price changes
  - Confidence vs change scatter plot
  - Current vs predicted price comparison
  - Sortable and filterable data table
- Download predictions as CSV
- Configurable display options (limit, caching)

### 3. Market Tendency (📈)
- Current market tendency classification
- Historical tendency analysis
- Multiple visualization types:
  - Tendency timeline
  - Confidence score tracking
  - Key metrics over time
  - Tendency distribution
- Configurable lookback periods

### 4. Data Collection (⚙️)
- Admin page for data collection management
- Real-time collection status monitoring
- Manual collection trigger with modes:
  - Backward: Historical data collection
  - Forward: Update to latest data
  - Gap Fill: Detect and fill missing data
- System information and statistics
- Collection results and detailed logs

## Running the Dashboard

### Prerequisites
- Flask API must be running on http://localhost:5000
- Python environment with required dependencies installed

### Start the Dashboard

From the project root directory:

```bash
streamlit run dashboard.py
```

The dashboard will be available at http://localhost:8501

### Configuration

The dashboard connects to the Flask API at `http://localhost:5000` by default. To change this, modify the `base_url` parameter in the `APIClient` initialization in each page.

## Architecture

```
src/dashboard/
├── __init__.py
├── README.md
├── utils.py              # API client and utility functions
└── pages/
    ├── __init__.py
    ├── market_overview.py    # Market overview page
    ├── predictions.py        # Predictions visualization page
    ├── market_tendency.py    # Market tendency analysis page
    └── data_collection.py    # Data collection admin page
```

## API Integration

The dashboard uses the `APIClient` class from `utils.py` to interact with the Flask API:

- `GET /api/market/overview` - Market overview data
- `GET /api/predictions/top20` - Top predictions
- `GET /api/market/tendency` - Current market tendency
- `GET /api/market/tendency/history` - Historical tendencies
- `POST /api/admin/collect/trigger` - Trigger data collection
- `GET /api/admin/collect/status` - Collection status
- `GET /api/admin/system/info` - System information

## Customization

### Adding New Pages

1. Create a new file in `src/dashboard/pages/`
2. Implement a `show()` function
3. Add the page to the navigation in `dashboard.py`

### Styling

Custom CSS is defined in `dashboard.py`. Modify the `st.markdown()` call with custom styles to change the appearance.

### Charts

The dashboard uses Plotly for interactive charts. Modify the chart creation functions in each page to customize visualizations.

## Troubleshooting

### "Failed to load data" errors
- Ensure the Flask API is running on http://localhost:5000
- Check that the database has been initialized
- Verify data collection has run at least once

### Empty charts or tables
- Run data collection from the Data Collection page
- Check that predictions have been generated
- Verify the API endpoints are returning data

### Auto-refresh not working
- Streamlit's auto-refresh uses `st.rerun()` which may have limitations
- Consider using Streamlit's built-in `st.experimental_rerun()` for better control
- Manual refresh button is always available

## Performance Tips

- Use caching options to reduce API calls
- Limit the number of predictions displayed for faster rendering
- Reduce historical lookback periods for faster chart rendering
- Disable auto-refresh when not needed
