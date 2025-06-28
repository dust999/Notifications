@echo off
setlocal EnableDelayedExpansion

set "APP_NAME=NotifyApp"
set "INSTALL_DIR=%USERPROFILE%\%APP_NAME%"
set "PYTHON_VERSION=3.13.0"
set "PYTHON_INSTALLER=python-%PYTHON_VERSION%-amd64.exe"
set "PYTHON_URL=https://www.python.org/ftp/python/%PYTHON_VERSION%/%PYTHON_INSTALLER%"
set "PROJECT_FILES=app.pyw utils.py settings_dialog.py notify_list_dialog.py fullscreen_reminder.py add_notify_dialog.py config_static.json config_dynamic.json"
set "DEPENDENCIES=PyQt6"

chcp 65001 >nul

:: Find or install Python
for /f "tokens=*" %%i in ('where python') do (
    set "PYTHON=%%i"
    goto :python_found
)

powershell -Command "Invoke-WebRequest -Uri %PYTHON_URL% -OutFile %TEMP%\%PYTHON_INSTALLER%"
if not exist "%TEMP%\%PYTHON_INSTALLER%" exit /b 1
start /wait "" "%TEMP%\%PYTHON_INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1
del "%TEMP%\%PYTHON_INSTALLER%"
for /f "tokens=*" %%i in ('where python') do (
    set "PYTHON=%%i"
    goto :python_found
)
exit /b 1

:python_found
for %%i in ("%PYTHON%") do set "PYTHON_DIR=%%~dpi"
set "PIP=%PYTHON_DIR%Scripts\pip.exe"

:: Ensure pip is installed and up-to-date
"%PYTHON%" -m ensurepip
"%PYTHON%" -m pip install --upgrade pip
if not exist "%PIP%" exit /b 1

:: Install dependencies
for %%d in (%DEPENDENCIES%) do (
    "%PIP%" install %%d
    if %ERRORLEVEL% neq 0 exit /b 1
)

:: Create installation directory
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

:: Copy project files
for %%f in (%PROJECT_FILES%) do (
    if exist "%%f" (
        copy "%%f" "%INSTALL_DIR%\%%f"
        if %ERRORLEVEL% neq 0 exit /b 1
    )
)

:: Create run script
(
    echo @echo off
    echo cd /d "%INSTALL_DIR%"
    echo "%PYTHON%" app.pyw
) > "%INSTALL_DIR%\run_%APP_NAME%.bat"

:: Create desktop shortcut
powershell -Command ^
    "$WShell = New-Object -ComObject WScript.Shell; " ^
    "$Shortcut = $WShell.CreateShortcut(\"$env:USERPROFILE\Desktop\%APP_NAME%.lnk\"); " ^
    "$Shortcut.TargetPath = \"%INSTALL_DIR%\run_%APP_NAME%.bat\"; " ^
    "$Shortcut.WorkingDirectory = \"%INSTALL_DIR%\"; " ^
    "$Shortcut.Save()"

exit /b 0