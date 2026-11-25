import json
from pathlib import Path
import httpx, pytest
from app.adapters import invoke
from app.metrics import Case


def test_provider_structured_trace_observed_usage(monkeypatch):
    case = Case.model_validate(json.loads(Path("data/suite.json").read_text())[0])
    monkeypatch.setenv("LLM_API_KEY", "mock-only-key")

    def handler(request):
        data = json.loads(request.content)
        assert data["response_format"]["type"] == "json_schema"
        assert json.loads(data["messages"][1]["content"])["output_schema"] == case.output_schema
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": case.fixture.model_dump_json()}}],
                "usage": {"total_tokens": 123},
            },
        )

    trace, tokens = invoke(case, "provider", httpx.MockTransport(handler))
    assert trace == case.fixture and tokens == 123


def test_local_target_boundary_and_missing_credentials(monkeypatch):
    case = Case.model_validate(json.loads(Path("data/suite.json").read_text())[0])
    monkeypatch.setenv("LOCAL_TARGET_URL", "https://example.org/evaluate")
    with pytest.raises(ValueError):
        invoke(case, "local-http")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    with pytest.raises(ValueError, match="credentials"):
        invoke(case, "provider")
