@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

set "SKIP_TEST=0"
set "SKIP_PIP=0"
set "SKIP_REBUILD=0"
for %%a in (%*) do (
    if /I "%%~a"=="--no-test" set "SKIP_TEST=1"
    if /I "%%~a"=="/no-test" set "SKIP_TEST=1"
    if /I "%%~a"=="--no-pip" set "SKIP_PIP=1"
    if /I "%%~a"=="/no-pip" set "SKIP_PIP=1"
    if /I "%%~a"=="--no-rebuild" set "SKIP_REBUILD=1"
    if /I "%%~a"=="/no-rebuild" set "SKIP_REBUILD=1"
    if /I "%%~a"=="--fast" (
        set "SKIP_TEST=1"
        set "SKIP_PIP=1"
        set "SKIP_REBUILD=1"
    )
    if /I "%%~a"=="/fast" (
        set "SKIP_TEST=1"
        set "SKIP_PIP=1"
        set "SKIP_REBUILD=1"
    )
)

title eGOdary - update and run

echo.
echo ============================================
echo   eGOdary - update catalogs and run
echo ============================================
echo   Flags: --no-pip --no-rebuild --no-test --fast (= all three)
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
if "!SKIP_PIP!"=="0" (
    echo [1/4] Installing / updating package...
    %PYTHON_CMD% -m pip install -e ".[dev]" --no-build-isolation
    if errorlevel 1 (
        echo [ERROR] pip install failed.
        goto :fail
    )
) else (
    echo [1/4] Package install skipped - flag --no-pip
)

echo.
if "!SKIP_REBUILD!"=="0" (
    echo [2/4] Rebuilding content catalogs...
    set "BUILD_ERR=0"

    call :build_script "scripts\build_character_catalog.py"
    if errorlevel 1 set "BUILD_ERR=1"

    call :build_script "scripts\build_outfit_catalog.py"
    if errorlevel 1 set "BUILD_ERR=1"

    call :build_script "scripts\build_appearance_catalog.py"
    if errorlevel 1 set "BUILD_ERR=1"

    call :build_script "scripts\build_clothing_state_catalog.py"
    if errorlevel 1 set "BUILD_ERR=1"

    call :build_script "scripts\build_pose_catalog.py"
    if errorlevel 1 set "BUILD_ERR=1"

    call :build_script "scripts\build_fetish_catalog.py"
    if errorlevel 1 set "BUILD_ERR=1"

    call :build_script "scripts\build_face_catalog.py"
    if errorlevel 1 set "BUILD_ERR=1"

    call :build_script "scripts\build_camera_catalog.py"
    if errorlevel 1 set "BUILD_ERR=1"

    call :build_script "scripts\build_lighting_catalog.py"
    if errorlevel 1 set "BUILD_ERR=1"

    call :build_script "scripts\build_environment_catalog.py"
    if errorlevel 1 set "BUILD_ERR=1"

    call :build_script "scripts\build_style_catalog.py"
    if errorlevel 1 set "BUILD_ERR=1"

    call :build_script "scripts\build_tag_tooltips_ru.py"
    if errorlevel 1 set "BUILD_ERR=1"

    if "!BUILD_ERR!"=="1" (
        echo.
        echo [ERROR] One or more catalog rebuild scripts failed.
        goto :fail
    )
) else (
    echo [2/4] Catalog rebuild skipped - flag --no-rebuild
)

if "!SKIP_TEST!"=="0" (
    echo.
    echo [3/4] Running tests...
    %PYTHON_CMD% -m pytest -q
    if errorlevel 1 (
        echo.
        echo [ERROR] Tests failed. Server was not started.
        echo To skip tests: update_and_run.bat --no-test ^(or --fast to skip pip+rebuild+test^)
        goto :fail
    )
) else (
    echo.
    echo [3/4] Tests skipped - flag --no-test
)

echo.
echo [4/4] Starting web UI...
echo Open in browser: http://127.0.0.1:8000/
echo Stop server: Ctrl+C
echo.

start "" "http://127.0.0.1:8000/"
%PYTHON_CMD% -m egodary.cli.main serve

REM Note: we deliberately do NOT treat a non-zero exit here as a script
REM failure (no [ERROR], no :fail). Stopping the dev server with Ctrl+C is
REM the normal way to end this script, and on Windows that often makes the
REM server process return a non-zero exit code even though nothing actually
REM went wrong - treating it as [ERROR] + pause was confusing ("I press a
REM key and everything just closes"). If the server genuinely failed to
REM start (e.g. port already in use), uvicorn's own error output above is
REM what to look at; the line below just keeps the window open long enough
REM to read it.
echo.
echo Server stopped.
pause
goto :eof

:build_script
echo   - %~1
%PYTHON_CMD% "%~1"
if errorlevel 1 (
    echo     [FAIL] %~1
    exit /b 1
)
exit /b 0

:fail
echo.
pause
exit /b 1
