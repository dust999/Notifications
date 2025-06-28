@echo off
setlocal EnableDelayedExpansion

set "APP_NAME=NotifyApp"
set "INSTALL_DIR=%USERPROFILE%\%APP_NAME%"
set "PROJECT_FILES=app.pyw utils.py settings_dialog.py notify_list_dialog.py fullscreen_reminder.py add_notify_dialog.py config_static.json config_dynamic.json"
set "DEPENDENCIES=PyQt6"

echo ===============================================
echo NotifyApp Installer
echo ===============================================

:: Check if Python is installed and accessible
echo Checking Python installation...
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Python is not installed or not in PATH.
    echo Please install Python from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    start "" "https://www.python.org/downloads/"
    exit /b 1
)

python --version
echo Python found successfully!

:: Check if pip is available
echo Checking pip...
python -m pip --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: pip is not available.
    echo Please reinstall Python with pip included.
    pause
    exit /b 1
)

echo pip found successfully!

:: Install dependencies
echo.
echo Installing dependencies...
for %%d in (%DEPENDENCIES%) do (
    echo Installing %%d...
    python -m pip install %%d
    if %ERRORLEVEL% neq 0 (
        echo ERROR: Failed to install %%d.
        echo Please check your internet connection and try again.
        pause
        exit /b 1
    )
)

:: Create installation directory
echo.
echo Creating installation directory...
if not exist "%INSTALL_DIR%" (
    mkdir "%INSTALL_DIR%"
    if %ERRORLEVEL% neq 0 (
        echo ERROR: Failed to create installation directory.
        pause
        exit /b 1
    )
)

echo Installation directory: %INSTALL_DIR%

:: Copy project files
echo.
echo Copying project files...
set "MISSING_FILES="
for %%f in (%PROJECT_FILES%) do (
    if exist "%%f" (
        echo Copying %%f...
        copy "%%f" "%INSTALL_DIR%\%%f" >nul
        if %ERRORLEVEL% neq 0 (
            echo ERROR: Failed to copy %%f.
            pause
            exit /b 1
        )
    ) else (
        echo WARNING: %%f not found in current directory.
        set "MISSING_FILES=!MISSING_FILES! %%f"
    )
)

if not "!MISSING_FILES!"=="" (
    echo.
    echo Some files were not found:!MISSING_FILES!
    echo The application may not work correctly.
    echo Please ensure all required files are in the current directory.
)

:: Create startup script
echo.
echo Creating startup script...
(
    echo @echo off
    echo cd /d "%INSTALL_DIR%"
    echo python app.pyw
    echo pause
) > "%INSTALL_DIR%\run_%APP_NAME%.bat"

:: Create desktop shortcut
echo Creating desktop shortcut...
powershell -Command "try { $WShell = New-Object -ComObject WScript.Shell; $Shortcut = $WShell.CreateShortcut(\"$env:USERPROFILE\Desktop\%APP_NAME%.lnk\"); $Shortcut.TargetPath = \"%INSTALL_DIR%\run_%APP_NAME%.bat\"; $Shortcut.WorkingDirectory = \"%INSTALL_DIR%\"; $Shortcut.Description = 'NotifyApp - Notification Manager'; $Shortcut.Save(); Write-Output 'Desktop shortcut created successfully.' } catch { Write-Output 'Failed to create desktop shortcut.' }"

echo.
echo ===============================================
echo Installation completed!
echo ===============================================
echo.
echo Application installed to: %INSTALL_DIR%
echo Desktop shortcut created: %USERPROFILE%\Desktop\%APP_NAME%.lnk
echo.
echo You can run the application by:
echo 1. Double-clicking the desktop shortcut
echo 2. Running: %INSTALL_DIR%\run_%APP_NAME%.bat
echo 3. Going to %INSTALL_DIR% and running: python app.pyw
echo.
pause