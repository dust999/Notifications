@echo off
setlocal

rem Installs the Python packages Notify needs, puts a shortcut on the desktop and starts the app.
rem The app runs from this folder: nothing is copied elsewhere, so the shortcut
rem always starts the current version (older installers copied a few files to
rem %USERPROFILE%\NotifyApp, and that copy went stale and broke).

set "APP_DIR=%~dp0"
set "SHORTCUT=%USERPROFILE%\Desktop\Notify.lnk"

echo ===============================================
echo Notify installer
echo ===============================================

python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed or not in PATH.
    echo Install it from https://www.python.org/downloads/ and tick "Add Python to PATH".
    start "" "https://www.python.org/downloads/"
    pause
    exit /b 1
)
python --version

python -m pip --version >nul 2>&1
if errorlevel 1 (
    echo pip is not available. Reinstall Python with pip included.
    pause
    exit /b 1
)

echo.
echo Installing what Notify needs (requirements.txt)...
python -m pip install --upgrade -r "%APP_DIR%requirements.txt"
if errorlevel 1 (
    echo Couldn't install the packages. Check your internet connection and try again.
    pause
    exit /b 1
)

echo.
echo Creating the desktop shortcut...
powershell -NoProfile -Command "$s = (New-Object -ComObject WScript.Shell).CreateShortcut('%SHORTCUT%'); $s.TargetPath = '%APP_DIR%Start.bat'; $s.WorkingDirectory = '%APP_DIR%'; $s.IconLocation = '%APP_DIR%icons\notify.ico,0'; $s.WindowStyle = 7; $s.Description = 'Notify - reminders in the tray'; $s.Save()"

if exist "%USERPROFILE%\NotifyApp\run_NotifyApp.bat" (
    echo.
    echo Note: an old copy from a previous installer is in %USERPROFILE%\NotifyApp
    echo and its shortcut NotifyApp.lnk is on the desktop. They are no longer needed.
)

echo.
echo Done. Starting Notify - look for the bell in the tray.
echo Next time, start it with the "Notify" shortcut on your desktop.
rem Start.bat ends with "exit", which also closes this window
call "%APP_DIR%Start.bat"
