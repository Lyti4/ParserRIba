@echo off
setlocal
cd /d "%~dp0"

if exist ".env" (
    echo .env already exists. Nothing was overwritten.
    echo Edit .env manually if you need to change proxy settings.
    pause
    exit /b 0
)

if not exist ".env.example" (
    echo .env.example was not found.
    pause
    exit /b 1
)

copy ".env.example" ".env" >nul
echo Created .env from .env.example.
echo Open .env in Notepad and fill PARSER_PROXY or PARSER_PROXIES if needed.
pause
