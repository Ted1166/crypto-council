from typing import Any

from app.receipts.schema import Direction, Plan
from app.ryo.ledger import Ledger

PRICE_KEYS = ("price", "price_usd", "current_price", "last_price", "last")
ATR_KEYS = ("atr", "atr_14", "atr14", "atr_usd")
STOP_MULTIPLE = 1.5
TARGET_MULTIPLE = 3.0


def find_number(data: Any, names: tuple[str, ...]) -> float | None:
    queue = [data]
    while queue:
        node = queue.pop(0)
        if isinstance(node, dict):
            for key, value in node.items():
                if str(key).lower() in names and isinstance(value, (int, float)) and not isinstance(value, bool):
                    return float(value)
            queue.extend(value for value in node.values() if isinstance(value, (dict, list)))
        elif isinstance(node, list):
            queue.extend(value for value in node if isinstance(value, (dict, list)))
    return None


def build_plan(direction: Direction, ledger: Ledger) -> tuple[Plan | None, str | None]:
    if direction == "stand_aside":
        return None, None
    sources = [
        result
        for result in reversed(ledger.all())
        if result.status == "ok" and result.tool in ("analyze_token", "deep_analysis")
    ]
    price: float | None = None
    atr: float | None = None
    used: list[str] = []
    for result in sources:
        if price is None:
            price = find_number(result.data, PRICE_KEYS)
            if price is not None:
                used.append(result.id)
        if atr is None:
            atr = find_number(result.data, ATR_KEYS)
            if atr is not None and result.id not in used:
                used.append(result.id)
    if price is None or atr is None:
        return None, "Price or ATR(14) was not present in the evidence, so no practice plan was produced."
    if price <= 0 or atr <= 0:
        return None, "Price or ATR(14) in the evidence was not positive, so no practice plan was produced."
    sign = 1 if direction == "long" else -1
    stop = price - sign * STOP_MULTIPLE * atr
    target = price + sign * TARGET_MULTIPLE * atr
    if stop <= 0 or target <= 0:
        return None, "The ATR-based levels fell below zero, so no practice plan was produced."
    plan = Plan(
        direction=direction,
        entry=price,
        stop=stop,
        target=target,
        atr=atr,
        risk_reward=TARGET_MULTIPLE / STOP_MULTIPLE,
        evidence=used,
        basis=f"Entry at the reported price, stop {STOP_MULTIPLE} ATR away, target {TARGET_MULTIPLE} ATR away.",
    )
    return plan, None
