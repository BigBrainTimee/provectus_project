"""
Main script to process telemetry data and populate the database.

Usage:
    python process_data.py --telemetry output/telemetry_logs.jsonl --employees output/employees.csv
"""

import argparse
import os
import sys
from pathlib import Path
from src.data_processing import DataProcessor
from src.database import TelemetryDatabase
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main processing function."""
    parser = argparse.ArgumentParser(
        description="Process telemetry data and populate database"
    )
    parser.add_argument(
        '--telemetry',
        type=str,
        required=True,
        help='Path to telemetry_logs.jsonl file'
    )
    parser.add_argument(
        '--employees',
        type=str,
        required=True,
        help='Path to employees.csv file'
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
    
    # Validate input files
    if not os.path.exists(args.telemetry):
        logger.error(f"Telemetry file not found: {args.telemetry}")
        sys.exit(1)
    
    if not os.path.exists(args.employees):
        logger.error(f"Employees file not found: {args.employees}")
        sys.exit(1)
    
    # Clear database if requested
    if args.clear and os.path.exists(args.db):
        logger.info(f"Removing existing database: {args.db}")
        os.remove(args.db)
    
    try:
        # Initialize components
        logger.info("Initializing data processor...")
        processor = DataProcessor()
        
        logger.info("Loading employees...")
        employees = processor.load_employees(args.employees)
        
        logger.info("Processing telemetry data...")
        events = processor.process_telemetry_file(args.telemetry, args.employees)
        
        if not events:
            logger.warning("No events processed. Exiting.")
            sys.exit(1)
        
        # Get summary stats
        summary = processor.get_summary_stats()
        logger.info(f"\n=== Processing Summary ===")
        logger.info(f"Total events processed: {summary['total_events']:,}")
        logger.info(f"Unique users: {summary['unique_users']:,}")
        logger.info(f"Unique sessions: {summary['unique_sessions']:,}")
        logger.info(f"Total cost: ${summary['total_cost_usd']:.2f}")
        logger.info(f"Total tokens: {summary['total_tokens']:,}")
        logger.info(f"Date range: {summary['date_range']['min']} to {summary['date_range']['max']}")
        logger.info(f"\nEvent types:")
        for event_type, count in summary['event_types'].items():
            logger.info(f"  {event_type}: {count:,}")
        
        # Initialize database
        logger.info(f"\nInitializing database: {args.db}")
        db = TelemetryDatabase(args.db)
        
        # Insert employees
        logger.info("Inserting employees into database...")
        employee_list = list(employees.values())
        db.insert_employees(employee_list)
        
        # Insert events
        logger.info("Inserting events into database...")
        db.insert_events(events)
        
        logger.info("\n✅ Data processing completed successfully!")
        logger.info(f"Database ready: {args.db}")
        logger.info("\nNext steps:")
        logger.info("  1. Run the dashboard: streamlit run dashboard.py")
        logger.info("  2. Or start the API: python api.py")
        
        db.close()
        
    except Exception as e:
        logger.error(f"Error processing data: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
