@echo off
title MY_ISSB_Evaluator - Web Launcher
echo ========================================================
echo        MY_ISSB_Evaluator - Modern Web Stack Launcher
echo        FastAPI Backend (8000) + Lovable React UI (5173)
echo ========================================================
echo.

echo Starting FastAPI Backend on http://localhost:8000 ...
start "MY_ISSB_Evaluator Backend" python -m uvicorn backend.api:app --host 0.0.0.0 --port 8000 --reload

echo Starting Vite Frontend on http://localhost:5173 ...
cd frontend
npm.cmd run dev

pause
