# AgencyOS — Agent Guide

## Architecture

Two-process monorepo with an optional Telegram bot:

- **`backend/`** — FastAPI (Python 3.11), SQLAlchemy async (asyncpg), ARQ job queue (Redis), PostgreSQL, Alembic migrations
- **`frontend/`** — Next.js 16.2, React 19, Tailwind 4, shadcn/ui, standalone output mode
- **`main.py` + `bot/`** — Telegram bot (optional). Calls backend API over HTTP; never touches DB or core directly.

`backend/core/` is the business-logic layer. It must stay **framework-agnostic** — no imports from FastAPI, ARQ, Telegram, or Starlette. It only receives and returns plain dicts/strings. Route glue lives in `backend/api/routes/`, async task logic in `backend/jobs/`.

`backend/playbooks/*.json` — per-sector configuration consumed by `core/playbook.py`.

`backend/services/` — orchestration layer between routes/jobs and core (audit, outreach, proposal, lead, cost tracker, notifications).

**Root-level traps**: `core/` and `crm/` at repo root are **empty leftovers** — real code is `backend/core/`. `agencyos-bot-main/` is a stale full copy of the repo; never edit files there. `artifacts/` and `output/` are scratch. `.test-tools/` holds local helper scripts/caches.

## Commands

### Backend

```sh
cd backend

# Install (use a venv)
pip install -r requirements.txt        # runtime
pip install -r requirements-dev.txt    # pytest + pytest-asyncio

# DB setup (Postgres must be running)
alembic upgrade head

# Dev server
uvicorn main:app --reload

# ARQ worker (separate process, needs Redis)
arq jobs.worker.WorkerSettings

# Tests (unit tests run without DB; integration tests skip if no Postgres)
pytest -v
pytest tests/test_playbook.py -v       # single file
pytest -k "test_name" -v              # single test
```

`backend/pytest.ini` sets `asyncio_mode = auto` and session loop scope for both fixtures and tests (`asyncio_default_fixture_loop_scope`, `asyncio_default_test_loop_scope`). All async tests run in one shared event loop — don't override loop scope in fixtures.

### Frontend

```sh
cd frontend
npm ci
npm run dev        # dev server
npm run build      # production build (standalone output)
npm run lint       # eslint
```

### Docker Compose (full stack)

```sh
docker compose up                          # postgres + redis + api + worker + frontend
docker compose --profile bot up            # add Telegram bot
docker compose up -d --build               # rebuild after code changes
```

The `api` service sets `RUN_EMBEDDED_WORKER=0` because the `worker` service runs ARQ separately. The single-container entrypoint (`backend/entrypoint.sh`) embeds a worker by default.

## Critical constraints

1. **API auth**: Every `/api/*` request requires `X-API-Key` header (except `/health`, `/docs`, `/openapi.json`, `/redoc`). Key is `AGENCYOS_API_KEY` env var. Frontend bakes it at build time via `NEXT_PUBLIC_API_KEY`.

2. **Core is framework-free**: Never `from fastapi import …` or `from arq import …` in `backend/core/`. This is enforced by convention and AUDIT_OPERATIONS.md.

3. **Job contract is stable**: Trigger endpoints return `{ "job_id": "uuid", "status": "completed|pending", "result": {} }`. Job status fields (`status/progress_pct/progress_message/error_message/started_at/finished_at`) are the same across backend, ARQ, and frontend. Don't change this shape.

4. **Migration order matters**: `alembic upgrade head` runs automatically in `entrypoint.sh` before uvicorn starts. CI also runs it. New models must be registered in `backend/models/__init__.py` for Alembic autogenerate to see them.

5. **Frontend API URL is baked at build time**: `NEXT_PUBLIC_API_URL` and `NEXT_PUBLIC_API_KEY` are set as Docker build args, not runtime env vars. Changing them requires a rebuild.

6. **WeasyPrint needs system libs**: PDF generation (`backend/core/proposal_generator.py`) requires Cairo, Pango, GDK-Pixbuf. The backend Dockerfile installs these. Local dev on macOS: `brew install pango gdk-pixbuf cairo`.

7. **ARQ worker timeout**: `job_timeout=240s`, `max_tries=2`, `retry_delay=15s`. Tasks are idempotent — retry is safe because services check `since_dt` guards. A minute-level cron (`reconcile_audits`) closes orphaned audit jobs.

8. **Search enrichment is best-effort**: each search runs exactly 1 batch SERP call (`fetch_serp_data` + `apply_serp_data`) plus free HTML site fetches (`analyze_sites(check_index=False)` — no per-lead SerpAPI credits). Both are wrapped in try/except; enrichment failure must never fail the search. These enrichers were dead code (zero callers) for a long time — grep for callers before assuming a pipeline stage actually runs.

9. **`source_data` round-trip**: the search response returns each lead's full enriched dict as `source_data`; the frontend sends it back in `LeadCreate`, and `lead_to_core_dict` merges it so the audit inherits Maps velocity, `site_durumu`, and SERP fields instead of losing them at save.

## Test setup

- Unit tests: no infrastructure needed. conftest sets dummy env vars (`APP_ENV=test`, empty API keys).
- Integration tests: need Postgres (conftest `db_engine` fixture skips if unreachable). CI spins up `postgres:16-alpine` and runs `alembic upgrade head` before pytest.
- `requirements-test.txt` includes `requirements.txt` + pytest — use it for CI-like installs.
- Integration tests use `clean_db` fixture (explicit opt-in, not autouse) to TRUNCATE tables between tests.

## Production verification (live e2e)

- Production API: `https://agencyos-bot-production.up.railway.app`, header `X-API-Key: test123` (exact literal). Note: `agencyos.up.railway.app` is a *different* Express service with a `{success,data,meta}` envelope — wrong target.
- **Push to `main` = deploy**: Railway auto-deploys the backend, Vercel builds the frontend. No manual deploy step.
- Unit tests cannot catch pipeline-wiring bugs — twice, scoring worked in search but never reached `audit.result`. Before claiming a scoring/pipeline change works, run the live probe:

```sh
python backend/tests/night_audit_test.py   # search → save lead → run audit → assert audit.result.advanced_signals
```

- `/api/search` caches in Redis; pass `"force_refresh": true` in the body to bypass the cache when verifying fresh code.

## AI integration

- **Claude** (Anthropic SDK): audit generation, outreach writing, proposal narrative, hook engine. Model set via `CLAUDE_MODEL` (default `claude-sonnet-4-6`). Prompts live in `backend/core/prompts.py`.
- **OpenAI**: voice STT (Whisper) and TTS (`tts-1`, `nova` voice). Optional — only needed for voice assistant.
- **Apify**: Google Maps scraping for lead collection. Token via `APIFY_API_TOKEN`.
- **Cost tracking**: `backend/services/cost_tracker.py` logs every external API call. `DAILY_BUDGET_USD > 0` triggers Telegram admin alarm at 80% spend.

## Key env vars (see `.env.example` for full list)

| Var | Required | Notes |
|-----|----------|-------|
| `DATABASE_URL` | Yes | `postgresql+asyncpg://…` — alembic also reads this |
| `REDIS_URL` | Yes | ARQ worker + job queue |
| `AGENCYOS_API_KEY` | Yes | Must not be `changeme` in production (startup abort) |
| `CLAUDE_API_KEY` | Yes | Anthropic SDK |
| `APIFY_API_TOKEN` | For scraping | Lead collection |
| `OPENAI_API_KEY` | For voice | STT/TTS only |
| `PAGESPEED_API_KEY` | Optional | PageSpeed Insights audit data |
| `TELEGRAM_BOT_TOKEN` | For bot | Telegram notifications + bot |
| `RUN_EMBEDDED_WORKER` | No | `0` in Docker Compose (separate worker); `1` (default) in single-container |

## Deployment

- **Railway**: `railway.toml` points to `backend/Dockerfile`. Entry point is `entrypoint.sh` (migrations → optional embedded worker → uvicorn).
- **Docker Compose**: full stack with separate worker service. See `docker-compose.yml`.
- **CI**: `.github/workflows/ci.yml` — runs on `main` and `claude/**` branches. Backend tests only (no frontend CI).

## Next.js caveat

`frontend/AGENTS.md` warns that Next.js 16 may have breaking changes from training data. Read `node_modules/next/dist/docs/` before writing frontend code. `frontend/CLAUDE.md` is just `@AGENTS.md`.

## Related instruction files

- Root `CLAUDE.md` — Turkish project memory, expected to be updated after each completed step; keep it current when finishing work. This `AGENTS.md` complements it without duplication.
- The owner communicates in Turkish; code, identifiers, and commit messages stay English (conventional commits, e.g. `fix(scoring): …`).

## Lead Scoring Engine (Advanced Micro-Scoring)

4 yeni kriter `backend/core/advanced_signals.py`'da hesaplanır ve `lead_scorer.py`'ye entegre edilir:

| Kriter | Skorlama Katmanı | Frontend Component |
|--------|-----------------|-------------------|
| Rekabet Yoğunluğu | Opportunity (+12 max) | `AdvancedScores` — Swords icon |
| PPC İsrafı | Pattern (+5% max) | `AdvancedScores` — Megaphone icon |
| Sosyal Uyuşmazlık | Intent (+10 max) | `AdvancedScores` — Share2 icon |
| E-Ticaret Aciliyeti | Opportunity (+15 max) | `AdvancedScores` — ShoppingCart icon |

**Frontend entegrasyonu:**
- `components/ui/advanced-scores.tsx` — yeniden kullanılabilir skor bileşeni (compact + expanded modu)
- `app/search/result-card.tsx` — arama sonuçlarında compact badge + expanded bar
- `app/leads/[id]/page.tsx` — audit bölümünde 4'lü skor paneli
- `types/index.ts` — `SearchResultItem` interface'inde 4 yeni skor alanı

**Veri akışı:** search enrichment (`serp_enricher` + `site_analyzer` HTML sinyalleri) → `advanced_signals.py` (SERP verisi yoksa `serp_like_from_market(market)` ile `market_evidence`'ten serp-formatına çevrilir) → `lead_scorer.py` → `audit.result` JSONB → frontend

**Kaçırılması kolay doğrular:**

- **Audit iki fazda yazılır**: audit satırı skorlamadan *önce* oluşur. `advanced_signals` hesaplandıktan sonra `audit_result`'a merge edilip `AuditRepository.update(...)` ile yazılmalı — aksi halde skorlar hesaplansa bile frontend paneli (`audit.result.advanced_signals`) boş kalır.
- **`instagram_post_90d`'nın hiçbir üreticisi yok** kod tabanında → sosyal skor, fetch edilen HTML'de bulunan `has_instagram`/`has_facebook` profil linklerinden fallback alır (eşik 8).
- Sinyal yolları: viewport `site_data["technical"]["viewport_present"]`; social linkler `fetch_site_data` çıktısı (`instagram_link`/`facebook_link`).
- `market_evidence` çıktısı scorer'ın beklediği serp formatından farklıdır — arada `serp_like_from_market()` çevirisi vardır (ilk 5 organik domain = strong competitor).