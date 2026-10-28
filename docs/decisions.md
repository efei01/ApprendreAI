# Engineering decisions (Milestone 1)

Short records of the non-trivial choices, so they can be revisited deliberately later.

---

### 1. Repository layout: the repo root *is* the project

**Decision:** Put `frontend/`, `backend/`, `docs/` directly in the repo root instead of a nested `french-ai-tutor/` folder.
**Why:** The git repository already exists as `ApprendreAI`. An extra folder level would add nothing.
**Alternative:** The nested folder from the original plan.
**Why not yet:** It would only matter if the repo held several unrelated projects.

### 2. Alembic migrations from day one

**Decision:** Manage the schema with Alembic (one migration, `0001_create_model_runs`), applied automatically by `backend/start.sh` before the server starts.
**Why:** The schema *will* change (users, exercises, evaluation tables). Alembic makes each change a reviewed, versioned file, and `alembic check` confirms models and migrations agree. Setup is small: `alembic.ini`, `env.py` and one migration file.
**Alternative:** `Base.metadata.create_all()` at startup.
**Why not:** `create_all` can create tables but never alter them. The first column change would force a switch to Alembic anyway, and possibly lose data.

*Caveat:* running migrations on app startup is fine for one backend container. With several replicas you'd run migrations as a separate deploy step.

### 3. Synchronous endpoints, SQLAlchemy and OpenAI client

**Decision:** Plain `def` route handlers with the sync SQLAlchemy session and sync `openai.OpenAI` client.
**Why:** FastAPI runs `def` handlers in a thread pool, so a slow LLM call doesn't block other requests. At this scale it performs fine, and sync code is easier to read, debug and test.
**Alternative:** `async def` throughout, with `AsyncOpenAI` and SQLAlchemy's async engine.
**Why not yet:** Async pays off with very high concurrency or many parallel calls per request (e.g. fanning out to several models during evaluation). It's a contained change in `llm_service.py`, `session.py` and the route when that need arrives.

### 4. OpenAI Responses API with `responses.parse(text_format=...)`

**Decision:** Use the SDK's Structured Outputs helper with our Pydantic model `AnalysisResult`.
**Why:** It's the current recommended approach. The SDK converts the model into a strict JSON schema, the API makes the model follow it, and the SDK validates the reply back into a typed object. No Markdown or regex parsing. The CEFR level is a `Literal[...]`, so it becomes an enum the model must respect.
**Alternative:** Chat Completions with `response_format`, or JSON mode plus manual parsing.
**Why not:** Chat Completions works but Responses is OpenAI's primary API now. JSON mode doesn't enforce the schema.

### 5. Store the full result as JSONB, plus `translation` as a column

**Decision:** `model_runs.analysis` (JSONB) holds the complete validated result. `translation` is also stored as its own text column.
**Why:** Grammar points and vocabulary are nested lists. JSONB keeps the exact output for future evaluation (re-scoring old runs, comparing prompt versions) without designing extra tables now, and PostgreSQL can still query inside it. `translation` is a column because it's the most-used field.
**Alternative:** Normalized `grammar_points` and `vocabulary_items` tables with foreign keys.
**Why not yet:** No feature queries individual grammar points yet. When analytics needs it, a dbt model or migration can flatten the JSONB.

### 6. Record failed runs too

**Decision:** Failed LLM calls create a row with `success=false` and `error_type` (`llm_provider_error` or `llm_invalid_output`).
**Why:** "How often does prompt v2 produce invalid output?" is a core evaluation question, and you can't answer it if failures disappear.
**Alternative:** Only log failures.
**Why not:** Logs are hard to aggregate. A table is directly queryable.

### 7. If the database write fails, return an error

**Decision:** If the LLM succeeded but saving fails, respond `500` ("could not be saved") instead of returning the result anyway.
**Why:** Every result shown to a user should be recorded. Silent gaps would bias later evaluation data, and fail-loud behavior surfaces database problems immediately.
**Alternative:** Return the result and only log the database error. That's friendlier to the user but loses data silently.
**Why not yet:** Revisit if the database becomes a reliability bottleneck, e.g. with a retry queue.

### 8. Cost estimation is opt-in via configuration

**Decision:** `estimated_cost` is computed only if `OPENAI_INPUT_PRICE_PER_1M_TOKENS` and `OPENAI_OUTPUT_PRICE_PER_1M_TOKENS` are set. Otherwise it is `NULL`. Token counts are always stored when OpenAI reports them.
**Why:** Prices differ per model and change over time. Hard-coding them would silently go stale. Tokens are the ground truth, and cost can be recomputed later.
**Alternative:** A built-in price table per model.
**Why not yet:** It needs maintenance and adds little until cost is analyzed.

### 9. The browser calls FastAPI directly, with an explicit CORS allow-list

**Decision:** The frontend calls `NEXT_PUBLIC_API_BASE_URL` (`http://localhost:8000`) from the browser. FastAPI allows only origins in `BACKEND_CORS_ORIGINS`.
**Why:** It's the simplest setup that keeps a clear frontend/backend separation, and the API key stays in the backend either way.
**Alternative:** A Next.js server-side route (`/api/analyze`) that proxies to FastAPI. Same origin, so no CORS needed.
**Why not yet:** It adds a second server hop and more code. It may be worth it at deployment time (one public domain).

### 10. Production Next.js build in Docker (standalone output)

**Decision:** The frontend image runs `next build` and serves the standalone output, with `NEXT_PUBLIC_API_BASE_URL` passed as a build argument.
**Why:** It matches how the app would really be deployed and starts fast. Build-time inlining of `NEXT_PUBLIC_` values is how Next.js works, and it's safe because they aren't secret.
**Alternative:** Run `next dev` in the container with hot reload.
**Why not yet:** It's convenient for UI work, but less production-like. For heavy frontend iteration, you can install Node locally and run `npm run dev` against the Dockerized backend.

### 11. Unit tests use SQLite and a fake LLM

**Decision:** Tests replace `get_db` with an in-memory SQLite session and `get_llm_service` with a `FakeLLM`, using FastAPI's `dependency_overrides`.
**Why:** The tests are fast (under a second), free, need no Docker, and still exercise real routing, validation, ORM inserts and error handling. The `analysis` column is `JSON` with a `JSONB` variant on PostgreSQL, so the same model works on both.
**Alternative:** Run tests against a real PostgreSQL (e.g. a test database in Compose, or testcontainers).
**Why not yet:** It's more setup than Milestone 1 warrants. A PostgreSQL integration test is the first thing to add when the schema grows.
