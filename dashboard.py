"""
Interactive Streamlit dashboard for Claude Code telemetry analytics.

Comprehensive dashboard using AnalyticsService to visualize insights from telemetry data.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Optional
from src.database import TelemetryDatabase
from src.analytics import AnalyticsService
import os

# Page configuration
st.set_page_config(
    page_title="Claude Code Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .section-header {
        font-size: 1.5rem;
        font-weight: bold;
        color: #2c3e50;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    </style>
""", unsafe_allow_html=True)


def get_database():
    """Get database connection (not cached to avoid thread issues)."""
    db_path = os.getenv("DB_PATH", "telemetry.db")
    return TelemetryDatabase(db_path)


def get_analytics_service():
    """Get analytics service (creates new connection per call to avoid thread issues)."""
    # Always create fresh connection to get latest data
    db = get_database()
    return AnalyticsService(db)


def render_kpi_cards(summary: dict):
    """
    Render KPI cards at the top of the dashboard.
    
    Args:
        summary: Dictionary with summary insights
    """
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Total Tokens",
            value=f"{summary.get('total_tokens', 0):,}",
            help="Total tokens consumed across all API requests"
        )
    
    with col2:
        st.metric(
            label="Total Sessions",
            value=f"{summary.get('total_sessions', 0):,}",
            help="Total number of coding sessions"
        )
    
    with col3:
        st.metric(
            label="Total Events",
            value=f"{summary.get('total_events', 0):,}",
            help="Total number of telemetry events"
        )
    
    with col4:
        st.metric(
            label="Total Users",
            value=f"{summary.get('total_users', 0):,}",
            help="Total number of unique users"
        )


def render_overview_section(analytics: AnalyticsService, start_date: Optional[datetime], 
                           end_date: Optional[datetime], summary: dict):
    """Render Overview section with high-level metrics and trends."""
    st.header("📊 Overview")
    st.markdown("High-level metrics and trends across all telemetry data.")
    
    # Additional metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Cost", f"${summary.get('total_cost_usd', 0):,.2f}")
    with col2:
        st.metric("Top Practice", summary.get('top_practice', 'N/A'))
    with col3:
        peak_hour = summary.get('peak_hour', 'N/A')
        st.metric("Peak Hour", f"{peak_hour}:00" if peak_hour != 'N/A' else 'N/A')
    with col4:
        st.metric("Top Tool", summary.get('top_tool', 'N/A'))
    
    # Daily trends
    st.subheader("Daily Usage Trends")
    daily_df = analytics.get_daily_trends(start_date, end_date)
    
    if not daily_df.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            fig = px.line(
                daily_df,
                x='Date',
                y='Event Count',
                title='Daily Event Count',
                labels={'Event Count': 'Events', 'Date': 'Date'},
                markers=True
            )
            fig.update_layout(height=400, hovermode='x unified')
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            fig = px.line(
                daily_df,
                x='Date',
                y='Cost (USD)',
                title='Daily Cost Trend',
                labels={'Cost (USD)': 'Cost ($)', 'Date': 'Date'},
                markers=True
            )
            fig.update_layout(height=400, hovermode='x unified')
            st.plotly_chart(fig, use_container_width=True)
        
        # Session and user trends
        col1, col2 = st.columns(2)
        
        with col1:
            fig = px.line(
                daily_df,
                x='Date',
                y='Session Count',
                title='Daily Session Count',
                labels={'Session Count': 'Sessions', 'Date': 'Date'},
                markers=True
            )
            fig.update_layout(height=400, hovermode='x unified')
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            fig = px.line(
                daily_df,
                x='Date',
                y='User Count',
                title='Daily Active Users',
                labels={'User Count': 'Users', 'Date': 'Date'},
                markers=True
            )
            fig.update_layout(height=400, hovermode='x unified')
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data available for the selected date range.")


def render_token_usage_section(analytics: AnalyticsService, start_date: Optional[datetime], 
                               end_date: Optional[datetime], top_n: int):
    """Render Token Usage Analytics section."""
    st.header("💰 Token Usage Analytics")
    st.markdown("Analyze token consumption patterns by role, project type, and session metrics.")
    
    # Token consumption by role
    st.subheader("Token Consumption by User Role")
    role_df = analytics.get_token_consumption_by_role(start_date, end_date)
    
    if not role_df.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            fig = px.bar(
                role_df,
                x='Practice',
                y='Total Tokens',
                title='Total Tokens by Engineering Practice',
                labels={'Total Tokens': 'Total Tokens', 'Practice': 'Practice'},
                color='Total Tokens',
                color_continuous_scale='Blues'
            )
            fig.update_layout(height=400, xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            fig = px.bar(
                role_df,
                x='Practice',
                y='Cost (USD)',
                title='Cost by Engineering Practice',
                labels={'Cost (USD)': 'Cost ($)', 'Practice': 'Practice'},
                color='Cost (USD)',
                color_continuous_scale='Reds'
            )
            fig.update_layout(height=400, xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
        
        # Token breakdown
        col1, col2 = st.columns(2)
        
        with col1:
            fig = px.bar(
                role_df,
                x='Practice',
                y=['Input Tokens', 'Output Tokens'],
                title='Input vs Output Tokens by Practice',
                labels={'value': 'Tokens', 'Practice': 'Practice'},
                barmode='group'
            )
            fig.update_layout(height=400, xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.dataframe(role_df, use_container_width=True)
    
    # Average tokens per session by role
    st.subheader("Average Tokens per Session by Role")
    avg_tokens_df = analytics.get_average_tokens_per_session_by_role(start_date, end_date)
    
    if not avg_tokens_df.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            fig = px.bar(
                avg_tokens_df,
                x='Practice',
                y='Avg Tokens per Session',
                title='Average Tokens per Session by Practice',
                labels={'Avg Tokens per Session': 'Avg Tokens/Session', 'Practice': 'Practice'},
                color='Avg Tokens per Session',
                color_continuous_scale='Greens'
            )
            fig.update_layout(height=400, xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.dataframe(avg_tokens_df, use_container_width=True)
    
    # Token consumption by project type (same as role, but with different visualization)
    st.subheader("Token Consumption by Project Type")
    project_df = analytics.get_token_consumption_by_project_type(start_date, end_date)
    
    if not project_df.empty:
        fig = px.pie(
            project_df,
            values='Total Tokens',
            names='Practice',
            title='Token Distribution by Project Type',
            hole=0.4
        )
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)


def render_usage_patterns_section(analytics: AnalyticsService, start_date: Optional[datetime], 
                                  end_date: Optional[datetime], top_n: int):
    """Render Usage Patterns section."""
    st.header("⏰ Usage Patterns")
    st.markdown("Analyze usage patterns by time and event types.")
    
    # Usage by hour of day
    st.subheader("Usage Distribution by Hour of Day")
    hour_df = analytics.get_usage_by_hour_of_day(start_date, end_date)
    
    if not hour_df.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            fig = px.bar(
                hour_df,
                x='Hour',
                y='Event Count',
                title='Events by Hour of Day',
                labels={'Event Count': 'Event Count', 'Hour': 'Hour'},
                color='Event Count',
                color_continuous_scale='Viridis'
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            fig = px.bar(
                hour_df,
                x='Hour',
                y='Cost (USD)',
                title='Cost by Hour of Day',
                labels={'Cost (USD)': 'Cost ($)', 'Hour': 'Hour'},
                color='Cost (USD)',
                color_continuous_scale='Plasma'
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        # Additional hour metrics
        col1, col2 = st.columns(2)
        
        with col1:
            fig = px.line(
                hour_df,
                x='Hour',
                y='Session Count',
                title='Sessions by Hour of Day',
                labels={'Session Count': 'Sessions', 'Hour': 'Hour'},
                markers=True
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            fig = px.line(
                hour_df,
                x='Hour',
                y='Avg Events per Session',
                title='Average Events per Session by Hour',
                labels={'Avg Events per Session': 'Avg Events/Session', 'Hour': 'Hour'},
                markers=True
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
    
    # Usage by day of week
    st.subheader("Usage Distribution by Day of Week")
    day_df = analytics.get_usage_by_day_of_week(start_date, end_date)
    
    if not day_df.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            fig = px.bar(
                day_df,
                x='Day of Week',
                y='Event Count',
                title='Events by Day of Week',
                labels={'Event Count': 'Event Count', 'Day of Week': 'Day'},
                color='Event Count',
                color_continuous_scale='Cividis'
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            fig = px.bar(
                day_df,
                x='Day of Week',
                y='Cost (USD)',
                title='Cost by Day of Week',
                labels={'Cost (USD)': 'Cost ($)', 'Day of Week': 'Day'},
                color='Cost (USD)',
                color_continuous_scale='Inferno'
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
    
    # Peak activity windows
    st.subheader("Peak Activity Windows")
    peak_windows_df = analytics.get_peak_activity_windows(start_date, end_date, top_n=top_n)
    
    if not peak_windows_df.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            fig = px.bar(
                peak_windows_df,
                x='Hour Range',
                y='Activity Score',
                title=f'Top {top_n} Peak Activity Windows',
                labels={'Activity Score': 'Activity Score (0-100)', 'Hour Range': 'Hour Range'},
                color='Activity Score',
                color_continuous_scale='Turbo'
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.dataframe(peak_windows_df, use_container_width=True)
    
    # Most common event types
    st.subheader("Most Common Event Types")
    event_types_df = analytics.get_most_common_event_types(start_date, end_date, top_n=top_n)
    
    if not event_types_df.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            fig = px.bar(
                event_types_df,
                x='Event Type',
                y='Count',
                title=f'Top {top_n} Event Types',
                labels={'Count': 'Count', 'Event Type': 'Event Type'},
                color='Count',
                color_continuous_scale='Blues'
            )
            fig.update_layout(height=400, xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            fig = px.pie(
                event_types_df,
                values='Count',
                names='Event Type',
                title=f'Event Type Distribution (Top {top_n})',
                hole=0.3
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        st.dataframe(event_types_df, use_container_width=True)


def render_session_insights_section(analytics: AnalyticsService, start_date: Optional[datetime], 
                                   end_date: Optional[datetime]):
    """Render Session Insights section."""
    st.header("📈 Session Insights")
    st.markdown("Analyze session-level metrics and patterns.")
    
    # Average session duration
    st.subheader("Average Session Duration")
    duration_stats = analytics.get_average_session_duration(start_date, end_date)
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Avg Duration", f"{duration_stats.get('avg_duration_minutes', 0):.1f} min")
    with col2:
        st.metric("Median Duration", f"{duration_stats.get('median_duration_minutes', 0):.1f} min")
    with col3:
        st.metric("Min Duration", f"{duration_stats.get('min_duration_minutes', 0):.1f} min")
    with col4:
        st.metric("Max Duration", f"{duration_stats.get('max_duration_minutes', 0):.1f} min")
    with col5:
        st.metric("Total Sessions", f"{duration_stats.get('total_sessions', 0):,}")
    
    # Average events per session
    st.subheader("Average Events per Session")
    events_per_session = analytics.get_average_events_per_session(start_date, end_date)
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Avg Events", f"{events_per_session.get('avg_events_per_session', 0):.1f}")
    with col2:
        st.metric("Median Events", f"{events_per_session.get('median_events_per_session', 0):.1f}")
    with col3:
        st.metric("Min Events", f"{events_per_session.get('min_events', 0)}")
    with col4:
        st.metric("Max Events", f"{events_per_session.get('max_events', 0)}")
    with col5:
        st.metric("Total Sessions", f"{events_per_session.get('total_sessions', 0):,}")
    
    # Session activity distribution
    st.subheader("Session Activity Distribution")
    sessions_per_user_df = analytics.get_sessions_per_user(start_date, end_date, top_n=20)
    
    if not sessions_per_user_df.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            fig = px.histogram(
                sessions_per_user_df,
                x='Session Count',
                title='Distribution of Sessions per User',
                labels={'Session Count': 'Sessions per User', 'count': 'Number of Users'},
                nbins=20
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            fig = px.scatter(
                sessions_per_user_df.head(20),
                x='Session Count',
                y='Total Events',
                size='Total Cost (USD)',
                color='Practice',
                title='Sessions vs Events (Top 20 Users)',
                labels={'Session Count': 'Sessions', 'Total Events': 'Total Events'},
                hover_data=['User Email', 'Level']
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)


def render_user_activity_section(analytics: AnalyticsService, start_date: Optional[datetime], 
                                end_date: Optional[datetime], top_n: int):
    """Render User Activity section."""
    st.header("👥 User Activity")
    st.markdown("Analyze user engagement and activity patterns.")
    
    # Most active users
    st.subheader(f"Most Active Users (Top {top_n})")
    active_users_df = analytics.get_most_active_users(start_date, end_date, top_n=top_n)
    
    if not active_users_df.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            fig = px.bar(
                active_users_df,
                x='User Email',
                y='Total Events',
                title=f'Top {top_n} Most Active Users by Events',
                labels={'Total Events': 'Total Events', 'User Email': 'User'},
                color='Activity Score',
                color_continuous_scale='Viridis'
            )
            fig.update_layout(height=500, xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            fig = px.scatter(
                active_users_df,
                x='Total Sessions',
                y='Total Events',
                size='Total Cost (USD)',
                color='Practice',
                title='User Activity: Sessions vs Events',
                labels={'Total Sessions': 'Sessions', 'Total Events': 'Events'},
                hover_data=['User Email', 'Level', 'Activity Score']
            )
            fig.update_layout(height=500)
            st.plotly_chart(fig, use_container_width=True)
        
        st.dataframe(active_users_df, use_container_width=True)
    
    # Sessions per user
    st.subheader("Sessions per User")
    sessions_per_user_df = analytics.get_sessions_per_user(start_date, end_date, top_n=top_n)
    
    if not sessions_per_user_df.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            fig = px.bar(
                sessions_per_user_df.head(top_n),
                x='User Email',
                y='Session Count',
                title=f'Top {top_n} Users by Session Count',
                labels={'Session Count': 'Sessions', 'User Email': 'User'},
                color='Session Count',
                color_continuous_scale='Blues'
            )
            fig.update_layout(height=500, xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            fig = px.bar(
                sessions_per_user_df.head(top_n),
                x='User Email',
                y='Avg Events per Session',
                title=f'Average Events per Session (Top {top_n})',
                labels={'Avg Events per Session': 'Avg Events/Session', 'User Email': 'User'},
                color='Avg Events per Session',
                color_continuous_scale='Greens'
            )
            fig.update_layout(height=500, xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
        
        st.dataframe(sessions_per_user_df, use_container_width=True)


def main():
    """Main dashboard function."""
    st.markdown('<h1 class="main-header">📊 Claude Code Analytics Platform</h1>', unsafe_allow_html=True)
    
    # Initialize database and analytics
    try:
        analytics = get_analytics_service()
        db = get_database()
    except Exception as e:
        st.error(f"Failed to connect to database: {str(e)}")
        st.info("Please ensure you have processed the telemetry data first.")
        st.info("Run: `python process_data.py --telemetry output/telemetry_logs.jsonl --employees output/employees.csv`")
        return
    
    # Get actual data date range from database
    try:
        cursor = db.conn.cursor()
        cursor.execute("SELECT MIN(timestamp) as min_date, MAX(timestamp) as max_date FROM events")
        result = cursor.fetchone()
        if result and result[0] and result[1]:
            # Parse timestamp strings to datetime, then to date
            try:
                # Handle different timestamp formats
                min_str = str(result[0])
                max_str = str(result[1])
                
                # Try parsing with common formats
                for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%S.%f']:
                    try:
                        data_min_date = datetime.strptime(min_str.split('.')[0], fmt.split('.')[0])
                        data_max_date = datetime.strptime(max_str.split('.')[0], fmt.split('.')[0])
                        data_min_date_only = data_min_date.date()
                        data_max_date_only = data_max_date.date()
                        break
                    except:
                        continue
                else:
                    # If all parsing fails, use wide default
                    data_min_date_only = datetime.now().date() - timedelta(days=90)
                    data_max_date_only = datetime.now().date()
            except:
                # Fallback parsing
                data_min_date_only = datetime.now().date() - timedelta(days=90)
                data_max_date_only = datetime.now().date()
        else:
            data_min_date_only = datetime.now().date() - timedelta(days=90)
            data_max_date_only = datetime.now().date()
    except Exception as e:
        # Fallback to wide default range if query fails
        data_min_date_only = datetime.now().date() - timedelta(days=90)
        data_max_date_only = datetime.now().date()
    
    # Sidebar filters and controls
    st.sidebar.header("⚙️ Dashboard Controls")
    
    # Refresh button
    if st.sidebar.button("🔄 Refresh Data", help="Reload data from database"):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.rerun()
    
    # Date range filter - default to all available data
    st.sidebar.subheader("📅 Date Range")
    date_range = st.sidebar.date_input(
        "Select Date Range",
        value=(data_min_date_only, data_max_date_only),
        min_value=data_min_date_only,
        max_value=data_max_date_only,
        help="Filter data by date range (defaults to all available data)"
    )
    
    start_date = datetime.combine(date_range[0], datetime.min.time()) if len(date_range) > 0 else None
    end_date = datetime.combine(date_range[1], datetime.max.time()) if len(date_range) > 1 else None
    
    # Top N selector
    st.sidebar.subheader("📊 Display Options")
    top_n = st.sidebar.slider(
        "Top N Results",
        min_value=5,
        max_value=50,
        value=10,
        step=5,
        help="Number of top results to display in charts"
    )
    
    # Get summary insights
    try:
        summary = analytics.get_summary_insights(start_date, end_date)
    except Exception as e:
        st.error(f"Error loading summary: {str(e)}")
        return
    
    # KPI Cards at the top
    render_kpi_cards(summary)
    
    # Main tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Overview",
        "💰 Token Usage",
        "⏰ Usage Patterns",
        "📈 Session Insights",
        "👥 User Activity"
    ])
    
    # Tab 1: Overview
    with tab1:
        render_overview_section(analytics, start_date, end_date, summary)
    
    # Tab 2: Token Usage Analytics
    with tab2:
        render_token_usage_section(analytics, start_date, end_date, top_n)
    
    # Tab 3: Usage Patterns
    with tab3:
        render_usage_patterns_section(analytics, start_date, end_date, top_n)
    
    # Tab 4: Session Insights
    with tab4:
        render_session_insights_section(analytics, start_date, end_date)
    
    # Tab 5: User Activity
    with tab5:
        render_user_activity_section(analytics, start_date, end_date, top_n)
    
    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: #666; padding: 1rem;'>"
        "Claude Code Analytics Platform | Built with Streamlit & Plotly"
        "</div>",
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
