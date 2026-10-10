@echo off
setlocal
chcp 65001 >nul
set "AC4_ARCH=%PROCESSOR_ARCHITECTURE%"
if defined PROCESSOR_ARCHITEW6432 set "AC4_ARCH=%PROCESSOR_ARCHITEW6432%"
set "AC4_HOST="
if /I "%AC4_ARCH%"=="AMD64" set "AC4_HOST=windows-x64"
if /I "%AC4_ARCH%"=="ARM64" set "AC4_HOST=windows-arm64"
if not defined AC4_HOST (
 echo Unsupported architecture: %AC4_ARCH%
 pause
 exit /b 1
)
set "AC4_PY=%~dp0runtime\%AC4_HOST%\python.exe"
if not exist "%AC4_PY%" (
 echo Bundled Python missing. Extract the whole package first.
 pause
 exit /b 1
)
"%AC4_PY%" -E -s -B "%~dp0player_tools.py" %*
set "AC4_STATUS=%ERRORLEVEL%"
if "%~1"=="" pause
exit /b %AC4_STATUS%
