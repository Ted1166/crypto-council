import asyncio
import json
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, AsyncIterator, Literal

import httpx
from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamable_http_client

from app.config import Settings

Status = Literal["ok", "unavailable", "error"]

RATE_LIMIT_MARKERS = ("rate limit", "rate-limit", "rate_limit", "429", "too many requests", "quota")


class RyoUnavailable(Exception):
    pass


@dataclass
class Outcome:
    status: Status
    data: Any = None
    error: str | None = None
    latency_ms: int = 0


def describe(exc: BaseException) -> str:
    while isinstance(exc, BaseExceptionGroup) and exc.exceptions:
        exc = exc.exceptions[0]
    text = str(exc)
    label = f"{type(exc).__name__}: {text}" if text else type(exc).__name__
    return label[:300]


def _parse_text(parts: list[str]) -> Any:
    parsed: list[Any] = []
    for part in parts:
        try:
            parsed.append(json.loads(part))
        except (json.JSONDecodeError, TypeError):
            parsed.append({"text": part})
    if not parsed:
        return None
    return parsed[0] if len(parsed) == 1 else parsed


class RyoClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._tools: dict[str, dict[str, Any]] | None = None
        self._tools_lock = asyncio.Lock()
        self._gate = asyncio.Semaphore(settings.ryo_max_concurrency)

    def _headers(self) -> dict[str, str]:
        settings = self._settings
        if not settings.ryo_api_token:
            return {}
        value = f"{settings.ryo_auth_scheme} {settings.ryo_api_token}".strip()
        return {settings.ryo_auth_header: value}

    @asynccontextmanager
    async def _session(self) -> AsyncIterator[ClientSession]:
        settings = self._settings
        if settings.ryo_transport == "sse":
            async with sse_client(
                settings.ryo_mcp_url,
                headers=self._headers(),
                timeout=settings.ryo_timeout_seconds,
            ) as streams:
                async with ClientSession(streams[0], streams[1]) as session:
                    await session.initialize()
                    yield session
            return
        http_client = httpx.AsyncClient(
            headers=self._headers(),
            timeout=httpx.Timeout(settings.ryo_timeout_seconds, read=300.0),
            follow_redirects=True,
        )
        async with http_client:
            async with streamable_http_client(settings.ryo_mcp_url, http_client=http_client) as streams:
                async with ClientSession(streams[0], streams[1]) as session:
                    await session.initialize()
                    yield session

    async def tools(self, refresh: bool = False) -> dict[str, dict[str, Any]]:
        async with self._tools_lock:
            if self._tools is not None and not refresh:
                return self._tools
            if not self._settings.ryo_configured:
                raise RyoUnavailable("RYO_MCP_URL is not set")

            async def fetch() -> dict[str, dict[str, Any]]:
                async with self._session() as session:
                    listed = await session.list_tools()
                    return {
                        tool.name: {
                            "description": tool.description or "",
                            "schema": tool.inputSchema or {},
                        }
                        for tool in listed.tools
                    }

            try:
                self._tools = await asyncio.wait_for(fetch(), self._settings.ryo_timeout_seconds)
            except Exception as exc:
                raise RyoUnavailable(describe(exc)) from exc
            return self._tools

    async def _invoke(self, tool: str, arguments: dict[str, Any]) -> Any:
        async with self._session() as session:
            return await session.call_tool(tool, arguments)

    @staticmethod
    def _interpret(result: Any) -> Outcome:
        parts = [item.text for item in result.content if getattr(item, "type", None) == "text"]
        if result.isError:
            message = " ".join(parts).strip() or "the tool reported an error"
            lowered = message.lower()
            status: Status = "unavailable" if any(m in lowered for m in RATE_LIMIT_MARKERS) else "error"
            return Outcome(status, error=message[:500])
        structured = getattr(result, "structuredContent", None)
        data = structured if structured is not None else _parse_text(parts)
        return Outcome("ok", data=data)

    async def call(self, tool: str, arguments: dict[str, Any]) -> Outcome:
        started = time.monotonic()
        attempts = self._settings.ryo_max_retries + 1
        last_error = "no response"
        outcome: Outcome | None = None
        for attempt in range(attempts):
            try:
                async with self._gate:
                    result = await asyncio.wait_for(
                        self._invoke(tool, arguments), self._settings.ryo_timeout_seconds
                    )
            except Exception as exc:
                last_error = describe(exc)
                outcome = None
                if attempt < attempts - 1:
                    await asyncio.sleep(0.6 * 2**attempt)
                continue
            outcome = self._interpret(result)
            if outcome.status == "unavailable" and attempt < attempts - 1:
                last_error = outcome.error or last_error
                await asyncio.sleep(0.6 * 2**attempt)
                continue
            break
        elapsed = int((time.monotonic() - started) * 1000)
        if outcome is None:
            return Outcome("unavailable", error=last_error, latency_ms=elapsed)
        outcome.latency_ms = elapsed
        return outcome
