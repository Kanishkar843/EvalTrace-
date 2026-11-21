import json, time
from pathlib import Path
import pytest
from sqlalchemy import text
from app.engine import Engine
from app.metrics import Trace, grounding


@pytest.fixture
def engine(tmp_path):
    e = Engine("sqlite:///" + str(tmp_path / "durable.db"))
    e.migrate()
    return e


def test_checkpoint_recovery_and_policy_snapshot(engine, monkeypatch):
    raw = json.loads(Path("data/suite.json").read_text())
    d = engine.register("recovery", raw)
    queued = engine.enqueue(d["id"], "fixture-baseline")
    calls = []

    def interrupt(case, target):
        calls.append(case.id)
        if len(calls) == 2:
            raise KeyboardInterrupt()
        return case.fixture, None

    monkeypatch.setattr("app.adapters.invoke", interrupt)
    with pytest.raises(KeyboardInterrupt):
        engine.work_one(queued["id"])
    partial = engine.run(queued["id"])
    assert partial["status"] == "interrupted" and partial["completed_cases"] == 1
    with engine.db.begin() as c:
        c.execute(
            text("UPDATE gate_policies SET policy=:p WHERE id=1"),
            {"p": json.dumps({"recall_at_5": 0})},
        )
    monkeypatch.setattr(
        "app.adapters.invoke", lambda case, target: (case.fixture, None)
    )
    result = engine.work_one(queued["id"])
    assert result["gate"]["passed"] and result["policy_snapshot"]["recall_at_5"] == 0.8
    with engine.db.connect() as c:
        assert c.execute(text("SELECT count(*) FROM run_cases")).scalar() == len(raw)
        assert c.execute(text("SELECT count(*) FROM model_outputs")).scalar() == len(
            raw
        )
    assert engine.work_one(queued["id"]) is None


def test_lease_reclaim_fences_old_worker(engine):
    d = engine.register("lease", json.loads(Path("data/suite.json").read_text()))
    queued = engine.enqueue(d["id"], "fixture-baseline")
    old = engine.claim(queued["id"])
    assert old
    assert engine.claim(queued["id"]) is None
    with engine.db.begin() as c:
        c.execute(
            text("UPDATE run_jobs SET lease_until=0 WHERE run_id=:id"),
            {"id": queued["id"]},
        )
    new = engine.claim(queued["id"])
    assert new and new[1] != old[1]
    with engine.db.begin() as c:
        with pytest.raises(RuntimeError, match="lease lost"):
            engine.checkpoint(c, queued["id"], old[1], {}, 0)


def test_claim_support_rejects_negation_and_numbers():
    def trace(answer):
        return Trace(
            answer=answer,
            structured={},
            retrieved=[{"id": "a", "text": "The service stores 10 records"}],
            citations=["a"],
        )

    assert grounding(trace("The service stores 10 records"))["supported_fraction"] == 1
    assert (
        grounding(trace("The service does not store 10 records"))["supported_fraction"]
        == 0
    )
    assert grounding(trace("The service stores 100 records"))["supported_fraction"] == 0
