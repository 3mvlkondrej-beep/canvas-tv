@echo off
chcp 65001 >nul
title Canvas TV server
cd /d "%~dp0"
set PATH=%~dp0;%PATH%
if not exist python\python.exe (
  echo Stahuji Python...
  curl -L -o py.zip https://www.python.org/ftp/python/3.12.8/python-3.12.8-embed-amd64.zip
  mkdir python
  tar -xf py.zip -C python
  del py.zip
)
if not exist yt-dlp.exe (
  echo Stahuji yt-dlp...
  curl -L -o yt-dlp.exe https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe
)
if not exist deno.exe (
  echo Stahuji Deno ^(potrebuje ho yt-dlp pro YouTube^)...
  curl -L -o deno.zip https://github.com/denoland/deno/releases/latest/download/deno-x86_64-pc-windows-msvc.zip
  tar -xf deno.zip
  del deno.zip
)
if not exist cloudflared.exe (
  echo Stahuji cloudflared...
  curl -L -o cloudflared.exe https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe
)
echo Aktualizuji yt-dlp...
yt-dlp.exe -U
python\python.exe server.py
pause
