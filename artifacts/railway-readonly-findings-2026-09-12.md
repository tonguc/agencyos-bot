# Railway read-only deployment check — 2026-09-12

No production settings, data, migrations or deployments were changed.

## Verified

- Railway project: easygoing-fulfillment; environment: production.
- Active backend deployment: `7be779e2-580f-4e49-88d6-a96bfaa9fccc`.
- Source: `tonguc/agencyos-bot`, `main`, commit `c70779b4a831eaf98649ac82fb90477ecb4b1da1`.
- Deployment details show `/backend`, Dockerfile `backend/Dockerfile`, one replica, `/health`, failure restart policy with 10 retries.
- Architecture shows three online services: agencyos-bot, Postgres and Redis. There is no separately deployed worker service in this project/environment.
- Deploy logs contain ARQ worker stack frames dated 2026-09-05 20:12 (dashboard GMT+3), plus Redis `ConnectionError: Connection closed by server` and `TimeoutError: Timeout connecting to server` at that time.
- These are evidence of a worker/Redis failure. They do not establish the worker's current process state or prove an invalid Redis URL. The old entrypoint's unsupervised worker allows the API to remain online after worker death.
- Filter `audit` returned no matching retained deployment logs. Absence of matching logs is not proof that no audit has ever run.
- PostgreSQL `alembic_version` table shows `0003`. Table list does not include `api_usage_log`.
- Previously verified Vercel production source is `917e00d`, while prepared PR source is `b138de7` (94 CI tests passed). Frontend and backend therefore currently have different baselines.

## Deployment blocker

The reconciled branch retains upstream migrations 0004–0006. The entrypoint runs `alembic upgrade head`; deploying it against this database would change production schema:

- 0004: unique partial index on phoneless lead name/city; duplicates can block upgrade.
- 0005: lead status CHECK constraint; invalid existing status values can block upgrade.
- 0006: API usage table/indexes.

The user's restriction on production migrations remains in force. Do not merge/deploy this branch as a migration-free fix. First decide between an explicitly authorized migration rollout with read-only preflight checks/backups, and a narrower backend hotfix based on the deployed c70779b source.

## Additional defect

Live logs also show SQLAlchemy concurrent-session and illegal-close errors on September 11–12. Current source `backend/api/routes/leads.py:85` runs two repository calls with `asyncio.gather` on one AsyncSession. This is a concrete matching defect, still present in the prepared branch; the filtered log excerpt alone does not prove every logged exception came from that endpoint. Execute those two database queries sequentially in a scoped follow-up fix.

## Next verification

Before rollout, check pending legacy jobs and existing audit results without retrying or modifying them; inspect Redis heartbeat and queue with read-only operations. A working API/Redis service badge does not establish worker liveness. After an authorized rollout, verify health includes the worker and a controlled audit completes, then simulate worker loss in staging. Do not auto-rerun legacy jobs or send outreach.
