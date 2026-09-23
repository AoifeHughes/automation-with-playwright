@echo off
REM Install Playwright and its browser binaries (Windows).
setlocal

cd /d "%~dp0"

echo ==> Creating virtualenv in .venv
python -m venv .venv

echo ==> Installing playwright
.venv\Scripts\python.exe -m pip install --quiet --upgrade pip
.venv\Scripts\python.exe -m pip install --quiet playwright

echo ==> Installing browser binaries (this may take a while)
.venv\Scripts\python.exe -m playwright install chromium

echo.
echo ==> Done. Next steps:
echo     .venv\Scripts\activate.bat
echo     python record.py [url]
echo     python replay.py [script]
