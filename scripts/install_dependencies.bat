@echo off
REM 安装Self-Operating Computer依赖

echo ========================================
echo 安装Self-Operating Computer依赖
echo ========================================

REM 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到Python，请先安装Python 3.8+
    pause
    exit /b 1
)

REM 检查pip
pip --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到pip
    pause
    exit /b 1
)

echo.
echo [1/4] 安装基础依赖...
pip install pyautogui pyperclip pillow

echo.
echo [2/4] 安装Self-Operating Computer...
pip install self-operating-computer

echo.
echo [3/4] 安装OpenAI SDK...
pip install openai

echo.
echo [4/4] 验证安装...
python -c "import pyautogui; print('✓ pyautogui 安装成功')"
python -c "from self_operating_computer import operate; print('✓ self-operating-computer 安装成功')"

echo.
echo ========================================
echo 安装完成！
echo ========================================
echo.
echo 使用方法:
echo   1. 设置环境变量: set OPENAI_API_KEY=your_api_key
echo   2. 运行脚本: python scripts\self_operate_deliver.py --platform boss --keyword java --count 5
echo.
echo 注意事项:
echo   1. 需要授予终端屏幕录制和辅助功能权限
echo   2. 需要预先登录各招聘平台
echo   3. 建议在虚拟环境中运行
echo.
pause
