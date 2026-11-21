"""Real PostgreSQL process-death recovery. No SQLite fallback."""

import json, os, subprocess, sys, time
from pathlib import Path
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
import psutil
from sqlalchemy import text
from app.engine import Engine


def test_postgres_worker_death_recovery(tmp_path):
    url = os.environ.get("TEST_DATABASE_URL", "")
    assert url.startswith("postgresql")
    env = {**os.environ, "DATABASE_URL": url}
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        env=env,
        check=True,
        capture_output=True,
    )
    engine = Engine(url)
    raw = json.loads(Path("data/suite.json").read_text())
    dataset = engine.register("recovery-" + uuid4().hex, raw)
    queued = engine.enqueue(dataset["id"], "fixture-baseline")
    marker = tmp_path / "blocked.marker"
    env.update({"WORKER_RUN_ID": queued["id"], "WORKER_MARKER": str(marker)})
    code = """import os,time
from pathlib import Path
from app.engine import Engine
import app.adapters
calls=0
def block(case,target):
    global calls
    calls+=1
    if calls==2:
        Path(os.environ['WORKER_MARKER']).write_text('blocked after first checkpoint')
        time.sleep(120)
    return case.fixture,None
app.adapters.invoke=block
Engine().work_one(os.environ['WORKER_RUN_ID'])
"""
    process = subprocess.Popen(
        [sys.executable, "-u", "-c", code],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.monotonic() + 45
        while not marker.exists() and time.monotonic() < deadline:
            assert process.poll() is None, "Worker exited before checkpoint"
            time.sleep(0.1)
        assert marker.exists(), "Worker did not reach checkpoint"
        owned = psutil.Process(process.pid).children(recursive=True)
        for child in owned:
            child.kill()
        process.kill()
        process.wait(timeout=10)
        psutil.wait_procs(owned, timeout=10)
        assert engine.run(queued["id"])["completed_cases"] == 1
        # Accelerate the 90-second lease deadline; process death above is real.
        with engine.db.begin() as c:
            c.execute(
                text("UPDATE run_jobs SET lease_until=0 WHERE run_id=:id"),
                {"id": queued["id"]},
            )
        restarted = Engine(url)
        result = restarted.work_one(queued["id"])
        assert result["gate"]["passed"] and len(result["cases"]) == len(raw)
        repeat = restarted.execute(dataset["id"], "fixture-baseline")
        bad = restarted.execute(dataset["id"], "fixture-regressed")
        assert repeat["scores"] == result["scores"] and not bad["gate"]["passed"]
        assert restarted.compare(result["id"], bad["id"])["delta"]["recall_at_5"] == -1
        extra = restarted.enqueue(dataset["id"], "fixture-baseline")
        with ThreadPoolExecutor(2) as pool:
            outcomes = list(
                pool.map(lambda _: restarted.work_one(extra["id"]), range(2))
            )
        assert sum(x is not None for x in outcomes) == 1
        with engine.db.connect() as c:
            assert (
                c.execute(text("SELECT version_num FROM alembic_version")).scalar()
                == "0002"
            )
            assert c.execute(
                text("SELECT count(*) FROM run_cases WHERE run_id=:id"),
                {"id": queued["id"]},
            ).scalar() == len(raw)
            assert c.execute(
                text("SELECT count(*) FROM model_outputs WHERE run_id=:id"),
                {"id": queued["id"]},
            ).scalar() == len(raw)
            assert (
                c.execute(
                    text("SELECT attempts FROM run_jobs WHERE run_id=:id"),
                    {"id": queued["id"]},
                ).scalar()
                == 2
            )
        restarted.db.dispose()
    finally:
        if process.poll() is None:
            owned = psutil.Process(process.pid).children(recursive=True)
            for child in owned:
                child.kill()
            process.kill()
            process.wait(timeout=10)
        engine.db.dispose()
