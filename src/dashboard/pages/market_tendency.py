"""
Market Tendency page for Streamlit dashboard.
Displays current market tendency and historical trends.
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime
import logging

from src.dashboard.utils import (
    APIClient,
    format_percentage,
    get_tendency_emoji,
    get_tendency_color
)

logger = logging.getLogger(__name__)


def create_tendency_timeline(history_df: pd.DataFrame) -> go.Figure:
    """
    Create timeline chart showing tendency changes over time.
    
    Args:
        history_df: DataFrame with historical tendency data
    
    Returns:
        Plotly figure
    """
    # Map tendencies to numeric values for plotting
    tendency_map = {
        'bullish': 2,
        'stable': 1,
        'consolidating': 0,
        'volatile': -1,
        'bearish': -2
    }
    
    history_df['tendency_value'] = history_df['tendency'].map(tendency_map)
    history_df['color'] = history_df['tendency'].apply(get_tendency_color)
    
    fig = go.Figure()
    
    # Add scatter plot with colors
    fig.add_trace(go.Scatter(
        x=history_df['timestamp'],
        y=history_df['tendency_value'],
        mode='lines+markers',
        marker=dict(
            size=10,
            color=history_df['color'],
            line=dict(width=2, color='white')
        ),
        line=dict(width=2, color='#666'),
        text=history_df['tendency'],
        hovertemplate=(
            '<b>%{text}</b><br>' +
            'Time: %{x}<br>' +
            'Confidence: %{customdata:.2f}<br>' +
            '<extra></extra>'
        ),
        customdata=history_df['confidence']
    ))
    
    fig.update_layout(
        title="Market Tendency Timeline",
        xaxis_title="Time",
        yaxis_title="Market Tendency",
        yaxis=dict(
            tickmode='array',
            tickvals=[-2, -1, 0, 1, 2],
            ticktext=['Bearish', 'Volatile', 'Consolidating', 'Stable', 'Bullish']
        ),
        height=400,
        hovermode='closest'
    )
    
    return fig


def create_confidence_timeline(history_df: pd.DataFrame) -> go.Figure:
    """
    Create timeline chart showing confidence scores over time.
    
    Args:
        history_df: DataFrame with historical tendency data
    
    Returns:
        Plotly figure
    """
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=history_df['timestamp'],
        y=history_df['confidence'],
        mode='lines+markers',
        fill='tozeroy',
        marker=dict(size=8, color='#1976d2'),
        line=dict(width=2, color='#1976d2'),
        hovertemplate=(
            'Time: %{x}<br>' +
            'Confidence: %{y:.2f}<br>' +
            '<extra></extra>'
        )
    ))
    
    # Add threshold line
    fig.add_hline(
        y=0.7,
        line_dash="dash",
        line_color="green",
        annotation_text="High Confidence"
    )
    
    fig.add_hline(
        y=0.5,
        line_dash="dash",
        line_color="orange",
        annotation_text="Medium Confidence"
    )
    
    fig.update_layout(
        title="Confidence Score Over Time",
        xaxis_title="Time",
        yaxis_title="Confidence Score",
        yaxis=dict(range=[0, 1]),
        height=400,
        hovermode='x unified'
    )
    
    return fig


def create_tendency_distribution(history_df: pd.DataFrame) -> go.Figure:
    """
    Create pie chart showing distribution of tendencies.
    
    Args:
        history_df: DataFrame with historical tendency data
    
    Returns:
        Plotly figure
    """
    tendency_counts = history_df['tendency'].value_counts()
    
    colors = [get_tendency_color(t) for t in tendency_counts.index]
    
    fig = go.Figure(data=[go.Pie(
        labels=tendency_counts.index,
        values=tendency_counts.values,
        marker=dict(colors=colors),
        hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>'
    )])
    
    fig.update_layout(
        title="Tendency Distribution",
        height=400
    )
    
    return fig


def create_metrics_timeline(history_df: pd.DataFrame) -> go.Figure:
    """
    Create multi-line chart showing key metrics over time.
    
    Args:
        history_df: DataFrame with historical tendency data
    
    Returns:
        Plotly figure
    """
    fig = go.Figure()
    
    # Average change percent
    fig.add_trace(go.Scatter(
        x=history_df['timestamp'],
        y=history_df['avg_change_percent'],
        mode='lines',
        name='Avg Change %',
        line=dict(width=2, color='#1976d2')
    ))
    
    # Volatility index (scaled for visibility)
    fig.add_trace(go.Scatter(
        x=history_df['timestamp'],
        y=history_df['volatility_index'] * 100,
        mode='lines',
        name='Volatility Index (×100)',
        line=dict(width=2, color='#ff6f00')
    ))
    
    # Market cap change
    fig.add_trace(go.Scatter(
        x=history_df['timestamp'],
        y=history_df['market_cap_change'],
        mode='lines',
        name='Market Cap Change %',
        line=dict(width=2, color='#00c853')
    ))
    
    fig.update_layout(
        title="Key Metrics Over Time",
        xaxis_title="Time",
        yaxis_title="Value",
        height=400,
        hovermode='x unified',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    return fig


def show():
    """Display market tendency page."""
    st.markdown('<h1 class="main-header">📈 Market Tendency</h1>', unsafe_allow_html=True)
    
    # Initialize API client
    api_client = APIClient(base_url="http://localhost:5000")
    
    # Controls
    col1, col2, col3 = st.columns([1, 1, 4])
    
    with col1:
        if st.button("🔄 Refresh"):
            st.rerun()
    
    with col2:
        lookback_hours = st.selectbox(
            "Lookback Period",
            [24, 48, 72, 168],
            format_func=lambda x: f"{x}h ({x//24}d)" if x >= 24 else f"{x}h"
        )
    
    # Fetch current tendency
    try:
        with st.spinner("Loading market tendency..."):
            current_data = api_client.get_market_tendency(
                use_cache=True,
                max_age_hours=1,
                lookback_hours=lookback_hours
            )
        
        tendency = current_data.get('tendency', 'unknown')
        confidence = current_data.get('confidence', 0.0)
        metrics = current_data.get('metrics', {})
        
        # Display current tendency
        st.markdown("### 🎯 Current Market Tendency")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            emoji = get_tendency_emoji(tendency)
            st.markdown(
                f"""
                <div style="text-align: center; padding: 1.5rem; background-color: {get_tendency_color(tendency)}20; border-radius: 0.5rem; border: 2px solid {get_tendency_color(tendency)};">
                    <div style="font-size: 4rem;">{emoji}</div>
                    <div style="font-size: 1.8rem; font-weight: bold; color: {get_tendency_color(tendency)};">
                        {tendency.upper()}
                    </div>
                    <div style="font-size: 1rem; color: #666; margin-top: 0.5rem;">
                        Confidence: {confidence:.0%}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
        
        with col2:
            st.metric(
                "Avg Change",
                format_percentage(metrics.get('avg_change_percent', 0.0))
            )
        
        with col3:
            st.metric(
                "Volatility",
                f"{metrics.get('volatility_index', 0.0):.4f}"
            )
        
        with col4:
            st.metric(
                "Market Cap Δ",
                format_percentage(metrics.get('market_cap_change', 0.0))
            )
        
        with col5:
            positive_ratio = metrics.get('positive_ratio', 0.0)
            st.metric(
                "Positive Ratio",
                f"{positive_ratio:.0%}"
            )
        
        # Detailed metrics
        st.markdown("---")
        st.markdown("### 📊 Detailed Metrics")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Positive Cryptos",
                metrics.get('positive_count', 0)
            )
        
        with col2:
            st.metric(
                "Negative Cryptos",
                metrics.get('negative_count', 0)
            )
        
        with col3:
            st.metric(
                "Total Analyzed",
                metrics.get('total_count', 0)
            )
        
        st.markdown("---")
        
        # Historical analysis
        st.markdown("### 📈 Historical Analysis")
        
        # Time range selector
        history_hours = st.selectbox(
            "Historical Period",
            [24, 48, 72, 168, 336, 720],
            index=3,
            format_func=lambda x: f"{x}h ({x//24}d)"
        )
        
        # Fetch historical data
        with st.spinner("Loading historical data..."):
            history_data = api_client.get_tendency_history(hours=history_hours)
        
        tendencies = history_data.get('tendencies', [])
        
        if tendencies:
            # Convert to DataFrame
            history_records = []
            for t in tendencies:
                record = {
                    'timestamp': pd.to_datetime(t['timestamp']),
                    'tendency': t['tendency'],
                    'confidence': t['confidence'],
                    'avg_change_percent': t['metrics']['avg_change_percent'],
                    'volatility_index': t['metrics']['volatility_index'],
                    'market_cap_change': t['metrics']['market_cap_change'],
                    'positive_ratio': t['metrics']['positive_ratio']
                }
                history_records.append(record)
            
            df_history = pd.DataFrame(history_records)
            df_history = df_history.sort_values('timestamp')
            
            # Display charts in tabs
            tab1, tab2, tab3, tab4 = st.tabs([
                "📊 Tendency Timeline",
                "🎯 Confidence",
                "📈 Key Metrics",
                "🥧 Distribution"
            ])
            
            with tab1:
                st.plotly_chart(
                    create_tendency_timeline(df_history),
                    use_container_width=True
                )
                
                # Summary statistics
                st.markdown("#### Summary")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    most_common = df_history['tendency'].mode()[0]
                    st.metric("Most Common", most_common.upper())
                
                with col2:
                    avg_conf = df_history['confidence'].mean()
                    st.metric("Avg Confidence", f"{avg_conf:.2f}")
                
                with col3:
                    changes = (df_history['tendency'] != df_history['tendency'].shift()).sum()
                    st.metric("Tendency Changes", changes)
            
            with tab2:
                st.plotly_chart(
                    create_confidence_timeline(df_history),
                    use_container_width=True
                )
                
                # Confidence statistics
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    high_conf = len(df_history[df_history['confidence'] >= 0.7])
                    st.metric("High Confidence", f"{high_conf}/{len(df_history)}")
                
                with col2:
                    avg_conf = df_history['confidence'].mean()
                    st.metric("Average", f"{avg_conf:.2f}")
                
                with col3:
                    min_conf = df_history['confidence'].min()
                    st.metric("Minimum", f"{min_conf:.2f}")
            
            with tab3:
                st.plotly_chart(
                    create_metrics_timeline(df_history),
                    use_container_width=True
                )
            
            with tab4:
                st.plotly_chart(
                    create_tendency_distribution(df_history),
                    use_container_width=True
                )
        else:
            st.info("No historical data available for the selected period.")
        
        # Metadata
        st.markdown("---")
        timestamp = current_data.get('timestamp', datetime.now().isoformat())
        cached = current_data.get('cached', False)
        st.caption(f"Last updated: {timestamp} | Source: {'Cached' if cached else 'Fresh'}")
    
    except Exception as e:
        logger.error(f"Error loading market tendency: {e}", exc_info=True)
        st.error(f"Failed to load market tendency: {str(e)}")
        st.info("Make sure the Flask API is running on http://localhost:5000")
