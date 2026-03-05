#!/usr/bin/env python3
"""
Generate Insights Summary Report from Analytics Database.

This script queries the database using AnalyticsService and generates
a concise insights summary report suitable for analytics presentations.

Usage:
    python generate_insights_summary.py [--db PATH] [--output PATH]
"""

import argparse
import os
import sys
from datetime import datetime, timedelta
from src.database import TelemetryDatabase
from src.analytics import AnalyticsService
import logging

logging.basicConfig(level=logging.WARNING)  # Suppress info logs
logger = logging.getLogger(__name__)


def format_number(num):
    """Format number with commas."""
    return f"{num:,}"


def format_percentage(value, total):
    """Format as percentage."""
    if total == 0:
        return "0.0%"
    return f"{(value / total * 100):.1f}%"


def generate_insights_summary(db_path: str = "telemetry.db", output_path: str = None):
    """
    Generate insights summary report from database.
    
    Args:
        db_path: Path to SQLite database
        output_path: Optional path to save report (default: print to stdout)
    """
    try:
        # Initialize database and analytics
        db = TelemetryDatabase(db_path)
        analytics = AnalyticsService(db)
        
        # Get date range from data
        cursor = db.conn.cursor()
        cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM events")
        date_range = cursor.fetchone()
        start_date = datetime.fromisoformat(date_range[0]) if date_range[0] else None
        end_date = datetime.fromisoformat(date_range[1]) if date_range[1] else None
        
        # Generate summary insights
        summary = analytics.get_summary_insights(start_date, end_date)
        
        # Build report
        report_lines = []
        
        # Header
        report_lines.append("=" * 80)
        report_lines.append("CLAUDE CODE ANALYTICS - INSIGHTS SUMMARY")
        report_lines.append("=" * 80)
        report_lines.append("")
        
        if start_date and end_date:
            report_lines.append(f"Analysis Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
            report_lines.append(f"Total Days: {(end_date - start_date).days + 1}")
            report_lines.append("")
        
        # 1. Token Usage by User Role
        report_lines.append("-" * 80)
        report_lines.append("1. TOKEN USAGE BY USER ROLE")
        report_lines.append("-" * 80)
        report_lines.append("")
        
        role_df = analytics.get_token_consumption_by_role(start_date, end_date)
        if not role_df.empty:
            total_tokens_all = role_df['Total Tokens'].sum()
            total_cost_all = role_df['Cost (USD)'].sum()
            
            report_lines.append(f"Total tokens consumed across all roles: {format_number(int(total_tokens_all))}")
            report_lines.append(f"Total cost across all roles: ${total_cost_all:,.2f}")
            report_lines.append("")
            report_lines.append("Token consumption by engineering practice:")
            report_lines.append("")
            
            for idx, row in role_df.iterrows():
                practice = row['Practice']
                tokens = int(row['Total Tokens'])
                cost = row['Cost (USD)']
                percentage = format_percentage(tokens, total_tokens_all)
                
                report_lines.append(f"  • {practice:30} | Tokens: {format_number(tokens):>12} ({percentage:>6}) | Cost: ${cost:>10,.2f}")
            
            # Top role
            top_role = role_df.iloc[0]
            report_lines.append("")
            report_lines.append(f"Key Finding: '{top_role['Practice']}' generates the highest token usage")
            report_lines.append(f"  - Accounts for {format_percentage(int(top_role['Total Tokens']), total_tokens_all)} of total tokens")
            report_lines.append(f"  - Represents ${top_role['Cost (USD)']:,.2f} in costs")
        else:
            report_lines.append("No token usage data available by role.")
        
        report_lines.append("")
        
        # 2. Peak Usage Hours and Activity Patterns
        report_lines.append("-" * 80)
        report_lines.append("2. PEAK USAGE HOURS AND DEVELOPER ACTIVITY PATTERNS")
        report_lines.append("-" * 80)
        report_lines.append("")
        
        hour_df = analytics.get_usage_by_hour_of_day(start_date, end_date)
        if not hour_df.empty:
            # Find peak hour
            peak_hour_row = hour_df.loc[hour_df['Event Count'].idxmax()]
            peak_hour = int(peak_hour_row['Hour'])
            peak_events = int(peak_hour_row['Event Count'])
            
            # Calculate business hours vs off-hours
            business_hours = hour_df[(hour_df['Hour'] >= 9) & (hour_df['Hour'] <= 17)]
            off_hours = hour_df[(hour_df['Hour'] < 9) | (hour_df['Hour'] > 17)]
            
            business_events = int(business_hours['Event Count'].sum()) if not business_hours.empty else 0
            off_hours_events = int(off_hours['Event Count'].sum()) if not off_hours.empty else 0
            total_events_hour = int(hour_df['Event Count'].sum())
            
            report_lines.append(f"Peak Activity Hour: {peak_hour}:00")
            report_lines.append(f"  - {format_number(peak_events)} events during peak hour")
            report_lines.append(f"  - {format_percentage(peak_events, total_events_hour)} of daily events")
            report_lines.append("")
            
            report_lines.append("Activity Distribution:")
            report_lines.append(f"  • Business Hours (9 AM - 5 PM): {format_number(business_events)} events ({format_percentage(business_events, total_events_hour)})")
            report_lines.append(f"  • Off-Hours (before 9 AM, after 5 PM): {format_number(off_hours_events)} events ({format_percentage(off_hours_events, total_events_hour)})")
            report_lines.append("")
            
            # Top 3 hours
            top_hours = hour_df.nlargest(3, 'Event Count')
            report_lines.append("Top 3 Most Active Hours:")
            for idx, row in top_hours.iterrows():
                hour = int(row['Hour'])
                events = int(row['Event Count'])
                sessions = int(row['Session Count'])
                report_lines.append(f"  • {hour:2d}:00 - {format_number(events)} events, {format_number(sessions)} sessions")
            
            # Day of week patterns
            day_df = analytics.get_usage_by_day_of_week(start_date, end_date)
            if not day_df.empty:
                peak_day_row = day_df.loc[day_df['Event Count'].idxmax()]
                peak_day = peak_day_row['Day of Week']
                peak_day_events = int(peak_day_row['Event Count'])
                total_events_day = int(day_df['Event Count'].sum())
                
                report_lines.append("")
                report_lines.append(f"Peak Activity Day: {peak_day}")
                report_lines.append(f"  - {format_number(peak_day_events)} events on {peak_day}")
                report_lines.append(f"  - {format_percentage(peak_day_events, total_events_day)} of weekly events")
        else:
            report_lines.append("No hourly usage data available.")
        
        report_lines.append("")
        
        # 3. Most Common Telemetry Events
        report_lines.append("-" * 80)
        report_lines.append("3. MOST COMMON TELEMETRY EVENTS")
        report_lines.append("-" * 80)
        report_lines.append("")
        
        event_types_df = analytics.get_most_common_event_types(start_date, end_date, top_n=10)
        if not event_types_df.empty:
            total_events = int(event_types_df['Count'].sum())
            
            report_lines.append(f"Total events analyzed: {format_number(total_events)}")
            report_lines.append("")
            report_lines.append("Event type distribution:")
            report_lines.append("")
            
            for idx, row in event_types_df.iterrows():
                event_type = row['Event Type']
                count = int(row['Count'])
                percentage = row['Percentage']
                avg_per_session = row['Avg per Session']
                
                # Clean event type name for display
                display_name = event_type.replace('claude_code.', '').replace('_', ' ').title()
                
                report_lines.append(f"  • {display_name:35} | Count: {format_number(count):>10} ({percentage:>5.1f}%) | Avg/Session: {avg_per_session:>5.1f}")
            
            # Top event
            top_event = event_types_df.iloc[0]
            top_event_name = top_event['Event Type'].replace('claude_code.', '').replace('_', ' ').title()
            report_lines.append("")
            report_lines.append(f"Key Finding: '{top_event_name}' is the most common event type")
            report_lines.append(f"  - Represents {top_event['Percentage']:.1f}% of all events")
            report_lines.append(f"  - Occurs {top_event['Avg per Session']:.1f} times per session on average")
        else:
            report_lines.append("No event type data available.")
        
        report_lines.append("")
        
        # 4. Session Behavior Trends
        report_lines.append("-" * 80)
        report_lines.append("4. SESSION BEHAVIOR TRENDS")
        report_lines.append("-" * 80)
        report_lines.append("")
        
        # Session duration
        duration_stats = analytics.get_average_session_duration(start_date, end_date)
        if duration_stats.get('total_sessions', 0) > 0:
            report_lines.append("Session Duration Statistics:")
            report_lines.append(f"  • Average Duration: {duration_stats.get('avg_duration_minutes', 0):.1f} minutes")
            report_lines.append(f"  • Median Duration: {duration_stats.get('median_duration_minutes', 0):.1f} minutes")
            report_lines.append(f"  • Range: {duration_stats.get('min_duration_minutes', 0):.1f} - {duration_stats.get('max_duration_minutes', 0):.1f} minutes")
            report_lines.append(f"  • Total Sessions: {format_number(duration_stats.get('total_sessions', 0))}")
            report_lines.append("")
        
        # Events per session
        events_per_session = analytics.get_average_events_per_session(start_date, end_date)
        if events_per_session.get('total_sessions', 0) > 0:
            report_lines.append("Events per Session Statistics:")
            report_lines.append(f"  • Average Events: {events_per_session.get('avg_events_per_session', 0):.1f} events")
            report_lines.append(f"  • Median Events: {events_per_session.get('median_events_per_session', 0):.1f} events")
            report_lines.append(f"  • Range: {events_per_session.get('min_events', 0)} - {events_per_session.get('max_events', 0)} events")
            report_lines.append("")
        
        # Most active users
        active_users_df = analytics.get_most_active_users(start_date, end_date, top_n=5)
        if not active_users_df.empty:
            report_lines.append("Top 5 Most Active Users:")
            for idx, row in active_users_df.iterrows():
                email = row['User Email']
                events = int(row['Total Events'])
                sessions = int(row['Total Sessions'])
                practice = row['Practice']
                report_lines.append(f"  • {email:40} | {format_number(events):>8} events | {format_number(sessions):>4} sessions | {practice}")
            report_lines.append("")
        
        # Tool usage patterns
        tool_df = analytics.get_most_frequent_tool_usage(start_date, end_date, top_n=5)
        if not tool_df.empty:
            report_lines.append("Top 5 Most Used Tools:")
            for idx, row in tool_df.iterrows():
                tool = row['Tool Name']
                usage = int(row['Usage Count'])
                success_rate = row['Success Rate (%)']
                report_lines.append(f"  • {tool:30} | Used {format_number(usage):>6} times | Success Rate: {success_rate:>5.1f}%")
            report_lines.append("")
        
        # Summary insights
        report_lines.append("-" * 80)
        report_lines.append("SUMMARY INSIGHTS")
        report_lines.append("-" * 80)
        report_lines.append("")
        
        # Key findings
        if not role_df.empty:
            top_role = role_df.iloc[0]
            report_lines.append(f"• {top_role['Practice']} generates the highest token consumption, accounting for "
                              f"{format_percentage(int(top_role['Total Tokens']), int(role_df['Total Tokens'].sum()))} of total usage.")
        
        if not hour_df.empty:
            peak_hour = int(hour_df.loc[hour_df['Event Count'].idxmax(), 'Hour'])
            report_lines.append(f"• Peak developer activity occurs at {peak_hour}:00, indicating when developers are most engaged with Claude Code.")
        
        if not event_types_df.empty:
            top_event = event_types_df.iloc[0]
            top_event_name = top_event['Event Type'].replace('claude_code.', '').replace('_', ' ').title()
            report_lines.append(f"• {top_event_name} is the most frequent event type, representing {top_event['Percentage']:.1f}% of all telemetry events.")
        
        if duration_stats.get('total_sessions', 0) > 0:
            avg_duration = duration_stats.get('avg_duration_minutes', 0)
            report_lines.append(f"• Average session duration is {avg_duration:.1f} minutes, with {events_per_session.get('avg_events_per_session', 0):.1f} events per session on average.")
        
        report_lines.append("")
        report_lines.append("=" * 80)
        report_lines.append(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("=" * 80)
        
        # Output report
        report_text = "\n".join(report_lines)
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report_text)
            print(f"✅ Insights summary saved to: {output_path}")
        else:
            print(report_text)
        
        db.close()
        
    except FileNotFoundError:
        print(f"❌ Error: Database file not found: {db_path}")
        print("   Please run the data pipeline first: python run_pipeline.py")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error generating insights: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Generate insights summary report from analytics database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate and print to console
  python generate_insights_summary.py
  
  # Save to file
  python generate_insights_summary.py --output insights_report.txt
  
  # Use custom database
  python generate_insights_summary.py --db custom.db --output report.txt
        """
    )
    
    parser.add_argument(
        '--db',
        type=str,
        default='telemetry.db',
        help='Path to SQLite database file (default: telemetry.db)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Output file path (default: print to stdout)'
    )
    
    args = parser.parse_args()
    
    generate_insights_summary(args.db, args.output)


if __name__ == "__main__":
    main()
