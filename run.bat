@echo off
title ADES BIDAI - Dengue Outbreak Prediction ^& Alert System
echo ============================================================
echo   ADES BIDAI - Dengue Outbreak Prediction ^& Alert System
echo   AI-Powered Epidemiological Surveillance Dashboard
echo ============================================================
echo.
set OPENBLAS_NUM_THREADS=1
set MKL_NUM_THREADS=1
set OMP_NUM_THREADS=1
set NUMEXPR_NUM_THREADS=1

echo Launching Streamlit Surveillance Application on port 8501...
cd /d D:\tazki\PROJECT\ADES-BIDAI
"C:\Users\USER\AppData\Local\Python\bin\python.exe" -m streamlit run app.py --server.headless true --server.port 8501
pause
