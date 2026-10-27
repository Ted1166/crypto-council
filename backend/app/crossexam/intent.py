import re
from typing import Any

from app.agents.drafts import CrossPlanDraft
from app.agents.llm import LLM
from app.agents.prompts import load_prompt
from app.agents.structured import ask
from app.receipts.schema import Case, PlannedCall

SYMBOL = re.compile(r"^[A-Za-z0-9]{1,15}$")
SYMBOL_TOOLS = {"analyze_token", "deep_analysis", "check_safety"}
MAX_CALLS = 3


def _clean_symbol(value: Any) -> str | None:
    if isinstance(value, str) and SYMBOL.match(value.strip()):
        return value.strip().upper()
    return None


def _clean_arguments(tool: str, raw: dict[str, Any], default_symbol: str) -> tuple[dict[str, Any], str | None]:
    arguments: dict[str, Any] = {}
    if tool in SYMBOL_TOOLS:
        symbol = _clean_symbol(raw.get("symbol")) or default_symbol
        arguments["symbol"] = symbol
    elif tool == "compare_tokens":
        symbols = [s for s in (_clean_symbol(item) for item in raw.get("symbols", []) or []) if s]
        if default_symbol not in symbols:
            symbols.insert(0, default_symbol)
        symbols = list(dict.fromkeys(symbols))[:4]
        if len(symbols) < 2:
            return {}, "compare_tokens needs at least two token symbols"
        arguments["symbols"] = symbols
    elif tool == "scan_market":
        theme = raw.get("theme")
        if isinstance(theme, str) and theme.strip():
            arguments["theme"] = theme.strip()[:60]
        limit = raw.get("limit")
        if isinstance(limit, int) and 1 <= limit <= 25:
            arguments["limit"] = limit
    return arguments, None


async def plan_crossexam(
    llm: LLM,
    challenge: str,
    case: Case,
    offered: dict[str, dict[str, Any]],
) -> tuple[list[PlannedCall], str, list[str]]:
    catalogue = "\n".join(
        f"- {name}: {spec.get('description', '').strip()[:240]}" for name, spec in sorted(offered.items())
    )
    verdict = case.verdict
    user = "\n\n".join(
        [
            f"Token under hearing: {case.symbol}",
            f"Current verdict: {verdict.direction}, conviction {verdict.conviction}" if verdict else "No verdict yet.",
            f"Available tools:\n{catalogue or 'none'}",
            f'Challenge: "{challenge}"',
            "Reply with the JSON object now.",
        ]
    )
    draft = await ask(llm, load_prompt("intent"), user, CrossPlanDraft)
    calls: list[PlannedCall] = []
    dropped: list[str] = []
    for item in draft.calls:
        if len(calls) >= MAX_CALLS:
            dropped.append(f"{item.tool}: more than {MAX_CALLS} calls were requested")
            continue
        if item.tool not in offered:
            dropped.append(f"{item.tool}: the RYO server does not offer this tool")
            continue
        arguments, problem = _clean_arguments(item.tool, dict(item.arguments), case.symbol)
        if problem:
            dropped.append(f"{item.tool}: {problem}")
            continue
        calls.append(PlannedCall(tool=item.tool, arguments=arguments, reason=item.reason.strip()[:200]))
    return calls, draft.reading.strip()[:300], dropped
