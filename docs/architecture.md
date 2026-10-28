# Architecture: how ApprendreAI works

This document follows a single click of **Analyze** through the whole system, then explains the concepts involved. File paths are relative to the repo root.

## The big picture

```text
 Your browser
   │  1. GET http://localhost:3000             → Next.js sends the page (HTML + JS)
   │  2. POST http://localhost:8000/api/v1/analyze   (JSON)
   ▼
 FastAPI backend (container "backend")
   │  3. validate request (Pydantic)
   │  4. call OpenAI with prompt + JSON schema ──────────► OpenAI API
   │  5. validate structured reply (Pydantic)  ◄──────────
   │  6. INSERT INTO model_runs ─────────────────────────► PostgreSQL (container "db")
   ▼
 7. JSON response → browser renders results
```

The three boxes you run yourself (frontend, backend, db) are separate **Docker containers** started together by **Docker Compose**.

## What happens when I click Analyze?

1. **You type a passage.** Each keystroke calls `setText(...)` in `frontend/src/app/page.tsx`, which stores the text in React state.

2. **You click Analyze.** The form's `onSubmit` handler, `handleSubmit` (also in `page.tsx`), runs. It stops the browser's default full-page form submission, rejects empty input immediately, sets `isLoading = true` (the button shows "Analyzing…") and calls `analyzePassage(text)`.

3. **The frontend sends an HTTP POST.** `analyzePassage` in `frontend/src/lib/api.ts` calls `fetch("http://localhost:8000/api/v1/analyze", { method: "POST", body: JSON.stringify({ text }) })`. Because the page came from `localhost:3000` and the API is on `localhost:8000`, the browser first checks **CORS**: it asks the backend whether this origin is allowed. `backend/app/main.py` answers yes only for origins listed in `BACKEND_CORS_ORIGINS`.

4. **FastAPI routes the request.** FastAPI matches `POST /api/v1/analyze` to the `analyze` function in `backend/app/api/routes/analyze.py`. Before running it, FastAPI resolves its **dependencies** (`Depends(...)`):
   - `get_llm_service` (`backend/app/api/dependencies.py`) returns the shared `FrenchAnalysisLLM` object
   - `get_db` (`backend/app/db/session.py`) opens a database session for this request
   - `get_settings` (`backend/app/core/config.py`) returns configuration

5. **Pydantic validates the request.** The parameter `request: AnalyzeRequest` tells FastAPI to parse the JSON body into `AnalyzeRequest` (`backend/app/schemas/analysis.py`). The text is trimmed and must be 1–2000 characters. If not, FastAPI replies `422` automatically and our function never runs (so no LLM cost).

6. **The service calls the LLM.** The route calls `analyze_passage(...)` in `backend/app/services/analysis_service.py`. It starts a timer and calls `llm.analyze(text)` in `backend/app/services/llm_service.py`, which makes the actual call:
   ```python
   client.responses.parse(model=..., instructions=SYSTEM_INSTRUCTIONS,
                          input=build_user_input(text), text_format=AnalysisResult)
   ```
   The prompt comes from `backend/app/prompts/french_analysis.py` (version `french_analysis_v1`). `text_format=AnalysisResult` makes the SDK send our Pydantic model to OpenAI as a **strict JSON schema** (Structured Outputs), so the model has to reply with JSON of exactly that shape.

7. **Pydantic validates the LLM response.** The SDK parses the reply into an `AnalysisResult`, running all the same checks (required fields, `level` must be A1–C2, no extra fields). If parsing fails, or the model refused (no parsed output), `llm_service.py` raises `LLMOutputValidationError`. If the HTTP call itself fails (bad key, timeout, rate limit), it raises `LLMProviderError`.

8. **SQLAlchemy inserts a model run.** Back in `analysis_service.py`, a `ModelRun` object (`backend/app/models/model_run.py`) is built with the input, model name, prompt version, translation, full JSON result, latency and token counts. `db.add(run); db.commit()` turns it into an `INSERT INTO model_runs ...`. On failure, a row with `success=False` and the `error_type` is saved instead, and the error is re-raised.

9. **FastAPI serializes the response.** The route returns the `AnalysisResult`. Because of `response_model=AnalysisResult`, FastAPI converts it to JSON. Our own exceptions are caught in the route and turned into safe messages (`502`/`500` with a `detail` string), never stack traces.

10. **The browser renders results.** `analyzePassage` returns the parsed JSON, and `handleSubmit` stores it with `setResult(...)`. React re-renders, and `AnalysisResultView` (`frontend/src/components/AnalysisResultView.tsx`) displays the translation, grammar cards and vocabulary table. On error, the message is shown in a red box. If the backend is unreachable, `fetch` throws and the user sees "Could not reach the server".

## Why the code is split this way

| Layer | File(s) | Knows about |
|---|---|---|
| Route | `api/routes/analyze.py` | HTTP: status codes, request/response |
| Service | `services/analysis_service.py` | the workflow: call LLM → save → return |
| LLM wrapper | `services/llm_service.py` | OpenAI only |
| Prompt | `prompts/french_analysis.py` | wording + version |
| Schemas | `schemas/analysis.py` | data shapes |
| ORM model | `models/model_run.py` | database table |

Each layer can change without rewriting the others. For example, switching models is just an environment variable, and switching providers would only touch `llm_service.py`. Tests can also replace the LLM with a fake.

## Key concepts

**Frontend vs backend.** The *frontend* is code that runs in the user's browser (our React page). Anyone can read it. The *backend* is code that runs on a server we control (FastAPI). It can hold secrets and talk to databases. Here Next.js serves the frontend files, and FastAPI is the backend.

**API.** An Application Programming Interface is a defined way for programs to talk to each other. Our backend's API is the set of URLs it accepts (`POST /api/v1/analyze`, `GET /health`) and the JSON shapes they use. FastAPI documents it automatically at <http://localhost:8000/docs>.

**REST.** A common style for web APIs: URLs name *resources* or actions, and standard HTTP methods say what to do (GET = read, POST = create/submit). Responses use standard status codes (200 OK, 422 invalid input, 502 upstream failure...). `/api/v1/` puts a version in the URL so the API can change later without breaking old clients.

**HTTP POST.** An HTTP request that sends data in its *body*. We use POST rather than GET because we're submitting a passage (possibly long, and not something to put in a URL) and the request has side effects (a database row, a paid LLM call).

**JSON.** A text format for structured data (`{"key": "value", "list": [1, 2]}`). The browser, FastAPI, OpenAI and PostgreSQL's `jsonb` column all speak it.

**Pydantic validation.** You declare the expected shape of data as a Python class with type hints, and Pydantic checks real data against it, raising a clear error if anything is wrong. We use it at every boundary where untrusted data enters: the HTTP request, the LLM's reply, and environment variables. LLM output is *untrusted* even with Structured Outputs, so we always validate before saving or returning it.

**ORM (Object-Relational Mapper).** SQLAlchemy lets us work with Python objects (`ModelRun(...)`) instead of hand-writing SQL. It translates `db.add(run)` into `INSERT ...` and query results back into objects. The table definition lives in one Python class.

**Database session.** A session is SQLAlchemy's unit of work: a short conversation with the database. We open one per request (`get_db`), add objects, `commit()` to write them all at once (or `rollback()` on error), then close it. Sessions borrow connections from the *engine's* connection pool, so we don't open a new raw connection every time.

**Database migrations (Alembic).** A migration is a versioned script that changes the schema (`create_table`, `add_column`...). Alembic records the current version in the `alembic_version` table and applies any newer scripts with `alembic upgrade head`, which the backend runs on startup. This way schema changes are reviewable code, not manual SQL.

**Environment variables.** Settings passed to a program from outside its code (`OPENAI_MODEL=gpt-5-mini`). They let the same code run with different configuration and keep secrets out of git. We keep them in `.env` (git-ignored). Compose passes them to containers, and `pydantic-settings` loads and validates them.

**Docker container.** A lightweight, isolated environment containing an app plus everything it needs (Python, libraries, OS files), built from a recipe called a `Dockerfile`. It runs the same on any machine with Docker, so there's no "works on my machine" problem.

**Docker Compose.** A tool for running several containers together, defined in `docker-compose.yml`. It creates a private network where containers find each other by service name (the backend connects to host `db`), wires up ports and environment variables, starts services in order (`depends_on` + health check), and attaches a **volume** so database files survive container restarts.

**Why the API key must stay server-side.** Anything sent to the browser can be read by anyone who opens the site: the JavaScript source, network requests and `NEXT_PUBLIC_` variables are all visible. If the OpenAI key were in the frontend, anyone could copy it and run up charges on your account. So the browser only talks to *our* backend, and only the backend container receives `OPENAI_API_KEY`. The backend also logs only error types, never request headers or the key.

**CORS (Cross-Origin Resource Sharing).** Browsers block a page from one origin (`localhost:3000`) from reading responses from another (`localhost:8000`) unless that server explicitly allows it. We allow a specific list of origins rather than `*`. A wildcard would let any website's JavaScript call our API from a visitor's browser, which is harmless for local development but a bad default to carry into production. CORS is a browser rule only. It doesn't stop `curl` or other servers, so it is not authentication.
