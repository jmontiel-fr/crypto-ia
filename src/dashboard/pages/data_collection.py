"""
Data Collection page for Streamlit dashboard.
Admin page for monitoring and controlling data collection.
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta
import logging

from src.dashboard.utils import APIClient

logger = logging.getLogger(__name__)


def create_collection_progress_bar(status_data: dict) -> go.Figure:
    """
    Create progress bar for collection status.
    
    Args:
        status_data: Collection status data
    
    Returns:
        Plotly figure
    """
    is_running = status_data.get('is_running', False)
    
    if not is_running:
        return None
    
    # For now, show indeterminate progress
    # In production, you'd track actual progress
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=50,
        title={'text': "Collection Progress"},
        gauge={
            'axis': {'range': [None, 100]},
            'bar': {'color': "#1976d2"},
            'steps': [
                {'range': [0, 100], 'color': "#e3f2fd"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 90
            }
        }
    ))
    
    fig.update_layout(height=300)
    
    return fig


def show():
    """Display data collection page."""
    st.markdown('<h1 class="main-header">⚙️ Data Collection</h1>', unsafe_allow_html=True)
    
    st.warning("⚠️ Admin Access Required - This page controls data collection operations")
    
    # Initialize API client
    api_client = APIClient(base_url="http://localhost:5000")
    
    # Auto-refresh for status monitoring
    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("🔄 Refresh"):
            st.rerun()
    with col2:
        auto_refresh = st.checkbox("Auto-refresh (5s)", value=False)
    
    if auto_refresh:
        import time
        time.sleep(5)
        st.rerun()
    
    # Fetch collection status
    try:
        with st.spinner("Loading collection status..."):
            status_data = api_client.get_collection_status()
        
        is_running = status_data.get('is_running', False)
        current_operation = status_data.get('current_operation')
        start_time = status_data.get('start_time')
        
        # Display current status
        st.markdown("### 📊 Current Status")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            status_text = "🟢 RUNNING" if is_running else "⚪ IDLE"
            status_color = "#00c853" if is_running else "#757575"
            st.markdown(
                f"""
                <div style="text-align: center; padding: 1rem; background-color: {status_color}20; border-radius: 0.5rem; border: 2px solid {status_color};">
                    <div style="font-size: 1.5rem; font-weight: bold; color: {status_color};">
                        {status_text}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
        
        with col2:
            if current_operation:
                st.metric("Current Operation", current_operation.upper())
            else:
                st.metric("Current Operation", "None")
        
        with col3:
            if start_time:
                elapsed = status_data.get('elapsed_seconds', 0)
                st.metric("Elapsed Time", f"{elapsed}s")
            else:
                st.metric("Elapsed Time", "N/A")
        
        # Show last results if available
        if 'last_results' in status_data:
            st.markdown("---")
            st.markdown("### 📈 Last Collection Results")
            
            results = status_data['last_results']
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Cryptos", results.get('total_cryptos', 0))
            
            with col2:
                st.metric("Successful", results.get('successful', 0))
            
            with col3:
                st.metric("Failed", results.get('failed', 0))
            
            with col4:
                st.metric("Total Records", results.get('total_records', 0))
            
            # Detailed results
            if results.get('details'):
                with st.expander("📋 View Detailed Results"):
                    details_df = pd.DataFrame(results['details'])
                    
                    if not details_df.empty:
                        # Format for display
                        if 'success' in details_df.columns:
                            details_df['Status'] = details_df['success'].apply(
                                lambda x: '✅ Success' if x else '❌ Failed'
                            )
                        
                        st.dataframe(
                            details_df,
                            use_container_width=True,
                            hide_index=True
                        )
        
        st.markdown("---")
        
        # Manual collection trigger
        st.markdown("### 🚀 Manual Collection")
        
        col1, col2 = st.columns(2)
        
        with col1:
            collection_mode = st.selectbox(
                "Collection Mode",
                ["backward", "forward", "gap_fill"],
                help=(
                    "backward: Collect from yesterday to start date\n"
                    "forward: Collect from last recorded date to now\n"
                    "gap_fill: Detect and fill gaps in data"
                )
            )
        
        with col2:
            if collection_mode in ["backward", "gap_fill"]:
                start_date = st.date_input(
                    "Start Date",
                    value=datetime.now() - timedelta(days=30)
                )
            else:
                start_date = None
        
        # Trigger button
        if st.button("▶️ Start Collection", type="primary", disabled=is_running):
            if is_running:
                st.error("Collection is already running. Please wait for it to complete.")
            else:
                try:
                    with st.spinner("Triggering collection..."):
                        start_datetime = datetime.combine(start_date, datetime.min.time()) if start_date else None
                        
                        response = api_client.trigger_collection(
                            mode=collection_mode,
                            start_date=start_datetime
                        )
                    
                    st.success(f"✅ Collection started: {collection_mode}")
                    st.info("Refresh the page to see progress updates")
                    
                    # Auto-refresh after trigger
                    import time
                    time.sleep(2)
                    st.rerun()
                
                except Exception as e:
                    st.error(f"Failed to trigger collection: {str(e)}")
        
        if is_running:
            st.info("⏳ Collection is currently running. The page will auto-refresh if enabled.")
        
        st.markdown("---")
        
        # System information
        st.markdown("### 💻 System Information")
        
        try:
            with st.spinner("Loading system info..."):
                system_info = api_client.get_system_info()
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### System")
                system = system_info.get('system', {})
                st.text(f"Service: {system.get('service', 'N/A')}")
                st.text(f"Version: {system.get('version', 'N/A')}")
                st.text(f"Timestamp: {system.get('timestamp', 'N/A')}")
            
            with col2:
                st.markdown("#### Database")
                database = system_info.get('database', {})
                st.metric("Total Cryptocurrencies", database.get('total_cryptocurrencies', 0))
                st.metric("Total Predictions", database.get('total_predictions', 0))
                st.metric("Total Chat Messages", database.get('total_chat_messages', 0))
                
                latest_price = database.get('latest_price_data')
                if latest_price:
                    st.text(f"Latest Price Data: {latest_price}")
                else:
                    st.text("Latest Price Data: No data")
        
        except Exception as e:
            st.error(f"Failed to load system info: {str(e)}")
        
        st.markdown("---")
        
        # Data coverage information
        st.markdown("### 📅 Data Coverage")
        
        st.info(
            "Data coverage information shows the time range of collected data. "
            "Use gap_fill mode to detect and fill missing data ranges."
        )
        
        # Placeholder for data coverage visualization
        # In production, you'd query the database for actual coverage
        st.markdown("#### Coverage by Cryptocurrency")
        st.caption("This feature requires additional API endpoints to query data coverage.")
        
        # Tips and best practices
        with st.expander("💡 Tips & Best Practices"):
            st.markdown("""
            **Collection Modes:**
            - **Backward**: Use for initial historical data collection. Collects from yesterday back to the start date.
            - **Forward**: Use for regular updates. Collects from the last recorded date to the present.
            - **Gap Fill**: Use to detect and fill missing data ranges in your database.
            
            **Best Practices:**
            - Run backward collection once during initial setup
            - Schedule forward collection to run every 6-24 hours
            - Run gap_fill periodically to ensure data completeness
            - Monitor the collection status to ensure successful completion
            - Check system info to verify data is being collected
            
            **Troubleshooting:**
            - If collection fails, check the API logs for error details
            - Ensure Binance API credentials are configured correctly
            - Verify database connection is working
            - Check network connectivity to Binance API
            """)
    
    except Exception as e:
        logger.error(f"Error loading collection status: {e}", exc_info=True)
        st.error(f"Failed to load collection status: {str(e)}")
        st.info("Make sure the Flask API is running on http://localhost:5000")
