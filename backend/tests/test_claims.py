from app.agents.claims import checkable_numbers, collect_numbers, validate_claim
from app.receipts.schema import Claim, Figure
from app.ryo.ledger import Ledger
from app.ryo.result import ToolResult


def ledger() -> Ledger:
    store = Ledger()
    store.add(
        ToolResult(
            id="E1",
            tool="analyze_token",
            status="ok",
            data={"price": 67215.4, "rsi_14": 61.3, "change_24h": 0.0341, "volume": "1,250,000,000"},
        )
    )
    store.add(ToolResult(id="E2", tool="check_safety", status="unavailable", error="timeout"))
    return store


def test_collects_nested_and_string_numbers():
    assert sorted(collect_numbers({"a": [1, {"b": "2.5"}], "c": "x"})) == [1.0, 2.5]


def test_small_integers_and_years_are_not_checkable():
    assert checkable_numbers("RSI(14) over 7 days in 2026") == []


def test_marked_numbers_are_checkable():
    values = [item[0] for item in checkable_numbers("Up 3.4% to $67.2k with 1,250,000 in volume")]
    assert 3.4 in values
    assert any(abs(value - 67200) < 1 for value in values)
    assert 1250000 in values


def test_valid_claim_passes():
    claim = Claim(
        text="RSI(14) is 61.3 and price is near 67.2k.",
        evidence=["E1"],
        figures=[Figure(label="RSI", value=61.3, evidence="E1")],
    )
    assert validate_claim(claim, ledger()) is None


def test_percent_matches_fraction_in_evidence():
    claim = Claim(text="Price gained 3.4% in a day.", evidence=["E1"])
    assert validate_claim(claim, ledger()) is None


def test_invented_number_is_rejected():
    claim = Claim(text="RSI(14) is 71.8.", evidence=["E1"])
    assert "71.8" in (validate_claim(claim, ledger()) or "")


def test_invented_figure_is_rejected():
    claim = Claim(text="Momentum is strong.", evidence=["E1"], figures=[Figure(label="RSI", value=80.1, evidence="E1")])
    assert validate_claim(claim, ledger()) is not None


def test_missing_citation_is_rejected():
    assert validate_claim(Claim(text="Momentum is strong."), ledger()) == "it cited no evidence"


def test_unknown_evidence_is_rejected():
    assert "does not exist" in (validate_claim(Claim(text="Looks fine.", evidence=["E9"]), ledger()) or "")


def test_unavailable_evidence_is_rejected():
    assert "unavailable" in (validate_claim(Claim(text="Safe.", evidence=["E2"]), ledger()) or "")
