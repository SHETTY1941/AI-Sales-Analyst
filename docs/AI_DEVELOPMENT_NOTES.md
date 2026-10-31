# AI Tools and Development Notes

> Review this note and make sure it accurately reflects your own work before submitting it.

## 1. AI tools and APIs used

- ChatGPT assistance was used during development to plan the architecture, explain Python/FastAPI/SQLite concepts, draft and review code, design tests, and improve documentation. Review and understand every submitted file.
- Google Gemini API (`gemini-3.5-flash-lite` by default) can convert natural-language analytics questions into schema-grounded SQLite queries and summarize executed results.
- Groq API (`llama-3.3-70b-versatile` by default) provides an alternative/fallback model using an OpenAI-compatible chat-completions interface.
- API credentials are loaded from backend environment variables (`GEMINI_API_KEY`, `GROQ_API_KEY`) and are not hard-coded or sent to React.

## 2. Runtime AI workflow

The application does not classify questions into a fixed list of analytics intents. At request time it discovers the actual SQLite schema, including table names, columns, data types, and foreign-key relationships. The selected LLM receives that metadata, business metric definitions, the natural-language question, and limited recent conversation context. It returns structured JSON with one SQLite `SELECT` statement, bound parameters, and visualization hints.

The backend—not the LLM—validates and executes the query. SQLite is opened read-only, an authorizer blocks writes and prohibited operations, internal SQLite tables are inaccessible, and the result set is capped. The actual returned rows are then passed to the LLM for a concise explanation. The UI displays those rows and the executed SQL so the user can verify the answer.

With `AI_PROVIDER=auto`, Gemini is attempted first and Groq is the fallback. If no provider is ready, the API reports a configuration error instead of silently reverting to a limited rule-based question parser.

## 3. Safety and reliability decisions

1. **Schema grounding:** model-generated SQL must use discovered tables and columns. Unsupported questions should return an empty SQL proposal rather than inventing fields.
2. **Read-only execution:** only one `SELECT` or `WITH ... SELECT` is accepted. SQLite read-only mode and an authorizer provide defense in depth.
3. **Parameter binding:** user-supplied filter values should be passed using SQLite placeholders (`?`) and a separate parameter array.
4. **Data quality:** invalid CSV rows remain inspectable but are excluded from normal sales calculations through `data_quality_issue IS NULL`.
5. **Grounded explanations:** the answer model sees only the actual query result rows and must not invent numbers or unsupported causes.
6. **Visualization:** chart metadata is checked against actual returned columns; invalid or unsuitable chart requests fall back to a table/scalar result.
7. **Provider independence:** both Gemini and Groq can be configured; tests mock provider output and do not spend API credits.

## 4. Testing

Automated tests cover CSV validation, dashboard aggregates, schema discovery, successful read-only SQL, blocked write/multi-statement/internal-table queries, dynamic `/ask` orchestration, provider status, and invalid request shapes. Live model calls are not part of the automated suite.

## 5. Current limitations and next improvements

- Answers remain bounded by the data actually present in the database; absent fields or text cannot be inferred.
- The supplied dataset currently imports as one table. The schema discovery and foreign-key inspection support adding more related tables.
- A production deployment should add authentication, per-user authorization, process-level query timeouts, stricter SQL/function allowlists, rate limiting, audit logging, pagination, and prompt-injection/red-team testing.
- More chart types, downloadable reports, CSV upload previews, and user-defined metric definitions can be added later.
