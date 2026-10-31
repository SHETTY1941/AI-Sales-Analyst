@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul || (echo Python 3 is required.& pause & exit /b 1)
where node >nul 2>nul || (echo Node.js is required.& pause & exit /b 1)
if not exist .env copy .env.example .env >nul
if not exist .venv\Scripts\python.exe py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (echo Python dependency installation failed.& pause & exit /b 1)
if not exist frontend-react\.env copy frontend-react\.env.example frontend-react\.env >nul
if not exist frontend-react\node_modules\vite\bin\vite.js (cd frontend-react && npm install && cd ..)
if errorlevel 1 (echo npm install failed.& pause & exit /b 1)
start "AI Sales Analyst Backend" cmd /k "cd /d %~dp0 && .venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000"
start "AI Sales Analyst Frontend" cmd /k "cd /d %~dp0frontend-react && npm run dev -- --host 127.0.0.1"
echo Backend: http://127.0.0.1:8000
 echo Frontend: http://localhost:5173
start http://localhost:5173
pause
