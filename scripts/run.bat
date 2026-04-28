@echo off
:: PromptStash 自动化运行脚本
:: Windows Task Scheduler 调用入口
:: 使用方法: scripts\run.bat
cd /d "%~dp0\.."
python scripts\run.py
pause
