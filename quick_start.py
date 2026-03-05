"""
Quick start script to generate data, process it, and provide next steps.

This script automates the initial setup process.
"""

import os
import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"\n{'='*60}")
    print(f"Step: {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*60}\n")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error: {e.stderr}")
        return False
    except FileNotFoundError:
        print(f"Error: Command not found. Make sure Python is in your PATH.")
        return False


def main():
    """Main quick start function."""
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║     Claude Code Analytics Platform - Quick Start            ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    
    # Check if output directory exists
    output_dir = Path("output")
    if not output_dir.exists():
        print("Creating output directory...")
        output_dir.mkdir(exist_ok=True)
    
    # Step 1: Generate data
    print("\n📊 Step 1: Generating sample telemetry data...")
    generate_cmd = [
        sys.executable,
        "generate_fake_data.py",
        "--num-users", "50",
        "--num-sessions", "1000",
        "--days", "30",
        "--output-dir", "output"
    ]
    
    if not run_command(generate_cmd, "Generate sample data"):
        print("\n❌ Failed to generate data. Please check the error above.")
        return
    
    # Step 2: Process data
    print("\n🔄 Step 2: Processing data and creating database...")
    process_cmd = [
        sys.executable,
        "process_data.py",
        "--telemetry", "output/telemetry_logs.jsonl",
        "--employees", "output/employees.csv"
    ]
    
    if not run_command(process_cmd, "Process data"):
        print("\n❌ Failed to process data. Please check the error above.")
        return
    
    # Step 3: Success message
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║                    ✅ Setup Complete!                       ║
    ╚══════════════════════════════════════════════════════════════╝
    
    Your analytics platform is ready! Next steps:
    
    1. 📊 Launch the Dashboard:
       streamlit run dashboard.py
    
    2. 🔌 Start the API (optional):
       python api.py
    
    3. 📖 Read the README for more information:
       See README.md for detailed documentation
    
    The database 'telemetry.db' has been created with your data.
    """)


if __name__ == "__main__":
    main()
