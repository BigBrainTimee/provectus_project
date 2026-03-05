"""
Analytics module for extracting insights from telemetry data.

Provides a clean AnalyticsService interface for generating meaningful insights
from the telemetry database. All queries are optimized to use database indexes.
"""

from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import pandas as pd
from src.database import TelemetryDatabase
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AnalyticsService:
    """
    Clean analytics service interface for telemetry data insights.
    
    This class provides a separation between query logic and visualization logic.
    All methods return pandas DataFrames or dictionaries that can be easily
    consumed by the Streamlit dashboard.
    
    All queries are optimized to use the database indexes created in the schema.
    """
    
    def __init__(self, db: TelemetryDatabase):
        """
        Initialize analytics service.
        
        Args:
            db: TelemetryDatabase instance
        """
        self.db = db
    
    # ============================================================================
    # 1. Token Consumption Trends by User Role
    # ============================================================================
    
    def get_token_consumption_by_role(self, start_date: Optional[datetime] = None,
                                      end_date: Optional[datetime] = None) -> pd.DataFrame:
        """
        Get total tokens used per role (practice).
        
        Uses the token_usage table with indexes on practice and date for optimal performance.
        
        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            DataFrame with columns:
            - Practice: Engineering practice name
            - Total Tokens: Sum of input + output tokens
            - Input Tokens: Total input tokens
            - Output Tokens: Total output tokens
            - Cost (USD): Total cost in USD
            - Request Count: Number of API requests
        """
        results = self.db.get_token_usage_by_practice(start_date, end_date)
        
        data = []
        for row in results:
            input_tokens = row[1] or 0
            output_tokens = row[2] or 0
            data.append({
                'Practice': row[0],
                'Total Tokens': input_tokens + output_tokens,
                'Input Tokens': input_tokens,
                'Output Tokens': output_tokens,
                'Cost (USD)': row[3] or 0.0,
                'Request Count': 0  # Will be calculated separately if needed
            })
        
        return pd.DataFrame(data)
    
    def get_average_tokens_per_session_by_role(self, start_date: Optional[datetime] = None,
                                               end_date: Optional[datetime] = None) -> pd.DataFrame:
        """
        Get average tokens per session by role (practice).
        
        Uses sessions table with indexes on user_email and start_time for optimal performance.
        
        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            DataFrame with columns:
            - Practice: Engineering practice name
            - Avg Tokens per Session: Average tokens per session
            - Total Sessions: Number of sessions
            - Total Tokens: Total tokens across all sessions
        """
        cursor = self.db.conn.cursor()
        
        query = """
            SELECT 
                COALESCE(e.practice, 'Unknown') as practice,
                AVG(s.total_tokens) as avg_tokens_per_session,
                COUNT(DISTINCT s.session_id) as total_sessions,
                SUM(s.total_tokens) as total_tokens
            FROM sessions s
            JOIN events e ON s.session_id = e.session_id
            WHERE 1=1
        """
        
        params = []
        if start_date:
            query += " AND s.start_time >= ?"
            params.append(start_date)
        if end_date:
            query += " AND s.start_time <= ?"
            params.append(end_date)
        
        query += """
            GROUP BY e.practice
            ORDER BY avg_tokens_per_session DESC
        """
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        data = []
        for row in results:
            data.append({
                'Practice': row[0],
                'Avg Tokens per Session': round(row[1] or 0, 2),
                'Total Sessions': row[2] or 0,
                'Total Tokens': row[3] or 0
            })
        
        return pd.DataFrame(data)
    
    def get_token_consumption_by_project_type(self, start_date: Optional[datetime] = None,
                                              end_date: Optional[datetime] = None) -> pd.DataFrame:
        """
        Get token consumption by project type (practice).
        
        This is an alias for get_token_consumption_by_role, as practice represents project type.
        Uses token_usage table with indexes for optimal performance.
        
        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            DataFrame with token consumption metrics by practice/project type
        """
        return self.get_token_consumption_by_role(start_date, end_date)
    
    # ============================================================================
    # 2. Peak Usage Times
    # ============================================================================
    
    def get_usage_by_hour_of_day(self, start_date: Optional[datetime] = None,
                                 end_date: Optional[datetime] = None) -> pd.DataFrame:
        """
        Get usage distribution by hour of day.
        
        Uses events table with index on timestamp for optimal performance.
        
        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            DataFrame with columns:
            - Hour: Hour of day (0-23)
            - Event Count: Number of events in that hour
            - Session Count: Number of unique sessions
            - User Count: Number of unique users
            - Cost (USD): Total cost in that hour
            - Avg Events per Session: Average events per session
        """
        cursor = self.db.conn.cursor()
        
        query = """
            SELECT 
                CAST(strftime('%H', timestamp) AS INTEGER) as hour,
                COUNT(*) as event_count,
                COUNT(DISTINCT session_id) as session_count,
                COUNT(DISTINCT user_email) as user_count,
                SUM(CASE WHEN event_type = 'claude_code.api_request' THEN cost_usd ELSE 0 END) as cost_usd
            FROM events
            WHERE 1=1
        """
        
        params = []
        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date)
        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date)
        
        query += """
            GROUP BY hour
            ORDER BY hour
        """
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        data = []
        for row in results:
            event_count = row[1] or 0
            session_count = row[2] or 0
            avg_events_per_session = (event_count / session_count) if session_count > 0 else 0
            
            data.append({
                'Hour': row[0],
                'Event Count': event_count,
                'Session Count': session_count,
                'User Count': row[3] or 0,
                'Cost (USD)': round(row[4] or 0.0, 4),
                'Avg Events per Session': round(avg_events_per_session, 2)
            })
        
        return pd.DataFrame(data)
    
    def get_usage_by_day_of_week(self, start_date: Optional[datetime] = None,
                                 end_date: Optional[datetime] = None) -> pd.DataFrame:
        """
        Get usage distribution by day of week.
        
        Uses events table with index on timestamp for optimal performance.
        
        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            DataFrame with columns:
            - Day of Week: Day name (Monday-Sunday)
            - Day Number: Day number (0=Monday, 6=Sunday)
            - Event Count: Number of events
            - Session Count: Number of unique sessions
            - User Count: Number of unique users
            - Cost (USD): Total cost
        """
        cursor = self.db.conn.cursor()
        
        query = """
            SELECT 
                CAST(strftime('%w', timestamp) AS INTEGER) as day_of_week,
                CASE CAST(strftime('%w', timestamp) AS INTEGER)
                    WHEN 0 THEN 'Sunday'
                    WHEN 1 THEN 'Monday'
                    WHEN 2 THEN 'Tuesday'
                    WHEN 3 THEN 'Wednesday'
                    WHEN 4 THEN 'Thursday'
                    WHEN 5 THEN 'Friday'
                    WHEN 6 THEN 'Saturday'
                END as day_name,
                COUNT(*) as event_count,
                COUNT(DISTINCT session_id) as session_count,
                COUNT(DISTINCT user_email) as user_count,
                SUM(CASE WHEN event_type = 'claude_code.api_request' THEN cost_usd ELSE 0 END) as cost_usd
            FROM events
            WHERE 1=1
        """
        
        params = []
        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date)
        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date)
        
        query += """
            GROUP BY day_of_week, day_name
            ORDER BY day_of_week
        """
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        data = []
        for row in results:
            data.append({
                'Day of Week': row[1],
                'Day Number': row[0],
                'Event Count': row[2] or 0,
                'Session Count': row[3] or 0,
                'User Count': row[4] or 0,
                'Cost (USD)': round(row[5] or 0.0, 4)
            })
        
        return pd.DataFrame(data)
    
    def get_peak_activity_windows(self, start_date: Optional[datetime] = None,
                                 end_date: Optional[datetime] = None,
                                 top_n: int = 5) -> pd.DataFrame:
        """
        Identify peak activity windows (hour ranges with highest activity).
        
        Uses events table with index on timestamp for optimal performance.
        
        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter
            top_n: Number of top windows to return (default: 5)
            
        Returns:
            DataFrame with columns:
            - Hour Range: Time window (e.g., "9-10")
            - Event Count: Number of events in that window
            - Session Count: Number of unique sessions
            - Cost (USD): Total cost
            - Activity Score: Normalized activity score (0-100)
        """
        hour_df = self.get_usage_by_hour_of_day(start_date, end_date)
        
        if hour_df.empty:
            return pd.DataFrame()
        
        # Calculate activity score (normalized)
        max_events = hour_df['Event Count'].max()
        hour_df['Activity Score'] = (hour_df['Event Count'] / max_events * 100).round(2)
        
        # Create hour ranges (current hour to next hour)
        hour_df['Hour Range'] = hour_df['Hour'].astype(str) + '-' + (hour_df['Hour'] + 1).astype(str)
        
        # Sort by activity score and return top N
        top_windows = hour_df.nlargest(top_n, 'Activity Score')[
            ['Hour Range', 'Event Count', 'Session Count', 'Cost (USD)', 'Activity Score']
        ].copy()
        
        return top_windows.reset_index(drop=True)
    
    # ============================================================================
    # 3. Code Generation Behavior Patterns
    # ============================================================================
    
    def get_most_common_event_types(self, start_date: Optional[datetime] = None,
                                    end_date: Optional[datetime] = None,
                                    top_n: int = 10) -> pd.DataFrame:
        """
        Get most common event types.
        
        Uses events table with index on event_type and timestamp for optimal performance.
        
        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter
            top_n: Number of top event types to return (default: 10)
            
        Returns:
            DataFrame with columns:
            - Event Type: Type of event
            - Count: Number of occurrences
            - Percentage: Percentage of total events
            - Avg per Session: Average occurrences per session
        """
        cursor = self.db.conn.cursor()
        
        # Get total event count for percentage calculation
        total_query = """
            SELECT COUNT(*) FROM events WHERE 1=1
        """
        total_params = []
        if start_date:
            total_query += " AND timestamp >= ?"
            total_params.append(start_date)
        if end_date:
            total_query += " AND timestamp <= ?"
            total_params.append(end_date)
        
        cursor.execute(total_query, total_params)
        total_events = cursor.fetchone()[0] or 1
        
        # Get event type counts
        query = """
            SELECT 
                event_type,
                COUNT(*) as count
            FROM events
            WHERE 1=1
        """
        
        params = []
        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date)
        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date)
        
        query += """
            GROUP BY event_type
            ORDER BY count DESC
            LIMIT ?
        """
        params.append(top_n)
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        # Get average per session
        session_query = """
            SELECT COUNT(DISTINCT session_id) FROM events WHERE 1=1
        """
        session_params = []
        if start_date:
            session_query += " AND timestamp >= ?"
            session_params.append(start_date)
        if end_date:
            session_query += " AND timestamp <= ?"
            session_params.append(end_date)
        
        cursor.execute(session_query, session_params)
        total_sessions = cursor.fetchone()[0] or 1
        
        data = []
        for row in results:
            count = row[1] or 0
            data.append({
                'Event Type': row[0],
                'Count': count,
                'Percentage': round((count / total_events * 100), 2),
                'Avg per Session': round((count / total_sessions), 2)
            })
        
        return pd.DataFrame(data)
    
    def get_average_events_per_session(self, start_date: Optional[datetime] = None,
                                       end_date: Optional[datetime] = None) -> Dict:
        """
        Get average events per session statistics.
        
        Uses sessions table with indexes for optimal performance.
        
        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            Dictionary with:
            - avg_events_per_session: Average number of events per session
            - median_events_per_session: Median number of events per session
            - min_events: Minimum events in a session
            - max_events: Maximum events in a session
            - total_sessions: Total number of sessions
        """
        cursor = self.db.conn.cursor()
        
        query = """
            SELECT 
                event_count,
                COUNT(*) as session_count
            FROM sessions
            WHERE 1=1
        """
        
        params = []
        if start_date:
            query += " AND start_time >= ?"
            params.append(start_date)
        if end_date:
            query += " AND start_time <= ?"
            params.append(end_date)
        
        query += " GROUP BY event_count ORDER BY event_count"
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        if not results:
            return {
                'avg_events_per_session': 0,
                'median_events_per_session': 0,
                'min_events': 0,
                'max_events': 0,
                'total_sessions': 0
            }
        
        # Calculate statistics
        event_counts = []
        for row in results:
            event_count = row[0] or 0
            session_count = row[1] or 0
            event_counts.extend([event_count] * session_count)
        
        if not event_counts:
            return {
                'avg_events_per_session': 0,
                'median_events_per_session': 0,
                'min_events': 0,
                'max_events': 0,
                'total_sessions': 0
            }
        
        import numpy as np
        event_counts_array = np.array(event_counts)
        
        return {
            'avg_events_per_session': round(np.mean(event_counts_array), 2),
            'median_events_per_session': round(np.median(event_counts_array), 2),
            'min_events': int(np.min(event_counts_array)),
            'max_events': int(np.max(event_counts_array)),
            'total_sessions': len(event_counts)
        }
    
    def get_most_frequent_tool_usage(self, start_date: Optional[datetime] = None,
                                     end_date: Optional[datetime] = None,
                                     top_n: int = 10) -> pd.DataFrame:
        """
        Get most frequent tool or feature usage.
        
        Uses events table with index on event_type and timestamp for optimal performance.
        
        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter
            top_n: Number of top tools to return (default: 10)
            
        Returns:
            DataFrame with columns:
            - Tool Name: Name of the tool
            - Usage Count: Number of times tool was used
            - Success Count: Number of successful uses
            - Success Rate (%): Percentage of successful uses
            - Avg Duration (ms): Average execution duration
            - Percentage of Total: Percentage of all tool usage
        """
        cursor = self.db.conn.cursor()
        
        # Get total tool usage count
        total_query = """
            SELECT COUNT(*) FROM events
            WHERE event_type = 'claude_code.tool_result'
        """
        total_params = []
        if start_date:
            total_query += " AND timestamp >= ?"
            total_params.append(start_date)
        if end_date:
            total_query += " AND timestamp <= ?"
            total_params.append(end_date)
        
        cursor.execute(total_query, total_params)
        total_tool_usage = cursor.fetchone()[0] or 1
        
        # Get tool usage statistics
        query = """
            SELECT 
                tool_name,
                COUNT(*) as usage_count,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success_count,
                AVG(duration_ms) as avg_duration_ms
            FROM events
            WHERE event_type = 'claude_code.tool_result'
        """
        
        params = []
        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date)
        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date)
        
        query += """
            GROUP BY tool_name
            ORDER BY usage_count DESC
            LIMIT ?
        """
        params.append(top_n)
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        data = []
        for row in results:
            usage_count = row[1] or 0
            success_count = row[2] or 0
            success_rate = (success_count / usage_count * 100) if usage_count > 0 else 0
            
            data.append({
                'Tool Name': row[0] or 'Unknown',
                'Usage Count': usage_count,
                'Success Count': success_count,
                'Success Rate (%)': round(success_rate, 2),
                'Avg Duration (ms)': round(row[3] or 0, 2),
                'Percentage of Total': round((usage_count / total_tool_usage * 100), 2)
            })
        
        return pd.DataFrame(data)
    
    # ============================================================================
    # 4. Session-Level Insights
    # ============================================================================
    
    def get_average_session_duration(self, start_date: Optional[datetime] = None,
                                     end_date: Optional[datetime] = None) -> Dict:
        """
        Get average session duration statistics.
        
        Uses sessions table with indexes on start_time for optimal performance.
        
        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            Dictionary with:
            - avg_duration_minutes: Average session duration in minutes
            - median_duration_minutes: Median session duration in minutes
            - min_duration_minutes: Minimum session duration
            - max_duration_minutes: Maximum session duration
            - total_sessions: Total number of sessions
        """
        cursor = self.db.conn.cursor()
        
        query = """
            SELECT 
                duration_minutes
            FROM sessions
            WHERE duration_minutes IS NOT NULL
        """
        
        params = []
        if start_date:
            query += " AND start_time >= ?"
            params.append(start_date)
        if end_date:
            query += " AND start_time <= ?"
            params.append(end_date)
        
        query += " ORDER BY duration_minutes"
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        if not results:
            return {
                'avg_duration_minutes': 0,
                'median_duration_minutes': 0,
                'min_duration_minutes': 0,
                'max_duration_minutes': 0,
                'total_sessions': 0
            }
        
        durations = [row[0] for row in results if row[0] is not None]
        
        if not durations:
            return {
                'avg_duration_minutes': 0,
                'median_duration_minutes': 0,
                'min_duration_minutes': 0,
                'max_duration_minutes': 0,
                'total_sessions': 0
            }
        
        import numpy as np
        durations_array = np.array(durations)
        
        return {
            'avg_duration_minutes': round(np.mean(durations_array), 2),
            'median_duration_minutes': round(np.median(durations_array), 2),
            'min_duration_minutes': round(np.min(durations_array), 2),
            'max_duration_minutes': round(np.max(durations_array), 2),
            'total_sessions': len(durations)
        }
    
    def get_sessions_per_user(self, start_date: Optional[datetime] = None,
                              end_date: Optional[datetime] = None,
                              top_n: int = 20) -> pd.DataFrame:
        """
        Get sessions per user statistics.
        
        Uses sessions table with index on user_email and start_time for optimal performance.
        
        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter
            top_n: Number of top users to return (default: 20)
            
        Returns:
            DataFrame with columns:
            - User Email: User email address
            - Practice: Engineering practice
            - Level: Seniority level
            - Session Count: Number of sessions
            - Total Events: Total events across all sessions
            - Total Cost (USD): Total cost across all sessions
            - Avg Events per Session: Average events per session
        """
        cursor = self.db.conn.cursor()
        
        query = """
            SELECT 
                s.user_email,
                e.practice,
                e.level,
                COUNT(DISTINCT s.session_id) as session_count,
                SUM(s.event_count) as total_events,
                SUM(s.total_cost_usd) as total_cost
            FROM sessions s
            LEFT JOIN events e ON s.session_id = e.session_id
            WHERE 1=1
        """
        
        params = []
        if start_date:
            query += " AND s.start_time >= ?"
            params.append(start_date)
        if end_date:
            query += " AND s.start_time <= ?"
            params.append(end_date)
        
        query += """
            GROUP BY s.user_email, e.practice, e.level
            ORDER BY session_count DESC
            LIMIT ?
        """
        params.append(top_n)
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        data = []
        for row in results:
            session_count = row[3] or 0
            total_events = row[4] or 0
            avg_events = (total_events / session_count) if session_count > 0 else 0
            
            data.append({
                'User Email': row[0] or 'Unknown',
                'Practice': row[1] or 'Unknown',
                'Level': row[2] or 'Unknown',
                'Session Count': session_count,
                'Total Events': total_events,
                'Total Cost (USD)': round(row[5] or 0.0, 4),
                'Avg Events per Session': round(avg_events, 2)
            })
        
        return pd.DataFrame(data)
    
    def get_most_active_users(self, start_date: Optional[datetime] = None,
                              end_date: Optional[datetime] = None,
                              top_n: int = 20) -> pd.DataFrame:
        """
        Get most active users by total activity.
        
        Uses events table with indexes on user_email and timestamp for optimal performance.
        
        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter
            top_n: Number of top users to return (default: 20)
            
        Returns:
            DataFrame with columns:
            - User Email: User email address
            - Practice: Engineering practice
            - Level: Seniority level
            - Total Events: Total number of events
            - Total Sessions: Number of unique sessions
            - Total Tokens: Total tokens consumed
            - Total Cost (USD): Total cost
            - Activity Score: Normalized activity score (0-100)
        """
        cursor = self.db.conn.cursor()
        
        query = """
            SELECT 
                user_email,
                practice,
                level,
                COUNT(*) as total_events,
                COUNT(DISTINCT session_id) as total_sessions,
                SUM(CASE WHEN event_type = 'claude_code.api_request' 
                    THEN input_tokens + output_tokens ELSE 0 END) as total_tokens,
                SUM(CASE WHEN event_type = 'claude_code.api_request' 
                    THEN cost_usd ELSE 0 END) as total_cost
            FROM events
            WHERE user_email IS NOT NULL AND user_email != ''
        """
        
        params = []
        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date)
        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date)
        
        query += """
            GROUP BY user_email, practice, level
            ORDER BY total_events DESC
            LIMIT ?
        """
        params.append(top_n)
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        if not results:
            return pd.DataFrame()
        
        # Calculate activity score (normalized by max events)
        max_events = max(row[3] or 0 for row in results)
        
        data = []
        for row in results:
            total_events = row[3] or 0
            activity_score = (total_events / max_events * 100) if max_events > 0 else 0
            
            data.append({
                'User Email': row[0] or 'Unknown',
                'Practice': row[1] or 'Unknown',
                'Level': row[2] or 'Unknown',
                'Total Events': total_events,
                'Total Sessions': row[4] or 0,
                'Total Tokens': row[5] or 0,
                'Total Cost (USD)': round(row[6] or 0.0, 4),
                'Activity Score': round(activity_score, 2)
            })
        
        return pd.DataFrame(data)
    
    # ============================================================================
    # Legacy Methods (for backward compatibility)
    # ============================================================================
    
    def get_token_consumption_by_level(self, start_date: Optional[datetime] = None,
                                       end_date: Optional[datetime] = None) -> pd.DataFrame:
        """Get token consumption by seniority level (legacy method)."""
        results = self.db.get_token_usage_by_level(start_date, end_date)
        
        data = []
        for row in results:
            input_tokens = row[1] or 0
            output_tokens = row[2] or 0
            data.append({
                'Level': row[0],
                'Total Tokens': input_tokens + output_tokens,
                'Input Tokens': input_tokens,
                'Output Tokens': output_tokens,
                'Cost (USD)': row[3] or 0.0
            })
        
        return pd.DataFrame(data)
    
    def get_peak_usage_times(self, start_date: Optional[datetime] = None,
                            end_date: Optional[datetime] = None) -> pd.DataFrame:
        """Get peak usage times by hour (legacy method)."""
        return self.get_usage_by_hour_of_day(start_date, end_date)
    
    def get_tool_usage_patterns(self) -> pd.DataFrame:
        """Get tool usage patterns (legacy method)."""
        return self.get_most_frequent_tool_usage()
    
    def get_model_usage_analysis(self) -> pd.DataFrame:
        """Get model usage analysis (legacy method)."""
        results = self.db.get_model_usage_stats()
        
        data = []
        for row in results:
            data.append({
                'Model': row[0] or 'Unknown',
                'Request Count': row[1] or 0,
                'Input Tokens': row[2] or 0,
                'Output Tokens': row[3] or 0,
                'Total Tokens': (row[2] or 0) + (row[3] or 0),
                'Cost (USD)': round(row[4] or 0.0, 4),
                'Avg Duration (ms)': round(row[5] or 0, 2)
            })
        
        return pd.DataFrame(data)
    
    def get_daily_trends(self, start_date: Optional[datetime] = None,
                        end_date: Optional[datetime] = None) -> pd.DataFrame:
        """Get daily usage trends (legacy method)."""
        results = self.db.get_daily_usage_trend(start_date, end_date)
        
        data = []
        for row in results:
            data.append({
                'Date': row[0],
                'Event Count': row[1] or 0,
                'Session Count': row[2] or 0,
                'User Count': row[3] or 0,
                'Cost (USD)': round(row[4] or 0.0, 4)
            })
        
        df = pd.DataFrame(data)
        if not df.empty:
            df['Date'] = pd.to_datetime(df['Date'])
        return df
    
    def get_error_analysis(self) -> pd.DataFrame:
        """Get error analysis (legacy method)."""
        results = self.db.get_error_stats()
        
        data = []
        for row in results:
            data.append({
                'Error Message': row[0] or 'Unknown',
                'Status Code': row[1] or 'Unknown',
                'Error Count': row[2] or 0,
                'Avg Attempt': round(row[3] or 1, 2)
            })
        
        return pd.DataFrame(data)
    
    def get_summary_insights(self, start_date: Optional[datetime] = None,
                            end_date: Optional[datetime] = None) -> Dict:
        """
        Get high-level summary insights (legacy method).
        
        Returns:
            Dictionary with key insights
        """
        cursor = self.db.conn.cursor()
        
        query = """
            SELECT 
                COUNT(*) as total_events,
                COUNT(DISTINCT session_id) as total_sessions,
                COUNT(DISTINCT user_email) as total_users,
                SUM(CASE WHEN event_type = 'claude_code.api_request' THEN cost_usd ELSE 0 END) as total_cost,
                SUM(CASE WHEN event_type = 'claude_code.api_request' THEN input_tokens + output_tokens ELSE 0 END) as total_tokens
            FROM events
            WHERE 1=1
        """
        
        params = []
        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date)
        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date)
        
        cursor.execute(query, params)
        row = cursor.fetchone()
        
        # Get top metrics
        practice_df = self.get_token_consumption_by_role(start_date, end_date)
        top_practice = practice_df.iloc[0]['Practice'] if not practice_df.empty else 'N/A'
        
        hour_df = self.get_usage_by_hour_of_day(start_date, end_date)
        peak_hour = hour_df.loc[hour_df['Event Count'].idxmax(), 'Hour'] if not hour_df.empty else 'N/A'
        
        tool_df = self.get_most_frequent_tool_usage(start_date, end_date)
        top_tool = tool_df.iloc[0]['Tool Name'] if not tool_df.empty else 'N/A'
        
        model_df = self.get_model_usage_analysis()
        top_model = model_df.iloc[0]['Model'] if not model_df.empty else 'N/A'
        
        return {
            'total_events': row[0] or 0,
            'total_sessions': row[1] or 0,
            'total_users': row[2] or 0,
            'total_cost_usd': round(row[3] or 0.0, 4),
            'total_tokens': row[4] or 0,
            'top_practice': top_practice,
            'peak_hour': peak_hour,
            'top_tool': top_tool,
            'top_model': top_model
        }


# Backward compatibility alias
AnalyticsEngine = AnalyticsService
