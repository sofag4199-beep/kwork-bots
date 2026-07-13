@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo  VK-бот Beauty Studio
echo  ====================
echo.

if not exist .env (
    echo  Создай файл .env из .env.example и вставь VK_TOKEN
    pause
    exit /b 1
)

python -m pip install -r requirements.txt -q
python bot.py
pause
