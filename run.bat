@echo off
REM Launch AI Root Cause Coach locally.
cd /d "%~dp0"

REM Prefer a local virtual environment if one exists.
if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
)

echo Starting AI Root Cause Coach...
python -m streamlit run app.py

pause
