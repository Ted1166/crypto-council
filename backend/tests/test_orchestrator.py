import pytest

from app.config import Settings
from app.crossexam.diff import change_score
from app.orchestrator import Orchestrator
from app.receipts.bus import EventBus
from app.receipts.schema import Case, CrossExam
from app.receipts.store import Store
from app.ryo.client import RyoClient
from app.ryo.tools import RyoTools
from tests.support.scripted_llm import ScriptedLLM


async def build(tmp_path, url: str):
    settings = Settings(
        _env_file=None,
        ryo_mcp_url=url,
        ryo_timeout_seconds=5,
        ryo_max_retries=0,
        ryo_cache_ttl_seconds=0,
        database_path=str(tmp_path / "council.db"),
    )
    store = Store(settings.database_path)
    await store.init()
    bus = EventBus()
    llm = ScriptedLLM()
    orchestrator = Orchestrator(settings, RyoTools(RyoClient(settings), settings), llm, store, bus)
    case = Case(id="case000001", symbol="SOL", model=llm.name)
    await store.save_case(case)
    return orchestrator, store, case


async def test_full_hearing_records_evidence_rejections_and_plan(tmp_path, mcp_url):
    orchestrator, store, case = await build(tmp_path, mcp_url)
    await orchestrator.run_case(case.id)
    saved = await store.get_case(case.id)
    assert saved is not None and saved.status == "complete"
    assert [item.tool for item in saved.evidence] == [
        "market_overview",
        "analyze_token",
        "deep_analysis",
        "check_safety",
    ]
    assert all(item.status == "ok" for item in saved.evidence)
    opening = [a for a in saved.arguments if a.round == "opening"]
    assert len(opening) == 2
    for argument in opening:
        assert len(argument.claims) == 1
        assert len(argument.rejected) == 1 and "999" in argument.rejected[0].reason
    verdict = saved.verdict
    assert verdict is not None and verdict.direction == "long" and verdict.conviction == 82
    assert verdict.decisive_evidence == ["E2"]
    assert verdict.plan is not None
    assert verdict.plan.entry == 100.0 and verdict.plan.stop == pytest.approx(93.7)
    events = await store.events_after(case.id, 0)
    assert events[-1].kind == "verdict"
    assert [e.seq for e in events] == list(range(1, len(events) + 1))


async def test_cross_examination_reruns_tools_and_flips_the_call(tmp_path, mcp_url):
    orchestrator, store, case = await build(tmp_path, mcp_url)
    await orchestrator.run_case(case.id)
    current = await store.get_case(case.id)
    assert current is not None
    exam = CrossExam(id="exam0001", challenge="Is this token still safe?")
    current.crossexams.append(exam)
    await store.save_case(current)
    await orchestrator.run_crossexam(case.id, exam.id)
    saved = await store.get_case(case.id)
    assert saved is not None
    finished = saved.crossexams[0]
    assert finished.status == "complete"
    assert [call.tool for call in finished.plan] == ["check_safety"]
    assert any("nonexistent_tool" in item for item in finished.dropped_calls)
    assert finished.new_evidence == ["E5"]
    assert saved.evidence[-1].id == "E5" and saved.evidence[-1].tool == "check_safety"
    assert finished.diff is not None and finished.diff.flipped
    assert finished.diff.conviction_before == 82 and finished.diff.conviction_after == 35
    assert change_score(finished.diff) == 100
    assert saved.verdict is not None and saved.verdict.direction == "stand_aside"
    assert saved.verdict.plan is None
    board = await store.board()
    assert board[0].change_score == 100 and "flipped" in (board[0].change_summary or "")


async def test_missing_safety_tool_caps_conviction_and_is_disclosed(tmp_path, bare_mcp_url):
    orchestrator, store, case = await build(tmp_path, bare_mcp_url)
    await orchestrator.run_case(case.id)
    saved = await store.get_case(case.id)
    assert saved is not None and saved.status == "complete"
    safety = next(item for item in saved.evidence if item.tool == "check_safety")
    assert safety.status == "unavailable" and safety.data is None
    assert saved.verdict is not None and saved.verdict.conviction == 60
    assert any("safety check was unavailable" in note for note in saved.verdict.unresolved)


async def test_hearing_fails_honestly_when_ryo_is_down(tmp_path):
    orchestrator, store, case = await build(tmp_path, "http://127.0.0.1:9/mcp")
    await orchestrator.run_case(case.id)
    saved = await store.get_case(case.id)
    assert saved is not None and saved.status == "failed"
    assert "no market data" in (saved.error or "")
    assert saved.arguments == [] and saved.verdict is None
    assert all(item.status == "unavailable" for item in saved.evidence)
