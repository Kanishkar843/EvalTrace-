"""Real Compose queue/restart/run/comparison and CLI exit-code acceptance."""

import json, os, subprocess, time, ssl
import httpx, truststore

base = os.getenv("ACCEPTANCE_URL", "http://127.0.0.1:18082")
project = os.getenv("COMPOSE_PROJECT_NAME", "evaltrace-acceptance")
docker = os.getenv("DOCKER_BIN", "docker")
token = os.environ["ADMIN_TOKEN"]
with httpx.Client(
    base_url=base,
    verify=truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT),
    trust_env=False,
    timeout=30,
) as client:

    def call(path, data=None):
        response = client.request(
            "POST" if data is not None else "GET",
            path,
            json=data,
            headers={"Authorization": "Bearer " + token},
        )
        response.raise_for_status()
        return response.json()

    assert client.get("/runs").status_code == 401
    assert call("/health")["database"] == "postgresql"
    dataset = call("/datasets/seed", {})
    queued = call(
        "/runs/queue", {"dataset_id": dataset["id"], "target": "fixture-baseline"}
    )
    subprocess.run([docker, "compose", "-p", project, "restart", "api"], check=True)
    for _ in range(90):
        try:
            call("/ready")
            break
        except Exception:
            time.sleep(1)
    else:
        raise AssertionError("API failed to recover")
    assert call("/runs/" + queued["id"])["status"] == "queued"
    call("/workers/step", {})
    good = call("/runs/" + queued["id"])
    assert good["gate"]["passed"] and good["completed_cases"] == 3
    bad = call("/runs", {"dataset_id": dataset["id"], "target": "fixture-regressed"})
    assert not bad["gate"]["passed"]
    compared = call("/compare", {"baseline": good["id"], "candidate": bad["id"]})
    assert (
        compared["delta"]["recall_at_5"] == -1
        and not compared["release_gate"]["passed"]
    )
    for target, expected in [("fixture-baseline", 0), ("fixture-regressed", 1)]:
        result = subprocess.run(
            [
                docker,
                "compose",
                "-p",
                project,
                "exec",
                "-T",
                "api",
                "python",
                "-m",
                "app.cli",
                "--target",
                target,
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == expected, (target, result.returncode)
    print(
        json.dumps(
            {
                "database": "PostgreSQL",
                "queue_after_restart": "passed",
                "baseline": "passed",
                "intentional_regression": "blocked as expected",
                "comparison": "passed",
                "CLI_exit_codes": [0, 1],
            }
        )
    )
