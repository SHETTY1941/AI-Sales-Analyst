import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from .ai_service import generate_sql, summarize_results, ai_status
from .query_engine import discover_schema, validate_and_execute, chart_metadata
from . import analytics
from .database import ensure_database

app = FastAPI(
    title="Mini AI Business Intelligence Assistant",
    version="2.0.0",
    description=(
        "Schema-aware natural-language-to-SQL analytics using Gemini/Groq, "
        "validated read-only SQLite execution, and dynamic visualizations."
    ),
)

# Restrict browser access to local development frontends plus explicitly configured origins.
_allowed_origins = [
    "http://localhost:5173", "http://127.0.0.1:5173",
    "http://localhost:4173", "http://127.0.0.1:4173",
]
_allowed_origins.extend(
    origin.strip() for origin in os.getenv("CORS_ORIGINS", "").split(",") if origin.strip()
)
app.add_middleware(
    CORSMiddleware, allow_origins=_allowed_origins, allow_credentials=False,
    allow_methods=["GET", "POST"], allow_headers=["Content-Type"],
)


class AskRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=1000)
    history: list[dict] = Field(default_factory=list, max_length=8)

    @field_validator("question")
    @classmethod
    def question_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Please enter a meaningful question.")
        return value


@app.on_event("startup")
def startup():
    ensure_database()


@app.get("/health")
def health():
    return {"status": "ok", "service": "mini-ai-bi-assistant"}


@app.get("/ai-status")
def get_ai_status():
    return ai_status()


@app.get("/dashboard")
def get_dashboard():
    return analytics.dashboard_summary()


@app.get("/data-quality")
def get_data_quality():
    return analytics.data_quality()


@app.get("/schema")
def get_schema():
    """Expose discovered table/column metadata to the local analytics UI."""
    return discover_schema()


@app.post("/ask")
def ask(request: AskRequest):
    question = request.question
    try:
        schema = discover_schema()
        # Keep only short, relevant conversational context; never trust it as SQL.
        history = []
        for item in request.history[-6:]:
            if isinstance(item, dict):
                history.append({
                    "question": str(item.get("question", ""))[:500],
                    "answer": str(item.get("answer", ""))[:700],
                })

        plan, provider = generate_sql(question, schema, history)
        if plan is None:
            status = ai_status()
            if not status["gemini_configured"] and not status["groq_configured"]:
                detail = (
                    "No usable AI key was loaded. Put a real GEMINI_API_KEY and/or GROQ_API_KEY "
                    "in the project-root .env file (next to requirements.txt), then restart Uvicorn. "
                    "Do not use placeholder values such as YOUR_NEW_GROQ_KEY. Check GET /ai-status."
                )
            else:
                detail = (
                    f"AI keys were detected, but the configured model request failed ({provider}). "
                    "Check that the key is valid and not revoked, that the model name is available "
                    "to your account, and that your internet connection/quota is working. "
                    "For a Gemini-only test set AI_PROVIDER=gemini; for Groq-only set AI_PROVIDER=groq, "
                    "then restart Uvicorn."
                )
            raise HTTPException(status_code=503, detail=detail)
        if not plan.get("sql"):
            raise HTTPException(
                status_code=422,
                detail=("I could not answer that from the available sales tables and columns. "
                        "Try asking about fields shown in the database schema."),
            )

        rows, columns, executed_sql = validate_and_execute(plan["sql"], plan.get("parameters", []))
        chart = chart_metadata(plan, rows, columns)
        summary, summary_provider = summarize_results(question, executed_sql, rows, schema)
        return {
            "question": question,
            "answer": summary["answer"],
            "insights": summary["insights"],
            "limitations": summary["limitations"],
            "rows": rows,
            "columns": columns,
            "row_count": len(rows),
            "chart": chart,
            "sql": executed_sql,
            "interpretation_source": provider,
            "summary_source": summary_provider,
            "execution_source": "Local SQLite (read-only)",
        }
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        # Do not expose internal exception details or local database paths.
        raise HTTPException(status_code=500, detail="The analysis could not be completed. Please try again.") from exc
