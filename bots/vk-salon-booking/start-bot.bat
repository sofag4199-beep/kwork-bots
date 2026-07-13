@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo  VK-бот Beauty Studio (локально)
echo  ================================
echo  Render для VK должен быть ВЫКЛЮЧЕН!
echo.

set PORT=

if not exist .env (
    echo  Создай файл .env из .env.example и вставь VK_TOKEN
    pause
    exit /b 1
)

python -m pip install -r requirements.txt -q
python bot.py
pause
