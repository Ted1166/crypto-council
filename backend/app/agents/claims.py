import re
from typing import Any

from app.receipts.schema import Claim, RejectedClaim
from app.ryo.ledger import Ledger

NUMBER = re.compile(r"(?<![\w.])(\$?)(-?\d[\d,]*(?:\.\d+)?)\s?(%|[kKmMbB](?![A-Za-z]))?")
SCALES = {"k": 1e3, "m": 1e6, "b": 1e9}


def collect_numbers(data: Any) -> list[float]:
    found: list[float] = []
    stack = [data]
    while stack:
        node = stack.pop()
        if isinstance(node, bool):
            continue
        if isinstance(node, (int, float)):
            found.append(float(node))
        elif isinstance(node, str):
            cleaned = node.strip().replace(",", "").replace("$", "").rstrip("%")
            try:
                found.append(float(cleaned))
            except ValueError:
                continue
        elif isinstance(node, dict):
            stack.extend(node.values())
        elif isinstance(node, list):
            stack.extend(node)
    return found


def _decimals(raw: str) -> int:
    return len(raw.split(".")[1]) if "." in raw else 0


def checkable_numbers(text: str) -> list[tuple[float, int, float]]:
    found: list[tuple[float, int, float]] = []
    for match in NUMBER.finditer(text):
        dollar, raw, suffix = match.groups()
        cleaned = raw.replace(",", "")
        value = abs(float(cleaned))
        decimals = _decimals(cleaned)
        scale = SCALES.get((suffix or "").lower(), 1.0)
        marked = bool(dollar) or suffix == "%" or scale != 1.0 or decimals > 0
        large = value >= 1000 and not 1900 <= value <= 2100
        if not marked and not large:
            continue
        found.append((value * scale, decimals, scale))
    return found


def _matches(value: float, decimals: int, scale: float, pool: list[float]) -> bool:
    tolerance = 0.5 * 10 ** (-decimals) * scale + 1e-9
    for item in pool:
        magnitude = abs(item)
        if abs(value - magnitude) <= tolerance or abs(value - magnitude * 100) <= tolerance:
            return True
    return False


def _figure_decimals(value: float) -> int:
    text = repr(float(value))
    if "e" in text or "." not in text:
        return 0
    return len(text.split(".")[1].rstrip("0"))


def validate_claim(claim: Claim, ledger: Ledger) -> str | None:
    if not claim.text.strip():
        return "the claim was empty"
    cited = list(dict.fromkeys(claim.evidence + [figure.evidence for figure in claim.figures]))
    if not cited:
        return "it cited no evidence"
    pool: list[float] = []
    for evidence_id in cited:
        result = ledger.get(evidence_id)
        if result is None:
            return f"it cited {evidence_id}, which does not exist"
        if result.status != "ok":
            return f"it cited {evidence_id}, which was unavailable"
        pool.extend(collect_numbers(result.data))
    for figure in claim.figures:
        if not _matches(abs(figure.value), _figure_decimals(figure.value), 1.0, pool):
            return f"the figure {figure.value} for '{figure.label}' does not appear in {figure.evidence}"
    for value, decimals, scale in checkable_numbers(claim.text):
        if not _matches(value, decimals, scale, pool):
            shown = f"{value:g}"
            return f"the number {shown} in the text does not appear in the cited evidence"
    return None


def validate_claims(claims: list[Claim], ledger: Ledger) -> tuple[list[Claim], list[RejectedClaim]]:
    valid: list[Claim] = []
    rejected: list[RejectedClaim] = []
    for claim in claims:
        reason = validate_claim(claim, ledger)
        if reason is None:
            valid.append(claim)
        else:
            rejected.append(RejectedClaim(text=claim.text, reason=reason))
    return valid, rejected
