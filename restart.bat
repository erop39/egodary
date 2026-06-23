@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

set "PORT=8000"
set "NO_RELOAD=0"
if /I "%~1"=="--no-reload" set "NO_RELOAD=1"
if /I "%~1"=="/no-reload" set "NO_RELOAD=1"

title eGOdary - restart

echo.
echo ============================================
echo   eGOdary - restart server
echo ============================================
echo.

set "PYTHON_CMD="
where python >nul 2>&1 && set "PYTHON_CMD=python"
if not defined PYTHON_CMD (
    where py >nul 2>&1 && set "PYTHON_CMD=py -3"
)
if not defined PYTHON_CMD (
    echo [ERROR] Python not found in PATH.
    echo Install Python 3.11+ and add it to PATH.
    goto :fail
)

echo Using: %PYTHON_CMD%
%PYTHON_CMD% --version
if errorlevel 1 goto :fail

echo.
echo [1/2] Stopping server on port %PORT%...
set "KILLED=0"
for /f "tokens=5" %%p in ('netstat -ano 2^>nul ^| findstr ":%PORT% " ^| findstr "LISTENING"') do (
    echo   taskkill PID %%p
    taskkill /F /PID %%p >nul 2>&1
    if not errorlevel 1 set "KILLED=1"
)
if "!KILLED!"=="0" (
    echo   No listening process on port %PORT%.
) else (
    timeout /t 1 /nobreak >nul
)

echo.
echo [2/2] Starting web UI...
echo Open in browser: http://127.0.0.1:%PORT%/
echo Stop server: Ctrl+C
echo.

if "!NO_RELOAD!"=="1" (
    %PYTHON_CMD% -m egodary.cli.main serve --no-reload
) else (
    %PYTHON_CMD% -m egodary.cli.main serve
)

REM See update_and_run.bat for why we don't treat a non-zero exit here as
REM [ERROR] + :fail - stopping with Ctrl+C normally exits non-zero too, and
REM that's not a real failure.
echo.
echo Server stopped.
pause
goto :eof

:fail
echo.
pause
exit /b 1
