"""
REST API endpoints for programmatic access to telemetry data.

Optional enhancement for the analytics platform.
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime
from src.database import TelemetryDatabase
from src.analytics import AnalyticsEngine
import os

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend access

# Initialize database and analytics
db_path = os.getenv("DB_PATH", "telemetry.db")
db = TelemetryDatabase(db_path)
analytics = AnalyticsEngine(db)


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "service": "claude-code-analytics-api"})


@app.route('/api/summary', methods=['GET'])
def get_summary():
    """Get summary insights."""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        start = datetime.fromisoformat(start_date) if start_date else None
        end = datetime.fromisoformat(end_date) if end_date else None
        
        summary = analytics.get_summary_insights(start, end)
        return jsonify(summary)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/token-usage/practice', methods=['GET'])
def get_token_usage_by_practice():
    """Get token usage by practice."""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        start = datetime.fromisoformat(start_date) if start_date else None
        end = datetime.fromisoformat(end_date) if end_date else None
        
        df = analytics.get_token_consumption_by_role(start, end)
        return jsonify(df.to_dict('records'))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/token-usage/level', methods=['GET'])
def get_token_usage_by_level():
    """Get token usage by level."""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        start = datetime.fromisoformat(start_date) if start_date else None
        end = datetime.fromisoformat(end_date) if end_date else None
        
        df = analytics.get_token_consumption_by_level(start, end)
        return jsonify(df.to_dict('records'))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/peak-usage', methods=['GET'])
def get_peak_usage():
    """Get peak usage times."""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        start = datetime.fromisoformat(start_date) if start_date else None
        end = datetime.fromisoformat(end_date) if end_date else None
        
        df = analytics.get_peak_usage_times(start, end)
        return jsonify(df.to_dict('records'))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/tools', methods=['GET'])
def get_tool_usage():
    """Get tool usage statistics."""
    try:
        df = analytics.get_tool_usage_patterns()
        return jsonify(df.to_dict('records'))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/models', methods=['GET'])
def get_model_usage():
    """Get model usage statistics."""
    try:
        df = analytics.get_model_usage_analysis()
        return jsonify(df.to_dict('records'))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/daily-trends', methods=['GET'])
def get_daily_trends():
    """Get daily usage trends."""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        start = datetime.fromisoformat(start_date) if start_date else None
        end = datetime.fromisoformat(end_date) if end_date else None
        
        df = analytics.get_daily_trends(start, end)
        df['Date'] = df['Date'].astype(str)  # Convert datetime to string for JSON
        return jsonify(df.to_dict('records'))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/errors', methods=['GET'])
def get_errors():
    """Get error statistics."""
    try:
        df = analytics.get_error_analysis()
        return jsonify(df.to_dict('records'))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/behaviors', methods=['GET'])
def get_behaviors():
    """Get code generation behaviors."""
    try:
        behaviors = analytics.get_code_generation_behaviors()
        return jsonify(behaviors)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
