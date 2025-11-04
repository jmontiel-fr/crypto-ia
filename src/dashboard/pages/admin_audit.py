"""
Admin Audit Dashboard Page.
Provides comprehensive audit log review and monitoring capabilities.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging

from src.data.database import get_session
from src.data.repositories import AuditLogRepository
from src.utils.audit_logger import AuditLogger, AuditEventType, AuditSeverity
from src.dashboard.utils import format_currency, format_number

logger = logging.getLogger(__name__)


def render_admin_audit_page():
    """Render the admin audit dashboard page."""
    st.title("🔍 Admin Audit Dashboard")
    st.markdown("Monitor security events, user activities, and system compliance.")
    
    # Initialize session and repositories
    session = get_session()
    audit_logger = AuditLogger(session)
    audit_repo = AuditLogRepository(session)
    
    try:
        # Sidebar filters
        st.sidebar.header("Filters")
        
        # Date range filter
        col1, col2 = st.sidebar.columns(2)
        with col1:
            start_date = st.date_input(
                "Start Date",
                value=datetime.now().date() - timedelta(days=7),
                max_value=datetime.now().date()
            )
        with col2:
            end_date = st.date_input(
                "End Date",
                value=datetime.now().date(),
                max_value=datetime.now().date()
            )
        
        # Event type filter
        event_types = [e.value for e in AuditEventType]
        selected_event_type = st.sidebar.selectbox(
            "Event Type",
            options=["All"] + event_types,
            index=0
        )
        
        # Severity filter
        severities = [s.value for s in AuditSeverity]
        selected_severity = st.sidebar.selectbox(
            "Severity",
            options=["All"] + severities,
            index=0
        )
        
        # Limit
        limit = st.sidebar.slider("Max Records", 10, 1000, 100)
        
        # Convert dates to datetime
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())
        
        # Fetch audit logs
        audit_logs = audit_logger.get_audit_logs(
            limit=limit,
            event_type=selected_event_type if selected_event_type != "All" else None,
            severity=selected_severity if selected_severity != "All" else None,
            start_date=start_datetime,
            end_date=end_datetime
        )
        
        # Main dashboard tabs
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📊 Overview", 
            "🚨 Security Events", 
            "💬 Chat Queries", 
            "💰 Cost Tracking",
            "🗂️ Raw Logs"
        ])
        
        with tab1:
            render_overview_tab(audit_logs)
        
        with tab2:
            render_security_tab(audit_logs, audit_repo)
        
        with tab3:
            render_chat_queries_tab(audit_logs)
        
        with tab4:
            render_cost_tracking_tab(audit_logs)
        
        with tab5:
            render_raw_logs_tab(audit_logs)
        
        # Cleanup section
        st.sidebar.markdown("---")
        st.sidebar.header("Maintenance")
        
        if st.sidebar.button("🗑️ Cleanup Old Logs"):
            retention_days = st.sidebar.number_input(
                "Retention Days", 
                min_value=30, 
                max_value=365, 
                value=90
            )
            
            if st.sidebar.button("Confirm Cleanup"):
                deleted_count = audit_logger.cleanup_old_logs(retention_days)
                st.sidebar.success(f"Deleted {deleted_count} old audit logs")
    
    except Exception as e:
        st.error(f"Error loading audit dashboard: {e}")
        logger.error(f"Error in admin audit dashboard: {e}", exc_info=True)
    
    finally:
        session.close()


def render_overview_tab(audit_logs: List):
    """Render the overview tab with key metrics."""
    if not audit_logs:
        st.warning("No audit logs found for the selected criteria.")
        return
    
    # Convert to DataFrame for analysis
    df = pd.DataFrame([
        {
            'id': log.id,
            'event_type': log.event_type,
            'severity': log.severity,
            'message': log.message,
            'session_id': log.session_id,
            'ip_address': log.ip_address,
            'endpoint': log.endpoint,
            'method': log.method,
            'status_code': log.status_code,
            'response_time_ms': log.response_time_ms,
            'created_at': log.created_at,
            'additional_data': log.additional_data
        }
        for log in audit_logs
    ])
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Events", len(df))
    
    with col2:
        security_events = df[df['severity'].isin(['high', 'critical'])].shape[0]
        st.metric("Security Events", security_events)
    
    with col3:
        unique_sessions = df['session_id'].nunique()
        st.metric("Unique Sessions", unique_sessions)
    
    with col4:
        avg_response_time = df['response_time_ms'].mean()
        if pd.notna(avg_response_time):
            st.metric("Avg Response Time", f"{avg_response_time:.0f}ms")
        else:
            st.metric("Avg Response Time", "N/A")
    
    # Event type distribution
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Event Types")
        event_counts = df['event_type'].value_counts()
        fig = px.pie(
            values=event_counts.values,
            names=event_counts.index,
            title="Distribution of Event Types"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("Severity Levels")
        severity_counts = df['severity'].value_counts()
        fig = px.bar(
            x=severity_counts.index,
            y=severity_counts.values,
            title="Events by Severity Level",
            color=severity_counts.index,
            color_discrete_map={
                'low': 'green',
                'medium': 'yellow',
                'high': 'orange',
                'critical': 'red'
            }
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Timeline
    st.subheader("Event Timeline")
    df['hour'] = df['created_at'].dt.floor('H')
    timeline = df.groupby(['hour', 'severity']).size().reset_index(name='count')
    
    fig = px.line(
        timeline,
        x='hour',
        y='count',
        color='severity',
        title="Events Over Time by Severity",
        color_discrete_map={
            'low': 'green',
            'medium': 'yellow',
            'high': 'orange',
            'critical': 'red'
        }
    )
    st.plotly_chart(fig, use_container_width=True)


def render_security_tab(audit_logs: List, audit_repo):
    """Render the security events tab."""
    st.subheader("🚨 Security Events")
    
    # Get PII detections
    pii_detections = audit_repo.get_pii_detections(limit=50)
    
    if pii_detections:
        st.subheader("PII Detection Events")
        
        pii_df = pd.DataFrame([
            {
                'Session ID': detection.session_id,
                'Patterns': ', '.join(detection.pii_patterns_detected or []),
                'Question (Sanitized)': detection.question_sanitized[:100] + '...' if detection.question_sanitized and len(detection.question_sanitized) > 100 else detection.question_sanitized,
                'IP Address': detection.ip_address,
                'Timestamp': detection.created_at
            }
            for detection in pii_detections
        ])
        
        st.dataframe(pii_df, use_container_width=True)
        
        # PII patterns analysis
        all_patterns = []
        for detection in pii_detections:
            if detection.pii_patterns_detected:
                all_patterns.extend(detection.pii_patterns_detected)
        
        if all_patterns:
            pattern_counts = pd.Series(all_patterns).value_counts()
            fig = px.bar(
                x=pattern_counts.values,
                y=pattern_counts.index,
                orientation='h',
                title="Most Common PII Patterns Detected"
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No PII detection events found.")
    
    # Get rejected queries
    rejected_queries = audit_repo.get_rejected_queries(limit=50)
    
    if rejected_queries:
        st.subheader("Rejected Queries")
        
        rejected_df = pd.DataFrame([
            {
                'Session ID': query.session_id,
                'Reason': query.rejection_reason,
                'Topic Validation': query.topic_validation_result,
                'IP Address': query.ip_address,
                'Timestamp': query.created_at
            }
            for query in rejected_queries
        ])
        
        st.dataframe(rejected_df, use_container_width=True)
    else:
        st.info("No rejected queries found.")


def render_chat_queries_tab(audit_logs: List):
    """Render the chat queries analysis tab."""
    st.subheader("💬 Chat Query Analysis")
    
    # Filter for chat-related events
    chat_logs = [log for log in audit_logs if log.event_type == 'chat_query_processed']
    
    if not chat_logs:
        st.warning("No chat query logs found.")
        return
    
    # Convert to DataFrame
    df = pd.DataFrame([
        {
            'session_id': log.session_id,
            'response_time_ms': log.response_time_ms,
            'created_at': log.created_at,
            'additional_data': log.additional_data or {}
        }
        for log in chat_logs
    ])
    
    # Extract OpenAI usage data
    df['input_tokens'] = df['additional_data'].apply(lambda x: x.get('input_tokens', 0))
    df['output_tokens'] = df['additional_data'].apply(lambda x: x.get('output_tokens', 0))
    df['total_tokens'] = df['additional_data'].apply(lambda x: x.get('total_tokens', 0))
    df['cost_usd'] = df['additional_data'].apply(lambda x: x.get('cost_usd', 0))
    df['model'] = df['additional_data'].apply(lambda x: x.get('model', 'unknown'))
    
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Queries", len(df))
    
    with col2:
        avg_response_time = df['response_time_ms'].mean()
        st.metric("Avg Response Time", f"{avg_response_time:.0f}ms")
    
    with col3:
        total_tokens = df['total_tokens'].sum()
        st.metric("Total Tokens", format_number(total_tokens))
    
    with col4:
        total_cost = df['cost_usd'].sum()
        st.metric("Total Cost", format_currency(total_cost))
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        # Response time distribution
        fig = px.histogram(
            df,
            x='response_time_ms',
            title="Response Time Distribution",
            nbins=20
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Model usage
        model_counts = df['model'].value_counts()
        fig = px.pie(
            values=model_counts.values,
            names=model_counts.index,
            title="Model Usage Distribution"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Token usage over time
    st.subheader("Token Usage Over Time")
    df['hour'] = df['created_at'].dt.floor('H')
    hourly_tokens = df.groupby('hour')['total_tokens'].sum().reset_index()
    
    fig = px.line(
        hourly_tokens,
        x='hour',
        y='total_tokens',
        title="Token Usage Over Time"
    )
    st.plotly_chart(fig, use_container_width=True)


def render_cost_tracking_tab(audit_logs: List):
    """Render the cost tracking tab."""
    st.subheader("💰 Cost Tracking")
    
    # Filter for chat events with cost data
    chat_logs = [
        log for log in audit_logs 
        if log.event_type == 'chat_query_processed' and log.additional_data
    ]
    
    if not chat_logs:
        st.warning("No cost tracking data found.")
        return
    
    # Extract cost data
    cost_data = []
    for log in chat_logs:
        data = log.additional_data or {}
        if 'cost_usd' in data:
            cost_data.append({
                'timestamp': log.created_at,
                'cost_usd': data.get('cost_usd', 0),
                'input_tokens': data.get('input_tokens', 0),
                'output_tokens': data.get('output_tokens', 0),
                'total_tokens': data.get('total_tokens', 0),
                'model': data.get('model', 'unknown')
            })
    
    if not cost_data:
        st.warning("No cost data available.")
        return
    
    df = pd.DataFrame(cost_data)
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_cost = df['cost_usd'].sum()
        st.metric("Total Cost", format_currency(total_cost))
    
    with col2:
        avg_cost_per_query = df['cost_usd'].mean()
        st.metric("Avg Cost/Query", format_currency(avg_cost_per_query))
    
    with col3:
        total_tokens = df['total_tokens'].sum()
        st.metric("Total Tokens", format_number(total_tokens))
    
    with col4:
        avg_tokens_per_query = df['total_tokens'].mean()
        st.metric("Avg Tokens/Query", f"{avg_tokens_per_query:.0f}")
    
    # Cost over time
    st.subheader("Cost Trends")
    
    # Daily costs
    df['date'] = df['timestamp'].dt.date
    daily_costs = df.groupby('date')['cost_usd'].sum().reset_index()
    
    fig = px.line(
        daily_costs,
        x='date',
        y='cost_usd',
        title="Daily OpenAI Costs"
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Cost by model
    model_costs = df.groupby('model')['cost_usd'].sum().reset_index()
    fig = px.bar(
        model_costs,
        x='model',
        y='cost_usd',
        title="Cost by Model"
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Token efficiency
    st.subheader("Token Efficiency")
    df['cost_per_token'] = df['cost_usd'] / df['total_tokens']
    
    fig = px.scatter(
        df,
        x='total_tokens',
        y='cost_usd',
        color='model',
        title="Cost vs Token Usage",
        hover_data=['timestamp']
    )
    st.plotly_chart(fig, use_container_width=True)


def render_raw_logs_tab(audit_logs: List):
    """Render the raw logs tab."""
    st.subheader("🗂️ Raw Audit Logs")
    
    if not audit_logs:
        st.warning("No audit logs found.")
        return
    
    # Convert to DataFrame for display
    df = pd.DataFrame([
        {
            'ID': log.id,
            'Timestamp': log.created_at,
            'Event Type': log.event_type,
            'Severity': log.severity,
            'Message': log.message[:100] + '...' if len(log.message) > 100 else log.message,
            'Session ID': log.session_id,
            'IP Address': log.ip_address,
            'Endpoint': log.endpoint,
            'Method': log.method,
            'Status Code': log.status_code,
            'Response Time (ms)': log.response_time_ms
        }
        for log in audit_logs
    ])
    
    # Display with filtering
    st.dataframe(df, use_container_width=True)
    
    # Export functionality
    if st.button("📥 Export to CSV"):
        csv = df.to_csv(index=False)
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name=f"audit_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    
    # Detailed view
    st.subheader("Detailed Log View")
    selected_id = st.selectbox(
        "Select log ID for details:",
        options=[log.id for log in audit_logs],
        format_func=lambda x: f"ID {x} - {next(log.event_type for log in audit_logs if log.id == x)}"
    )
    
    if selected_id:
        selected_log = next(log for log in audit_logs if log.id == selected_id)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.json({
                "id": selected_log.id,
                "event_type": selected_log.event_type,
                "severity": selected_log.severity,
                "message": selected_log.message,
                "user_id": selected_log.user_id,
                "session_id": selected_log.session_id,
                "ip_address": selected_log.ip_address,
                "user_agent": selected_log.user_agent,
                "endpoint": selected_log.endpoint,
                "method": selected_log.method,
                "status_code": selected_log.status_code,
                "response_time_ms": selected_log.response_time_ms,
                "created_at": selected_log.created_at.isoformat() if selected_log.created_at else None
            })
        
        with col2:
            if selected_log.additional_data:
                st.subheader("Additional Data")
                st.json(selected_log.additional_data)
            else:
                st.info("No additional data available for this log entry.")


if __name__ == "__main__":
    render_admin_audit_page()