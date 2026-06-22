@echo off
cd /d "%~dp0"

set "PROJECT_DIR=%CD%"

if exist "%PROJECT_DIR%\.env" (
    for /f "usebackq eol=# tokens=1,* delims==" %%A in ("%PROJECT_DIR%\.env") do (
        if not "%%A"=="" if not defined %%A set "%%A=%%B"
    )
)

if not defined PYTHON_EXECUTABLE set "PYTHON_EXECUTABLE=%PROJECT_DIR%\.venv\Scripts\python.exe"
if not exist "%PYTHON_EXECUTABLE%" if exist "%PROJECT_DIR%\.venv\Scripts\python.exe" set "PYTHON_EXECUTABLE=%PROJECT_DIR%\.venv\Scripts\python.exe"
if not defined APP_JAR set "APP_JAR=%PROJECT_DIR%\target\npe_get_jobs-v1.1.0.jar"
if not defined APP_LIB set "APP_LIB=%PROJECT_DIR%\target\lib"
if not defined APP_URL set "APP_URL=http://127.0.0.1:8081"
if not defined JAVA_EXE set "JAVA_EXE=C:\Program Files\Eclipse Adoptium\jdk-21.0.11.10-hotspot\bin\java.exe"
if defined PROXY_HOST if defined PROXY_PORT if not defined VISION_PROXY set "VISION_PROXY=http://%PROXY_HOST%:%PROXY_PORT%"
if defined VISION_PROXY if not defined MIMO_PROXY set "MIMO_PROXY=%VISION_PROXY%"

if not exist "%APP_JAR%" goto missing_jar
if not exist "%PYTHON_EXECUTABLE%" goto missing_python
if exist "%JAVA_EXE%" goto start_app
set "JAVA_EXE=java"

:start_app
echo Starting NPE Get Jobs...
echo Project: %PROJECT_DIR%
echo URL: %APP_URL%
echo Python: %PYTHON_EXECUTABLE%
echo Java: %JAVA_EXE%
if defined VISION_MODEL (
    echo Vision model: %VISION_MODEL%
) else (
    echo Vision model: %MIMO_MODEL%
)
echo.

start "" "%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 12; Start-Process '%APP_URL%'"

"%JAVA_EXE%" -Dfile.encoding=UTF-8 -Dloader.path="%APP_LIB%" -jar "%APP_JAR%" --server.port=8081 --playwright.enabled=false

echo.
echo Application stopped or failed. Press any key to close this window.
pause >nul
exit /b %ERRORLEVEL%

:missing_jar
echo Missing application jar:
echo %APP_JAR%
echo.
echo Run Maven package first:
echo mvn -DskipTests package
pause >nul
exit /b 1

:missing_python
echo Missing project Python environment:
echo %PYTHON_EXECUTABLE%
echo.
echo Create .venv and install OCR dependencies before using OCR delivery.
pause >nul
exit /b 1
