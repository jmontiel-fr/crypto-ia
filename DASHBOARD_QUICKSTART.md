# Dashboard Quick Start Guide

## 🚀 Quick Start (5 Minutes)

### Step 1: Ensure Prerequisites
```bash
# 1. Check if Flask API is running
curl http://localhost:5000/health

# 2. If not running, start it
python run_api.py
```

### Step 2: Start the Dashboard
```bash
# Simple command
python run_dashboard.py

# Or use Streamlit directly
streamlit run dashboard.py
```

### Step 3: Access the Dashboard
Open your browser and go to: **http://localhost:8501**

## 📊 First Time Setup

If you see "No data available" messages:

### 1. Initialize Database (if not done)
```bash
python scripts/init_database.py
```

### 2. Collect Initial Data
1. Go to the **⚙️ Data Collection** page
2. Select **"backward"** mode
3. Choose a start date (e.g., 30 days ago)
4. Click **"▶️ Start Collection"**
5. Wait for collection to complete (may take several minutes)

### 3. View Your Data
Once collection completes:
- **🏠 Market Overview**: See current market status
- **🎯 Top Predictions**: View AI predictions (may need to wait for model to run)
- **📈 Market Tendency**: Analyze market trends

## 🎯 Common Tasks

### View Market Status
1. Click **🏠 Market Overview**
2. See current tendency, top gainers/losers
3. Enable auto-refresh for live updates

### Check Predictions
1. Click **🎯 Top Predictions**
2. Adjust number of predictions shown
3. Explore different chart types
4. Download data as CSV

### Analyze Trends
1. Click **📈 Market Tendency**
2. Select historical period
3. View tendency timeline and metrics
4. Check confidence scores

### Manage Data Collection
1. Click **⚙️ Data Collection**
2. View current status
3. Trigger manual collection
4. Check system information

## 🔧 Troubleshooting

### Dashboard Won't Start
```bash
# Install dependencies
pip install -r requirements.txt

# Try different port
streamlit run dashboard.py --server.port=8502
```

### No Data Displayed
1. Ensure Flask API is running: http://localhost:5000/health
2. Run data collection from the Data Collection page
3. Wait a few minutes for predictions to generate

### Connection Errors
- Check Flask API is running on port 5000
- Verify no firewall blocking localhost
- Restart both API and dashboard

## 📚 Learn More

- **Full Guide**: See `DASHBOARD_GUIDE.md` for comprehensive documentation
- **API Docs**: Check `src/api/API_DOCUMENTATION.md` for API details
- **Implementation**: See `DASHBOARD_IMPLEMENTATION_SUMMARY.md` for technical details

## 💡 Tips

- Use **cached data** for faster loading
- Enable **auto-refresh** only when monitoring active operations
- **Download CSV** from predictions page for offline analysis
- Check **System Information** regularly to verify data freshness
- Run **gap_fill** collection weekly to ensure data completeness

## 🎨 Dashboard Pages

| Page | Purpose | Key Features |
|------|---------|--------------|
| 🏠 Market Overview | Quick market snapshot | Tendency, gainers/losers, statistics |
| 🎯 Top Predictions | AI predictions | Top 20 cryptos, charts, confidence |
| 📈 Market Tendency | Trend analysis | Historical trends, metrics, distribution |
| ⚙️ Data Collection | Admin controls | Status, trigger, system info |

## ⚡ Performance Tips

- Limit predictions to 20 for faster rendering
- Use shorter historical periods (24-72h) for quick analysis
- Enable caching to reduce API calls
- Disable auto-refresh when not needed

## 🆘 Need Help?

1. Check the error message displayed in the dashboard
2. Review `DASHBOARD_GUIDE.md` for detailed troubleshooting
3. Verify all prerequisites are met
4. Check application logs for detailed errors

---

**Ready to explore?** Start the dashboard and navigate through the pages! 🚀
