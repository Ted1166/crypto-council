from app.receipts.schema import Direction, Verdict, VerdictDiff
from app.ryo.result import ToolResult

LABELS: dict[Direction, str] = {"long": "long", "short": "short", "stand_aside": "stand aside"}


def diff_verdicts(before: Verdict, after: Verdict, new_evidence: list[ToolResult]) -> VerdictDiff:
    flipped = before.direction != after.direction
    delta = after.conviction - before.conviction
    before_texts = [claim.text for claim in before.rationale]
    after_texts = [claim.text for claim in after.rationale]
    unavailable = [item.tool for item in new_evidence if item.status != "ok"]
    if flipped:
        summary = f"Call flipped from {LABELS[before.direction]} to {LABELS[after.direction]}."
    elif delta:
        summary = (
            f"Call held at {LABELS[after.direction]}; conviction moved from "
            f"{before.conviction} to {after.conviction}."
        )
    else:
        summary = f"Call held at {LABELS[after.direction]} with conviction {after.conviction}."
    if unavailable:
        summary += " Unavailable on re-run: " + ", ".join(dict.fromkeys(unavailable)) + "."
    return VerdictDiff(
        direction_before=before.direction,
        direction_after=after.direction,
        conviction_before=before.conviction,
        conviction_after=after.conviction,
        flipped=flipped,
        conviction_delta=delta,
        claims_added=[text for text in after_texts if text not in before_texts][:5],
        claims_dropped=[text for text in before_texts if text not in after_texts][:5],
        new_evidence=[item.id for item in new_evidence],
        unavailable=list(dict.fromkeys(unavailable)),
        summary=summary,
    )


def change_score(diff: VerdictDiff) -> int:
    if diff.flipped:
        return 100
    if diff.conviction_delta:
        return min(90, 20 + abs(diff.conviction_delta) * 2)
    return 10
