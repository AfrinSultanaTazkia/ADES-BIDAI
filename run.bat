@echo off
title ADES BIDAI - Dengue Outbreak Prediction & Constrained Resource Allocation Command
echo ===============================================================================
echo   ADES BIDAI (এডিস বিদায়) - Government Dengue Resource Allocation Command
echo   AI-Driven Surveillance, Constrained Greedy Allocation & Vector-Control Engine
echo ===============================================================================
echo.

set OPENBLAS_NUM_THREADS=1
set MKL_NUM_THREADS=1
set OMP_NUM_THREADS=1
set NUMEXPR_NUM_THREADS=1

cd /d "%~dp0"

echo [1/2] Starting ADES BIDAI FastAPI Server + Bundled React Dashboard on port 8000...
start "" http://localhost:8000
python api.py
pause
