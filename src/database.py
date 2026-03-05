"""
Database module for storing and querying telemetry data.

Uses SQLite with a normalized schema optimized for analytics queries.
Schema includes: employees, sessions, events, and token_usage aggregates.
"""

import sqlite3
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TelemetryDatabase:
    """SQLite database for telemetry data storage with normalized schema."""
    
    def __init__(self, db_path: str = "telemetry.db"):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.conn = None
        self._connect()
        self._create_schema()
    
    def _connect(self):
        """Establish database connection."""
        try:
            # Use check_same_thread=False to allow connection sharing across threads
            # This is safe for read-only operations and Streamlit's threading model
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row  # Enable column access by name
            # Enable foreign keys
            self.conn.execute("PRAGMA foreign_keys = ON")
            logger.info(f"Connected to database: {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to connect to database: {str(e)}")
            raise
    
    def _create_schema(self):
        """
        Create normalized database schema with proper relationships.
        
        Schema includes:
        - employees: User/employee metadata
        - sessions: Session information aggregated from events
        - events: Individual telemetry events
        - token_usage: Aggregated token usage for fast analytics
        """
        cursor = self.conn.cursor()
        
        # 1. Employees/Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS employees (
                email TEXT PRIMARY KEY,
                full_name TEXT NOT NULL,
                practice TEXT,
                level TEXT,
                location TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 2. Sessions table - aggregated session information
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                user_email TEXT NOT NULL,
                start_time DATETIME NOT NULL,
                end_time DATETIME,
                duration_minutes REAL,
                event_count INTEGER DEFAULT 0,
                total_cost_usd REAL DEFAULT 0.0,
                total_tokens INTEGER DEFAULT 0,
                FOREIGN KEY (user_email) REFERENCES employees(email) ON DELETE CASCADE
            )
        """)
        
        # 3. Events table - normalized event storage
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                session_id TEXT NOT NULL,
                user_email TEXT,
                user_id TEXT,
                organization_id TEXT,
                
                -- Environment metadata
                terminal_type TEXT,
                scope_version TEXT,
                host_arch TEXT,
                host_name TEXT,
                os_type TEXT,
                os_version TEXT,
                
                -- Employee metadata (denormalized for query performance)
                practice TEXT,
                level TEXT,
                location TEXT,
                
                -- API Request specific fields
                model TEXT,
                input_tokens INTEGER,
                output_tokens INTEGER,
                cache_read_tokens INTEGER,
                cache_create_tokens INTEGER,
                cost_usd REAL,
                duration_ms INTEGER,
                
                -- Tool Decision/Result specific fields
                tool_name TEXT,
                decision TEXT,
                source TEXT,
                success BOOLEAN,
                decision_source TEXT,
                decision_type TEXT,
                
                -- User Prompt specific fields
                prompt_length INTEGER,
                
                -- API Error specific fields
                error_message TEXT,
                status_code TEXT,
                attempt INTEGER,
                
                FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE,
                FOREIGN KEY (user_email) REFERENCES employees(email) ON DELETE SET NULL
            )
        """)
        
        # 4. Token Usage aggregate table - for fast analytics queries
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS token_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE NOT NULL,
                user_email TEXT,
                practice TEXT,
                level TEXT,
                model TEXT,
                input_tokens INTEGER DEFAULT 0,
                output_tokens INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0,
                cost_usd REAL DEFAULT 0.0,
                request_count INTEGER DEFAULT 0,
                FOREIGN KEY (user_email) REFERENCES employees(email) ON DELETE SET NULL,
                UNIQUE(date, user_email, practice, level, model)
            )
        """)
        
        # Create indexes for optimal query performance
        logger.info("Creating indexes for optimal query performance...")
        
        # Events table indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_session_id ON events(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_user_email ON events(user_email)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_event_type ON events(event_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_practice ON events(practice)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_level ON events(level)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_model ON events(model)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_timestamp_type ON events(timestamp, event_type)")
        
        # Sessions table indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user_email ON sessions(user_email)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_start_time ON sessions(start_time)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user_start ON sessions(user_email, start_time)")
        
        # Token usage table indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_token_usage_date ON token_usage(date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_token_usage_practice ON token_usage(practice)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_token_usage_level ON token_usage(level)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_token_usage_model ON token_usage(model)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_token_usage_date_practice ON token_usage(date, practice)")
        
        # Employees table indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_employees_practice ON employees(practice)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_employees_level ON employees(level)")
        
        self.conn.commit()
        logger.info("Database schema created/verified with all indexes")
    
    def insert_employees(self, employees: List[Dict]):
        """
        Insert or update employee records.
        
        Args:
            employees: List of employee dictionaries
        """
        cursor = self.conn.cursor()
        
        for emp in employees:
            cursor.execute("""
                INSERT OR REPLACE INTO employees (email, full_name, practice, level, location)
                VALUES (?, ?, ?, ?, ?)
            """, (
                emp.get('email', ''),
                emp.get('full_name', ''),
                emp.get('practice', ''),
                emp.get('level', ''),
                emp.get('location', ''),
            ))
        
        self.conn.commit()
        logger.info(f"Inserted/updated {len(employees)} employees")
    
    def upsert_session(self, session_id: str, user_email: str, start_time: datetime,
                      end_time: Optional[datetime] = None, event_count: int = 0,
                      total_cost: float = 0.0, total_tokens: int = 0):
        """
        Insert or update session information.
        
        Args:
            session_id: Unique session identifier
            user_email: User email
            start_time: Session start time
            end_time: Session end time (optional)
            event_count: Number of events in session
            total_cost: Total cost for session
            total_tokens: Total tokens for session
        """
        cursor = self.conn.cursor()
        
        duration = None
        if start_time and end_time:
            duration = (end_time - start_time).total_seconds() / 60.0
        
        cursor.execute("""
            INSERT OR REPLACE INTO sessions 
            (session_id, user_email, start_time, end_time, duration_minutes, 
             event_count, total_cost_usd, total_tokens)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (session_id, user_email, start_time, end_time, duration,
              event_count, total_cost, total_tokens))
        
        self.conn.commit()
    
    def insert_events(self, events: List[Dict], batch_size: int = 1000):
        """
        Insert events in batches for efficiency.
        Also updates session information and token_usage aggregates.
        
        Args:
            events: List of event dictionaries
            batch_size: Number of events to insert per batch
        """
        cursor = self.conn.cursor()
        
        # First pass: Collect session statistics
        logger.info("Collecting session information...")
        session_stats = {}  # session_id -> {start, end, cost, tokens, count, user_email}
        
        for event in events:
            session_id = event.get('session_id', '')
            if session_id:
                if session_id not in session_stats:
                    session_stats[session_id] = {
                        'start': event.get('timestamp'),
                        'end': event.get('timestamp'),
                        'cost': 0.0,
                        'tokens': 0,
                        'count': 0,
                        'user_email': event.get('user_email', '')
                    }
                else:
                    # Update end time if later
                    if event.get('timestamp') and session_stats[session_id]['end']:
                        if event.get('timestamp') > session_stats[session_id]['end']:
                            session_stats[session_id]['end'] = event.get('timestamp')
                    # Update start time if earlier
                    if event.get('timestamp') and session_stats[session_id]['start']:
                        if event.get('timestamp') < session_stats[session_id]['start']:
                            session_stats[session_id]['start'] = event.get('timestamp')
                
                session_stats[session_id]['count'] += 1
                
                # Aggregate cost and tokens for API requests
                if event.get('event_type') == 'claude_code.api_request':
                    session_stats[session_id]['cost'] += event.get('cost_usd', 0.0)
                    session_stats[session_id]['tokens'] += (
                        event.get('input_tokens', 0) + event.get('output_tokens', 0)
                    )
        
        # Create sessions first (required for foreign key constraint)
        logger.info(f"Creating {len(session_stats)} sessions...")
        for session_id, stats in session_stats.items():
            self.upsert_session(
                session_id=session_id,
                user_email=stats['user_email'],
                start_time=stats['start'],
                end_time=stats['end'],
                event_count=stats['count'],
                total_cost=stats['cost'],
                total_tokens=stats['tokens']
            )
        
        # Now insert events
        total_inserted = 0
        for i in range(0, len(events), batch_size):
            batch = events[i:i + batch_size]
            
            values = []
            for event in batch:
                session_id = event.get('session_id', '')
                
                values.append((
                    event.get('event_type', ''),
                    event.get('timestamp'),
                    session_id,
                    event.get('user_email', ''),
                    event.get('user_id', ''),
                    event.get('organization_id', ''),
                    event.get('terminal_type', ''),
                    event.get('scope_version', ''),
                    event.get('host_arch', ''),
                    event.get('host_name', ''),
                    event.get('os_type', ''),
                    event.get('os_version', ''),
                    event.get('practice', ''),
                    event.get('level', ''),
                    event.get('location', ''),
                    event.get('model', ''),
                    event.get('input_tokens', 0),
                    event.get('output_tokens', 0),
                    event.get('cache_read_tokens', 0),
                    event.get('cache_create_tokens', 0),
                    event.get('cost_usd', 0.0),
                    event.get('duration_ms', 0),
                    event.get('tool_name', ''),
                    event.get('decision', ''),
                    event.get('source', ''),
                    event.get('success'),
                    event.get('decision_source', ''),
                    event.get('decision_type', ''),
                    event.get('prompt_length', 0),
                    event.get('error_message', ''),
                    event.get('status_code', ''),
                    event.get('attempt', 1),
                ))
            
            cursor.executemany("""
                INSERT INTO events (
                    event_type, timestamp, session_id, user_email, user_id,
                    organization_id, terminal_type, scope_version,
                    host_arch, host_name, os_type, os_version,
                    practice, level, location,
                    model, input_tokens, output_tokens, cache_read_tokens,
                    cache_create_tokens, cost_usd, duration_ms,
                    tool_name, decision, source, success,
                    decision_source, decision_type,
                    prompt_length,
                    error_message, status_code, attempt
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, values)
            
            total_inserted += len(batch)
            if (i // batch_size + 1) % 10 == 0:
                logger.info(f"Inserted {total_inserted}/{len(events)} events...")
        
        # Sessions already created above, no need to update again
        
        # Update token_usage aggregates
        logger.info("Updating token usage aggregates...")
        self._update_token_usage_aggregates(events)
        
        self.conn.commit()
        logger.info(f"Inserted {total_inserted} events into database")
    
    def _update_token_usage_aggregates(self, events: List[Dict]):
        """
        Update token_usage aggregate table for fast analytics queries.
        
        Args:
            events: List of processed events
        """
        cursor = self.conn.cursor()
        
        # Aggregate by date, user, practice, level, model
        aggregates = {}  # (date, user_email, practice, level, model) -> stats
        
        for event in events:
            if event.get('event_type') != 'claude_code.api_request':
                continue
            
            timestamp = event.get('timestamp')
            if not timestamp:
                continue
            
            # Extract date
            if isinstance(timestamp, datetime):
                date = timestamp.date()
            elif isinstance(timestamp, str):
                date = datetime.fromisoformat(timestamp).date()
            else:
                continue
            
            key = (
                date,
                event.get('user_email', ''),
                event.get('practice', ''),
                event.get('level', ''),
                event.get('model', '')
            )
            
            if key not in aggregates:
                aggregates[key] = {
                    'input_tokens': 0,
                    'output_tokens': 0,
                    'cost': 0.0,
                    'count': 0
                }
            
            aggregates[key]['input_tokens'] += event.get('input_tokens', 0)
            aggregates[key]['output_tokens'] += event.get('output_tokens', 0)
            aggregates[key]['cost'] += event.get('cost_usd', 0.0)
            aggregates[key]['count'] += 1
        
        # Insert/update aggregates
        for key, stats in aggregates.items():
            date, user_email, practice, level, model = key
            cursor.execute("""
                INSERT INTO token_usage 
                (date, user_email, practice, level, model, 
                 input_tokens, output_tokens, total_tokens, cost_usd, request_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(date, user_email, practice, level, model) DO UPDATE SET
                    input_tokens = token_usage.input_tokens + ?,
                    output_tokens = token_usage.output_tokens + ?,
                    total_tokens = token_usage.total_tokens + ?,
                    cost_usd = token_usage.cost_usd + ?,
                    request_count = token_usage.request_count + ?
            """, (
                date, user_email, practice, level, model,
                stats['input_tokens'], stats['output_tokens'],
                stats['input_tokens'] + stats['output_tokens'],
                stats['cost'], stats['count'],
                # For ON CONFLICT update
                stats['input_tokens'], stats['output_tokens'],
                stats['input_tokens'] + stats['output_tokens'],
                stats['cost'], stats['count']
            ))
    
    # Query methods remain the same but can now leverage the normalized schema
    def get_token_usage_by_practice(self, start_date: Optional[datetime] = None,
                                    end_date: Optional[datetime] = None) -> List[Tuple]:
        """
        Get token usage aggregated by practice.
        Uses token_usage table for fast queries.
        
        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            List of (practice, total_input_tokens, total_output_tokens, total_cost) tuples
        """
        cursor = self.conn.cursor()
        
        query = """
            SELECT 
                COALESCE(practice, 'Unknown') as practice,
                SUM(input_tokens) as total_input_tokens,
                SUM(output_tokens) as total_output_tokens,
                SUM(cost_usd) as total_cost
            FROM token_usage
            WHERE 1=1
        """
        
        params = []
        if start_date:
            query += " AND date >= DATE(?)"
            params.append(start_date)
        if end_date:
            query += " AND date <= DATE(?)"
            params.append(end_date)
        
        query += " GROUP BY practice ORDER BY total_cost DESC"
        
        cursor.execute(query, params)
        return cursor.fetchall()
    
    def get_token_usage_by_level(self, start_date: Optional[datetime] = None,
                                 end_date: Optional[datetime] = None) -> List[Tuple]:
        """Get token usage aggregated by level."""
        cursor = self.conn.cursor()
        
        query = """
            SELECT 
                COALESCE(level, 'Unknown') as level,
                SUM(input_tokens) as total_input_tokens,
                SUM(output_tokens) as total_output_tokens,
                SUM(cost_usd) as total_cost
            FROM token_usage
            WHERE 1=1
        """
        
        params = []
        if start_date:
            query += " AND date >= DATE(?)"
            params.append(start_date)
        if end_date:
            query += " AND date <= DATE(?)"
            params.append(end_date)
        
        query += " GROUP BY level ORDER BY level"
        
        cursor.execute(query, params)
        return cursor.fetchall()
    
    def get_peak_usage_times(self, start_date: Optional[datetime] = None,
                             end_date: Optional[datetime] = None) -> List[Tuple]:
        """
        Get usage by hour of day.
        
        Returns:
            List of (hour, event_count, total_cost) tuples
        """
        cursor = self.conn.cursor()
        
        query = """
            SELECT 
                CAST(strftime('%H', timestamp) AS INTEGER) as hour,
                COUNT(*) as event_count,
                SUM(cost_usd) as total_cost
            FROM events
            WHERE event_type = 'claude_code.api_request'
        """
        
        params = []
        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date)
        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date)
        
        query += " GROUP BY hour ORDER BY hour"
        
        cursor.execute(query, params)
        return cursor.fetchall()
    
    def get_tool_usage_stats(self) -> List[Tuple]:
        """Get tool usage statistics."""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT 
                tool_name,
                COUNT(*) as usage_count,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success_count,
                AVG(duration_ms) as avg_duration_ms
            FROM events
            WHERE event_type = 'claude_code.tool_result'
            GROUP BY tool_name
            ORDER BY usage_count DESC
        """)
        
        return cursor.fetchall()
    
    def get_model_usage_stats(self) -> List[Tuple]:
        """Get model usage statistics."""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT 
                model,
                COUNT(*) as request_count,
                SUM(input_tokens) as total_input_tokens,
                SUM(output_tokens) as total_output_tokens,
                SUM(cost_usd) as total_cost,
                AVG(duration_ms) as avg_duration_ms
            FROM events
            WHERE event_type = 'claude_code.api_request'
            GROUP BY model
            ORDER BY request_count DESC
        """)
        
        return cursor.fetchall()
    
    def get_daily_usage_trend(self, start_date: Optional[datetime] = None,
                              end_date: Optional[datetime] = None) -> List[Tuple]:
        """Get daily usage trends using token_usage and events tables."""
        cursor = self.conn.cursor()
        
        query = """
            SELECT 
                tu.date,
                SUM(tu.request_count) as event_count,
                (SELECT COUNT(DISTINCT session_id) FROM events WHERE DATE(timestamp) = tu.date) as session_count,
                COUNT(DISTINCT tu.user_email) as user_count,
                SUM(tu.cost_usd) as total_cost
            FROM token_usage tu
            WHERE 1=1
        """
        
        params = []
        if start_date:
            query += " AND tu.date >= DATE(?)"
            params.append(start_date)
        if end_date:
            query += " AND tu.date <= DATE(?)"
            params.append(end_date)
        
        query += " GROUP BY tu.date ORDER BY tu.date"
        
        cursor.execute(query, params)
        return cursor.fetchall()
    
    def get_error_stats(self) -> List[Tuple]:
        """Get API error statistics."""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT 
                error_message,
                status_code,
                COUNT(*) as error_count,
                AVG(attempt) as avg_attempt
            FROM events
            WHERE event_type = 'claude_code.api_error'
            GROUP BY error_message, status_code
            ORDER BY error_count DESC
        """)
        
        return cursor.fetchall()
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")
