@echo off
echo ============================================================
echo Starting OCR Tool for ERP
echo ============================================================
echo.

echo Starting Flask API server on http://localhost:5000
start "OCR API Server" cmd /k "cd /d C:\wamp64\www\OCR_2 && venv\Scripts\activate && python api.py"

timeout /t 5 /nobreak > nul

echo Starting React frontend on http://localhost:5173
start "OCR Frontend" cmd /k "cd /d C:\wamp64\www\OCR_2\frontend && npm run dev"

echo.
echo ============================================================
echo Both servers are starting...
echo.
echo API Server:  http://localhost:5000
echo Frontend:    http://localhost:5173
echo ============================================================
echo.
pause
