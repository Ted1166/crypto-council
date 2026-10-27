from app.agents.claims import validate_claims
from app.agents.drafts import ArgumentDraft
from app.agents.llm import LLM
from app.agents.prompts import load_prompt
from app.agents.structured import ask
from app.receipts.schema import Argument, Round, Stance
from app.ryo.ledger import Ledger


def render_argument(argument: Argument) -> str:
    lines = [f"{argument.stance} ({argument.round}), conviction {argument.conviction}: {argument.headline}"]
    for claim in argument.claims:
        lines.append(f"- {claim.text} [{', '.join(claim.evidence)}]")
    for concession in argument.concessions:
        lines.append(f"- concedes: {concession}")
    return "\n".join(lines)


def build_prompt(
    symbol: str,
    round_name: Round,
    ledger: Ledger,
    opponent: Argument | None,
    challenge: str | None,
    new_ids: set[str] | None,
) -> str:
    parts = [f"Token: {symbol}", f"Round: {round_name}", "Evidence ledger:", ledger.render(new_ids)]
    unavailable = ledger.unavailable_tools()
    if unavailable:
        parts.append("Tools without usable data: " + ", ".join(unavailable))
    if opponent is not None:
        parts.append("Opponent's latest argument:\n" + render_argument(opponent))
    if challenge:
        parts.append(f'Challenge from the cross-examiner: "{challenge}"')
    parts.append("Reply with the JSON object now.")
    return "\n\n".join(parts)


async def argue(
    llm: LLM,
    stance: Stance,
    round_name: Round,
    symbol: str,
    ledger: Ledger,
    opponent: Argument | None = None,
    challenge: str | None = None,
    new_ids: set[str] | None = None,
) -> Argument:
    system = load_prompt(stance)
    user = build_prompt(symbol, round_name, ledger, opponent, challenge, new_ids)
    draft = await ask(llm, system, user, ArgumentDraft)
    valid, rejected = validate_claims(draft.claims, ledger)
    if rejected:
        feedback = "\n".join(f"- \"{item.text}\" was removed because {item.reason}" for item in rejected)
        retry = await ask(
            llm,
            system,
            f"{user}\n\nSome of your claims were removed by the evidence check:\n{feedback}\n"
            "Reply again with claims that cite real evidence and only figures present in it.",
            ArgumentDraft,
        )
        retry_valid, retry_rejected = validate_claims(retry.claims, ledger)
        if len(retry_valid) >= len(valid):
            draft, valid, rejected = retry, retry_valid, rejected + retry_rejected
    conviction = draft.conviction if valid else min(draft.conviction, 20)
    concessions = list(draft.concessions)
    if not valid:
        concessions.append("No claim survived the evidence check.")
    return Argument(
        stance=stance,
        round=round_name,
        headline=draft.headline,
        claims=valid,
        concessions=concessions,
        conviction=conviction,
        rejected=rejected,
    )
