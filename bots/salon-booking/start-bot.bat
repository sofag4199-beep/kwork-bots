@echo off
chcp 65001 >nul
cd /d "%~dp0bots\salon-booking"

echo.
echo  Запуск бота Beauty Studio...
echo.

if not exist ".env" (
    echo  ОШИБКА: нет файла .env с токеном!
    pause
    exit /b 1
)

python -m pip install -r requirements.txt -q
python bot.py

pause
