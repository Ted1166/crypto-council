from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.ryo.result import ToolResult, utcnow

Direction = Literal["long", "short", "stand_aside"]
Stance = Literal["bull", "bear"]
Round = Literal["opening", "rebuttal", "crossexam"]
CaseStatus = Literal["running", "complete", "failed", "interrupted"]
ExamStatus = Literal["running", "complete", "failed"]


class Figure(BaseModel):
    label: str
    value: float
    evidence: str


class Claim(BaseModel):
    text: str
    evidence: list[str] = Field(default_factory=list)
    figures: list[Figure] = Field(default_factory=list)


class RejectedClaim(BaseModel):
    text: str
    reason: str


class Argument(BaseModel):
    stance: Stance
    round: Round
    headline: str
    claims: list[Claim] = Field(default_factory=list)
    concessions: list[str] = Field(default_factory=list)
    conviction: int = 0
    rejected: list[RejectedClaim] = Field(default_factory=list)


class Plan(BaseModel):
    direction: Direction
    entry: float
    stop: float
    target: float
    atr: float
    risk_reward: float
    evidence: list[str]
    basis: str


class Verdict(BaseModel):
    direction: Direction
    conviction: int
    radio_call: str
    rationale: list[Claim] = Field(default_factory=list)
    decisive_evidence: list[str] = Field(default_factory=list)
    unresolved: list[str] = Field(default_factory=list)
    rejected: list[RejectedClaim] = Field(default_factory=list)
    plan: Plan | None = None
    plan_note: str | None = None


class PlannedCall(BaseModel):
    tool: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    reason: str = ""


class VerdictDiff(BaseModel):
    direction_before: Direction
    direction_after: Direction
    conviction_before: int
    conviction_after: int
    flipped: bool
    conviction_delta: int
    claims_added: list[str] = Field(default_factory=list)
    claims_dropped: list[str] = Field(default_factory=list)
    new_evidence: list[str] = Field(default_factory=list)
    unavailable: list[str] = Field(default_factory=list)
    summary: str


class CrossExam(BaseModel):
    id: str
    challenge: str
    status: ExamStatus = "running"
    reading: str | None = None
    plan: list[PlannedCall] = Field(default_factory=list)
    dropped_calls: list[str] = Field(default_factory=list)
    new_evidence: list[str] = Field(default_factory=list)
    arguments: list[Argument] = Field(default_factory=list)
    verdict_before: Verdict | None = None
    verdict_after: Verdict | None = None
    diff: VerdictDiff | None = None
    error: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
    completed_at: datetime | None = None


class Case(BaseModel):
    id: str
    symbol: str
    status: CaseStatus = "running"
    model: str = ""
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    evidence: list[ToolResult] = Field(default_factory=list)
    arguments: list[Argument] = Field(default_factory=list)
    verdict: Verdict | None = None
    crossexams: list[CrossExam] = Field(default_factory=list)
    error: str | None = None


class Event(BaseModel):
    seq: int
    case_id: str
    kind: str
    message: str
    created_at: datetime


class BoardItem(BaseModel):
    id: str
    symbol: str
    status: CaseStatus
    direction: Direction | None
    conviction: int | None
    change_score: int
    change_summary: str | None
    crossexam_count: int
    updated_at: datetime
