import json
import time

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app
from app.orchestrator import Orchestrator
from tests.support.scripted_llm import ScriptedLLM


@pytest.fixture
def client(tmp_path, mcp_url, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "api.db"))
    monkeypatch.setenv("RYO_MCP_URL", mcp_url)
    monkeypatch.setenv("RYO_CACHE_TTL_SECONDS", "0")
    monkeypatch.setenv("RYO_MAX_RETRIES", "0")
    monkeypatch.setenv("LLM_MODEL", "scripted")
    monkeypatch.setenv("LLM_API_KEY", "unused")
    get_settings.cache_clear()
    with TestClient(create_app()) as test_client:
        container = test_client.app.state.container
        llm = ScriptedLLM()
        container.llm = llm
        container.orchestrator = Orchestrator(
            container.settings, container.tools, llm, container.store, container.bus
        )
        yield test_client
    get_settings.cache_clear()


def wait_for(client: TestClient, case_id: str, predicate, seconds: float = 15.0):
    deadline = time.time() + seconds
    while time.time() < deadline:
        body = client.get(f"/api/cases/{case_id}").json()
        if predicate(body):
            return body
        time.sleep(0.1)
    raise AssertionError("condition not reached in time")


def test_health_reports_tools_and_missing(client):
    body = client.get("/api/health").json()
    assert body["ryo"]["reachable"] is True
    assert "analyze_token" in body["ryo"]["tools"]
    assert "monitor_market_sentiment_shift" in body["ryo"]["missing"]
    assert body["llm"]["configured"] is True


def test_rejects_wallet_addresses_and_unknown_cases(client):
    assert client.post("/api/cases", json={"symbol": "0x1234 5678"}).status_code == 422
    assert client.get("/api/cases/missing").status_code == 404
    assert client.post("/api/cases/missing/crossexam", json={"challenge": "why not"}).status_code == 404


def test_hearing_crossexam_board_and_stream(client):
    created = client.post("/api/cases", json={"symbol": "sol"})
    assert created.status_code == 201
    case_id = created.json()["id"]
    case = wait_for(client, case_id, lambda body: body["status"] in ("complete", "failed"))
    assert case["status"] == "complete" and case["symbol"] == "SOL"

    early = client.post(f"/api/cases/{case_id}/crossexam", json={"challenge": "ok"})
    assert early.status_code == 422

    accepted = client.post(f"/api/cases/{case_id}/crossexam", json={"challenge": "Is this token still safe?"})
    assert accepted.status_code == 202
    busy = client.post(f"/api/cases/{case_id}/crossexam", json={"challenge": "And what about funding?"})
    assert busy.status_code in (202, 409)
    case = wait_for(client, case_id, lambda body: body["crossexams"] and body["crossexams"][0]["status"] != "running")
    assert case["crossexams"][0]["diff"]["flipped"] is True
    assert case["verdict"]["direction"] == "stand_aside"

    board = client.get("/api/board").json()
    assert board[0]["id"] == case_id and board[0]["change_score"] == 100

    seen: list[dict] = []
    with client.stream("GET", f"/api/cases/{case_id}/stream") as response:
        assert response.headers["content-type"].startswith("text/event-stream")
        for line in response.iter_lines():
            if line.startswith("data: "):
                seen.append(json.loads(line[6:]))
                if [item["kind"] for item in seen].count("verdict") == 2:
                    break
            if len(seen) > 200:
                break
    kinds = [item["kind"] for item in seen]
    assert kinds[0] == "created" and "evidence" in kinds and "challenge" in kinds
    assert [item["seq"] for item in seen] == sorted(item["seq"] for item in seen)
