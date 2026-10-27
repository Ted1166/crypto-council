from app.config import Settings
from app.ryo.client import RyoClient, RyoUnavailable
from app.ryo.ledger import Ledger
from app.ryo.tools import EXPECTED_TOOLS, RyoTools
import pytest


def settings_for(url: str, **extra) -> Settings:
    values = {"ryo_timeout_seconds": 5, "ryo_max_retries": 0, "ryo_cache_ttl_seconds": 0, **extra}
    return Settings(_env_file=None, ryo_mcp_url=url, **values)


async def test_lists_tools_over_streamable_http(mcp_url):
    client = RyoClient(settings_for(mcp_url))
    tools = await client.tools()
    assert {"analyze_token", "deep_analysis", "check_safety"} <= set(tools)
    assert tools["analyze_token"]["schema"]["properties"]["symbol"]["type"] == "string"


async def test_typed_wrappers_return_data_with_sequential_ids(mcp_url):
    settings = settings_for(mcp_url)
    tools = RyoTools(RyoClient(settings), settings)
    ledger = Ledger()
    overview = await tools.market_overview(ledger)
    analysis = await tools.analyze_token(ledger, "SOL")
    comparison = await tools.compare_tokens(ledger, ["SOL", "ETH"])
    assert [overview.id, analysis.id, comparison.id] == ["E1", "E2", "E3"]
    assert analysis.status == "ok" and analysis.data["rsi_14"] == 61.3
    assert comparison.data["compared"] == ["SOL", "ETH"]
    assert analysis.latency_ms >= 0


async def test_tool_error_is_reported_as_error(mcp_url):
    settings = settings_for(mcp_url)
    result = await RyoTools(RyoClient(settings), settings).scan_market(Ledger(), theme="ai", limit=3)
    assert result.status == "error" and "scanner exploded" in (result.error or "")


async def test_rate_limit_text_is_reported_as_unavailable(mcp_url):
    settings = settings_for(mcp_url)
    result = await RyoTools(RyoClient(settings), settings).call(Ledger(), "supported_tokens")
    assert result.status == "unavailable"


async def test_missing_tool_is_unavailable_not_fabricated(bare_mcp_url):
    settings = settings_for(bare_mcp_url)
    result = await RyoTools(RyoClient(settings), settings).check_safety(Ledger(), "SOL")
    assert result.status == "unavailable" and result.data is None
    assert "does not offer" in (result.error or "")


async def test_unreachable_server_is_unavailable():
    settings = settings_for("http://127.0.0.1:9/mcp", ryo_timeout_seconds=2)
    result = await RyoTools(RyoClient(settings), settings).analyze_token(Ledger(), "SOL")
    assert result.status == "unavailable" and result.data is None and result.error


async def test_unset_url_is_reported():
    client = RyoClient(settings_for(""))
    with pytest.raises(RyoUnavailable):
        await client.tools()


async def test_cache_returns_fresh_ids_but_marks_cached(mcp_url):
    settings = Settings(_env_file=None, ryo_mcp_url=mcp_url, ryo_timeout_seconds=5, ryo_max_retries=0, ryo_cache_ttl_seconds=60)
    tools = RyoTools(RyoClient(settings), settings)
    ledger = Ledger()
    first = await tools.analyze_token(ledger, "SOL")
    second = await tools.analyze_token(ledger, "SOL")
    forced = await tools.analyze_token(ledger, "SOL", fresh=True)
    assert (first.cached, second.cached, forced.cached) == (False, True, False)
    assert len({first.id, second.id, forced.id}) == 3


def test_expected_tool_list_is_stable():
    assert "check_safety" in EXPECTED_TOOLS and len(EXPECTED_TOOLS) == 8
