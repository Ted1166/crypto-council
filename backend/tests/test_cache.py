from app.config import Settings
from app.receipts.store import Store
from app.ryo.client import RyoClient
from app.ryo.ledger import Ledger
from app.ryo.tools import RyoTools


def settings_for(url: str, ttl: float) -> Settings:
    return Settings(
        _env_file=None,
        ryo_mcp_url=url,
        ryo_timeout_seconds=3,
        ryo_max_retries=0,
        ryo_cache_ttl_seconds=ttl,
    )


async def test_cache_survives_a_restart_and_needs_no_network(tmp_path, mcp_url):
    store = Store(str(tmp_path / "cache.db"))
    await store.init()
    live = settings_for(mcp_url, 300)
    first = await RyoTools(RyoClient(live), live, store).analyze_token(Ledger(), "SOL")
    assert first.status == "ok" and first.cached is False

    offline = settings_for("http://127.0.0.1:9/mcp", 300)
    second = await RyoTools(RyoClient(offline), offline, store).analyze_token(Ledger(), "SOL")
    assert second.status == "ok" and second.cached is True
    assert second.data == first.data and second.fetched_at == first.fetched_at


async def test_fresh_bypasses_cache_and_zero_ttl_disables_it(tmp_path, mcp_url):
    store = Store(str(tmp_path / "cache.db"))
    await store.init()
    live = settings_for(mcp_url, 300)
    tools = RyoTools(RyoClient(live), live, store)
    await tools.analyze_token(Ledger(), "SOL")
    forced = await tools.analyze_token(Ledger(), "SOL", fresh=True)
    assert forced.cached is False

    off = settings_for(mcp_url, 0)
    disabled = RyoTools(RyoClient(off), off, store)
    await disabled.analyze_token(Ledger(), "ETH")
    again = await disabled.analyze_token(Ledger(), "ETH")
    assert again.cached is False


async def test_failures_are_never_cached(tmp_path, mcp_url):
    store = Store(str(tmp_path / "cache.db"))
    await store.init()
    live = settings_for(mcp_url, 300)
    tools = RyoTools(RyoClient(live), live, store)
    first = await tools.call(Ledger(), "exhausted_tool")
    second = await tools.call(Ledger(), "exhausted_tool")
    assert first.status == "unavailable" and second.cached is False
