# Audit worker baseline

The maintained application is the top-level `backend/` and `frontend/` tree.
The nested `agencyos-bot-main/` snapshot is not a deployment source for this fix.

## Runtime

API and worker must use the same PostgreSQL database and Redis database, and the
same application revision. Start both from the backend directory:

```sh
uvicorn main:app --host 0.0.0.0 --port 8000
# Separate process:
arq jobs.worker.WorkerSettings
```

Provide DATABASE_URL, REDIS_URL, CLAUDE_API_KEY and optional CLAUDE_MODEL via the
service environment. PLAYBOOKS_DIR defaults to `playbooks` relative to backend.
PAGESPEED_API_KEY remains optional. Never copy credential values into diagnostics.

Docker Compose uses its separate worker and sets RUN_EMBEDDED_WORKER=0 for the API.
The default container entrypoint embeds a supervised worker for a single-container
deployment. It retains the existing startup migration command; do not execute it
against production without separately authorizing that operation.

GET /health returns 503 unless DB, Redis and the ARQ heartbeat are available.
The heartbeat uses ARQ's default key and can lag process death by its expiry window.
There can be a short unavailable interval while the worker starts.
The heartbeat is shared by workers on the default queue, not a per-task health proof.

## Job behavior

Audit submission validates the lead and worker heartbeat before saving a job.
New audits use the DB UUID as their ARQ job ID and payload.queue_tracking=true.
Queue insertion failures persist a sanitized failure and return HTTP 503.
The audit has a 210-second application deadline, below the 240-second ARQ limit.
Audit, lead changes, activity and completion commit together. A terminal job is
not regenerated on redelivery. Cancellation rolls back unfinished work and leaves
ARQ free to retry it.

A minute-level worker cron checks tracked, nonterminal audits older than ten
minutes. Only missing or terminal ARQ jobs are closed as failed, after re-reading
the DB row under a lock. Queued/running work is never failed merely due to age.
Recovery needs a working worker, Redis and DB; it cannot update DB during an outage.
It does not submit replacement work or send outreach.

Legacy jobs have unrelated ARQ IDs and are deliberately untouched. Inspect their
queue status and any existing report before manually retrying. The UI reports
long waits and repeated polling errors without claiming the job has stopped.

## Verification

In an isolated Python environment install requirements-test.txt and run:

```sh
python -m pytest tests -q
```

These tests mock infrastructure/provider calls. A staging smoke test must still
verify real Redis consumption, PostgreSQL transactions, process supervision and
provider output. Capture baseline lead scores first: the existing audit service
recalculates them even though no scoring formulas were changed.

The live baseline preserves explicit PageSpeed absence metadata and prompt handling.
Known follow-up: other website fetch failures still use legacy fallback data semantics. Website/SERP enrichment wiring and lead ranking are outside this fix.

## Baseline reconciliation

This branch includes the exact Vercel production source commit `917e00d` and
its 34 commits missing from main. Existing security, cost tracking, playbook
fallback, migrations and service idempotency are retained. No production
migration or deployment is performed by this source reconciliation.
