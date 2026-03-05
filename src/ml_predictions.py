"""
Machine Learning module for predictive analytics.

Optional enhancement for trend forecasting and anomaly detection.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from datetime import datetime, timedelta
from src.database import TelemetryDatabase
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MLPredictor:
    """ML-based predictions for telemetry data."""
    
    def __init__(self, db: TelemetryDatabase):
        """
        Initialize ML predictor.
        
        Args:
            db: TelemetryDatabase instance
        """
        self.db = db
        self.scaler = StandardScaler()
    
    def prepare_daily_data(self, days: int = 60) -> pd.DataFrame:
        """
        Prepare daily aggregated data for forecasting.
        
        Args:
            days: Number of days to look back
            
        Returns:
            DataFrame with daily metrics
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT 
                DATE(timestamp) as date,
                COUNT(*) as event_count,
                SUM(cost_usd) as total_cost,
                SUM(input_tokens + output_tokens) as total_tokens,
                COUNT(DISTINCT user_email) as unique_users
            FROM events
            WHERE event_type = 'claude_code.api_request'
            AND timestamp >= ? AND timestamp <= ?
            GROUP BY DATE(timestamp)
            ORDER BY date
        """, (start_date, end_date))
        
        results = cursor.fetchall()
        data = []
        for row in results:
            data.append({
                'date': pd.to_datetime(row[0]),
                'event_count': row[1] or 0,
                'total_cost': row[2] or 0.0,
                'total_tokens': row[3] or 0,
                'unique_users': row[4] or 0
            })
        
        df = pd.DataFrame(data)
        if df.empty:
            return df
        
        # Add day of week and day number features
        df['day_of_week'] = df['date'].dt.dayofweek
        df['day_number'] = (df['date'] - df['date'].min()).dt.days
        
        return df
    
    def forecast_daily_usage(self, forecast_days: int = 7) -> pd.DataFrame:
        """
        Forecast daily usage for next N days using linear regression.
        
        Args:
            forecast_days: Number of days to forecast
            
        Returns:
            DataFrame with forecasted values
        """
        df = self.prepare_daily_data()
        
        if len(df) < 7:
            logger.warning("Insufficient data for forecasting")
            return pd.DataFrame()
        
        # Prepare features
        X = df[['day_number', 'day_of_week']].values
        y_event = df['event_count'].values
        y_cost = df['total_cost'].values
        y_tokens = df['total_tokens'].values
        
        # Train models
        model_event = LinearRegression()
        model_cost = LinearRegression()
        model_tokens = LinearRegression()
        
        model_event.fit(X, y_event)
        model_cost.fit(X, y_cost)
        model_tokens.fit(X, y_tokens)
        
        # Generate forecast dates
        last_date = df['date'].max()
        forecast_dates = [last_date + timedelta(days=i+1) for i in range(forecast_days)]
        
        # Prepare forecast features
        forecast_data = []
        for i, date in enumerate(forecast_dates):
            day_number = df['day_number'].max() + i + 1
            day_of_week = date.dayofweek
            
            X_pred = np.array([[day_number, day_of_week]])
            
            forecast_data.append({
                'date': date,
                'event_count': max(0, model_event.predict(X_pred)[0]),
                'total_cost': max(0, model_cost.predict(X_pred)[0]),
                'total_tokens': max(0, model_tokens.predict(X_pred)[0]),
                'is_forecast': True
            })
        
        return pd.DataFrame(forecast_data)
    
    def detect_anomalies(self, metric: str = 'cost_usd', threshold_std: float = 2.0) -> pd.DataFrame:
        """
        Detect anomalies in daily usage patterns.
        
        Args:
            metric: Metric to analyze ('cost_usd', 'event_count', 'total_tokens')
            threshold_std: Standard deviation threshold for anomaly detection
            
        Returns:
            DataFrame with anomalies flagged
        """
        df = self.prepare_daily_data()
        
        if df.empty:
            return df
        
        # Map metric name to column
        metric_map = {
            'cost_usd': 'total_cost',
            'event_count': 'event_count',
            'total_tokens': 'total_tokens'
        }
        
        col_name = metric_map.get(metric, 'total_cost')
        
        if col_name not in df.columns:
            logger.error(f"Metric {metric} not found")
            return pd.DataFrame()
        
        # Calculate z-scores
        mean = df[col_name].mean()
        std = df[col_name].std()
        
        if std == 0:
            return df
        
        df['z_score'] = (df[col_name] - mean) / std
        df['is_anomaly'] = abs(df['z_score']) > threshold_std
        df['anomaly_type'] = df.apply(
            lambda row: 'high' if row['z_score'] > threshold_std else ('low' if row['z_score'] < -threshold_std else 'normal'),
            axis=1
        )
        
        return df[['date', col_name, 'z_score', 'is_anomaly', 'anomaly_type']]
    
    def get_trend_analysis(self) -> Dict:
        """
        Get trend analysis for key metrics.
        
        Returns:
            Dictionary with trend information
        """
        df = self.prepare_daily_data()
        
        if len(df) < 2:
            return {}
        
        # Calculate trends (simple linear regression slope)
        X = df['day_number'].values.reshape(-1, 1)
        
        trends = {}
        for metric in ['event_count', 'total_cost', 'total_tokens']:
            if metric in df.columns:
                y = df[metric].values
                model = LinearRegression()
                model.fit(X, y)
                slope = model.coef_[0]
                
                # Calculate percentage change
                first_value = df[metric].iloc[0]
                last_value = df[metric].iloc[-1]
                pct_change = ((last_value - first_value) / first_value * 100) if first_value > 0 else 0
                
                trends[metric] = {
                    'slope': slope,
                    'trend': 'increasing' if slope > 0 else 'decreasing',
                    'pct_change': round(pct_change, 2),
                    'first_value': first_value,
                    'last_value': last_value
                }
        
        return trends
