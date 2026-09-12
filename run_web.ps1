Write-Host "========================================================" -ForegroundColor Green
Write-Host "       MY_ISSB_Evaluator - Modern Web Stack Launcher" -ForegroundColor Cyan
Write-Host "       FastAPI Backend (8000) + Lovable React UI (5173)" -ForegroundColor Yellow
Write-Host "========================================================" -ForegroundColor Green
Write-Host ""

Write-Host "Starting FastAPI Backend on http://localhost:8000 ..." -ForegroundColor Cyan
Start-Process python -ArgumentList "-m uvicorn backend.api:app --host 0.0.0.0 --port 8000 --reload"

Write-Host "Starting Vite Frontend on http://localhost:5173 ..." -ForegroundColor Cyan
Set-Location frontend
& npm.cmd run dev
