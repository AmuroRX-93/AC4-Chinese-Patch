@echo off
setlocal
pushd "%~dp0"
if not exist "runtime\windows-x64\python.exe" goto missing
"runtime\windows-x64\python.exe" -B "install.py" %*
set "AC4_EXIT=%ERRORLEVEL%"
pause
popd
exit /b %AC4_EXIT%
:missing
echo Bundled Python is missing. Extract the entire ZIP first.
pause
popd
exit /b 1
