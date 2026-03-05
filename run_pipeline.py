#!/usr/bin/env python3
"""
Simple CLI entry point for running the full data pipeline.

This script orchestrates the complete data processing pipeline:
1. Loads telemetry dataset files
2. Runs data ingestion
3. Validates and processes data
4. Inserts processed data into database

Usage:
    python run_pipeline.py [--telemetry PATH] [--employees PATH] [--db PATH] [--clear]
"""

import argparse
import os
import sys
from pathlib import Path
from src.data_processing import DataProcessor
from src.database import TelemetryDatabase
import logging

# Configure logging for clear progress messages
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


def print_header(text: str):
    """Print a formatted header."""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70 + "\n")


def print_step(step_num: int, total_steps: int, description: str):
    """Print a formatted step message."""
    print(f"[{step_num}/{total_steps}] {description}...")


def print_success(message: str):
    """Print a success message."""
    print(f"✅ {message}\n")


def print_error(message: str):
    """Print an error message."""
    print(f"❌ {message}\n")


def print_info(message: str):
    """Print an info message."""
    print(f"ℹ️  {message}\n")


def find_default_files():
    """
    Find default data files in common locations.
    
    Returns:
        Tuple of (telemetry_path, employees_path) or (None, None) if not found
    """
    # Common locations to check
    locations = [
        ("output/telemetry_logs.jsonl", "output/employees.csv"),
        ("data/telemetry_logs.jsonl", "data/employees.csv"),
        ("./telemetry_logs.jsonl", "./employees.csv"),
    ]
    
    for telemetry_path, employees_path in locations:
        if os.path.exists(telemetry_path) and os.path.exists(employees_path):
            return telemetry_path, employees_path
    
    return None, None


def main():
    """Main pipeline function."""
    parser = argparse.ArgumentParser(
        description="Run the complete data processing pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use default files (output/telemetry_logs.jsonl, output/employees.csv)
  python run_pipeline.py
  
  # Specify custom file paths
  python run_pipeline.py --telemetry data/logs.jsonl --employees data/employees.csv
  
  # Clear existing database and reprocess
  python run_pipeline.py --clear
  
  # Use custom database path
  python run_pipeline.py --db custom.db
        """
    )
    
    parser.add_argument(
        '--telemetry',
        type=str,
        default=None,
        help='Path to telemetry_logs.jsonl file (default: auto-detect)'
    )
    parser.add_argument(
        '--employees',
        type=str,
        default=None,
        help='Path to employees.csv file (default: auto-detect)'
    )
    parser.add_argument(
        '--db',
        type=str,
        default='telemetry.db',
        help='Path to SQLite database file (default: telemetry.db)'
    )
    parser.add_argument(
        '--clear',
        action='store_true',
        help='Clear existing database before processing'
    )
    
    args = parser.parse_args()
    
    # Print header
    print_header("Claude Code Analytics - Data Pipeline")
    
    # Step 1: Locate dataset files
    print_step(1, 5, "Locating dataset files")
    
    telemetry_path = args.telemetry
    employees_path = args.employees
    
    # Auto-detect files if not provided
    if not telemetry_path or not employees_path:
        print_info("Auto-detecting data files...")
        default_telemetry, default_employees = find_default_files()
        
        if default_telemetry and default_employees:
            telemetry_path = telemetry_path or default_telemetry
            employees_path = employees_path or default_employees
            print_success(f"Found telemetry file: {telemetry_path}")
            print_success(f"Found employees file: {employees_path}")
        else:
            print_error("Could not auto-detect data files.")
            print_info("Please specify file paths:")
            print_info("  python run_pipeline.py --telemetry PATH --employees PATH")
            print_info("\nOr place files in one of these locations:")
            print_info("  - output/telemetry_logs.jsonl and output/employees.csv")
            print_info("  - data/telemetry_logs.jsonl and data/employees.csv")
            sys.exit(1)
    
    # Validate files exist
    if not os.path.exists(telemetry_path):
        print_error(f"Telemetry file not found: {telemetry_path}")
        sys.exit(1)
    
    if not os.path.exists(employees_path):
        print_error(f"Employees file not found: {employees_path}")
        sys.exit(1)
    
    print_success(f"All dataset files located")
    
    # Step 2: Initialize data processor
    print_step(2, 5, "Initializing data processor")
    
    try:
        processor = DataProcessor()
        print_success("Data processor initialized")
    except Exception as e:
        print_error(f"Failed to initialize data processor: {str(e)}")
        sys.exit(1)
    
    # Step 3: Load and validate employees
    print_step(3, 5, "Loading and validating employees")
    
    try:
        employees = processor.load_employees(employees_path)
        print_success(f"Loaded {len(employees)} employees")
    except Exception as e:
        print_error(f"Failed to load employees: {str(e)}")
        sys.exit(1)
    
    # Step 4: Process telemetry data
    print_step(4, 5, "Processing telemetry data")
    print_info("This may take a few moments depending on dataset size...")
    
    try:
        events = processor.process_telemetry_file(telemetry_path, employees_path)
        
        if not events:
            print_error("No events were processed. Please check your data files.")
            sys.exit(1)
        
        # Get processing statistics
        stats = processor.get_summary_stats()
        
        print_success(f"Processed {stats.get('valid_events', 0):,} valid events")
        print_info(f"  - Total events examined: {stats.get('total_events', 0):,}")
        print_info(f"  - Skipped events: {stats.get('skipped_events', 0):,}")
        print_info(f"  - Unique users: {stats.get('unique_users', 0):,}")
        print_info(f"  - Unique sessions: {stats.get('unique_sessions', 0):,}")
        
        if stats.get('date_range', {}).get('min'):
            print_info(f"  - Date range: {stats['date_range']['min']} to {stats['date_range']['max']}")
        
    except Exception as e:
        print_error(f"Failed to process telemetry data: {str(e)}")
        sys.exit(1)
    
    # Step 5: Initialize database
    print_step(5, 5, "Initializing database")
    
    # Clear database if requested
    if args.clear and os.path.exists(args.db):
        print_info(f"Clearing existing database: {args.db}")
        try:
            os.remove(args.db)
            print_success("Existing database cleared")
        except Exception as e:
            print_error(f"Failed to clear database: {str(e)}")
            sys.exit(1)
    
    try:
        db = TelemetryDatabase(args.db)
        print_success(f"Database initialized: {args.db}")
    except Exception as e:
        print_error(f"Failed to initialize database: {str(e)}")
        sys.exit(1)
    
    # Step 6: Insert employees into database
    print_info("Inserting employees into database...")
    
    try:
        employee_list = list(employees.values())
        db.insert_employees(employee_list)
        print_success(f"Inserted {len(employee_list)} employees")
    except Exception as e:
        print_error(f"Failed to insert employees: {str(e)}")
        db.close()
        sys.exit(1)
    
    # Step 7: Insert events into database
    print_info("Inserting events into database...")
    print_info("This may take a few moments for large datasets...")
    
    try:
        db.insert_events(events)
        print_success(f"Inserted {len(events)} events")
    except Exception as e:
        print_error(f"Failed to insert events: {str(e)}")
        db.close()
        sys.exit(1)
    
    # Close database connection
    db.close()
    
    # Final summary
    print_header("Pipeline Completed Successfully!")
    
    stats = processor.get_summary_stats()
    
    print("📊 Processing Summary:")
    print(f"   • Total Events: {stats.get('total_events', 0):,}")
    print(f"   • Valid Events: {stats.get('valid_events', 0):,}")
    print(f"   • Unique Users: {stats.get('unique_users', 0):,}")
    print(f"   • Unique Sessions: {stats.get('unique_sessions', 0):,}")
    print(f"   • Total Tokens: {stats.get('total_tokens', 0):,}")
    print(f"   • Total Cost: ${stats.get('total_cost_usd', 0):.2f}")
    
    if stats.get('event_types'):
        print("\n📈 Event Types:")
        for event_type, count in sorted(stats['event_types'].items(), key=lambda x: -x[1]):
            print(f"   • {event_type}: {count:,}")
    
    print(f"\n💾 Database: {args.db}")
    print(f"   • Size: {os.path.getsize(args.db) / (1024 * 1024):.2f} MB")
    
    print("\n🚀 Next Steps:")
    print("   1. Launch the dashboard:")
    print("      streamlit run dashboard.py")
    print("\n   2. Or start the API server:")
    print("      python api.py")
    print("\n   3. Or explore the data programmatically:")
    print("      python -c \"from src.database import TelemetryDatabase; db = TelemetryDatabase('telemetry.db'); print('Connected!')\"")
    
    print("\n" + "=" * 70 + "\n")


if __name__ == "__main__":
    main()
