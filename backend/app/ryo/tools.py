import json
import time
from typing import Any

from app.config import Settings
from app.ryo.adapter import ArgumentMappingError, adapt
from app.ryo.client import RyoClient, RyoUnavailable
from app.ryo.ledger import Ledger
from app.ryo.result import ToolResult

EXPECTED_TOOLS = (
    "market_overview",
    "scan_market",
    "analyze_token",
    "deep_analysis",
    "compare_tokens",
    "check_safety",
    "monitor_market_sentiment_shift",
    "supported_tokens",
)

OPTIONAL_INPUTS: dict[str, frozenset[str]] = {
    "scan_market": frozenset({"theme", "limit"}),
}


class RyoTools:
    def __init__(self, client: RyoClient, settings: Settings) -> None:
        self._client = client
        self._ttl = settings.ryo_cache_ttl_seconds
        self._cache: dict[str, tuple[float, ToolResult]] = {}

    async def offered(self) -> dict[str, dict[str, Any]]:
        try:
            return await self._client.tools()
        except RyoUnavailable:
            return {}

    @staticmethod
    def _record(ledger: Ledger, result: ToolResult) -> ToolResult:
        ledger.add(result)
        return result

    async def call(
        self,
        ledger: Ledger,
        tool: str,
        canonical: dict[str, Any] | None = None,
        fresh: bool = False,
    ) -> ToolResult:
        canonical = dict(canonical or {})
        result_id = ledger.reserve()
        try:
            offered = await self._client.tools()
        except RyoUnavailable as exc:
            return self._record(
                ledger,
                ToolResult(id=result_id, tool=tool, arguments=canonical, status="unavailable", error=str(exc)),
            )
        spec = offered.get(tool)
        if spec is None:
            return self._record(
                ledger,
                ToolResult(
                    id=result_id,
                    tool=tool,
                    arguments=canonical,
                    status="unavailable",
                    error="the RYO server does not offer this tool",
                ),
            )
        try:
            arguments = adapt(spec["schema"], canonical, OPTIONAL_INPUTS.get(tool, frozenset()))
        except ArgumentMappingError as exc:
            return self._record(
                ledger,
                ToolResult(
                    id=result_id,
                    tool=tool,
                    arguments=canonical,
                    status="error",
                    error=f"arguments could not be mapped to the tool schema: {exc}",
                ),
            )
        key = f"{tool}:{json.dumps(arguments, sort_keys=True, default=str)}"
        if not fresh and key in self._cache:
            stored_at, stored = self._cache[key]
            if time.monotonic() - stored_at <= self._ttl:
                return self._record(ledger, stored.model_copy(update={"id": result_id, "cached": True}))
        outcome = await self._client.call(tool, arguments)
        result = ToolResult(
            id=result_id,
            tool=tool,
            arguments=arguments,
            status=outcome.status,
            data=outcome.data,
            error=outcome.error,
            latency_ms=outcome.latency_ms,
        )
        if outcome.status == "ok":
            self._cache[key] = (time.monotonic(), result)
        return self._record(ledger, result)

    async def market_overview(self, ledger: Ledger, fresh: bool = False) -> ToolResult:
        return await self.call(ledger, "market_overview", fresh=fresh)

    async def analyze_token(self, ledger: Ledger, symbol: str, fresh: bool = False) -> ToolResult:
        return await self.call(ledger, "analyze_token", {"symbol": symbol}, fresh=fresh)

    async def deep_analysis(self, ledger: Ledger, symbol: str, fresh: bool = False) -> ToolResult:
        return await self.call(ledger, "deep_analysis", {"symbol": symbol}, fresh=fresh)

    async def check_safety(self, ledger: Ledger, symbol: str, fresh: bool = False) -> ToolResult:
        return await self.call(ledger, "check_safety", {"symbol": symbol}, fresh=fresh)

    async def compare_tokens(self, ledger: Ledger, symbols: list[str], fresh: bool = False) -> ToolResult:
        return await self.call(ledger, "compare_tokens", {"symbols": symbols}, fresh=fresh)

    async def scan_market(
        self, ledger: Ledger, theme: str | None = None, limit: int | None = None, fresh: bool = False
    ) -> ToolResult:
        return await self.call(ledger, "scan_market", {"theme": theme, "limit": limit}, fresh=fresh)

    async def sentiment_shift(self, ledger: Ledger, fresh: bool = False) -> ToolResult:
        return await self.call(ledger, "monitor_market_sentiment_shift", fresh=fresh)
