# Analytics Layer Implementation

This document summarizes the comprehensive analytics implementation according to the assignment requirements.

## ✅ Completed Requirements

### 1. Token Consumption Trends by User Role

#### ✅ Total Tokens Used Per Role
- **Method**: `get_token_consumption_by_role()`
- **Uses**: `token_usage` table with indexes on `practice` and `date`
- **Returns**: DataFrame with Practice, Total Tokens, Input Tokens, Output Tokens, Cost, Request Count
- **Optimization**: Leverages pre-aggregated `token_usage` table for fast queries

#### ✅ Average Tokens Per Session
- **Method**: `get_average_tokens_per_session_by_role()`
- **Uses**: `sessions` table with indexes on `user_email` and `start_time`
- **Returns**: DataFrame with Practice, Avg Tokens per Session, Total Sessions, Total Tokens
- **Optimization**: JOINs sessions with events using indexed columns

#### ✅ Tokens Per Project Type
- **Method**: `get_token_consumption_by_project_type()`
- **Uses**: Alias for `get_token_consumption_by_role()` (practice = project type)
- **Returns**: Same format as token consumption by role
- **Optimization**: Reuses optimized token_usage queries

### 2. Peak Usage Times

#### ✅ Usage Distribution by Hour of Day
- **Method**: `get_usage_by_hour_of_day()`
- **Uses**: `events` table with index on `timestamp`
- **Returns**: DataFrame with Hour, Event Count, Session Count, User Count, Cost, Avg Events per Session
- **Optimization**: Uses `strftime('%H', timestamp)` with timestamp index

#### ✅ Usage Distribution by Day of Week
- **Method**: `get_usage_by_day_of_week()`
- **Uses**: `events` table with index on `timestamp`
- **Returns**: DataFrame with Day of Week, Day Number, Event Count, Session Count, User Count, Cost
- **Optimization**: Uses `strftime('%w', timestamp)` with timestamp index

#### ✅ Peak Activity Windows
- **Method**: `get_peak_activity_windows()`
- **Uses**: Builds on `get_usage_by_hour_of_day()` results
- **Returns**: DataFrame with Hour Range, Event Count, Session Count, Cost, Activity Score
- **Features**: 
  - Identifies top N peak windows
  - Calculates normalized activity score (0-100)
  - Configurable top_n parameter

### 3. Code Generation Behavior Patterns

#### ✅ Most Common Event Types
- **Method**: `get_most_common_event_types()`
- **Uses**: `events` table with index on `event_type` and `timestamp`
- **Returns**: DataFrame with Event Type, Count, Percentage, Avg per Session
- **Features**:
  - Calculates percentage of total events
  - Average occurrences per session
  - Configurable top_n parameter

#### ✅ Average Events Per Session
- **Method**: `get_average_events_per_session()`
- **Uses**: `sessions` table with indexes on `start_time`
- **Returns**: Dictionary with:
  - avg_events_per_session
  - median_events_per_session
  - min_events
  - max_events
  - total_sessions
- **Optimization**: Uses pre-aggregated `event_count` in sessions table

#### ✅ Most Frequent Tool Usage
- **Method**: `get_most_frequent_tool_usage()`
- **Uses**: `events` table with index on `event_type` and `timestamp`
- **Returns**: DataFrame with Tool Name, Usage Count, Success Count, Success Rate (%), Avg Duration, Percentage of Total
- **Features**:
  - Success rate calculation
  - Average execution duration
  - Percentage of total tool usage
  - Configurable top_n parameter

### 4. Session-Level Insights

#### ✅ Average Session Duration
- **Method**: `get_average_session_duration()`
- **Uses**: `sessions` table with index on `start_time`
- **Returns**: Dictionary with:
  - avg_duration_minutes
  - median_duration_minutes
  - min_duration_minutes
  - max_duration_minutes
  - total_sessions
- **Optimization**: Uses pre-calculated `duration_minutes` in sessions table

#### ✅ Sessions Per User
- **Method**: `get_sessions_per_user()`
- **Uses**: `sessions` table with indexes on `user_email` and `start_time`
- **Returns**: DataFrame with User Email, Practice, Level, Session Count, Total Events, Total Cost, Avg Events per Session
- **Optimization**: JOINs sessions with events using indexed columns

#### ✅ Most Active Users
- **Method**: `get_most_active_users()`
- **Uses**: `events` table with indexes on `user_email` and `timestamp`
- **Returns**: DataFrame with User Email, Practice, Level, Total Events, Total Sessions, Total Tokens, Total Cost, Activity Score
- **Features**:
  - Normalized activity score (0-100)
  - Configurable top_n parameter
  - Comprehensive user activity metrics

### 5. Query Optimization

#### Index Usage
All queries are optimized to use the database indexes:

- **Timestamp queries**: Use `idx_events_timestamp` and `idx_sessions_start_time`
- **User queries**: Use `idx_events_user_email` and `idx_sessions_user_email`
- **Practice/Level queries**: Use `idx_events_practice`, `idx_events_level`, `idx_token_usage_practice`
- **Event type queries**: Use `idx_events_event_type`
- **Composite indexes**: Use `idx_events_timestamp_type` for filtered event type queries

#### Performance Optimizations

1. **Pre-aggregated Data**: Token usage queries use `token_usage` table instead of aggregating from events
2. **Session Aggregation**: Session-level metrics use pre-aggregated `sessions` table
3. **Efficient JOINs**: All JOINs use indexed columns
4. **Date Filtering**: Date filters applied early in queries to reduce dataset size
5. **LIMIT Clauses**: Top N queries use LIMIT to reduce result set size

### 6. Clean Analytics Interface

#### AnalyticsService Class
- **Clean Interface**: Single `AnalyticsService` class with well-organized methods
- **Separation of Concerns**: Query logic separated from visualization logic
- **Consistent Return Types**: All methods return pandas DataFrames or dictionaries
- **Comprehensive Docstrings**: Every method has detailed docstrings explaining:
  - Purpose
  - Parameters
  - Return values
  - Column descriptions

#### Method Organization

Methods are organized by category:
1. Token Consumption Trends (3 methods)
2. Peak Usage Times (3 methods)
3. Code Generation Behavior Patterns (3 methods)
4. Session-Level Insights (3 methods)
5. Legacy Methods (for backward compatibility)

#### Return Format

All methods return data in formats optimized for dashboard consumption:

- **DataFrames**: Ready for Streamlit tables and charts
- **Dictionaries**: Ready for metric displays
- **Consistent Column Names**: Standardized naming for easy visualization
- **Proper Data Types**: Numeric types for calculations, strings for labels

## 📊 Analytics Methods Summary

### Token Consumption
1. `get_token_consumption_by_role()` - Total tokens by practice
2. `get_average_tokens_per_session_by_role()` - Avg tokens per session by practice
3. `get_token_consumption_by_project_type()` - Tokens by project type

### Peak Usage
4. `get_usage_by_hour_of_day()` - Hourly usage distribution
5. `get_usage_by_day_of_week()` - Daily usage distribution
6. `get_peak_activity_windows()` - Top peak activity windows

### Behavior Patterns
7. `get_most_common_event_types()` - Most common event types
8. `get_average_events_per_session()` - Average events per session stats
9. `get_most_frequent_tool_usage()` - Most frequent tool usage

### Session Insights
10. `get_average_session_duration()` - Session duration statistics
11. `get_sessions_per_user()` - Sessions per user
12. `get_most_active_users()` - Most active users

### Legacy Methods (Backward Compatibility)
- `get_token_consumption_by_level()` - Tokens by level
- `get_peak_usage_times()` - Peak usage (alias)
- `get_tool_usage_patterns()` - Tool patterns (alias)
- `get_model_usage_analysis()` - Model analysis
- `get_daily_trends()` - Daily trends
- `get_error_analysis()` - Error analysis
- `get_summary_insights()` - Summary insights

## 🎯 Key Features

### Date Filtering
All analytics methods support optional `start_date` and `end_date` parameters for time-based filtering.

### Configurable Top N
Methods that return top items support `top_n` parameter for customizable result sizes.

### Normalized Scores
Activity and usage scores are normalized (0-100) for easy comparison and visualization.

### Comprehensive Statistics
Methods return not just averages, but also medians, min, max, and totals for complete insights.

### Error Handling
All methods handle empty results gracefully, returning empty DataFrames or default dictionaries.

## 📈 Usage Example

```python
from src.database import TelemetryDatabase
from src.analytics import AnalyticsService
from datetime import datetime, timedelta

# Initialize
db = TelemetryDatabase("telemetry.db")
analytics = AnalyticsService(db)

# Get token consumption by role
token_df = analytics.get_token_consumption_by_role()

# Get peak usage times
peak_hours = analytics.get_usage_by_hour_of_day()

# Get most active users
active_users = analytics.get_most_active_users(top_n=10)

# Get session duration stats
duration_stats = analytics.get_average_session_duration()
```

## ✅ Assignment Requirements Met

✅ **Token consumption trends by user role** - 3 methods implemented
✅ **Peak usage times** - 3 methods with hour/day/week analysis
✅ **Code generation behavior patterns** - 3 methods for event and tool analysis
✅ **Session-level insights** - 3 methods for session analytics
✅ **Query optimization** - All queries use database indexes
✅ **Clean analytics interface** - AnalyticsService class with comprehensive docstrings
✅ **Dashboard-ready format** - All methods return pandas DataFrames or dictionaries

The analytics layer is complete and ready for dashboard integration!
