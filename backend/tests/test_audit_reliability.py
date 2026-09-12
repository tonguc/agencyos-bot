"""Isolated regressions: no network, production database or provider calls."""
import sys
import asyncio
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import models  # register ORM relationships
from config import Settings
from api.routes import audit as route
from api.routes import health
from core import audit_generator as generator
from core import sales_output_generator as sales
from jobs.tasks import audit as task
from jobs import reconcile
from arq.jobs import JobStatus
from fastapi import HTTPException, Response


@pytest.mark.parametrize("value,expected", [
    ("localhost:6379/2", "redis://localhost:6379/2"),
    (" redis://localhost/0 ", "redis://localhost/0"),
    ("rediss://localhost/1", "rediss://localhost/1"),
    ("unix:///tmp/redis.sock", "unix:///tmp/redis.sock"),
])
def test_shared_redis_dsn(value, expected):
    assert Settings(_env_file=None, REDIS_URL=value).redis_dsn == expected


@pytest.fixture
def fakes(monkeypatch):
    job = SimpleNamespace(id=uuid.uuid4(), status="pending", result=None, created_at=datetime.now(timezone.utc))
    repo = SimpleNamespace(find_active_for_lead=AsyncMock(return_value=None), get=AsyncMock(return_value=job), create=AsyncMock(return_value=job),
                           mark_running=AsyncMock(), mark_completed=AsyncMock(), mark_failed=AsyncMock())
    db = SimpleNamespace(commit=AsyncMock(), refresh=AsyncMock())
    class Session:
        async def __aenter__(self):
            return db
        async def __aexit__(self, *args):
            return False
    monkeypatch.setattr(task, "AsyncSessionFactory", Session)
    monkeypatch.setattr(task, "JobRepository", lambda _: repo)
    monkeypatch.setattr(route, "JobRepository", lambda _: repo)
    monkeypatch.setattr(route, "LeadRepository", lambda _: SimpleNamespace(get=AsyncMock(return_value=object())))
    queue = SimpleNamespace(exists=AsyncMock(return_value=True), enqueue_job=AsyncMock(return_value=object()))
    return job, repo, db, queue


@pytest.mark.asyncio
async def test_offline_worker_does_not_create_job(fakes):
    _, repo, db, queue = fakes
    queue.exists.return_value = False
    with pytest.raises(HTTPException) as exc:
        await route.trigger_audit(uuid.uuid4(), db, queue)
    assert exc.value.status_code == 503
    repo.create.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", [RuntimeError("secret must not escape"), None])
async def test_enqueue_failure_is_persisted(fakes, failure):
    _, repo, db, queue = fakes
    queue.enqueue_job.side_effect = failure
    queue.enqueue_job.return_value = None
    with pytest.raises(HTTPException):
        await route.trigger_audit(uuid.uuid4(), db, queue)
    repo.mark_failed.assert_awaited_once()
    assert "secret" not in str(repo.mark_failed.call_args)
    assert db.commit.await_count == 2


@pytest.mark.asyncio
async def test_stable_queue_id(fakes):
    job, repo, db, queue = fakes
    result = await route.trigger_audit(uuid.uuid4(), db, queue)
    assert result.job_id == job.id
    assert queue.enqueue_job.call_args.kwargs["_job_id"] == str(job.id)
    assert repo.create.call_args.kwargs["payload"]["queue_tracking"] is True


@pytest.mark.asyncio
async def test_existing_audit_is_reused_even_if_worker_is_offline(fakes):
    job, repo, db, queue = fakes
    repo.find_active_for_lead.return_value = job
    queue.exists.return_value = False
    result = await route.trigger_audit(uuid.uuid4(), db, queue)
    assert result.job_id == job.id
    repo.create.assert_not_awaited()
    queue.enqueue_job.assert_not_awaited()


@pytest.mark.asyncio
async def test_audit_deadline_leaves_worker_failure_persistence_time(fakes, monkeypatch):
    from jobs.worker import WorkerSettings
    job, _, _, _ = fakes
    durations = []
    original_timeout = asyncio.timeout
    def capture_timeout(seconds):
        durations.append(seconds)
        return original_timeout(seconds)
    monkeypatch.setattr(task.asyncio, "timeout", capture_timeout)
    monkeypatch.setattr(task, "run_audit", AsyncMock(return_value=SimpleNamespace(id=uuid.uuid4(), general_score=60)))
    await task.run_audit_job({}, str(uuid.uuid4()), str(job.id))
    assert durations == [210]
    assert durations[0] < WorkerSettings.job_timeout


@pytest.mark.asyncio
async def test_lost_enqueue_ack_does_not_fail_started_job(fakes):
    job, repo, db, queue = fakes
    queue.enqueue_job.side_effect = TimeoutError()
    db.refresh.side_effect = lambda *a, **kw: setattr(job, "status", "running")
    result = await route.trigger_audit(uuid.uuid4(), db, queue)
    assert result.status == "running"
    repo.mark_failed.assert_not_awaited()


@pytest.mark.asyncio
async def test_completion_commits_with_audit(fakes, monkeypatch):
    job, repo, db, _ = fakes
    report = SimpleNamespace(id=uuid.uuid4(), general_score=60)
    monkeypatch.setattr(task, "run_audit", AsyncMock(return_value=report))
    commits = []
    db.commit.side_effect = lambda: commits.append(repo.mark_completed.await_count)
    result = await task.run_audit_job({}, str(uuid.uuid4()), str(job.id))
    assert result["audit_id"] == str(report.id)
    assert task.run_audit.call_args.kwargs["since_dt"] == job.created_at
    assert commits == [0, 1]


@pytest.mark.asyncio
async def test_initial_db_failure_can_be_recorded(fakes, monkeypatch):
    job, repo, db, _ = fakes
    repo.get.side_effect = [RuntimeError("db unavailable"), job]
    run = AsyncMock()
    monkeypatch.setattr(task, "run_audit", run)
    with pytest.raises(RuntimeError):
        await task.run_audit_job({}, str(uuid.uuid4()), str(job.id))
    repo.mark_failed.assert_awaited_once()
    run.assert_not_awaited()


@pytest.mark.asyncio
async def test_timeout_is_terminal(fakes, monkeypatch):
    job, repo, _, _ = fakes
    monkeypatch.setattr(task, "run_audit", AsyncMock(side_effect=TimeoutError()))
    with pytest.raises(TimeoutError):
        await task.run_audit_job({}, str(uuid.uuid4()), str(job.id))
    assert "zaman aşımı" in repo.mark_failed.call_args.args[1]


@pytest.mark.asyncio
async def test_completed_retry_does_not_regenerate(fakes, monkeypatch):
    job, _, _, _ = fakes
    job.status = "completed"
    run = AsyncMock()
    monkeypatch.setattr(task, "run_audit", run)
    await task.run_audit_job({}, str(uuid.uuid4()), str(job.id))
    run.assert_not_awaited()


@pytest.mark.asyncio
async def test_cancellation_leaves_arq_free_to_retry(fakes, monkeypatch):
    job, repo, _, _ = fakes
    monkeypatch.setattr(task, "run_audit", AsyncMock(side_effect=asyncio.CancelledError()))
    with pytest.raises(asyncio.CancelledError):
        await task.run_audit_job({}, str(uuid.uuid4()), str(job.id))
    repo.mark_completed.assert_not_awaited()
    repo.mark_failed.assert_not_awaited()


@pytest.mark.asyncio
async def test_valid_audit_is_preserved(monkeypatch):
    monkeypatch.setattr(generator, "fetch_site_data", AsyncMock(return_value={"title": "Test"}))
    monkeypatch.setattr(generator, "build_audit_prompt", lambda *args: "test")
    data = {"skorlar": {"ux": 50, "seo": 60, "donusum": 70}, "genel_skor": 60}
    monkeypatch.setattr(generator, "claude_api_call", AsyncMock(return_value=json.dumps(data)))
    result = await generator.generate_audit({}, {})
    assert result["genel_skor"] == 60
    assert result["_site_data"]["title"] == "Test"


@pytest.mark.asyncio
@pytest.mark.parametrize("text", ["", "garbage", "{}", "[]", '{"skorlar":{"ux":null}}'])
async def test_invalid_ai_response_fails(monkeypatch, text):
    monkeypatch.setattr(generator, "fetch_site_data", AsyncMock(return_value={}))
    monkeypatch.setattr(generator, "build_audit_prompt", lambda *args: "test")
    monkeypatch.setattr(generator, "claude_api_call", AsyncMock(return_value=text))
    with pytest.raises(RuntimeError):
        await generator.generate_audit({}, {})


@pytest.mark.asyncio
async def test_sales_uses_configured_credentials(monkeypatch):
    monkeypatch.setattr(sales.settings, "CLAUDE_API_KEY", "test-only-not-a-secret")
    monkeypatch.setattr(sales.settings, "CLAUDE_MODEL", "test-model")
    create = AsyncMock(return_value=SimpleNamespace(content=[SimpleNamespace(text="Test.")]))
    seen = {}
    def client(**kwargs):
        seen.update(kwargs)
        return SimpleNamespace(messages=SimpleNamespace(create=create))
    monkeypatch.setattr(sales.anthropic, "AsyncAnthropic", client)
    await sales.generate_sales_output({}, {}, {})
    assert seen["api_key"] == "test-only-not-a-secret"
    assert all(c.kwargs["model"] == "test-model" for c in create.call_args_list)


@pytest.mark.asyncio
async def test_health_detects_missing_worker(monkeypatch):
    monkeypatch.setattr(health, "check_db", AsyncMock(return_value=True))
    pool = SimpleNamespace(ping=AsyncMock(return_value=True), exists=AsyncMock(return_value=False))
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(arq_pool=pool)))
    response = Response()
    result = await health.health(request, response)
    assert response.status_code == 503
    assert result.worker == "unavailable"


@pytest.mark.asyncio
@pytest.mark.parametrize("status,fail", [(JobStatus.in_progress, False), (JobStatus.queued, False),
                                        (JobStatus.not_found, True), (JobStatus.complete, True)])
async def test_reconcile_never_fails_live_queue_job(fakes, monkeypatch, status, fail):
    job, repo, db, _ = fakes
    db.execute = AsyncMock(return_value=SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [job])))
    class Session:
        async def __aenter__(self): return db
        async def __aexit__(self, *args): return False
    monkeypatch.setattr(reconcile, "AsyncSessionFactory", Session)
    monkeypatch.setattr(reconcile, "JobRepository", lambda _: repo)
    monkeypatch.setattr(reconcile, "QueueJob", lambda *a, **kw: SimpleNamespace(status=AsyncMock(return_value=status)))
    await reconcile.reconcile_audits({"redis": object()})
    assert repo.mark_failed.await_count == int(fail)


@pytest.mark.asyncio
async def test_reconcile_preserves_concurrent_completion(fakes, monkeypatch):
    job, repo, db, _ = fakes
    db.execute = AsyncMock(return_value=SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [job])))
    db.refresh.side_effect = lambda *a, **kw: setattr(job, "status", "completed")
    class Session:
        async def __aenter__(self): return db
        async def __aexit__(self, *args): return False
    monkeypatch.setattr(reconcile, "AsyncSessionFactory", Session)
    monkeypatch.setattr(reconcile, "JobRepository", lambda _: repo)
    monkeypatch.setattr(reconcile, "QueueJob", lambda *a, **kw: SimpleNamespace(status=AsyncMock(return_value=JobStatus.complete)))
    await reconcile.reconcile_audits({"redis": object()})
    repo.mark_failed.assert_not_awaited()
