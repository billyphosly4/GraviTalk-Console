@echo off
:: ==============================================================================
:: Script Name: setup_windows.bat
:: Description: Automated setup script for GraviTalk on Windows.
::              Configures Python virtual environment and installs dependencies.
:: ==============================================================================

echo ========================================================
echo  GraviTalk Console: Windows Setup Script
echo ========================================================
echo.

:: 1. Verify Python is installed and in path
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python was not found in your system PATH.
    echo Please install Python from https://www.python.org/
    echo and make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

:: 2. Create Python virtual environment
echo [INFO] Creating Python virtual environment in 'venv' folder...
python -m venv venv
if %errorlevel% neq 0 (
    echo [ERROR] Failed to create virtual environment.
    echo.
    pause
    exit /b 1
)

:: 3. Activate and install pip packages
echo [INFO] Activating virtual environment and installing packages (flask, requests, psutil)...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install requests psutil flask

if %errorlevel% neq 0 (
    echo [ERROR] Failed to install pip packages.
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================================
echo  Setup Complete!
echo ========================================================
echo  - Python virtual environment is created.
echo  - Necessary libraries are successfully installed.
echo.
echo  Next Steps to Run:
echo  1. Download and install Ollama for Windows:
echo     https://ollama.com/download/windows
echo.
echo  2. Open Command Prompt and download the default model:
echo     ollama pull phi3:mini
echo.
echo  3. Launch the Web Console:
echo     venv\Scripts\activate.bat
echo     python app.py
echo.
echo  4. Open in your browser:
echo     http://localhost:5000
echo ========================================================
echo.
pause
