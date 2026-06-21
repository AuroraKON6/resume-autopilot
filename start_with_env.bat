@echo off
REM npe_get_jobs 启动脚本（带环境变量配置）

REM 从环境变量读取API Key，如果没有设置则使用默认值
if "%DEEPSEEK_API_KEY%"=="" (
    echo 警告: 未设置DEEPSEEK_API_KEY环境变量
    echo 请运行: set DEEPSEEK_API_KEY=your_api_key
    echo 或创建.env文件
    pause
    exit /b 1
)

if "%DEEPSEEK_BASE_URL%"=="" (
    set DEEPSEEK_BASE_URL=https://api.deepseek.com
)

if "%DEEPSEEK_MODEL%"=="" (
    set DEEPSEEK_MODEL=deepseek-v4-flash
)

echo ==========================================
echo 启动 npe_get_jobs
echo AI 模型: DeepSeek V4 Flash
echo 端口: 8081
echo ==========================================

java -Xms512m -Xmx1024m -Dloader.path=target/lib -jar target/npe_get_jobs-v1.1.0.jar
