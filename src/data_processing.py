"""
Data ingestion and processing module with clean architecture.

Pipeline stages:
1. Ingestion - Read raw data files
2. Validation - Validate structure and fields
3. Transformation - Normalize and clean data
4. Database Insert - Store in database
"""

import json
import csv
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataIngestion:
    """Stage 1: Ingestion - Read raw data from files."""
    
    @staticmethod
    def load_employees(csv_path: str) -> Dict[str, Dict]:
        """
        Load employee data from CSV file.
        
        Args:
            csv_path: Path to employees.csv file
            
        Returns:
            Dictionary mapping email to employee data
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If CSV format is invalid
        """
        employees = {}
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                # Validate required columns
                required_columns = ['email', 'full_name', 'practice', 'level', 'location']
                if not all(col in reader.fieldnames for col in required_columns):
                    missing = [col for col in required_columns if col not in reader.fieldnames]
                    raise ValueError(f"Missing required columns in CSV: {missing}")
                
                for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
                    try:
                        email = row['email'].strip()
                        if not email:
                            logger.warning(f"Row {row_num}: Empty email, skipping")
                            continue
                        
                        employees[email] = {
                            'email': email,
                            'full_name': row['full_name'].strip(),
                            'practice': row['practice'].strip(),
                            'level': row['level'].strip(),
                            'location': row['location'].strip()
                        }
                    except KeyError as e:
                        logger.warning(f"Row {row_num}: Missing field {e}, skipping")
                        continue
                    except Exception as e:
                        logger.warning(f"Row {row_num}: Error processing row - {str(e)}, skipping")
                        continue
            
            logger.info(f"Loaded {len(employees)} employees from {csv_path}")
            return employees
            
        except FileNotFoundError:
            error_msg = f"Employees file not found: {csv_path}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)
        except Exception as e:
            error_msg = f"Error loading employees: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
    
    @staticmethod
    def load_telemetry_batches(jsonl_path: str) -> List[Dict]:
        """
        Load telemetry batches from JSONL file.
        
        Args:
            jsonl_path: Path to telemetry_logs.jsonl
            
        Yields:
            Dictionary representing a log batch
            
        Raises:
            FileNotFoundError: If file doesn't exist
        """
        try:
            with open(jsonl_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:  # Skip empty lines
                        continue
                    
                    try:
                        batch = json.loads(line)
                        yield batch
                    except json.JSONDecodeError as e:
                        logger.warning(f"Line {line_num}: Invalid JSON - {str(e)}, skipping")
                        continue
                    except Exception as e:
                        logger.warning(f"Line {line_num}: Error parsing batch - {str(e)}, skipping")
                        continue
        except FileNotFoundError:
            error_msg = f"Telemetry file not found: {jsonl_path}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)


class DataValidation:
    """Stage 2: Validation - Validate event structure and fields."""
    
    @staticmethod
    def parse_timestamp(timestamp_str: str) -> Optional[datetime]:
        """
        Parse timestamp string to datetime object.
        
        Args:
            timestamp_str: Timestamp in format "YYYY-MM-DDTHH:MM:SS.mmmZ"
            
        Returns:
            datetime object or None if parsing fails
        """
        if not timestamp_str or not isinstance(timestamp_str, str):
            return None
        
        try:
            # Handle microseconds
            if '.' in timestamp_str:
                dt = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S.%fZ")
            else:
                dt = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%SZ")
            return dt.replace(tzinfo=None)  # Remove timezone for SQLite compatibility
        except (ValueError, TypeError) as e:
            logger.debug(f"Failed to parse timestamp {timestamp_str}: {str(e)}")
            return None
    
    @staticmethod
    def validate_event(event: Dict) -> Tuple[bool, Optional[str]]:
        """
        Validate event structure and required fields.
        
        Args:
            event: Event dictionary
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not isinstance(event, dict):
            return False, "Event is not a dictionary"
        
        # Check required top-level fields
        required_fields = ['body', 'attributes']
        for field in required_fields:
            if field not in event:
                return False, f"Missing required field: {field}"
        
        attrs = event.get('attributes', {})
        if not isinstance(attrs, dict):
            return False, "Attributes is not a dictionary"
        
        # Check required attributes
        required_attrs = ['event.timestamp', 'user.email', 'session.id']
        for attr in required_attrs:
            if attr not in attrs:
                return False, f"Missing required attribute: {attr}"
        
        # Validate timestamp format
        timestamp_str = attrs.get('event.timestamp', '')
        if not timestamp_str:
            return False, "Empty timestamp"
        
        timestamp = DataValidation.parse_timestamp(timestamp_str)
        if timestamp is None:
            return False, f"Invalid timestamp format: {timestamp_str}"
        
        # Validate email format (basic check)
        email = attrs.get('user.email', '')
        if email and '@' not in email:
            logger.warning(f"Potentially invalid email format: {email}")
        
        # Validate session ID (should not be empty)
        session_id = attrs.get('session.id', '')
        if not session_id:
            return False, "Empty session.id"
        
        return True, None
    
    @staticmethod
    def validate_batch(batch: Dict) -> Tuple[bool, Optional[str]]:
        """
        Validate log batch structure.
        
        Args:
            batch: Batch dictionary
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not isinstance(batch, dict):
            return False, "Batch is not a dictionary"
        
        if 'logEvents' not in batch:
            return False, "Missing 'logEvents' field in batch"
        
        log_events = batch.get('logEvents', [])
        if not isinstance(log_events, list):
            return False, "'logEvents' is not a list"
        
        if len(log_events) == 0:
            return False, "Empty logEvents list"
        
        return True, None


class DataTransformation:
    """Stage 3: Transformation - Normalize and clean event data."""
    
    @staticmethod
    def extract_event_data(event: Dict, employee_data: Optional[Dict] = None) -> Dict:
        """
        Extract and normalize event data for database storage.
        
        Args:
            event: Raw event dictionary (validated)
            employee_data: Optional employee metadata
            
        Returns:
            Normalized event data dictionary
        """
        attrs = event.get('attributes', {})
        resource = event.get('resource', {})
        scope = event.get('scope', {})
        
        # Parse timestamp
        timestamp = DataValidation.parse_timestamp(attrs.get('event.timestamp', ''))
        
        # Base event data
        event_data = {
            'event_type': event.get('body', ''),
            'timestamp': timestamp,
            'user_email': attrs.get('user.email', ''),
            'user_id': attrs.get('user.id', ''),
            'session_id': attrs.get('session.id', ''),
            'organization_id': attrs.get('organization.id', ''),
            'terminal_type': attrs.get('terminal.type', ''),
            'scope_version': scope.get('version', '') if isinstance(scope, dict) else '',
            'host_arch': resource.get('host.arch', '') if isinstance(resource, dict) else '',
            'host_name': resource.get('host.name', '') if isinstance(resource, dict) else '',
            'os_type': resource.get('os.type', '') if isinstance(resource, dict) else '',
            'os_version': resource.get('os.version', '') if isinstance(resource, dict) else '',
        }
        
        # Add employee metadata if available
        if employee_data:
            event_data.update({
                'practice': employee_data.get('practice', ''),
                'level': employee_data.get('level', ''),
                'location': employee_data.get('location', ''),
            })
        else:
            event_data.update({
                'practice': '',
                'level': '',
                'location': '',
            })
        
        # Event-specific fields based on event.name
        event_name = attrs.get('event.name', '')
        
        if event_name == 'api_request':
            event_data.update({
                'model': attrs.get('model', ''),
                'input_tokens': DataTransformation._safe_int(attrs.get('input_tokens', '0')),
                'output_tokens': DataTransformation._safe_int(attrs.get('output_tokens', '0')),
                'cache_read_tokens': DataTransformation._safe_int(attrs.get('cache_read_tokens', '0')),
                'cache_create_tokens': DataTransformation._safe_int(attrs.get('cache_creation_tokens', '0')),
                'cost_usd': DataTransformation._safe_float(attrs.get('cost_usd', '0')),
                'duration_ms': DataTransformation._safe_int(attrs.get('duration_ms', '0')),
            })
        elif event_name == 'tool_decision':
            event_data.update({
                'tool_name': attrs.get('tool_name', ''),
                'decision': attrs.get('decision', ''),
                'source': attrs.get('source', ''),
            })
        elif event_name == 'tool_result':
            event_data.update({
                'tool_name': attrs.get('tool_name', ''),
                'success': DataTransformation._safe_bool(attrs.get('success', 'false')),
                'duration_ms': DataTransformation._safe_int(attrs.get('duration_ms', '0')),
                'decision_source': attrs.get('decision_source', ''),
                'decision_type': attrs.get('decision_type', ''),
            })
        elif event_name == 'user_prompt':
            event_data.update({
                'prompt_length': DataTransformation._safe_int(attrs.get('prompt_length', '0')),
            })
        elif event_name == 'api_error':
            event_data.update({
                'error_message': attrs.get('error', ''),
                'status_code': attrs.get('status_code', ''),
                'model': attrs.get('model', ''),
                'attempt': DataTransformation._safe_int(attrs.get('attempt', '1')),
                'duration_ms': DataTransformation._safe_int(attrs.get('duration_ms', '0')),
            })
        
        return event_data
    
    @staticmethod
    def _safe_int(value) -> int:
        """Safely convert value to int."""
        if value is None:
            return 0
        try:
            if isinstance(value, str):
                # Handle empty strings
                if not value.strip():
                    return 0
                return int(float(value))  # Handle "123.0" format
            return int(value)
        except (ValueError, TypeError):
            return 0
    
    @staticmethod
    def _safe_float(value) -> float:
        """Safely convert value to float."""
        if value is None:
            return 0.0
        try:
            if isinstance(value, str):
                if not value.strip():
                    return 0.0
                return float(value)
            return float(value)
        except (ValueError, TypeError):
            return 0.0
    
    @staticmethod
    def _safe_bool(value) -> bool:
        """Safely convert value to boolean."""
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
        return bool(value)


class DataProcessor:
    """
    Main data processor orchestrating the pipeline.
    
    Pipeline: Ingestion -> Validation -> Transformation -> Ready for Database
    """
    
    def __init__(self):
        """Initialize data processor with error tracking."""
        self.processed_events = []
        self.employees = {}
        self.errors = []
        self.stats = {
            'total_batches': 0,
            'total_events': 0,
            'valid_events': 0,
            'skipped_events': 0,
            'validation_errors': 0,
            'transformation_errors': 0
        }
    
    def load_employees(self, csv_path: str) -> Dict[str, Dict]:
        """
        Load employee data (Stage 1: Ingestion).
        
        Args:
            csv_path: Path to employees.csv file
            
        Returns:
            Dictionary mapping email to employee data
        """
        try:
            self.employees = DataIngestion.load_employees(csv_path)
            return self.employees
        except Exception as e:
            error_msg = f"Failed to load employees: {str(e)}"
            logger.error(error_msg)
            self.errors.append(error_msg)
            raise
    
    def process_telemetry_file(self, jsonl_path: str, employees_path: Optional[str] = None) -> List[Dict]:
        """
        Process telemetry logs through the full pipeline.
        
        Pipeline stages:
        1. Ingestion: Load batches from JSONL
        2. Validation: Validate batch and event structure
        3. Transformation: Normalize event data
        4. Ready for database insertion
        
        Args:
            jsonl_path: Path to telemetry_logs.jsonl
            employees_path: Optional path to employees.csv
            
        Returns:
            List of processed event dictionaries
        """
        # Load employees if provided
        if employees_path:
            self.load_employees(employees_path)
        
        processed_events = []
        
        try:
            # Stage 1: Ingestion - Load batches
            for batch in DataIngestion.load_telemetry_batches(jsonl_path):
                self.stats['total_batches'] += 1
                
                # Stage 2: Validation - Validate batch structure
                is_valid, error_msg = DataValidation.validate_batch(batch)
                if not is_valid:
                    logger.warning(f"Batch {self.stats['total_batches']}: Invalid batch - {error_msg}")
                    self.stats['validation_errors'] += 1
                    continue
                
                log_events = batch.get('logEvents', [])
                
                # Process each event in the batch
                for log_event in log_events:
                    self.stats['total_events'] += 1
                    
                    try:
                        # Extract message JSON
                        message = log_event.get('message', '')
                        if not message:
                            logger.warning(f"Event {self.stats['total_events']}: Empty message, skipping")
                            self.stats['skipped_events'] += 1
                            continue
                        
                        # Parse event JSON
                        try:
                            event = json.loads(message)
                        except json.JSONDecodeError as e:
                            logger.warning(f"Event {self.stats['total_events']}: Invalid JSON - {str(e)}")
                            self.stats['skipped_events'] += 1
                            continue
                        
                        # Stage 2: Validation - Validate event structure
                        is_valid, error_msg = DataValidation.validate_event(event)
                        if not is_valid:
                            logger.warning(f"Event {self.stats['total_events']}: Invalid event - {error_msg}")
                            self.stats['skipped_events'] += 1
                            self.stats['validation_errors'] += 1
                            continue
                        
                        # Stage 3: Transformation - Extract and normalize event data
                        try:
                            user_email = event['attributes'].get('user.email', '')
                            employee_data = self.employees.get(user_email)
                            
                            event_data = DataTransformation.extract_event_data(event, employee_data)
                            
                            # Ensure timestamp is valid
                            if not event_data.get('timestamp'):
                                logger.warning(f"Event {self.stats['total_events']}: Invalid timestamp, skipping")
                                self.stats['skipped_events'] += 1
                                continue
                            
                            processed_events.append(event_data)
                            self.stats['valid_events'] += 1
                            
                        except Exception as e:
                            logger.warning(f"Event {self.stats['total_events']}: Transformation error - {str(e)}")
                            self.stats['skipped_events'] += 1
                            self.stats['transformation_errors'] += 1
                            continue
                    
                    except Exception as e:
                        logger.warning(f"Event {self.stats['total_events']}: Unexpected error - {str(e)}")
                        self.stats['skipped_events'] += 1
                        continue
            
            # Log summary
            logger.info(f"\n=== Processing Summary ===")
            logger.info(f"Total batches: {self.stats['total_batches']}")
            logger.info(f"Total events: {self.stats['total_events']}")
            logger.info(f"Valid events: {self.stats['valid_events']}")
            logger.info(f"Skipped events: {self.stats['skipped_events']}")
            logger.info(f"Validation errors: {self.stats['validation_errors']}")
            logger.info(f"Transformation errors: {self.stats['transformation_errors']}")
            logger.info(f"Success rate: {(self.stats['valid_events']/self.stats['total_events']*100):.2f}%" if self.stats['total_events'] > 0 else "N/A")
            
            self.processed_events = processed_events
            return processed_events
        
        except FileNotFoundError:
            error_msg = f"File not found: {jsonl_path}"
            logger.error(error_msg)
            self.errors.append(error_msg)
            raise
        except Exception as e:
            error_msg = f"Error processing telemetry file: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.errors.append(error_msg)
            raise
    
    def get_summary_stats(self) -> Dict:
        """Get summary statistics of processed data."""
        if not self.processed_events:
            return self.stats
        
        event_types = {}
        total_cost = 0.0
        total_tokens = 0
        date_range = {'min': None, 'max': None}
        
        for event in self.processed_events:
            event_type = event.get('event_type', 'unknown')
            event_types[event_type] = event_types.get(event_type, 0) + 1
            
            if event_type == 'claude_code.api_request':
                total_cost += event.get('cost_usd', 0.0)
                total_tokens += event.get('input_tokens', 0) + event.get('output_tokens', 0)
            
            timestamp = event.get('timestamp')
            if timestamp:
                if date_range['min'] is None or timestamp < date_range['min']:
                    date_range['min'] = timestamp
                if date_range['max'] is None or timestamp > date_range['max']:
                    date_range['max'] = timestamp
        
        summary = self.stats.copy()
        summary.update({
            'event_types': event_types,
            'total_cost_usd': total_cost,
            'total_tokens': total_tokens,
            'date_range': date_range,
            'unique_users': len(set(e.get('user_email', '') for e in self.processed_events)),
            'unique_sessions': len(set(e.get('session_id', '') for e in self.processed_events)),
        })
        
        return summary
