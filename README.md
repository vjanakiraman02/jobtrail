# JobTrail

A personal job-application tracker that I'm growing into an AI-assisted job search copilot. I'm building it because I'm in the middle of a job search and spreadsheets don't cut it.

**Status: Phase 1 (tracker).** The REST API, database, and web UI for tracking applications work today. The AI features below are the roadmap, not shipped yet.

## What works today

- Add, list, filter, update, and delete applications (company, title, location, posting link, status)
- Status pipeline: `saved → applied → assessment → interview → offer / rejected`
- FastAPI backend with OpenAPI docs at `/docs`, PostgreSQL storage, input validation, pagination
- Next.js frontend with status filters and inline status changes
- Tests (pytest), lint and format checks (ruff), CI and CodeQL on GitHub Actions, Dependabot

## Roadmap

- [x] **Phase 1:** tracker (schema, REST API, UI)
- [ ] **Phase 1b:** paste a job posting and let an LLM fill in the fields
- [ ] **Phase 2:** resume knowledge base (RAG) with match scoring and tailored drafts. Every claim cites the resume line it came from.
- [ ] **Phase 3:** daily ingestion of postings from public ATS board APIs (Greenhouse, Lever) with deduping and data-quality checks
- [ ] **Phase 4:** agent with tool schemas, step limits, a human-approval gate, and a trace viewer
- [ ] **Phase 5:** hand-labeled evaluation set that runs in CI and fails the build if quality drops

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
2. Run these tasks from **Terminal → Run Task**:
   - `setup: backend venv + deps`
   - `setup: frontend deps`
   - `db: start Postgres (Docker)`
3. Copy `.env.example` to `.env` (the database URL in it matches the Docker database).
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

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness check |
| GET | `/api/v1/applications` | List (`?status=`, `?limit=`, `?offset=`) |
| POST | `/api/v1/applications` | Create |
| GET | `/api/v1/applications/{id}` | Fetch one |
| PATCH | `/api/v1/applications/{id}` | Partial update |
| DELETE | `/api/v1/applications/{id}` | Delete |

## Project layout

```
backend/        FastAPI app, SQLAlchemy models, tests
frontend/       Next.js (App Router) UI
sample_data/    Fake applications for demos and tests
scripts/        Helper scripts (seed data)
.github/        CI, CodeQL, Dependabot
.vscode/        Shared editor settings, debug configs, tasks
```

## Privacy and data handling

This tool is meant to hold my real job search, so:

- Real data lives only in my local Postgres volume. `.env`, `*.db`, `private/`, and `data/` are gitignored.
- The repo contains only fake records (`sample_data/`, using `example.com` links).
- Docker publishes the database and API on `127.0.0.1` only.
- There is no authentication yet, so don't expose this to a network. Auth and per-user data isolation are required before any hosted version.

## Known limitations

- Tables are created at startup; there are no migrations yet (Alembic is planned once the schema starts changing).
- Single user, no login.
- No LLM features yet (see the roadmap).
