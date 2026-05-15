@echo off
REM Запуск графового клиента (нужен установленный Python и зависимости из requirements-gui.txt)
cd /d "%~dp0"
python -m gui
pause
