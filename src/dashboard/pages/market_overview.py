"""
Market Overview page for Streamlit dashboard.
Displays key market metrics and overall market status.
"""

import streamlit as st
import plotly.graph_objects as go
from datetime import datetime
import logging

from src.dashboard.utils import (
    APIClient,
    format_currency,
    format_percentage,
    get_tendency_emoji,
    get_tendency_color
)

logger = logging.getLogger(__name__)


def show():
    """Display market overview page."""
    st.markdown('<h1 class="main-header">🏠 Market Overview</h1>', unsafe_allow_html=True)
    
    # Initialize API client
    api_client = APIClient(base_url="http://localhost:5000")
    
    # Add refresh button
    col1, col2, col3 = st.columns([1, 1, 4])
    with col1:
        if st.button("🔄 Refresh Data"):
            st.rerun()
    with col2:
        auto_refresh = st.checkbox("Auto-refresh (30s)", value=False)
    
    if auto_refresh:
        st.empty()
        import time
        time.sleep(30)
        st.rerun()
    
    # Fetch market overview data
    try:
        with st.spinner("Loading market data..."):
            overview_data = api_client.get_market_overview()
        
        # Display market tendency
        st.markdown("### 📊 Current Market Tendency")
        
        tendency_data = overview_data.get('tendency', {})
        tendency = tendency_data.get('tendency', 'unknown')
        confidence = tendency_data.get('confidence', 0.0)
        metrics = tendency_data.get('metrics', {})
        
        # Tendency card
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            emoji = get_tendency_emoji(tendency)
            st.markdown(
                f"""
                <div style="text-align: center; padding: 1rem; background-color: {get_tendency_color(tendency)}20; border-radius: 0.5rem;">
                    <div style="font-size: 3rem;">{emoji}</div>
                    <div style="font-size: 1.5rem; font-weight: bold; color: {get_tendency_color(tendency)};">
                        {tendency.upper()}
                    </div>
                    <div style="font-size: 0.9rem; color: #666;">
                        Confidence: {confidence:.0%}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
        
        with col2:
            st.metric(
                "Avg Price Change",
                format_percentage(metrics.get('avg_change_percent', 0.0)),
                delta=None
            )
        
        with col3:
            st.metric(
                "Volatility Index",
                f"{metrics.get('volatility_index', 0.0):.4f}",
                delta=None
            )
        
        with col4:
            positive_ratio = metrics.get('positive_ratio', 0.0)
            st.metric(
                "Positive Ratio",
                f"{positive_ratio:.0%}",
                delta=None
            )
        
        st.markdown("---")
        
        # Top gainers and losers
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 🚀 Top Gainers (24h)")
            top_gainers = overview_data.get('top_gainers', [])
            
            if top_gainers:
                for gainer in top_gainers:
                    symbol = gainer.get('symbol', 'N/A')
                    change = gainer.get('change_percent', 0.0)
                    
                    st.markdown(
                        f"""
                        <div style="padding: 0.5rem; margin: 0.25rem 0; background-color: #00c85320; border-radius: 0.25rem;">
                            <span style="font-weight: bold;">{symbol}</span>
                            <span style="float: right; color: #00c853; font-weight: bold;">
                                {format_percentage(change)}
                            </span>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
            else:
                st.info("No data available")
        
        with col2:
            st.markdown("### 📉 Top Losers (24h)")
            top_losers = overview_data.get('top_losers', [])
            
            if top_losers:
                for loser in top_losers:
                    symbol = loser.get('symbol', 'N/A')
                    change = loser.get('change_percent', 0.0)
                    
                    st.markdown(
                        f"""
                        <div style="padding: 0.5rem; margin: 0.25rem 0; background-color: #d32f2f20; border-radius: 0.25rem;">
                            <span style="font-weight: bold;">{symbol}</span>
                            <span style="float: right; color: #d32f2f; font-weight: bold;">
                                {format_percentage(change)}
                            </span>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
            else:
                st.info("No data available")
        
        st.markdown("---")
        
        # Market statistics
        st.markdown("### 📈 Market Statistics")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Total Cryptos Analyzed",
                overview_data.get('total_cryptos_analyzed', 0)
            )
        
        with col2:
            st.metric(
                "Positive Cryptos",
                metrics.get('positive_count', 0)
            )
        
        with col3:
            st.metric(
                "Negative Cryptos",
                metrics.get('negative_count', 0)
            )
        
        # Last updated
        timestamp = overview_data.get('timestamp', datetime.now().isoformat())
        st.caption(f"Last updated: {timestamp}")
    
    except Exception as e:
        logger.error(f"Error loading market overview: {e}", exc_info=True)
        st.error(f"Failed to load market data: {str(e)}")
        st.info("Make sure the Flask API is running on http://localhost:5000")
