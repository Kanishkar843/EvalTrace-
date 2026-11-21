import os, json, hashlib, time
from uuid import uuid4
from datetime import datetime, timezone
from sqlalchemy import create_engine, text
from jsonschema import Draft202012Validator
from .metrics import Case, Trace, score, gate, DEFAULT_POLICY


def now():
    return datetime.now(timezone.utc).isoformat()


class Engine:
    def __init__(self, url=None):
        self.db = create_engine(
            url or os.getenv("DATABASE_URL", "sqlite:///./evaltrace.db")
        )

    def migrate(self):
        from .schema import upgrade

        with self.db.begin() as c:
            upgrade(c)
            c.execute(
                text(
                    "INSERT INTO gate_policies VALUES (1,:p) ON CONFLICT(id) DO NOTHING"
                ),
                {"p": json.dumps(DEFAULT_POLICY)},
            )

    def normalize_dataset(self, c, identity, version, cases):
        c.execute(
            text(
                "INSERT INTO eval_projects VALUES ('local','Local evaluation studio') ON CONFLICT(id) DO NOTHING"
            )
        )
        c.execute(
            text(
                "INSERT INTO dataset_versions VALUES (:id,'local',:version) ON CONFLICT(id) DO NOTHING"
            ),
            {"id": identity, "version": version},
        )
        for case in cases:
            c.execute(
                text(
                    "INSERT INTO test_cases VALUES (:d,:id,:payload) ON CONFLICT(dataset_id,case_id) DO NOTHING"
                ),
                {"d": identity, "id": case.id, "payload": case.model_dump_json()},
            )

    def policy(self):
        with self.db.connect() as c:
            return json.loads(
                c.execute(
                    text("SELECT policy FROM gate_policies WHERE id=1")
                ).scalar_one()
            )

    def register(self, name, raw):
        if len(raw) > 100:
            raise ValueError("At most 100 cases")
        cases = [Case.model_validate(x) for x in raw]
        if not cases or len({c.id for c in cases}) != len(cases):
            raise ValueError("Cases must have unique IDs and dataset must not be empty")
        for case in cases:
            Draft202012Validator.check_schema(case.output_schema)
        payload = json.dumps([c.model_dump() for c in cases], sort_keys=True)
        version = hashlib.sha256(payload.encode()).hexdigest()
        identity = str(uuid4())
        with self.db.begin() as c:
            existing = c.execute(
                text("SELECT id FROM datasets WHERE name=:n AND version=:v"),
                {"n": name, "v": version},
            ).scalar()
            if existing:
                self.normalize_dataset(c, existing, version, cases)
                return {"id": existing, "version": version, "reused": True}
            c.execute(
                text("INSERT INTO datasets VALUES (:id,:n,:v,:cases,:stamp)"),
                {
                    "id": identity,
                    "n": name,
                    "v": version,
                    "cases": payload,
                    "stamp": now(),
                },
            )
            self.normalize_dataset(c, identity, version, cases)
        return {"id": identity, "version": version, "reused": False}

    def datasets(self):
        with self.db.connect() as c:
            return [
                dict(r)
                for r in c.execute(
                    text(
                        "SELECT id,name,version,created_at FROM datasets ORDER BY created_at DESC"
                    )
                ).mappings()
            ]

    def enqueue(self, dataset_id, target):
        from .adapters import TARGETS

        if target not in TARGETS:
            raise ValueError("Unknown adapter")
        with self.db.connect() as c:
            dataset = (
                c.execute(
                    text("SELECT * FROM datasets WHERE id=:id"), {"id": dataset_id}
                )
                .mappings()
                .first()
            )
        if not dataset:
            raise KeyError("Dataset not found")
        identity = str(uuid4())
        policy = self.policy()
        with self.db.begin() as c:
            c.execute(
                text(
                    "INSERT INTO target_adapters VALUES (:id,:kind) ON CONFLICT(id) DO NOTHING"
                ),
                {
                    "id": target,
                    "kind": "fixture" if target.startswith("fixture") else "http",
                },
            )
            c.execute(
                text("INSERT INTO runs VALUES (:id,:d,:t,'queued',:r,:stamp)"),
                {
                    "id": identity,
                    "d": dataset_id,
                    "t": target,
                    "r": "{}",
                    "stamp": now(),
                },
            )
            c.execute(
                text(
                    "INSERT INTO run_jobs VALUES (:id,'queued',NULL,0,0,:policy,:stamp)"
                ),
                {"id": identity, "policy": json.dumps(policy), "stamp": now()},
            )
        return {
            "id": identity,
            "status": "queued",
            "total": len(json.loads(dataset["cases"])),
        }

    def claim(self, identity=None):
        owner = str(uuid4())
        stamp = time.time()
        with self.db.begin() as c:
            query = "SELECT * FROM run_jobs WHERE (state IN ('queued','interrupted') OR (state='running' AND lease_until<:stamp))"
            if identity:
                query += " AND run_id=:id"
            query += " ORDER BY updated_at LIMIT 1"
            if self.db.dialect.name == "postgresql":
                query += " FOR UPDATE SKIP LOCKED"
            row = (
                c.execute(text(query), {"stamp": stamp, "id": identity})
                .mappings()
                .first()
            )
            if not row:
                return None
            result = c.execute(
                text(
                    "UPDATE run_jobs SET state='running',owner=:owner,lease_until=:lease,attempts=attempts+1,updated_at=:updated WHERE run_id=:id AND (state IN ('queued','interrupted') OR lease_until<:stamp)"
                ),
                {
                    "owner": owner,
                    "lease": stamp + 90,
                    "updated": now(),
                    "id": row["run_id"],
                    "stamp": stamp,
                },
            )
            if result.rowcount != 1:
                return None
            c.execute(
                text("UPDATE runs SET status='running' WHERE id=:id"),
                {"id": row["run_id"]},
            )
        return row["run_id"], owner, json.loads(row["policy"])

    def checkpoint(self, c, identity, owner, row, ordinal):
        changed = c.execute(
            text(
                "UPDATE run_jobs SET lease_until=:lease,updated_at=:stamp WHERE run_id=:id AND owner=:owner AND state='running'"
            ),
            {"lease": time.time() + 90, "stamp": now(), "id": identity, "owner": owner},
        )
        if changed.rowcount != 1:
            raise RuntimeError("Worker lease lost")
        params = {
            "run": identity,
            "case": row["case_id"],
            "ordinal": ordinal,
            "payload": json.dumps(row),
        }
        c.execute(
            text("INSERT INTO run_cases VALUES (:run,:case,:ordinal,:payload)"), params
        )
        trace = row["trace"]
        c.execute(
            text("INSERT INTO model_outputs VALUES (:run,:case,:answer,:structured)"),
            {
                **params,
                "answer": trace["answer"],
                "structured": json.dumps(trace["structured"]),
            },
        )
        for i, tool in enumerate(trace["tools"]):
            c.execute(
                text("INSERT INTO tool_calls VALUES (:run,:case,:i,:name,:args)"),
                {
                    **params,
                    "i": i,
                    "name": tool["name"],
                    "args": json.dumps(tool["arguments"]),
                },
            )
        for i, doc in enumerate(trace["retrieved"]):
            c.execute(
                text(
                    "INSERT INTO retrieved_documents VALUES (:run,:case,:i,:doc,:content)"
                ),
                {**params, "i": i, "doc": doc["id"], "content": doc["text"]},
            )
        for i, doc in enumerate(trace["citations"]):
            c.execute(
                text("INSERT INTO citations VALUES (:run,:case,:i,:doc)"),
                {**params, "i": i, "doc": doc},
            )
        for metric, value in row["scores"].items():
            c.execute(
                text("INSERT INTO scores VALUES (:run,:case,:metric,:value)"),
                {**params, "metric": metric, "value": value},
            )

    def work_one(self, identity=None):
        from .adapters import invoke
        from .metrics import grounding

        claimed = self.claim(identity)
        if not claimed:
            return None
        identity, owner, policy = claimed
        try:
            with self.db.connect() as c:
                run = (
                    c.execute(text("SELECT * FROM runs WHERE id=:id"), {"id": identity})
                    .mappings()
                    .one()
                )
                dataset = (
                    c.execute(
                        text("SELECT * FROM datasets WHERE id=:id"),
                        {"id": run["dataset_id"]},
                    )
                    .mappings()
                    .one()
                )
                done = set(
                    c.execute(
                        text("SELECT case_id FROM run_cases WHERE run_id=:id"),
                        {"id": identity},
                    ).scalars()
                )
            for ordinal, raw in enumerate(json.loads(dataset["cases"])):
                case = Case.model_validate(raw)
                if case.id in done:
                    continue
                started = time.perf_counter()
                tokens = None
                try:
                    trace, tokens = invoke(case, run["target"])
                except Exception as error:
                    trace = Trace(
                        answer="",
                        structured={},
                        completed=False,
                        exception=type(error).__name__,
                    )
                scores = score(case, trace)
                row = {
                    "case_id": case.id,
                    "prompt": case.prompt,
                    "trace": trace.model_dump(),
                    "scores": scores,
                    "elapsed_ms": (time.perf_counter() - started) * 1000,
                    "relevant_ids": case.relevant_ids,
                    "grounding": grounding(trace),
                    "tokens": tokens,
                    "metric_version": "2",
                    "prompt_version": "trace-v1",
                    "adapter_model": os.getenv("LLM_MODEL", "gpt-4.1-mini")
                    if run["target"] == "provider"
                    else run["target"],
                    "failures": [
                        name
                        for name, value in scores.items()
                        if (name == "exception_rate" and value > 0)
                        or (name != "exception_rate" and value < policy.get(name, 1))
                    ],
                }
                with self.db.begin() as c:
                    self.checkpoint(c, identity, owner, row, ordinal)
            with self.db.connect() as c:
                results = [
                    json.loads(x)
                    for x in c.execute(
                        text(
                            "SELECT payload FROM run_cases WHERE run_id=:id ORDER BY ordinal"
                        ),
                        {"id": identity},
                    ).scalars()
                ]
            average = {
                k: sum(row["scores"][k] for row in results) / len(results)
                for k in results[0]["scores"]
            }
            observed = [x["tokens"] for x in results]
            result = {
                "id": identity,
                "dataset_id": run["dataset_id"],
                "dataset_version": dataset["version"],
                "target": run["target"],
                "scores": average,
                "gate": gate(average, policy),
                "policy_snapshot": policy,
                "cases": results,
                "mode": "synthetic fixture"
                if run["target"].startswith("fixture")
                else run["target"],
                "judge": "not configured; deterministic claim support is not semantic entailment or a hallucination detector",
                "tokens": sum(observed)
                if all(x is not None for x in observed)
                else None,
                "cost": None,
                "metric_version": "2",
            }
            with self.db.begin() as c:
                changed = c.execute(
                    text(
                        "UPDATE run_jobs SET state='completed',lease_until=0,updated_at=:stamp WHERE run_id=:id AND owner=:owner"
                    ),
                    {"stamp": now(), "id": identity, "owner": owner},
                )
                if changed.rowcount != 1:
                    raise RuntimeError("Worker lease lost")
                c.execute(
                    text(
                        "UPDATE runs SET status='completed',result=:result WHERE id=:id"
                    ),
                    {"id": identity, "result": json.dumps(result)},
                )
            return result
        except BaseException:
            with self.db.begin() as c:
                changed = c.execute(
                    text(
                        "UPDATE run_jobs SET state='interrupted',lease_until=0,updated_at=:stamp WHERE run_id=:id AND owner=:owner AND state='running'"
                    ),
                    {"stamp": now(), "id": identity, "owner": owner},
                )
                if changed.rowcount:
                    c.execute(
                        text("UPDATE runs SET status='interrupted' WHERE id=:id"),
                        {"id": identity},
                    )
            raise

    def execute(self, dataset_id, target):
        queued = self.enqueue(dataset_id, target)
        result = self.work_one(queued["id"])
        if result is None:
            raise RuntimeError("Run was claimed by another worker")
        return result

    def runs(self):
        with self.db.connect() as c:
            return [
                dict(r) | {"result": json.loads(r["result"])}
                for r in c.execute(
                    text("SELECT * FROM runs ORDER BY created_at DESC LIMIT 100")
                ).mappings()
            ]

    def run(self, identity):
        with self.db.connect() as c:
            r = (
                c.execute(text("SELECT * FROM runs WHERE id=:id"), {"id": identity})
                .mappings()
                .first()
            )
        if not r:
            raise KeyError("Run not found")
        with self.db.connect() as c:
            partial = [
                json.loads(x)
                for x in c.execute(
                    text(
                        "SELECT payload FROM run_cases WHERE run_id=:id ORDER BY ordinal"
                    ),
                    {"id": identity},
                ).scalars()
            ]
            total = len(
                json.loads(
                    c.execute(
                        text("SELECT cases FROM datasets WHERE id=:id"),
                        {"id": r["dataset_id"]},
                    ).scalar_one()
                )
            )
        return {
            "id": identity,
            "status": r["status"],
            "completed_cases": len(partial),
            "total_cases": total,
            "cases": partial,
            **json.loads(r["result"]),
        }

    def compare(self, baseline, candidate):
        a = self.run(baseline)
        b = self.run(candidate)
        if a["status"] != "completed" or b["status"] != "completed":
            raise ValueError("Both runs must be completed")
        if a.get("metric_version") != b.get("metric_version"):
            raise ValueError("Metric versions must match")
        if a["dataset_version"] != b["dataset_version"]:
            raise ValueError("Comparisons require identical dataset versions")
        result = {
            "baseline": baseline,
            "candidate": candidate,
            "delta": {k: b["scores"][k] - a["scores"][k] for k in a["scores"]},
            "candidate_gate": b["gate"],
        }

        regressions = [
            name
            for name, delta in result["delta"].items()
            if (delta > 1e-9 if name == "exception_rate" else delta < -1e-9)
        ]
        result["release_gate"] = {
            "passed": b["gate"]["passed"] and not regressions,
            "regressions": regressions,
        }
        with self.db.begin() as c:
            c.execute(
                text("INSERT INTO comparisons VALUES (:id,:a,:b,:p,:stamp)"),
                {
                    "id": str(uuid4()),
                    "a": baseline,
                    "b": candidate,
                    "p": json.dumps(result),
                    "stamp": now(),
                },
            )
        return result
