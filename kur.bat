@echo off
rem viztools kurulumu: vizrt-reji skill'ini bu kullanicinin Claude klasorune kurar
cd /d "%~dp0"
python kur.py %*
pause
