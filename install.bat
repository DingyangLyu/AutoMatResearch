@echo off
setlocal enabledelayedexpansion

echo 🚀 AutoMatResearch 安装脚本
echo ==========================
echo.

:: 检查Python版本
set "required_version=3.8"
python --version 2>NUL || (
    echo ❌ Python未安装，请先安装Python %required_version%或更高版本
    exit /b 1
)

for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do (
    set "python_version=%%v"
)
set "python_version=!python_version:~0,3!"

:: 版本比较
call :compare_versions "!python_version!" "%required_version%"
if !errorlevel! lss 0 (
    echo ❌ 需要Python %required_version%或更高版本，当前版本: !python_version!
    exit /b 1
) else (
    echo ✅ Python版本检查通过: !python_version!
)

:: 检查pip
pip --version >NUL 2>&1 || (
    echo ❌ pip未安装，请先安装pip
    exit /b 1
)
echo ✅ pip已安装
echo.

:: 创建虚拟环境
if not exist "venv" (
    echo 📦 创建虚拟环境...
    python -m venv venv
    if !errorlevel! equ 0 (
        echo ✅ 虚拟环境创建完成
    ) else (
        echo ❌ 虚拟环境创建失败
        exit /b 1
    )
) else (
    echo ℹ️  虚拟环境已存在
)
echo.

:: 升级pip并安装依赖
echo 🔄 激活虚拟环境并安装依赖...
call venv\Scripts\activate.bat || (
    echo ❌ 无法激活虚拟环境
    exit /b 1
)

echo ⬆️ 升级pip...
pip install --upgrade pip >NUL 2>&1 || (
    echo ❌ pip升级失败
    exit /b 1
)

echo 📥 进行可编辑安装...
pip install -e ".[dev]" || (
    echo ❌ 依赖安装失败
    exit /b 1
)

:: 复制环境变量文件
if not exist ".env" (
    echo 📝 创建环境变量文件...
    copy .env.example .env >NUL 2>&1 || (
        echo ❌ 无法创建.env文件，请手动复制.env.example到.env
    )
    echo ✅ 已创建.env文件
    echo ⚠️  请编辑.env文件，设置你的API密钥和配置
) else (
    echo ✅ .env文件已存在
)

:: 创建必要的目录
echo 📁 创建必要的目录...
mkdir data\logs >NUL 2>&1
mkdir data\database >NUL 2>&1
mkdir data\exports >NUL 2>&1
mkdir data\insights >NUL 2>&1
echo ✅ 目录创建完成
echo.

echo 🎉 安装完成！
echo.
echo 📋 下一步操作：
echo 1. 编辑.env文件，设置你的DEEPSEEK_API_KEY
echo 2. 激活虚拟环境: venv\Scripts\activate.bat
echo 3. 运行程序: python run.py --mode cli
echo 4. 或者启动Web界面: python run.py --mode web
echo.
echo 💡 更多使用方法请查看README.md

deactivate
endlocal
exit /b 0

:: 版本比较函数
:compare_versions
set "v1=%1"
set "v2=%2"
set "v1=!v1:"=!"
set "v2=!v2:"=!"

for /f "tokens=1,2 delims=." %%a in ("!v1!") do (
    set "v1_major=%%a"
    set "v1_minor=%%b"
)
for /f "tokens=1,2 delims=." %%a in ("!v2!") do (
    set "v2_major=%%a"
    set "v2_minor=%%b"
)

if !v1_major! gtr !v2_major! exit /b 1
if !v1_major! lss !v2_major! exit /b -1
if !v1_minor! gtr !v2_minor! exit /b 1
if !v1_minor! lss !v2_minor! exit /b -1
exit /b 0