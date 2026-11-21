import os

os.environ["DATABASE_URL"] = "sqlite:///./test-api.db"
os.environ["ADMIN_TOKEN"] = "test-token"
from fastapi.testclient import TestClient
from app.main import app


def test_full_api_run_compare():
    with TestClient(app) as c:
        assert c.get("/datasets").status_code == 401
        h = {"Authorization": "Bearer test-token"}
        d = c.post("/datasets/seed", headers=h).json()
        a = c.post(
            "/runs",
            headers=h,
            json={"dataset_id": d["id"], "target": "fixture-baseline"},
        ).json()
        b = c.post(
            "/runs",
            headers=h,
            json={"dataset_id": d["id"], "target": "fixture-regressed"},
        ).json()
        assert a["gate"]["passed"] and not b["gate"]["passed"]
        comp = c.post(
            "/compare", headers=h, json={"baseline": a["id"], "candidate": b["id"]}
        ).json()
        assert comp["delta"]["recall_at_5"] == -1
        assert len(c.get("/runs/" + a["id"] + "/cases", headers=h).json()) == 3
        assert c.put("/gates", headers=h, json={"recall_at_5": 2}).status_code == 422
        assert c.get("/").status_code == 200


def test_mutation_auth_and_import_validation():
    with TestClient(app) as c:
        for route, body in [
            ("/datasets/seed", {}),
            ("/workers/step", {}),
            ("/runs/queue", {"dataset_id": "x", "target": "fixture-baseline"}),
        ]:
            assert c.post(route, json=body).status_code == 401
        h = {"Authorization": "Bearer test-token"}
        assert (
            c.post(
                "/datasets/import",
                headers=h,
                json={"name": "bad", "content": "not json"},
            ).status_code
            == 422
        )
