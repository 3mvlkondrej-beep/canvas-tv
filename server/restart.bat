@echo off
title Canvas TV restart
cd /d "%~dp0"
echo Ukoncuji predchozi beh serveru...
taskkill /f /fi "WINDOWTITLE eq Canvas TV server*" >nul 2>&1
powershell -NoProfile -Command "Get-Process python,cloudflared -ErrorAction SilentlyContinue | Where-Object { $_.Path -like '*CanvasTV-server*' } | Stop-Process -Force"
timeout /t 2 >nul
start "" "%~dp0start.bat"
exit
