@echo off
rem Arranca Refraccion en desarrollo, sin ventana de consola, con el entorno del proyecto.
cd /d "%~dp0"
if exist ".venv\Scripts\pythonw.exe" (
    start "Refraccion" ".venv\Scripts\pythonw.exe" "%~dp0run.py"
) else (
    echo Falta el entorno del proyecto. Crealo con:
    echo   python -m venv .venv
    echo   .venv\Scripts\pip install -e .[dev]
    pause
)
