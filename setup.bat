@echo off
REM Setup script for PHP RAG Assistant (Windows)

setlocal enabledelayedexpansion

echo.
echo ╔════════════════════════════════════════════════════════╗
echo ║  PHP RAG Assistant - Setup Script                     ║
echo ║  Version 1.0 (Windows)                                ║
echo ╚════════════════════════════════════════════════════════╝
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
	echo ❌ Python is not installed or not in PATH
	echo Please install Python 3.8+ from https://www.python.org
	echo Make sure to check "Add Python to PATH" during installation
	pause
	exit /b 1
)

for /f "tokens=*" %%i in ('python --version') do set PYTHON_VERSION=%%i
echo ✓ Python found: %PYTHON_VERSION%

REM Step 1: Create virtual environment
set VENV_DIR=venv
echo.
echo ════════════════════════════════════════════════════════
echo 📦 Creating virtual environment...
echo ════════════════════════════════════════════════════════

if exist "%VENV_DIR%" (
	echo ✓ Virtual environment already exists at %VENV_DIR%\
) else (
	python -m venv %VENV_DIR%
	if errorlevel 1 (
		echo ❌ Failed to create virtual environment
		pause
		exit /b 1
	)
	echo ✓ Virtual environment created
)

REM Step 2: Activate virtual environment
call %VENV_DIR%\Scripts\activate.bat
if errorlevel 1 (
	echo ❌ Failed to activate virtual environment
	pause
	exit /b 1
)
echo ✓ Virtual environment activated

REM Step 3: Upgrade pip
echo.
echo ════════════════════════════════════════════════════════
echo 📦 Upgrading pip, setuptools, and wheel...
echo ════════════════════════════════════════════════════════

python -m pip install --upgrade pip setuptools wheel >nul 2>&1
if errorlevel 1 (
	echo ⚠ pip upgrade had issues, continuing anyway...
) else (
	echo ✓ pip upgraded successfully
)

REM Step 4: Install requirements
echo.
echo ════════════════════════════════════════════════════════
echo 📦 Installing Python dependencies...
echo ════════════════════════════════════════════════════════
echo (This may take 5-10 minutes)
echo.

python -m pip install -r requirements.txt
if errorlevel 1 (
	echo ❌ Failed to install dependencies
	pause
	exit /b 1
)
echo ✓ Dependencies installed successfully

REM Step 5: Create directories
echo.
echo ════════════════════════════════════════════════════════
echo 📁 Creating project directories...
echo ════════════════════════════════════════════════════════

if not exist "data\laravel-crm-2.2" mkdir data\laravel-crm-2.2
if not exist "vectorstore" mkdir vectorstore

echo ✓ Created data\laravel-crm-2.2
echo ✓ Created vectorstore

REM Success message
echo.
echo ╔════════════════════════════════════════════════════════╗
echo ║     Setup Completed Successfully! ✓                   ║
echo ╚════════════════════════════════════════════════════════╝
echo.

echo 📋 Next Steps:
echo.
echo 1. ✓ Virtual environment is ALREADY ACTIVATED
echo   (You see "(venv)" at the start of your terminal)
echo.
echo 2. ADD YOUR PHP FILES:
echo   Copy your PHP files to: data\laravel-crm-2.2\
echo.
echo 3. INGEST DATA:
echo   python ingest.py
echo.
echo 4. RUN STREAMLIT APP:
echo   streamlit run app.py
echo.
echo 📚 Full documentation at: README.md
echo ⚡ Quick start guide at: QUICKSTART.md
echo.
echo ════════════════════════════════════════════════════════
echo.
echo Press any key to close this window...
pause >nul
