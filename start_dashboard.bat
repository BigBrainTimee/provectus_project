@echo off
echo Starting Claude Code Analytics Dashboard...
echo.
cd /d "%~dp0"
python -m streamlit run dashboard.py
pause
