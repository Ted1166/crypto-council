from app.agents.plan import build_plan, find_number
from app.ryo.ledger import Ledger
from app.ryo.result import ToolResult


def ledger_with(data) -> Ledger:
    store = Ledger()
    store.add(ToolResult(id="E1", tool="analyze_token", status="ok", data=data))
    return store


def test_find_number_searches_nested_data():
    assert find_number({"a": {"b": [{"ATR_14": 3.5}]}}, ("atr_14",)) == 3.5


def test_long_plan_levels():
    plan, note = build_plan("long", ledger_with({"price": 100, "atr_14": 4}))
    assert note is None and plan is not None
    assert plan.entry == 100
    assert plan.stop == 94
    assert plan.target == 112
    assert plan.risk_reward == 2.0


def test_short_plan_levels():
    plan, _ = build_plan("short", ledger_with({"price": 100, "atr": 4}))
    assert plan is not None and plan.stop == 106 and plan.target == 88


def test_missing_atr_gives_no_plan():
    plan, note = build_plan("long", ledger_with({"price": 100}))
    assert plan is None and "ATR" in (note or "")


def test_stand_aside_has_no_plan_and_no_note():
    assert build_plan("stand_aside", ledger_with({"price": 100, "atr": 4})) == (None, None)
