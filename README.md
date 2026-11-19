# JobTrail

A personal job-application tracker that I'm growing into an AI-assisted job search copilot. I'm building it because I'm in the middle of a job search and spreadsheets don't cut it.

**Status: Phase 1b.** The tracker works, and you can paste a job posting to have a language model fill in the form. Later AI features (below) are the roadmap, not shipped yet.

## What works today

- Add, list, filter, update, and delete applications (company, title, location, posting link, status)
- Status pipeline: `saved → applied → assessment → interview → offer / rejected`
- **Paste a posting, get the fields filled in.** A model extracts company, title, location, work mode, pay, and skills. You review before anything is saved, and the original text is kept with the application.
- Works with a free local model (Ollama) or OpenAI through one setting
- An eval harness that scores extraction on postings with known answers, including a prompt-injection case
- FastAPI backend with OpenAPI docs at `/docs`, PostgreSQL storage, input validation, pagination
- Next.js frontend with status filters and inline status changes
- Tests (pytest, 64 of them), lint and format checks (ruff), CI and CodeQL on GitHub Actions, Dependabot

## Roadmap

- [x] **Phase 1:** tracker (schema, REST API, UI)
- [x] **Phase 1b:** paste a job posting and let an LLM fill in the fields
- [ ] **Phase 2:** resume knowledge base (RAG) with match scoring and tailored drafts. Every claim cites the resume line it came from.
- [ ] **Phase 3:** daily ingestion of postings from public ATS board APIs (Greenhouse, Lever) with deduping and data-quality checks
- [ ] **Phase 4:** agent with tool schemas, step limits, a human-approval gate, and a trace viewer
- [ ] **Phase 5:** larger hand-labeled evaluation set that runs against a real model in CI and fails the build if quality drops

## Quick start (Docker)

```bash
cp .env.example .env        # then edit the password
docker compose up --build
```

- Web app: http://localhost:3000
- API docs: http://localhost:8000/docs

Load fake sample data (optional):

```bash
python3 scripts/seed_sample_data.py
```

## Local development in VS Code

1. Open this folder in VS Code and accept the recommended extensions.
2. Copy `.env.example` to `.env` and put the **same password** in `POSTGRES_PASSWORD` and in `DATABASE_URL`. Use letters and numbers only, since special characters must be URL-encoded inside `DATABASE_URL`. Do this **before** starting the database: Postgres only reads the password the first time its data volume is created. If you started the database first, run `docker compose down -v` to reset it (this deletes the local data), then start it again.
3. Run these tasks from **Terminal → Run Task**:
   - `setup: backend venv + deps`
   - `setup: frontend deps`
   - `db: start Postgres (Docker)`
4. Press **F5** and choose **Full stack (API + web)**. This starts the FastAPI debugger and the Next.js dev server together.
5. Run tests with the `backend: test` task, or from the Testing panel.

The interpreter path in `.vscode/settings.json` is the macOS/Linux one. On Windows, change it to `${workspaceFolder}/backend/.venv/Scripts/python.exe`.

### Without VS Code tasks

```bash
# API
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload       # needs Postgres; see `docker compose up -d db`
pytest                              # uses in-memory SQLite, no database needed

# Web
cd frontend
npm install
npm run dev
```

## Turning on AI extraction

It is off by default. The app works fully without it.

**Option A: Ollama (free, private).** Install [Ollama](https://ollama.com), then pull a model and set these in `.env`:

```
LLM_PROVIDER=ollama
LLM_MODEL=<the model you pulled>
```

**Option B: OpenAI (pay per use).**

```
LLM_PROVIDER=openai
LLM_MODEL=<a model available on your account>
LLM_API_KEY=<your key>
```

Restart the API after editing `.env`. If the API runs in Docker and Ollama runs on your computer, also set `LLM_BASE_URL=http://host.docker.internal:11434/v1`.

### How extraction works

1. The pasted text is sent to the model with a fixed instruction and a JSON-only reply format. The text goes in the user message inside delimiters, never into the instructions.
2. The reply is parsed and validated against a schema (`app/extraction/schema.py`). Placeholders like "N/A" become null and unknown work modes are dropped.
3. If the reply is invalid, the model gets the validation error and one more try. After that the API returns a 502 and the form stays manual.
4. Nothing is saved by the extract call. The UI fills the form and you check each field before adding.

Design choices worth knowing:

- **Posting text is untrusted.** Postings can contain instructions aimed at the model. The model has no tools, and its output only pre-fills a form you review, so the worst case is a wrong field you can see. The eval set includes an injection attempt.
- **Never guess.** The prompt says to use null when something isn't stated, and the evals check that.
- **JSON mode plus schema validation** rather than provider-specific structured-output features, so one code path works for OpenAI and local models.

## Running the evals

`backend/evals/cases.json` holds postings with known answers: clear ones, missing fields, noisy ones, and a prompt-injection attempt. From `backend/`:

```bash
python -m evals.run_eval            # scores the model configured in .env
python -m evals.run_eval --oracle   # sanity-checks the harness itself (should be 100%)
```

It reports per-field accuracy, skill recall, **ungrounded skills** (skills the model returned that don't appear in the posting), and whether injected text leaked into any field. It exits non-zero below the thresholds.

**What CI runs:** the unit tests and the oracle run, which check the code and the scoring. CI does **not** call a real model, so it can't catch a model getting worse. That is Phase 5.

My results (fill in from your own runs):

| Model | Field accuracy | Skill recall | Ungrounded skills | Injection leaks |
|---|---|---|---|---|
| _run the evals and add a row_ | | | | |

The 8 starter cases are synthetic. The plan is to add real postings from my own search, with company names removed, until there are about 30.

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness check |
| GET | `/api/v1/applications` | List (`?status=`, `?limit=`, `?offset=`) |
| POST | `/api/v1/applications` | Create |
| GET | `/api/v1/applications/{id}` | Fetch one |
| PATCH | `/api/v1/applications/{id}` | Partial update |
| DELETE | `/api/v1/applications/{id}` | Delete |
| POST | `/api/v1/extract` | Extract fields from posting text (not saved). 503 if no model is configured, 502 if the model fails. |

## Project layout

```
backend/
  app/            FastAPI app, models, routers
  app/extraction/ Schema, prompt, model providers
  evals/          Extraction eval cases and scoring
  tests/          pytest suite (uses a fake model and in-memory SQLite)
frontend/         Next.js (App Router) UI
sample_data/      Fake applications for demos and tests
scripts/          Helper scripts (seed data)
.github/          CI, CodeQL, Dependabot
.vscode/          Shared editor settings, debug configs, tasks
```

## Privacy and data handling

This tool is meant to hold my real job search, so:

- Real data lives only in my local Postgres volume. `.env`, `*.db`, `private/`, and `data/` are gitignored.
- The repo contains only fake records (`sample_data/`, using `example.com` links) and synthetic eval postings.
- Docker publishes the database and API on `127.0.0.1` only.
- With Ollama, posting text never leaves my computer. With OpenAI, the pasted text is sent to OpenAI.
- Posting text is never written to the logs. Only error messages are.
- There is no authentication yet, so don't expose this to a network. Auth and per-user data isolation are required before any hosted version.

## Known limitations

- Tables are created at startup; there are no migrations yet (Alembic is planned once the schema starts changing).
- Single user, no login.
- Extraction quality depends on the model. Small local models can return invalid or incomplete JSON; the retry and the evals exist for that reason.
- Only the first 12,000 characters of a posting are sent to the model.
- CI does not evaluate a real model (see above).
