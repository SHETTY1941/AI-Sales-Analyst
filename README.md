# AI Sales Analyst — Natural Language to SQL

A full-stack, schema-aware AI analyst for the supplied sales CSV. Users can ask questions in ordinary language instead of choosing from a fixed list of predefined analytics. Gemini or Groq reads the live database schema, proposes a SQLite query, and the FastAPI backend validates and executes that query locally in read-only mode. The React dashboard presents the grounded result as a written explanation, dynamic chart, result table, and inspectable SQL.

## Interface experience

The Sales Intelligence interface is organized into three clearly separated destinations: **AI Analyst** (natural-language questions and grounded results), **Overview** (sales KPIs, monthly revenue, regions, products, and category charts), and **Data Quality** (valid/excluded row counts and data-health percentage). The layout uses responsive navigation, consistent typography, clear section headings, and a restrained navy/teal visual system.

## Core capabilities

- **Open-ended questions over available data:** totals, averages, rankings, comparisons, date filters, category/region/product breakdowns, outliers, trends, and multi-step aggregations—as long as the requested information is represented in the available tables.
- **Schema discovery:** reads table names, columns, types, and foreign-key relationships from SQLite at runtime. It does not rely on a hardcoded list of supported questions.
- **Natural-language SQL planning:** Gemini or Groq generates one SQLite `SELECT` query and typed query parameters from the user's question and schema.
- **Local execution:** the SQL runs on the user's local SQLite database, not on the model provider's servers.
- **Grounded explanations:** the model summarizes only the rows returned by SQLite. Exact result rows are also displayed so users can verify the explanation.
- **Dynamic visualizations:** chart type and axes are selected for the returned data (bar, line, area, pie, table, or scalar result).
- **Follow-up context:** the frontend sends a short recent conversation history for questions such as "now show only the South region".
- **Data quality:** invalid source rows are retained with an issue description and excluded from normal completed-sales analytics by default.

The system can answer any question that can meaningfully be answered from the available schema and records; it cannot infer information absent from the data. For example, customer sentiment cannot be calculated if the dataset contains no customer comments or review text.

## Architecture

```text
Sales CSV → validation/import → local SQLite database
                                  ↑
User → React dashboard → FastAPI /ask
                         ↓
              Discover schema + relationships
                         ↓
              Gemini / Groq query planner
                         ↓
              JSON: SQL + bound parameters + chart hint
                         ↓
              SQL safety validation / SQLite authorizer
                         ↓
              Local read-only SQLite execution
                         ↓
              Actual rows → AI grounded explanation
                         ↓
              JSON result → React chart + table + SQL
```

## Technology

- Python 3.10+, FastAPI, Uvicorn, Pydantic
- SQLite relational database
- Google Gemini API (`gemini-3.5-flash-lite`) and Groq API (`llama-3.3-70b-versatile` default)
- React + Vite, Recharts, Framer Motion, Lucide React
- Python `unittest` and FastAPI TestClient

## Setup

Create and activate a virtual environment:

```bash
python -m venv .venv
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
# macOS/Linux:
source .venv/bin/activate
```

Install Python dependencies and create your environment file:

```bash
pip install -r requirements.txt
cp .env.example .env
```

Open the `.env` file in the project root (the same folder as `requirements.txt` and `backend/`) and add at least one API key. The backend also supports `backend/.env`, but the project-root `.env` is recommended. Gemini key: https://aistudio.google.com/app/apikey . Groq key: https://console.groq.com/keys . Never paste API keys into frontend code or commit `.env`.

Example:

```dotenv
AI_PROVIDER=auto
GEMINI_API_KEY=your_gemini_key
GROQ_API_KEY=your_groq_key
GEMINI_MODEL=gemini-3.5-flash-lite
GROQ_MODEL=llama-3.3-70b-versatile
```

Provider selection:

| `AI_PROVIDER` | Behavior |
|---|---|
| `auto` | Try Gemini first, then Groq if Gemini is unavailable or returns an invalid response. |
| `gemini` | Use Gemini only. |
| `groq` | Use Groq only. |

If both keys are configured, `auto` uses Gemini first and Groq as a fallback. Model API calls require internet access and may be subject to provider rate limits or charges. The app deliberately does not silently fall back to a fixed-intent parser: when no AI provider is ready, it explains how to configure one.

## Run the application (one command)

### Linux / macOS (recommended)

1. Open a terminal in the extracted project folder (the folder containing `requirements.txt`).
2. Copy `.env.example` to `.env` if it does not already exist, then add at least one real API key to `.env`.
3. Run:

```bash
chmod +x start.sh
./start.sh
```

`start.sh` locates the project root automatically even if launched from another working directory, creates/reuses a Python virtual environment, installs Python and React dependencies when needed, creates the frontend `.env` with only the backend URL, starts FastAPI, waits for its health endpoint, and then starts Vite. Press `Ctrl+C` to stop the app.

### Windows

1. Add your API key to the project-root `.env` file.
2. Double-click `start.bat` (or run `start.bat` from Command Prompt). It opens separate backend and frontend terminals.

### Manual start (optional)

Run both commands from the project root in separate terminals:

```bash
# Terminal 1 — project root
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2 — frontend folder
cd frontend-react
npm install
npm run dev -- --host 127.0.0.1
```

Open http://localhost:5173 . On first backend startup, `data/sales_data.csv` is imported into `sales.db` automatically. The API defaults to http://127.0.0.1:8000 . The backend loads `.env` relative to the project files, not the terminal's current directory. Do not put Gemini/Groq secrets in `frontend-react/.env`.

## API endpoints

- `GET /health` — backend health.
- `GET /ai-status` — provider readiness; never returns API keys.
- `GET /schema` — live database schema, column types, and foreign-key metadata.
- `GET /dashboard` — predefined dashboard aggregates for the landing page.
- `GET /data-quality` — source-row validation summary.
- `POST /ask` — dynamic natural-language analytics.
- `GET /docs` — interactive FastAPI documentation.

Example request:

```json
{
  "question": "Which five products generated the most net revenue in the South region?",
  "history": []
}
```

The response includes `answer`, `insights`, `rows`, `columns`, `row_count`, `chart`, `sql`, `interpretation_source`, `summary_source`, and `execution_source`. `chart` contains a validated chart type, title, x-axis key, and numeric series keys. `history` is optional and carries a small amount of recent question/answer context for follow-up questions.

## SQL safety and data grounding

The LLM does **not** receive a database connection, database file, or credentials. It receives only the discovered schema, business metric definitions, the question, and limited conversation context. It returns a structured SQL proposal. Before execution, the backend:

1. Requires exactly one `SELECT` or `WITH ... SELECT` statement.
2. Rejects DDL, DML, PRAGMA, attach/detach, multiple statements, and prohibited operations.
3. Uses SQLite `?` placeholders and separately supplied scalar parameters for filter values.
4. Opens the database using SQLite read-only mode.
5. Installs a SQLite authorizer that permits reads only from discovered application tables/views and denies writes, schema changes, internal SQLite tables, and dangerous functions.
6. Applies a query progress limit and caps returned rows at 500.
7. Returns actual rows and columns; the answer summary is generated from those returned rows, not from model memory.

For ordinary business-performance questions on `sales_transactions`, the AI is instructed to use rows where `data_quality_issue IS NULL`. If a user explicitly asks about invalid, rejected, or cancelled records, the AI can query those rows for a data-quality analysis. Revenue is `quantity * unit_price - discount_amount`.

This is a strong assessment-oriented safety baseline, not a substitute for a production SQL sandbox. For production, add query timeouts at the process level, stricter function allowlists, pagination, rate limiting, authentication, audit logs, and adversarial prompt-injection tests.

## Tests

Run from the project root:

```bash
python -m unittest discover -s tests -v
```

Tests cover CSV validation, deterministic dashboard analytics, schema discovery, read-only SQL execution, prohibited SQL, internal table denial, API response structure, provider status, and mocked dynamic AI responses. Tests do not make live Gemini or Groq calls and therefore do not consume API credits.

## Project structure

```text
backend/
  ai_service.py       # Gemini/Groq SQL planning and grounded result summaries
  query_engine.py    # schema discovery, SQL safety, local execution, chart metadata
  database.py        # CSV validation and SQLite import
  analytics.py       # deterministic dashboard aggregates and data quality
  main.py            # FastAPI routes and orchestration
data/
  sales_data.csv
frontend-react/
  src/App.jsx         # React dashboard, dynamic AI answer/chart/table
  src/styles.css
  package.json
tests/
  test_analytics.py
  test_api.py
  test_query_engine.py
```

## Known boundaries

- The AI can only answer questions supported by actual tables, columns, and data. It must say when a requested metric or field is unavailable.
- The supplied CSV currently imports into one sales table. Schema discovery is dynamic and will include additional tables and declared foreign keys if they are added to the SQLite database.
- The current project has no login, role-based permissions, or multi-user production deployment.
- Live AI features require a valid Gemini or Groq API key and internet connectivity.
- Review and understand the generated SQL and outputs before presenting the project; no AI-generated query should be treated as automatically correct.

## Git submission

The project has a local Git repository. Set your own Git author identity, commit, and push to your own GitHub repository:

```bash
git config user.name "YOUR_NAME"
git config user.email "YOUR_EMAIL"
git add -A
git commit -m "Build schema-aware AI Sales Analyst"
git remote add origin https://github.com/YOUR_USERNAME/mini-ai-bi-assistant.git
git push -u origin main
```

Commit `.env.example`, never `.env`.
