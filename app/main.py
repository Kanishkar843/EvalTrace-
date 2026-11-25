import os, secrets, json, threading
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Literal
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import text
from .engine import Engine
from .metrics import Case, DEFAULT_POLICY

engine = Engine()
run_lock = threading.Lock()


@asynccontextmanager
async def lifespan(app):
    if engine.db.dialect.name == "sqlite":
        engine.migrate()
    yield


app = FastAPI(title="EvalTrace", lifespan=lifespan)


def admin(authorization: str = Header(default="")):
    expected = os.getenv("ADMIN_TOKEN")
    if not expected:
        raise HTTPException(503, "Set ADMIN_TOKEN for local studio access")
    if not secrets.compare_digest(authorization, "Bearer " + expected):
        raise HTTPException(401, "Invalid admin token")


class Dataset(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    cases: list[Case] = Field(min_length=1, max_length=100)


class Run(BaseModel):
    dataset_id: str
    target: Literal[
        "fixture-baseline", "fixture-regressed", "local-http", "remote-http", "provider"
    ] = "fixture-baseline"


class Comparison(BaseModel):
    baseline: str
    candidate: str


@app.get("/health")
def health():
    return {"status": "ok", "mode": "local-demo", "database": engine.db.dialect.name}


@app.get("/datasets", dependencies=[Depends(admin)])
@app.get("/suites", dependencies=[Depends(admin)])
def datasets():
    return engine.datasets()


@app.post("/datasets", dependencies=[Depends(admin)])
def register(data: Dataset):
    try:
        return engine.register(data.name, [c.model_dump() for c in data.cases])
    except ValueError as e:
        raise HTTPException(422, str(e))


@app.post("/datasets/seed", dependencies=[Depends(admin)])
def seed():
    return engine.register(
        "Synthetic agent regression suite",
        json.loads((Path(__file__).parent.parent / "data/suite.json").read_text()),
    )


@app.get("/runs", dependencies=[Depends(admin)])
def runs():
    return engine.runs()


@app.post("/runs", dependencies=[Depends(admin)])
def execute(data: Run):
    if not run_lock.acquire(blocking=False):
        raise HTTPException(409, "A run is already executing")
    try:
        return engine.execute(data.dataset_id, data.target)
    except KeyError:
        raise HTTPException(404, "Dataset not found")
    finally:
        run_lock.release()


@app.get("/runs/{identity}", dependencies=[Depends(admin)])
def run(identity: str):
    try:
        return engine.run(identity)
    except KeyError:
        raise HTTPException(404, "Run not found")


@app.get("/runs/{identity}/cases", dependencies=[Depends(admin)])
def cases(identity: str):
    return run(identity).get("cases", [])


@app.get("/traces", dependencies=[Depends(admin)])
def traces(run_id: str):
    return cases(run_id)


@app.post("/compare", dependencies=[Depends(admin)])
def compare(data: Comparison):
    try:
        return engine.compare(data.baseline, data.candidate)
    except KeyError:
        raise HTTPException(404, "Run not found")
    except ValueError as e:
        raise HTTPException(422, str(e))


@app.get("/gates", dependencies=[Depends(admin)])
def gates():
    return engine.policy()


@app.put("/gates", dependencies=[Depends(admin)])
def update(policy: dict[str, float]):
    if not policy or any(
        k not in (set(DEFAULT_POLICY) | {"citation_support", "grounded_token_overlap"})
        or not 0 <= v <= 1
        for k, v in policy.items()
    ):
        raise HTTPException(422, "Use supported metric floors from 0 to 1")
    with engine.db.begin() as c:
        c.execute(
            text("UPDATE gate_policies SET policy=:p WHERE id=1"),
            {"p": json.dumps(policy)},
        )
    return policy


class ImportDataset(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=2_000_000)


@app.post("/datasets/import", dependencies=[Depends(admin)])
def import_dataset(data: ImportDataset):
    try:
        rows = [json.loads(line) for line in data.content.splitlines() if line.strip()]
        return engine.register(data.name, rows)
    except ValueError:
        raise HTTPException(422, "Invalid JSONL or case schema")


@app.post("/runs/queue", dependencies=[Depends(admin)])
def queue(data: Run):
    try:
        return engine.enqueue(data.dataset_id, data.target)
    except KeyError:
        raise HTTPException(404, "Dataset not found")


@app.post("/workers/step", dependencies=[Depends(admin)])
def worker_step():
    result = engine.work_one()
    return {"worked": result is not None, "run": result}


@app.get("/datasets/{identity}/cases", dependencies=[Depends(admin)])
def dataset_cases(identity: str):
    with engine.db.connect() as c:
        raw = c.execute(
            text("SELECT cases FROM datasets WHERE id=:id"), {"id": identity}
        ).scalar()
    if raw is None:
        raise HTTPException(404, "Dataset not found")
    return json.loads(raw)


@app.get("/ready")
def ready():
    with engine.db.connect() as c:
        c.execute(text("SELECT 1 FROM run_jobs LIMIT 1"))
    return {"ready": True}


static = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static), name="static")
FRONTEND = Path(__file__).parent.parent / "frontend/dist"
if (FRONTEND / "assets").exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND / "assets"), name="assets")


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(
        FRONTEND / "index.html"
        if (FRONTEND / "index.html").exists()
        else static / "index.html"
    )


@app.get("/legacy", include_in_schema=False)
def legacy():
    return FileResponse(static / "index.html")
