# AgencyOS production rollout — 2026-09-12

User explicitly authorized production migrations 0004–0006 and deployment to Railway/Vercel.

## Backup and preflight

- PostgreSQL pre-upgrade revision: 0003; lead count: 22.
- Blocking phoneless duplicate groups (non-null city): 0.
- Invalid lead statuses: 0.
- Custom-format pg_dump created and its archive listing verified with pg_restore.
- Persistent backup: `/var/lib/postgresql/data/agencyos-backups/agencyos-preupgrade-20260912.dump` on the existing PostgreSQL volume; mode 600, directory mode 700.
- SHA256: `1072650922c9dcf46be6a0982824c375b6e218e17b8d331047c9e509888f35f5`.
- A browser download was initiated but a local file has not been verified. The verified backup is on the same database volume and is not an independent disaster-recovery copy.
- No lead records deleted; no credentials changed or disclosed.

## Releases

- PR 1 merged as 0f16bd9: live baseline reconciliation, audit lifecycle repairs, pipeline concurrent-session fix. CI: 95 passed. Railway deployment 7d507b7a-d0dd-4963-a881-5aafceeb9b5b.
- PostgreSQL revision 0006 verified in the Railway database UI; pipeline UI displays all 22 records.
- Recovered worker consumed a previously queued audit, which failed promptly due to Anthropic SDK rejecting the legacy temperature keyword.
- PR 2 merged as cf584ca: retain sampling values via extra_body per official SDK migration guide; pin Anthropic 1.5.0; test actual SDK serialization using mock HTTP transport. CI: 96 passed. Railway deployment c6249bb5-2dba-4c6f-8719-ba64c7be7f14; Vercel production dpl_22ifYS53oAwutPeTquzUExLfu7Sd.
- Controlled Hilal Veteriner audit attempt returned HTTP 503 without creating a new job: ARQ's one-hour default heartbeat refresh did not recover promptly after the previous worker deleted the shared health key during overlapping deployments.
- PR 3 merged as `101d052fb1dab84bf55f7223bae66e05433dc521`; heartbeat interval is five seconds. CI: **97 passed**.
- Final Railway deployment: `fe161cee-b63d-494c-934f-8dbab4b96d3b`, successful.
- Final Vercel production deployment: `dpl_AKn2jqGf2iC3RfzXCcDhmpMjYnKy`, READY, source main at the same commit, production aliases verified.
- Backend `/health` from the running container: status ok, db connected, redis connected, worker available (2026-09-12 00:45:16 UTC).
- Hilal Veteriner controlled audit job `2bccb22b-3c1b-4b69-89c7-52043878e7e7`: API confirms **completed**, error null, audit `a23dc5cc-b68b-4754-9ebf-feb1d0987808`, report score 55. UI displayed RUNNING then the report, sales draft, message/proposal controls.
- Existing scoring recalculated this lead's opportunity score from 39 to 36. Scoring formulas were not changed. No outreach was sent.
- Existing content-quality follow-up: generated sales draft exposes `clinic_general`; conversion-loss/traffic claims in generated audit text are not independently verified by this deployment smoke test. Delivery reliability is verified; commercial accuracy is a separate evaluation.
- Local Git checkout fast-forwarded to deployed main; working tree clean.

## References

- https://github.com/tonguc/agencyos-bot/pull/1
- https://github.com/tonguc/agencyos-bot/pull/2
- https://github.com/tonguc/agencyos-bot/pull/3
- https://github.com/anthropics/anthropic-sdk-python/blob/main/MIGRATION.md
