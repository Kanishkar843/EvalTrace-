"""Real React journey using only a test-owned server and temporary database."""

import json, os, secrets, socket, subprocess, sys, tempfile, time
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

root = Path(__file__).resolve().parents[1]
(root / ".cache").mkdir(exist_ok=True)
assets = root / "docs/assets"
assets.mkdir(exist_ok=True)
with (
    tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp,
    socket.socket() as sock,
):
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    token = secrets.token_urlsafe(32)
    env = {
        **os.environ,
        "ADMIN_TOKEN": token,
        "DATABASE_URL": "sqlite:///" + str(Path(tmp) / "browser.db"),
    }
    env.pop("REDIS_URL", None)
    with (root / ".cache/browser-server.log").open("w") as log:
        proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            cwd=root,
            env=env,
            stdout=log,
            stderr=log,
        )
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(
                    executable_path=os.getenv(
                        "CHROME_PATH",
                        "C:/Program Files/Google/Chrome/Application/chrome.exe",
                    ),
                    headless=True,
                )
                page = browser.new_page(viewport={"width": 1440, "height": 1000})
                errors = []
                page.on("pageerror", lambda e: errors.append(str(e)))
                base = f"http://127.0.0.1:{port}"
                for _ in range(90):
                    try:
                        if page.request.get(base + "/ready").ok:
                            break
                    except Exception:
                        pass
                    if proc.poll() is not None:
                        raise AssertionError("Test API exited")
                    time.sleep(0.5)
                page.goto(base, wait_until="networkidle")
                page.get_by_role("button", name="Connect studio").click()
                expect(page.get_by_role("alert")).to_contain_text("Invalid admin token")
                page.locator("#token").fill(token)
                page.get_by_role("button", name="Connect studio").click()
                expect(page.locator("#status")).to_contain_text("Connected")
                page.get_by_role("button", name="Register synthetic suite").click()
                expect(page.locator("#status")).to_contain_text("registered")
                page.get_by_role("button", name="Run evaluation", exact=True).click()
                expect(page.get_by_role("heading", name="GATE PASSED")).to_be_visible(
                    timeout=30000
                )
                page.get_by_label("Target adapter").select_option("fixture-regressed")
                page.get_by_role("button", name="Run evaluation", exact=True).click()
                expect(
                    page.get_by_role("heading", name="RELEASE BLOCKED")
                ).to_be_visible(timeout=30000)
                rows = page.request.get(
                    base + "/runs", headers={"Authorization": "Bearer " + token}
                ).json()
                baseline = next(
                    x["id"] for x in rows if x["target"] == "fixture-baseline"
                )
                candidate = next(
                    x["id"] for x in rows if x["target"] == "fixture-regressed"
                )
                page.get_by_label("Baseline", exact=True).select_option(baseline)
                page.get_by_label("Candidate", exact=True).select_option(candidate)
                page.get_by_role("button", name="Compare releases").click()
                expect(page.locator("#comparison")).to_contain_text("-1.0000")
                page.locator("#cases summary").first.click()
                expect(page.locator("#cases")).to_contain_text("wrong_tool")
                expect(page.locator("#cases")).to_contain_text("Needs review")
                page.get_by_text("Release gate policy", exact=True).click()
                page.get_by_role("button", name="Save gate policy").click()
                expect(page.locator("#status")).to_contain_text("policy saved")
                page.get_by_text("Import JSONL dataset", exact=True).click()
                page.get_by_label("JSONL cases").fill("not-json")
                page.get_by_role("button", name="Import dataset", exact=True).click()
                expect(page.get_by_role("alert")).to_contain_text("Invalid JSONL")
                page.get_by_label("JSONL cases").fill(
                    (root / "data/suite.jsonl").read_text()
                )
                page.get_by_role("button", name="Import dataset", exact=True).click()
                expect(page.locator("#status")).to_contain_text("Dataset imported")
                page.get_by_label("JSONL cases").fill("")
                page.get_by_text("Import JSONL dataset", exact=True).click()
                page.locator("#token").fill("")
                page.screenshot(path=str(assets / "desktop.png"), full_page=True)
                page.get_by_role("button", name="Change theme").click()
                page.screenshot(path=str(assets / "light.png"), full_page=True)
                page.set_viewport_size({"width": 390, "height": 844})
                page.screenshot(path=str(assets / "mobile.png"), full_page=True)
                assert page.evaluate(
                    "document.documentElement.scrollWidth <= innerWidth"
                )
                assert not errors, errors
                browser.close()
                (root / "docs/browser-report.json").write_text(
                    json.dumps(
                        {
                            "status": "PASSED",
                            "frontend": "React TypeScript",
                            "backend": "SQLite deterministic traces; PostgreSQL recovery tested separately",
                            "checks": [
                                "authorization rejection",
                                "baseline pass",
                                "regressed gate block",
                                "comparison",
                                "failed trace evidence",
                                "policy save",
                                "JSONL validation",
                                "JSONL import",
                                "dark/light/mobile",
                            ],
                            "page_errors": errors,
                        },
                        indent=2,
                    )
                )
                print("EvalTrace React browser journey PASSED")
        finally:
            proc.terminate()
            proc.wait(timeout=15)
