# AgencyOS — Agent Guide

## Repository boundaries

- `backend/` is the FastAPI/PostgreSQL/Redis application. Business rules belong in `backend/core/`; keep that package free of FastAPI, Starlette, ARQ, and Telegram imports. HTTP glue lives in `backend/api/routes/`, queue tasks in `backend/jobs/`, and DB-backed orchestration in `backend/services/`.
- `frontend/` is Next.js 16/React 19. Before changing it, read `frontend/AGENTS.md` and the relevant installed guide under `frontend/node_modules/next/dist/docs/`; this Next.js version differs from older conventions. `frontend/CLAUDE.md` is just `@AGENTS.md`.
- `main.py` plus `bot/` is the optional Telegram client. It calls the backend API and must not import backend DB/core internals. Its container dependencies come from `Dockerfile.bot`, not the root requirements file.
- Do not edit the root `core/` or `crm/` leftovers, `agencyos-bot-main/`, or the nested checkout under `.test-tools/agencyos-github/`. Real application code is under `backend/` and `frontend/`. `artifacts/` and `output/` are scratch.
- Sector behavior is data-driven through `backend/playbooks/*.json` and `backend/core/playbook.py`.

## Commands

Backend commands run from `backend/` (Python 3.11 in CI):

```sh
python -m venv .venv
source .venv/bin/activate           # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r requirements-dev.txt

alembic upgrade head                 # PostgreSQL must be reachable
uvicorn main:app --reload
arq jobs.worker.WorkerSettings       # separate terminal; Redis required

pytest -v
pytest tests/test_playbook.py -v     # one file
pytest -k "test_name" -v            # one test/filter
```

Use the same two requirements installs as CI; `requirements-test.txt` is an alternate aggregate with different pytest bounds, not the literal CI setup.

Frontend commands run from `frontend/`:

```sh
npm ci
npm run dev
npm run lint
npm run build       # production compile plus TypeScript check
```

Full stack:

```sh
docker compose up
docker compose --profile bot up
docker compose up -d --build
```

## Configuration and runtime traps

- `backend/config.py` loads `.env` relative to the process working directory. A root `.env` is used by Compose but is not automatically loaded by `cd backend && uvicorn ...`; provide environment variables or a backend-local `.env`.
- API-key middleware protects every non-exempt route, not only `/api/*`. Only `/health`, docs/OpenAPI routes, and all `OPTIONS` requests bypass it.
- `NEXT_PUBLIC_API_URL` and `NEXT_PUBLIC_API_KEY` are baked in at build time: Docker build args for the Compose image (`frontend/Dockerfile`) and project env vars for the Vercel build. Changing either requires rebuilding the image or redeploying the Vercel project; the browser-visible API key is not a secret boundary.
- Lead collection prefers Apify Google Maps scraping when `APIFY_API_TOKEN` is set; without it (and always in `search_only` "Firma Ara" mode) collection falls back to SerpAPI Maps, which requires `SERPAPI_API_KEY`. SERP enrichment and market evidence are best-effort and skip cleanly without `SERPAPI_API_KEY`; HTML site analysis runs without per-lead SerpAPI calls. Enrichment failures must not fail the search.
- Cost tracking covers Claude, Apify, and OpenAI STT/TTS, but not SerpAPI or PageSpeed; budget totals are not total external spend. The Anthropic model comes from `CLAUDE_MODEL` (default `claude-sonnet-4-6`); prompts live in `backend/core/prompts.py`. `DAILY_BUDGET_USD > 0` triggers a Telegram admin alarm at 80% of spend.
- Proposal PDF generation needs Cairo/Pango/GDK-PixBuf locally; the backend image installs them. macOS: `brew install pango gdk-pixbuf cairo`.

### Key environment variables

| Var | Required | Notes |
|-----|----------|-------|
| `DATABASE_URL` | Yes | `postgresql+asyncpg://…` — Alembic reads it too |
| `REDIS_URL` | Yes | ARQ worker + job queue |
| `AGENCYOS_API_KEY` | Yes | Production startup aborts while it is empty or `changeme` (`backend/main.py`) |
| `CLAUDE_API_KEY` | Yes | Anthropic SDK (audit/outreach/proposal) |
| `APIFY_API_TOKEN` | For Maps collection | Preferred Google Maps collector |
| `SERPAPI_API_KEY` | Conditional | Required for the SerpAPI Maps fallback and `search_only` mode; also powers SERP enrichment and market evidence (both skip without it) |
| `OPENAI_API_KEY` | Voice only | STT/TTS |
| `PAGESPEED_API_KEY` | Optional | PageSpeed audit data |
| `TELEGRAM_BOT_TOKEN` | Bot only | Notifications |
| `RUN_EMBEDDED_WORKER` | No | `0` in Compose (separate worker); `1` (default) single-container |

See `.env.example` for the full list.

## Stable contracts and data flow

- Trigger endpoints keep the job envelope `{ "job_id": "uuid", "status": "completed|pending", "result": {} }`. Keep `status/progress_pct/progress_message/error_message/started_at/finished_at` aligned across models, jobs, API, and frontend.
- Register every new ORM model in `backend/models/__init__.py` so Alembic sees it. `backend/entrypoint.sh` migrates before starting the API; the Compose worker overrides that entrypoint and does not run migrations itself.
- ARQ uses `job_timeout=240`, `max_tries=2`, and `retry_delay=15`. Retry safety depends on the existing `since_dt` idempotency guards. A minute-level reconciliation cron closes orphaned audit jobs.
- Search returns the full enriched lead as `source_data`; the frontend must send it back in `LeadCreate`, and `lead_to_core_dict` must merge it. Dropping this round trip silently removes Maps, site, and SERP signals before audit.
- Advanced scoring flows through search enrichment → `advanced_signals.py` → `lead_scorer.py` → `audit.result.advanced_signals`. Audit rows are created before scoring, so the service must merge the signals and call `AuditRepository.update(...)` afterward.
- Advanced-scoring signal paths: viewport `site_data["technical"]["viewport_present"]`, social links `instagram_link`/`facebook_link` from fetched site data. Social fallback threshold is 8; the top 5 organic domains count as a strong competitor.
- Advanced-scoring UI: `frontend/components/ui/advanced-scores.tsx` (reusable panel), `frontend/app/search/result-card.tsx` (search badges), `frontend/app/leads/[id]/page.tsx` (audit panel), and the four score fields on `SearchResultItem` in `frontend/types/index.ts`.
- Before assuming a pipeline stage actually runs, grep for its callers — enrichment stages were dead code with zero callers for a long time (fixed in `aa73cbc`).
- `market_evidence` is not in scorer SERP format; use `serp_like_from_market()`. Social scoring falls back to fetched Instagram/Facebook links because no producer currently fills `instagram_post_90d`.

## Testing and deployment

- Unit tests need no infrastructure. Integration tests request `db_engine` and skip when PostgreSQL is unavailable; CI starts PostgreSQL and runs `alembic upgrade head` first.
- `backend/pytest.ini` deliberately gives async fixtures and tests one session-scoped event loop. Do not override fixture loop scopes. `clean_db` is explicit, not autouse.
- CI (`.github/workflows/ci.yml`) runs on `main` and `claude/**` for pushes, backend tests only. For frontend changes, run both lint and build locally; build is the available TypeScript verification. Frontend lint currently has a baseline of 7 errors / 6 warnings — compare against it before blaming your change.
- Production API: `https://agencyos-bot-production.up.railway.app` with header `X-API-Key` set from `AGENCYOS_API_KEY`. `agencyos.up.railway.app` is a *different* Express service with a `{success,data,meta}` envelope — the wrong target for probes.
- Pushes to `main` deploy the backend to Railway and build the frontend on Vercel. Railway uses `backend/Dockerfile`; single-container startup embeds the ARQ worker by default, while Compose sets `RUN_EMBEDDED_WORKER=0` and runs a separate worker.
- Scoring/pipeline wiring needs more than unit tests. With explicit approval to mutate production and spend provider credits, run `python backend/tests/night_audit_test.py`; it forces a fresh search, creates/reuses a lead, runs an audit, and checks persisted advanced signals.
- `/api/search` caches in Redis; pass `"force_refresh": true` in the request body when checking fresh code manually (curl), otherwise you get cached results.

## Working conventions

- The owner communicates in Turkish; keep code, identifiers, and conventional commit messages in English.
- `CLAUDE.md` is historical project memory (milestone and status notes), not the current rulebook; this file and executable config/current code are authoritative whenever anything conflicts.
