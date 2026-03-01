@echo off
title YT Downloader
echo.
echo  ============================
echo   YT Downloader - Setup
echo  ============================
echo.
echo  [1/2] Install / update dependencies...
pip install -r requirements.txt --quiet
echo.
echo  [2/2] Menjalankan server di http://localhost:5000
echo         Browser akan terbuka otomatis...
echo.
echo  Tekan Ctrl+C untuk berhenti.
echo.
python app.py
pause
