@echo off
cd /d "%~dp0"
py -3.11 iniciar.py
if errorlevel 1 pause
