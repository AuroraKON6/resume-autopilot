@echo off
cd /d "%~dp0"

set "PROJECT_DIR=%CD%"
set "PYTHON_EXECUTABLE=%PROJECT_DIR%\.venv\Scripts\python.exe"
set "APP_JAR=%PROJECT_DIR%\target\npe_get_jobs-v1.1.0.jar"
set "APP_LIB=%PROJECT_DIR%\target\lib"
set "APP_URL=http://127.0.0.1:8081"
set "JAVA_EXE=C:\Program Files\Eclipse Adoptium\jdk-21.0.11.10-hotspot\bin\java.exe"

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
echo.

start "" "%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 12; Start-Process 'http://127.0.0.1:8081'"

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
