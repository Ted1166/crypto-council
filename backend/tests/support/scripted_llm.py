import json


def claim(text: str, evidence: list[str], figures: list[dict] | None = None) -> dict:
    return {"text": text, "evidence": evidence, "figures": figures or []}


GOOD_RSI = claim(
    "RSI(14) is 61.3 and price rose 3.41% in the last day.",
    ["E2"],
    [{"label": "RSI(14)", "value": 61.3, "evidence": "E2"}],
)
BAD_OPEN_INTEREST = claim(
    "Open interest reached 999M dollars.",
    ["E3"],
    [{"label": "open interest", "value": 999000000, "evidence": "E3"}],
)


class ScriptedLLM:
    name = "scripted:protocol-test"

    def __init__(self) -> None:
        self.prompts: list[str] = []

    async def aclose(self) -> None:
        return None

    async def complete(self, system: str, user: str) -> str:
        self.prompts.append(user)
        if "cross-examination planner" in system:
            return json.dumps(
                {
                    "reading": "The challenge asks whether the token is still safe.",
                    "calls": [
                        {"tool": "check_safety", "arguments": {"symbol": "SOL"}, "reason": "Re-check safety live."},
                        {"tool": "nonexistent_tool", "arguments": {}, "reason": "Should be dropped."},
                    ],
                }
            )
        if "presiding judge" in system:
            if "Previous verdict" in user:
                return json.dumps(
                    {
                        "direction": "stand_aside",
                        "conviction": 35,
                        "radio_call": "Standing aside until the fresh safety read settles.",
                        "rationale": [claim("The safety re-run reported a low risk level.", ["E5"])],
                        "decisive_evidence": ["E5"],
                        "unresolved": [],
                    }
                )
            return json.dumps(
                {
                    "direction": "long",
                    "conviction": 82,
                    "radio_call": "Momentum is intact, enter with the ATR stop.",
                    "rationale": [GOOD_RSI],
                    "decisive_evidence": ["E2", "E9"],
                    "unresolved": [],
                }
            )
        retry = "removed by the evidence check" in user
        claims = [GOOD_RSI] if retry else [GOOD_RSI, BAD_OPEN_INTEREST]
        stance = "bull" if "bull advocate" in system else "bear"
        return json.dumps(
            {
                "headline": f"The {stance} case rests on momentum and derivatives.",
                "claims": claims,
                "concessions": ["Weekend liquidity is thin."],
                "conviction": 70,
            }
        )
