from app.agents.claims import validate_claims
from app.agents.debater import render_argument
from app.agents.drafts import VerdictDraft
from app.agents.llm import LLM
from app.agents.plan import build_plan
from app.agents.prompts import load_prompt
from app.agents.structured import ask
from app.receipts.schema import Argument, Verdict
from app.ryo.ledger import Ledger

SAFETY_CAP = 60
NO_CLAIMS_CAP = 20


def render_verdict(verdict: Verdict) -> str:
    lines = [f"{verdict.direction}, conviction {verdict.conviction}: {verdict.radio_call}"]
    for claim in verdict.rationale:
        lines.append(f"- {claim.text} [{', '.join(claim.evidence)}]")
    return "\n".join(lines)


async def judge(
    llm: LLM,
    symbol: str,
    ledger: Ledger,
    bull: Argument,
    bear: Argument,
    challenge: str | None = None,
    previous: Verdict | None = None,
    new_ids: set[str] | None = None,
) -> Verdict:
    parts = [
        f"Token: {symbol}",
        "Evidence ledger:",
        ledger.render(new_ids),
        "Bull advocate:\n" + render_argument(bull),
        f"Bull claims removed by the evidence check: {len(bull.rejected)}",
        "Bear advocate:\n" + render_argument(bear),
        f"Bear claims removed by the evidence check: {len(bear.rejected)}",
    ]
    unavailable = ledger.unavailable_tools()
    if unavailable:
        parts.append("Tools without usable data: " + ", ".join(unavailable))
    if previous is not None:
        parts.append("Previous verdict:\n" + render_verdict(previous))
    if challenge:
        parts.append(f'Challenge that prompted this re-judgement: "{challenge}"')
    parts.append("Reply with the JSON object now.")
    user = "\n\n".join(parts)
    system = load_prompt("judge")

    draft = await ask(llm, system, user, VerdictDraft)
    valid, rejected = validate_claims(draft.rationale, ledger)
    if rejected:
        feedback = "\n".join(f"- \"{item.text}\" was removed because {item.reason}" for item in rejected)
        retry = await ask(
            llm,
            system,
            f"{user}\n\nSome of your rationale claims were removed by the evidence check:\n{feedback}\n"
            "Reply again with claims that cite real evidence and only figures present in it.",
            VerdictDraft,
        )
        retry_valid, retry_rejected = validate_claims(retry.rationale, ledger)
        if len(retry_valid) >= len(valid):
            draft, valid, rejected = retry, retry_valid, rejected + retry_rejected

    direction = draft.direction
    conviction = draft.conviction
    unresolved = list(draft.unresolved)
    if not bull.claims and not bear.claims:
        direction = "stand_aside"
        conviction = min(conviction, NO_CLAIMS_CAP)
        unresolved.append("Neither advocate produced a claim that survived the evidence check.")
    if not ledger.has_ok("check_safety"):
        conviction = min(conviction, SAFETY_CAP)
        unresolved.append(f"The safety check was unavailable, so conviction is capped at {SAFETY_CAP}.")
    decisive = [item for item in draft.decisive_evidence if (found := ledger.get(item)) and found.status == "ok"]
    plan, plan_note = build_plan(direction, ledger)
    return Verdict(
        direction=direction,
        conviction=conviction,
        radio_call=draft.radio_call.strip()[:160],
        rationale=valid,
        decisive_evidence=decisive,
        unresolved=list(dict.fromkeys(unresolved)),
        rejected=rejected,
        plan=plan,
        plan_note=plan_note,
    )
