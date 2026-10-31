# Start Here — Sales Intelligence · AI Sales Analyst

## First time only

1. Extract the ZIP file.
2. Open the extracted `ai-bi-assistant` folder.
3. Open `.env` and add your real `GEMINI_API_KEY` and/or `GROQ_API_KEY`. If `.env` is missing, copy `.env.example` and rename the copy to `.env`.
4. Make sure Python 3.10+ and Node.js 18+ are installed.

## Linux / macOS

From the project root, run:

```bash
chmod +x start.sh
./start.sh
```

You can also run it while your terminal is inside `frontend-react` by using:

```bash
../start.sh
```

The launcher finds the correct project root itself, installs missing dependencies, starts the backend and frontend, and waits for the backend health check.

## Windows

Double-click `start.bat` from File Explorer, or run it from Command Prompt.

## Explore the interface

The app opens with a clean sales overview. Use the left navigation to move between **AI Analyst**, **Overview**, and **Data Quality**. The AI Analyst accepts free-form questions and displays grounded explanations, generated SQL, result tables, and charts. The Overview contains KPI cards and sales charts. Data Quality shows validated rows, excluded rows, and the data-health rate.

## Open the app

- Dashboard: http://localhost:5173
- Backend health: http://127.0.0.1:8000/health
- AI key detection: http://127.0.0.1:8000/ai-status
- API documentation: http://127.0.0.1:8000/docs

Keep provider API keys only in the project-root `.env`. Never place them in `frontend-react/.env`, commit them, or share them in chat. If a key was exposed, revoke it and generate a new one.

If the backend fails to start, read `backend.log` in the project root. Press Ctrl+C in the launcher terminal to stop the app.
