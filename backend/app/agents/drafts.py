from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.receipts.schema import Claim


def _clamp(value: object) -> int:
    return max(0, min(100, int(round(float(value)))))


class ArgumentDraft(BaseModel):
    headline: str
    claims: list[Claim] = Field(default_factory=list)
    concessions: list[str] = Field(default_factory=list)
    conviction: int = 50

    @field_validator("conviction", mode="before")
    @classmethod
    def clamp_conviction(cls, value: object) -> int:
        return _clamp(value)


class VerdictDraft(BaseModel):
    direction: Literal["long", "short", "stand_aside"]
    conviction: int = 50
    radio_call: str
    rationale: list[Claim] = Field(default_factory=list)
    decisive_evidence: list[str] = Field(default_factory=list)
    unresolved: list[str] = Field(default_factory=list)

    @field_validator("conviction", mode="before")
    @classmethod
    def clamp_conviction(cls, value: object) -> int:
        return _clamp(value)

    @field_validator("direction", mode="before")
    @classmethod
    def normalise_direction(cls, value: object) -> str:
        text = str(value).strip().lower().replace("-", "_").replace(" ", "_")
        if text in ("avoid", "neutral", "none", "hold", "wait", "standaside"):
            return "stand_aside"
        return text


class CallDraft(BaseModel):
    tool: str
    arguments: dict[str, object] = Field(default_factory=dict)
    reason: str = ""


class CrossPlanDraft(BaseModel):
    reading: str = ""
    calls: list[CallDraft] = Field(default_factory=list)
