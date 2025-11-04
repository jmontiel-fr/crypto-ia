"""
Streamlit Dashboard for Crypto Market Analysis SaaS.
Main entry point for the multi-page dashboard application.
"""

import streamlit as st
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config.config_loader import load_config

# Page configuration
st.set_page_config(
    page_title="Crypto Market Analysis",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load configuration
try:
    config = load_config()
except Exception as e:
    st.error(f"Failed to load configuration: {e}")
    st.stop()

# Custom CSS for better styling
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .stMetric {
        background-color: #ffffff;
        padding: 1rem;
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    </style>
""", unsafe_allow_html=True)

# Sidebar navigation
st.sidebar.title("📊 Navigation")
st.sidebar.markdown("---")

# Page selection
page = st.sidebar.radio(
    "Select View",
    [
        "🏠 Market Overview",
        "🎯 Top Predictions",
        "📈 Market Tendency",
        "⚙️ Data Collection",
        "🔍 Admin Audit"
    ],
    index=0
)

st.sidebar.markdown("---")
st.sidebar.markdown("### About")
st.sidebar.info(
    "Crypto Market Analysis SaaS provides AI-powered predictions "
    "and market insights for cryptocurrency trading."
)

# Display selected page
if page == "🏠 Market Overview":
    from src.dashboard.pages import market_overview
    market_overview.show()
elif page == "🎯 Top Predictions":
    from src.dashboard.pages import predictions
    predictions.show()
elif page == "📈 Market Tendency":
    from src.dashboard.pages import market_tendency
    market_tendency.show()
elif page == "⚙️ Data Collection":
    from src.dashboard.pages import data_collection
    data_collection.show()
elif page == "🔍 Admin Audit":
    from src.dashboard.pages import admin_audit
    admin_audit.render_admin_audit_page()
