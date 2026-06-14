@echo off
chcp 65001 >nul
title Nova — AI 私人助手
cd /d "%~dp0"
python nova.py
pause
