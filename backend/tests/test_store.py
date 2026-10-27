from app.receipts.schema import Case, CrossExam, Verdict
from app.receipts.store import Store


async def make_store(tmp_path) -> Store:
    store = Store(str(tmp_path / "council.db"))
    await store.init()
    return store


async def test_case_round_trip_and_board_order(tmp_path):
    store = await make_store(tmp_path)
    first = Case(id="a1", symbol="SOL", status="complete", verdict=Verdict(direction="long", conviction=70, radio_call="Go."))
    second = Case(id="b2", symbol="ETH", status="complete", verdict=Verdict(direction="short", conviction=55, radio_call="No."))
    await store.save_case(first, change_score=30, change_summary="New call: long at 70.")
    await store.save_case(second, change_score=100, change_summary="Call flipped.")
    loaded = await store.get_case("a1")
    assert loaded is not None and loaded.verdict is not None and loaded.verdict.conviction == 70
    board = await store.board()
    assert [item.id for item in board] == ["b2", "a1"]
    assert board[0].change_summary == "Call flipped."


async def test_summary_survives_a_plain_save(tmp_path):
    store = await make_store(tmp_path)
    case = Case(id="a1", symbol="SOL")
    await store.save_case(case, change_score=40, change_summary="Kept.")
    await store.save_case(case)
    assert (await store.board())[0].change_score == 40


async def test_events_are_sequenced_per_case(tmp_path):
    store = await make_store(tmp_path)
    one = await store.append_event("a1", "stage", "first")
    two = await store.append_event("a1", "stage", "second")
    other = await store.append_event("b2", "stage", "elsewhere")
    assert (one.seq, two.seq, other.seq) == (1, 2, 1)
    assert [e.message for e in await store.events_after("a1", 1)] == ["second"]


async def test_unfinished_cases_are_found(tmp_path):
    store = await make_store(tmp_path)
    await store.save_case(Case(id="run", symbol="SOL", status="running"))
    done = Case(id="done", symbol="ETH", status="complete", crossexams=[CrossExam(id="x", challenge="why")])
    await store.save_case(done)
    await store.save_case(Case(id="idle", symbol="BTC", status="complete"))
    ids = sorted(case.id for case in await store.unfinished())
    assert ids == ["done", "run"]
