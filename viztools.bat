@echo off
rem viztools: sahne tarama + reji uygulamasi uretme arayuzu (yalnizca 127.0.0.1, sahneye yazmaz)
cd /d "%~dp0"
echo viztools baslatiliyor... Kapatmak icin bu pencereyi kapatin.
python vizscan_web.py
pause
