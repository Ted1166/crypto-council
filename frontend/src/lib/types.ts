export type Direction = "long" | "short" | "stand_aside";
export type Stance = "bull" | "bear";
export type Round = "opening" | "rebuttal" | "crossexam";
export type CaseStatus = "running" | "complete" | "failed" | "interrupted";
export type ExamStatus = "running" | "complete" | "failed";
export type ToolStatus = "ok" | "unavailable" | "error";

export interface Figure {
    label: string;
    value: number;
    evidence: string;
}

export interface Claim {
    text: string;
    evidence: string[];
    figures: Figure[];
}

export interface RejectedClaim {
    text: string;
    reason: string;
}

export interface Argument {
    stance: Stance;
    round: Round;
    headline: string;
    claims: Claim[];
    concessions: string[];
    conviction: number;
    rejected: RejectedClaim[];
}

export interface Plan {
    direction: Direction;
    entry: number;
    stop: number;
    target: number;
    atr: number;
    risk_reward: number;
    evidence: string[];
    basis: string;
}

export interface Verdict {
    direction: Direction;
    conviction: number;
    radio_call: string;
    rationale: Claim[];
    decisive_evidence: string[];
    unresolved: string[];
    rejected: RejectedClaim[];
    plan: Plan | null;
    plan_note: string | null;
}

export interface PlannedCall {
    tool: string;
    arguments: Record<string, unknown>;
    reason: string;
}

export interface VerdictDiff {
    direction_before: Direction;
    direction_after: Direction;
    conviction_before: number;
    conviction_after: number;
    flipped: boolean;
    conviction_delta: number;
    claims_added: string[];
    claims_dropped: string[];
    new_evidence: string[];
    unavailable: string[];
    summary: string;
}

export interface CrossExam {
    id: string;
    challenge: string;
    status: ExamStatus;
    reading: string | null;
    plan: PlannedCall[];
    dropped_calls: string[];
    new_evidence: string[];
    arguments: Argument[];
    verdict_before: Verdict | null;
    verdict_after: Verdict | null;
    diff: VerdictDiff | null;
    error: string | null;
    created_at: string;
    completed_at: string | null;
}

export interface ToolResult {
    id: string;
    tool: string;
    arguments: Record<string, unknown>;
    status: ToolStatus;
    data: unknown;
    error: string | null;
    fetched_at: string;
    latency_ms: number;
    cached: boolean;
}

export interface CouncilCase {
    id: string;
    symbol: string;
    status: CaseStatus;
    model: string;
    created_at: string;
    updated_at: string;
    evidence: ToolResult[];
    arguments: Argument[];
    verdict: Verdict | null;
    crossexams: CrossExam[];
    error: string | null;
}

export interface CaseEvent {
    seq: number;
    case_id: string;
    kind: string;
    message: string;
    created_at: string;
}

export interface BoardItem {
    id: string;
    symbol: string;
    status: CaseStatus;
    direction: Direction | null;
    conviction: number | null;
    change_score: number;
    change_summary: string | null;
    crossexam_count: number;
    updated_at: string;
}

export interface Health {
    status: "ready" | "degraded";
    ryo: {
        configured: boolean;
        reachable: boolean;
        tools: string[];
        missing: string[];
        error?: string;
    };
    llm: {
        configured: boolean;
        provider: string;
        model: string | null;
    };
}
