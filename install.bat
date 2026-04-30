@echo off
chcp 65001 >nul
title 🐟 Установка ParserRIba
echo Установка зависимостей...
pip install -r requirements.txt
echo.
echo Установка браузеров Playwright...
playwright install chromium
echo.
echo ✅ Установка завершена!
echo Теперь запустите start.bat для запуска парсера.
pause
