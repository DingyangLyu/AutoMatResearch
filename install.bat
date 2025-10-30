@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul

echo [INFO] AutoMatResearch Install Script
echo ==========================
echo.

:: 检查Python版本
set "required_version=3.8"
python --version 2>NUL || (
    echo [ERROR] Python not found, please install Python %required_version% or higher, or add python to PATH
    exit /b 1
)

for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do (
    set "full_python_version=%%v"
)
for /f "tokens=1,2 delims=." %%a in ("!full_python_version!") do (
    if "%%b"=="" (
        set "python_version=%%a.0"
    ) else (
        set "python_version=%%a.%%b"
    )
)

:: 版本比较
call :compare_versions "!python_version!" "%required_version%"
if %errorlevel% EQU 0 (
    echo [ERROR] Need Python %required_version% or higher, current version: !python_version!
    exit /b 1
) else (
    echo [OK] Python version check passed: !python_version!
)

:: 检查pip
python -m pip --version >NUL 2>&1 || (
    echo [ERROR] pip not installed, please install pip first
    exit /b 1
)
echo [OK] pip installed
echo.

:: 删除并重新创建虚拟环境（确保pip正确安装）
echo [INFO] Recreating virtual environment to ensure pip is installed...
if exist "venv" (
    echo [INFO] Removing existing virtual environment...
    rmdir /s /q "venv" >NUL 2>&1
)

echo [INFO] Creating virtual environment with pip...
python -m venv --copies --upgrade-deps venv
if !errorlevel! neq 0 (
    echo [INFO] Trying alternative method to create virtual environment...
    python -m venv venv
)

if !errorlevel! equ 0 (
    echo [OK] Virtual environment created
) else (
    echo [ERROR] Virtual environment creation failed
    exit /b 1
)
echo.

:: 激活虚拟环境并安装依赖
echo [INFO] Activating virtual environment and installing dependencies...
call "venv\Scripts\activate.bat" || (
    echo [ERROR] Cannot activate virtual environment
    exit /b 1
)

:: 检查虚拟环境中的pip
echo [INFO] Checking pip in virtual environment...
python -m pip --version >NUL 2>&1
if !errorlevel! neq 0 (
    echo [INFO] Installing pip in virtual environment...
    python -m ensurepip --default-pip || (
        echo [ERROR] Cannot install pip in virtual environment
        call "venv\Scripts\deactivate.bat" >nul 2>&1
        exit /b 1
    )
)

echo [INFO] Upgrading pip...
python -m pip install --upgrade pip || (
    echo [WARNING] pip upgrade failed, continuing with installation...
)

echo [INFO] Installing dependencies...
pip install -e ".[dev]" || (
    echo [ERROR] Dependency installation failed
    call "venv\Scripts\deactivate.bat" >nul 2>&1
    exit /b 1
)

:: 复制环境变量文件
if not exist ".env" (
    echo [INFO] Creating environment file...
    copy ".env.example" ".env" >NUL 2>&1 || (
        echo [WARNING] Cannot create .env file, please manually copy .env.example to .env
    )
    echo [OK] .env file created
    echo [WARNING] Please edit .env file to set your API keys and configuration
) else (
    echo [OK] .env file already exists
)

:: 创建必要的目录
echo [INFO] Creating necessary directories...
if not exist "data" mkdir data
if not exist "data\logs" mkdir "data\logs"
if not exist "data\database" mkdir "data\database"
if not exist "data\exports" mkdir "data\exports"
if not exist "data\insights" mkdir "data\insights"
echo [OK] Directories created
echo.

echo [DONE] Installation completed!
echo.
echo [NEXT] Next steps:
echo 1. Edit .env file, set your DEEPSEEK_API_KEY
echo 2. Activate virtual environment: venv\Scripts\activate
echo 3. Run program: python run.py --mode cli
echo 4. Or start web interface: python run.py --mode web
echo.
echo For more usage, please check README.md

call "venv\Scripts\deactivate.bat" >nul 2>&1
endlocal
exit /b 0

:: 版本比较函数
:compare_versions
set "v1=%~1"
set "v2=%~2"
for /f "tokens=1,2 delims=." %%a in ("%v1%") do (
    set "v1_major=%%a"
    set "v1_minor=%%b"
)
for /f "tokens=1,2 delims=." %%a in ("%v2%") do (
    set "v2_major=%%a"
    set "v2_minor=%%b"
)
if "%v1_minor%"=="" set "v1_minor=0"
if "%v2_minor%"=="" set "v2_minor=0"
if %v1_major% GTR %v2_major% (exit /b 1)
if %v1_major% LSS %v2_major% (exit /b 0)
if %v1_minor% GTR %v2_minor% (exit /b 1)
if %v1_minor% LSS %v2_minor% (exit /b 0)
exit /b 1