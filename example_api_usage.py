"""
Example script demonstrating API usage.

This script shows how to interact with the REST API programmatically.
"""

import requests
import json
from datetime import datetime, timedelta


BASE_URL = "http://localhost:5000/api"


def print_section(title):
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def get_summary():
    """Get summary insights."""
    print_section("Summary Insights")
    
    response = requests.get(f"{BASE_URL}/summary")
    if response.status_code == 200:
        data = response.json()
        print(f"Total Events: {data.get('total_events', 0):,}")
        print(f"Total Sessions: {data.get('total_sessions', 0):,}")
        print(f"Total Users: {data.get('total_users', 0):,}")
        print(f"Total Cost: ${data.get('total_cost_usd', 0):.2f}")
        print(f"Total Tokens: {data.get('total_tokens', 0):,}")
        print(f"Top Practice: {data.get('top_practice', 'N/A')}")
        print(f"Peak Hour: {data.get('peak_hour', 'N/A')}:00")
    else:
        print(f"Error: {response.status_code} - {response.text}")


def get_token_usage_by_practice():
    """Get token usage by practice."""
    print_section("Token Usage by Practice")
    
    response = requests.get(f"{BASE_URL}/token-usage/practice")
    if response.status_code == 200:
        practices = response.json()
        for practice in practices:
            print(f"{practice['Practice']:30} | "
                  f"Tokens: {practice['Total Tokens']:>10,} | "
                  f"Cost: ${practice['Cost (USD)']:>8.2f}")
    else:
        print(f"Error: {response.status_code} - {response.text}")


def get_peak_usage():
    """Get peak usage times."""
    print_section("Peak Usage by Hour")
    
    response = requests.get(f"{BASE_URL}/peak-usage")
    if response.status_code == 200:
        hours = response.json()
        for hour_data in hours:
            hour = hour_data['Hour']
            count = hour_data['Event Count']
            cost = hour_data['Cost (USD)']
            bar = "█" * (count // 10)  # Simple bar chart
            print(f"{hour:2d}:00 | {bar:50} | Events: {count:>6,} | Cost: ${cost:>6.2f}")
    else:
        print(f"Error: {response.status_code} - {response.text}")


def get_tool_usage():
    """Get tool usage statistics."""
    print_section("Top 10 Tools by Usage")
    
    response = requests.get(f"{BASE_URL}/tools")
    if response.status_code == 200:
        tools = response.json()
        for tool in tools[:10]:
            print(f"{tool['Tool Name']:20} | "
                  f"Usage: {tool['Usage Count']:>6,} | "
                  f"Success Rate: {tool['Success Rate (%)']:>5.1f}%")
    else:
        print(f"Error: {response.status_code} - {response.text}")


def get_model_usage():
    """Get model usage statistics."""
    print_section("Model Usage Statistics")
    
    response = requests.get(f"{BASE_URL}/models")
    if response.status_code == 200:
        models = response.json()
        for model in models:
            print(f"{model['Model']:40} | "
                  f"Requests: {model['Request Count']:>6,} | "
                  f"Cost: ${model['Cost (USD)']:>8.4f}")
    else:
        print(f"Error: {response.status_code} - {response.text}")


def get_daily_trends():
    """Get daily trends."""
    print_section("Daily Trends (Last 7 Days)")
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    params = {
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat()
    }
    
    response = requests.get(f"{BASE_URL}/daily-trends", params=params)
    if response.status_code == 200:
        trends = response.json()
        for trend in trends[-7:]:  # Last 7 days
            print(f"{trend['Date']:12} | "
                  f"Events: {trend['Event Count']:>6,} | "
                  f"Sessions: {trend['Session Count']:>4,} | "
                  f"Users: {trend['User Count']:>3,} | "
                  f"Cost: ${trend['Cost (USD)']:>6.2f}")
    else:
        print(f"Error: {response.status_code} - {response.text}")


def main():
    """Main function."""
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║              API Usage Example Script                       ║
    ╚══════════════════════════════════════════════════════════════╝
    
    Make sure the API is running:
    python api.py
    """)
    
    try:
        # Check if API is running
        response = requests.get(f"{BASE_URL}/health", timeout=2)
        if response.status_code != 200:
            print("❌ API is not responding. Please start the API first:")
            print("   python api.py")
            return
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API. Please start the API first:")
        print("   python api.py")
        return
    
    # Run examples
    get_summary()
    get_token_usage_by_practice()
    get_peak_usage()
    get_tool_usage()
    get_model_usage()
    get_daily_trends()
    
    print("\n" + "="*60)
    print("✅ API examples completed!")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
