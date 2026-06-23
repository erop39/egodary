@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

title eGOdary - prepare transfer package
echo.
echo ============================================
echo   eGOdary - pre-release transfer pack
echo ============================================
echo.

set "PYTHON_CMD="
where python >nul 2>&1 && set "PYTHON_CMD=python"
if not defined PYTHON_CMD (
    where py >nul 2>&1 && set "PYTHON_CMD=py -3"
)
if not defined PYTHON_CMD (
    echo [ERROR] Python not found in PATH.
    goto :fail
)

echo Using: %PYTHON_CMD%
%PYTHON_CMD% --version
if errorlevel 1 goto :fail

echo.
echo [1/6] Installing / updating package...
%PYTHON_CMD% -m pip install -e ".[dev]"
if errorlevel 1 goto :fail

echo.
echo [2/6] Rebuilding catalogs...
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
if "!BUILD_ERR!"=="1" goto :fail

echo.
echo [3/6] Running linters...
%PYTHON_CMD% -m ruff check .
if errorlevel 1 goto :fail

echo.
echo [4/6] Running tests...
%PYTHON_CMD% -m pytest -q
if errorlevel 1 goto :fail

echo.
echo [5/6] Creating transfer archive...
if not exist "release" mkdir "release"
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd-HHmm"') do set "STAMP=%%i"
set "ARCHIVE=release\egodary-transfer-%STAMP%.zip"

powershell -NoProfile -Command ^
  "$src = (Get-Location).Path;" ^
  "$dst = Join-Path $src '%ARCHIVE%';" ^
  "$tmp = Join-Path $src ('release\_stage_' + [Guid]::NewGuid().ToString('N'));" ^
  "New-Item -ItemType Directory -Path $tmp | Out-Null;" ^
  "$exclude = @('.git','.venv','venv','.pytest_cache','.ruff_cache','__pycache__','release','.cursor','.idea','.vscode');" ^
  "Get-ChildItem -Path $src -Force | Where-Object { $exclude -notcontains $_.Name } | ForEach-Object { Copy-Item -Path $_.FullName -Destination $tmp -Recurse -Force };" ^
  "Get-ChildItem -Path $tmp -Recurse -File | Where-Object { $_.Extension -in '.db','.sqlite3','.pyc' } | Remove-Item -Force;" ^
  "if (Test-Path $dst) { Remove-Item $dst -Force };" ^
  "Compress-Archive -Path (Join-Path $tmp '*') -DestinationPath $dst -CompressionLevel Optimal;" ^
  "Remove-Item -Path $tmp -Recurse -Force;"
if errorlevel 1 goto :fail

echo.
echo [6/6] Done.
echo Archive: %ARCHIVE%
echo Next: follow TRANSFER.md on the target machine.
echo.
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
echo [ERROR] Transfer preparation failed.
pause
exit /b 1
