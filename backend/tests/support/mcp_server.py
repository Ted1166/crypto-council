import socket
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager

import uvicorn
from mcp.server.fastmcp import FastMCP


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def build_server(port: int, include_safety: bool = True) -> FastMCP:
    server = FastMCP("protocol-test-server", host="127.0.0.1", port=port)

    @server.tool()
    def market_overview() -> dict:
        return {"regime": "risk_on", "fear_greed": 61, "btc_dominance": 52.4}

    @server.tool()
    def analyze_token(symbol: str) -> dict:
        return {
            "symbol": symbol,
            "price": 100.0,
            "atr_14": 4.2,
            "rsi_14": 61.3,
            "change_24h_pct": 3.41,
            "volume_24h": 1250000000,
        }

    @server.tool()
    def deep_analysis(symbol: str) -> dict:
        return {
            "symbol": symbol,
            "derivatives": {"funding_rate": 0.0123, "open_interest": 420000000},
            "risks": ["thin weekend liquidity"],
        }

    @server.tool()
    def compare_tokens(symbols: list[str]) -> dict:
        return {"compared": symbols, "leader": symbols[0]}

    @server.tool()
    def scan_market(theme: str = "", limit: int = 5) -> dict:
        raise RuntimeError("scanner exploded")

    @server.tool()
    def supported_tokens() -> dict:
        raise RuntimeError("429 too many requests")

    if include_safety:

        @server.tool()
        def check_safety(symbol: str) -> dict:
            return {"symbol": symbol, "risk_level": "low", "flags": []}

    return server


@contextmanager
def run_server(include_safety: bool = True) -> Iterator[str]:
    port = free_port()
    app = build_server(port, include_safety).streamable_http_app()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.time() + 10
    while not server.started and time.time() < deadline:
        time.sleep(0.05)
    try:
        yield f"http://127.0.0.1:{port}/mcp"
    finally:
        server.should_exit = True
        thread.join(5)
