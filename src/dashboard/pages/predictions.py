"""
Predictions page for Streamlit dashboard.
Displays top 20 cryptocurrency predictions with interactive charts.
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime
import logging

from src.dashboard.utils import (
    APIClient,
    format_currency,
    format_percentage
)

logger = logging.getLogger(__name__)


def create_predictions_bar_chart(predictions_df: pd.DataFrame) -> go.Figure:
    """
    Create bar chart for predicted price changes.
    
    Args:
        predictions_df: DataFrame with prediction data
    
    Returns:
        Plotly figure
    """
    # Sort by predicted change
    df_sorted = predictions_df.sort_values('predicted_change_percent', ascending=True)
    
    # Color bars based on positive/negative
    colors = ['#00c853' if x > 0 else '#d32f2f' for x in df_sorted['predicted_change_percent']]
    
    fig = go.Figure(data=[
        go.Bar(
            x=df_sorted['predicted_change_percent'],
            y=df_sorted['symbol'],
            orientation='h',
            marker=dict(color=colors),
            text=[f"{x:+.2f}%" for x in df_sorted['predicted_change_percent']],
            textposition='outside',
            hovertemplate=(
                '<b>%{y}</b><br>' +
                'Predicted Change: %{x:.2f}%<br>' +
                '<extra></extra>'
            )
        )
    ])
    
    fig.update_layout(
        title="Predicted Price Changes (Next 24 Hours)",
        xaxis_title="Predicted Change (%)",
        yaxis_title="Cryptocurrency",
        height=600,
        showlegend=False,
        hovermode='closest'
    )
    
    return fig


def create_confidence_scatter(predictions_df: pd.DataFrame) -> go.Figure:
    """
    Create scatter plot of predicted change vs confidence.
    
    Args:
        predictions_df: DataFrame with prediction data
    
    Returns:
        Plotly figure
    """
    fig = px.scatter(
        predictions_df,
        x='predicted_change_percent',
        y='confidence',
        text='symbol',
        size='confidence',
        color='predicted_change_percent',
        color_continuous_scale=['#d32f2f', '#ffd54f', '#00c853'],
        hover_data={
            'symbol': True,
            'predicted_change_percent': ':.2f',
            'confidence': ':.2f',
            'current_price': ':,.2f',
            'predicted_price': ':,.2f'
        }
    )
    
    fig.update_traces(
        textposition='top center',
        marker=dict(line=dict(width=1, color='white'))
    )
    
    fig.update_layout(
        title="Prediction Confidence vs Expected Change",
        xaxis_title="Predicted Change (%)",
        yaxis_title="Confidence Score",
        height=500,
        showlegend=False
    )
    
    return fig


def create_price_comparison_chart(predictions_df: pd.DataFrame) -> go.Figure:
    """
    Create grouped bar chart comparing current vs predicted prices.
    
    Args:
        predictions_df: DataFrame with prediction data
    
    Returns:
        Plotly figure
    """
    # Select top 10 for readability
    df_top = predictions_df.nlargest(10, 'predicted_change_percent')
    
    fig = go.Figure(data=[
        go.Bar(
            name='Current Price',
            x=df_top['symbol'],
            y=df_top['current_price'],
            marker_color='#1976d2',
            text=[format_currency(x) for x in df_top['current_price']],
            textposition='outside'
        ),
        go.Bar(
            name='Predicted Price',
            x=df_top['symbol'],
            y=df_top['predicted_price'],
            marker_color='#00c853',
            text=[format_currency(x) for x in df_top['predicted_price']],
            textposition='outside'
        )
    ])
    
    fig.update_layout(
        title="Current vs Predicted Prices (Top 10 Performers)",
        xaxis_title="Cryptocurrency",
        yaxis_title="Price (USD)",
        barmode='group',
        height=500,
        hovermode='x unified'
    )
    
    return fig


def show():
    """Display predictions page."""
    st.markdown('<h1 class="main-header">🎯 Top Predictions</h1>', unsafe_allow_html=True)
    
    # Initialize API client
    api_client = APIClient(base_url="http://localhost:5000")
    
    # Controls
    col1, col2, col3, col4 = st.columns([1, 1, 1, 3])
    
    with col1:
        if st.button("🔄 Refresh"):
            st.rerun()
    
    with col2:
        limit = st.selectbox("Show Top", [10, 20, 30, 50], index=1)
    
    with col3:
        use_cache = st.checkbox("Use Cache", value=True)
    
    # Fetch predictions
    try:
        with st.spinner("Loading predictions..."):
            data = api_client.get_top_predictions(
                limit=limit,
                use_cache=use_cache,
                max_age_hours=24
            )
        
        predictions = data.get('predictions', [])
        
        if not predictions:
            st.warning("No predictions available. Please ensure data collection has run.")
            return
        
        # Convert to DataFrame
        df = pd.DataFrame(predictions)
        
        # Display summary metrics
        st.markdown("### 📊 Summary")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            avg_change = df['predicted_change_percent'].mean()
            st.metric(
                "Avg Predicted Change",
                format_percentage(avg_change),
                delta=None
            )
        
        with col2:
            max_gain = df['predicted_change_percent'].max()
            st.metric(
                "Highest Gain",
                format_percentage(max_gain),
                delta=None
            )
        
        with col3:
            avg_confidence = df['confidence'].mean()
            st.metric(
                "Avg Confidence",
                f"{avg_confidence:.2f}",
                delta=None
            )
        
        with col4:
            positive_count = len(df[df['predicted_change_percent'] > 0])
            st.metric(
                "Positive Predictions",
                f"{positive_count}/{len(df)}",
                delta=None
            )
        
        st.markdown("---")
        
        # Visualization tabs
        tab1, tab2, tab3, tab4 = st.tabs([
            "📊 Bar Chart",
            "🎯 Confidence Analysis",
            "💰 Price Comparison",
            "📋 Data Table"
        ])
        
        with tab1:
            st.plotly_chart(
                create_predictions_bar_chart(df),
                use_container_width=True
            )
        
        with tab2:
            st.plotly_chart(
                create_confidence_scatter(df),
                use_container_width=True
            )
            
            # Confidence distribution
            st.markdown("#### Confidence Distribution")
            col1, col2, col3 = st.columns(3)
            
            high_conf = len(df[df['confidence'] >= 0.7])
            med_conf = len(df[(df['confidence'] >= 0.5) & (df['confidence'] < 0.7)])
            low_conf = len(df[df['confidence'] < 0.5])
            
            with col1:
                st.metric("High (≥0.7)", high_conf)
            with col2:
                st.metric("Medium (0.5-0.7)", med_conf)
            with col3:
                st.metric("Low (<0.5)", low_conf)
        
        with tab3:
            st.plotly_chart(
                create_price_comparison_chart(df),
                use_container_width=True
            )
        
        with tab4:
            # Filtering and sorting options
            st.markdown("#### Filter & Sort")
            
            col1, col2 = st.columns(2)
            
            with col1:
                sort_by = st.selectbox(
                    "Sort by",
                    [
                        "Predicted Change (High to Low)",
                        "Predicted Change (Low to High)",
                        "Confidence (High to Low)",
                        "Symbol (A-Z)"
                    ]
                )
            
            with col2:
                min_confidence = st.slider(
                    "Min Confidence",
                    0.0, 1.0, 0.0, 0.1
                )
            
            # Apply filters
            df_filtered = df[df['confidence'] >= min_confidence].copy()
            
            # Apply sorting
            if sort_by == "Predicted Change (High to Low)":
                df_filtered = df_filtered.sort_values('predicted_change_percent', ascending=False)
            elif sort_by == "Predicted Change (Low to High)":
                df_filtered = df_filtered.sort_values('predicted_change_percent', ascending=True)
            elif sort_by == "Confidence (High to Low)":
                df_filtered = df_filtered.sort_values('confidence', ascending=False)
            else:  # Symbol A-Z
                df_filtered = df_filtered.sort_values('symbol')
            
            # Format for display
            df_display = df_filtered.copy()
            df_display['current_price'] = df_display['current_price'].apply(format_currency)
            df_display['predicted_price'] = df_display['predicted_price'].apply(format_currency)
            df_display['predicted_change_percent'] = df_display['predicted_change_percent'].apply(
                lambda x: format_percentage(x)
            )
            df_display['confidence'] = df_display['confidence'].apply(lambda x: f"{x:.2f}")
            
            # Rename columns for display
            df_display = df_display.rename(columns={
                'symbol': 'Symbol',
                'name': 'Name',
                'current_price': 'Current Price',
                'predicted_price': 'Predicted Price',
                'predicted_change_percent': 'Change %',
                'confidence': 'Confidence'
            })
            
            st.dataframe(
                df_display,
                use_container_width=True,
                hide_index=True
            )
            
            # Download button
            csv = df_filtered.to_csv(index=False)
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name=f"predictions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        
        # Metadata
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.caption(f"Prediction Time: {data.get('prediction_time', 'N/A')}")
        with col2:
            st.caption(f"Horizon: {data.get('horizon_hours', 24)} hours")
        with col3:
            cached = data.get('cached', False)
            st.caption(f"Source: {'Cached' if cached else 'Fresh'}")
    
    except Exception as e:
        logger.error(f"Error loading predictions: {e}", exc_info=True)
        st.error(f"Failed to load predictions: {str(e)}")
        st.info("Make sure the Flask API is running on http://localhost:5000")
