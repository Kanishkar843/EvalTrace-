import json, os, subprocess, sys


def test_release_cli_exit_codes(tmp_path):
    env = {**os.environ, "DATABASE_URL": "sqlite:///" + str(tmp_path / "cli.db")}
    ids = []
    for target, code in [("fixture-baseline", 0), ("fixture-regressed", 1)]:
        result = subprocess.run(
            [sys.executable, "-m", "app.cli", "--target", target],
            env=env,
            capture_output=True,
            text=True,
        )
        assert result.returncode == code, result.stderr
        ids.append(json.loads(result.stdout)["run_id"])
    result = subprocess.run(
        [sys.executable, "-m", "app.cli", "--baseline", ids[0], "--candidate", ids[1]],
        env=env,
        capture_output=True,
        text=True,
    )
    assert (
        result.returncode == 1
        and not json.loads(result.stdout)["release_gate"]["passed"]
    )
