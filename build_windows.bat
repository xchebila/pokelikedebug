@echo off
REM Build PokelikeDebugger.exe for Windows
setlocal

cd /d "%~dp0"

IF NOT EXIST ".venv\Scripts\activate.bat" (
    echo Creating virtual environment...
    python -m venv .venv
)

call .venv\Scripts\activate.bat

echo Installing / updating dependencies...
pip install -r requirements.txt -q

echo Cleaning previous build...
if exist build rmdir /s /q build
if exist dist  rmdir /s /q dist

echo Running PyInstaller...
pyinstaller PokelikeDebugger.spec

echo.
echo Done -- dist\PokelikeDebugger.exe
pause
