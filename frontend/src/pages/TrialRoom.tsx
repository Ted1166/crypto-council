import { useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArgumentPanel } from "../components/debate/ArgumentPanel";
import { EvidenceList } from "../components/debate/EvidenceList";
import { Timeline } from "../components/debate/Timeline";
import { VerdictPanel } from "../components/debate/VerdictPanel";
import { CrossExamLog } from "../components/crossexam/CrossExamLog";
import { InterruptBar } from "../components/crossexam/InterruptBar";
import { HealthNotice } from "../components/common/HealthNotice";
import { useCase } from "../hooks/useCase";
import { api, messageOf } from "../lib/api";
import type { CouncilCase, Stance } from "../lib/types";

function StartForm() {
    const navigate = useNavigate();
    const [symbol, setSymbol] = useState("");
    const [busy, setBusy] = useState(false);
    const [failure, setFailure] = useState<string | null>(null);

    const submit = async (event: FormEvent) => {
        event.preventDefault();
        if (!symbol.trim() || busy) return;
        setBusy(true);
        setFailure(null);
        try {
            const created = await api.createCase(symbol.trim());
            navigate(`/case/${created.id}`);
            setSymbol("");
        } catch (error) {
            setFailure(messageOf(error));
        } finally {
            setBusy(false);
        }
    };

    return (
        <form className="start" onSubmit={submit}>
            <label htmlFor="symbol">Token to put before the council</label>
            <div className="start-row">
                <input
                    id="symbol"
                    value={symbol}
                    maxLength={15}
                    autoComplete="off"
                    autoCapitalize="characters"
                    placeholder="SOL"
                    onChange={(event) => setSymbol(event.target.value)}
                />
                <button type="submit" className="primary" disabled={busy || !symbol.trim()}>
                    {busy ? "Opening" : "Open hearing"}
                </button>
            </div>
            {failure ? (
                <p className="failure" role="alert">
                    {failure}
                </p>
            ) : null}
        </form>
    );
}

function argumentsFor(data: CouncilCase, stance: Stance) {
    return data.arguments.filter((item) => item.stance === stance);
}

function newEvidence(data: CouncilCase): string[] {
    const latest = data.crossexams[data.crossexams.length - 1];
    return latest && latest.status === "running" ? [] : latest?.new_evidence ?? [];
}

function blockedReason(data: CouncilCase | null): string | null {
    if (!data) return "Open a hearing to cross-examine it.";
    if (data.status === "running") return "The hearing is still in progress.";
    if (data.status !== "complete") return "This hearing did not finish, so it cannot be cross-examined.";
    if (data.crossexams.some((exam) => exam.status === "running")) return "A cross-examination is running.";
    return null;
}

export default function TrialRoom() {
    const { id } = useParams();
    const { data, events, error, live, refresh } = useCase(id);

    const challenge = async (text: string) => {
        if (!id) return;
        await api.crossExam(id, text);
        await refresh();
    };

    return (
        <div className="page">
            <HealthNotice />
            <StartForm />
            {error ? (
                <p className="failure" role="alert">
                    {error}
                </p>
            ) : null}
            {!id ? (
                <p className="empty">
                    Enter a token symbol to open a hearing. A bull and a bear argue from live RYO evidence, a judge rules, and you
                    can interrupt to make them check again. Past hearings are on the <Link to="/board">case board</Link>.
                </p>
            ) : null}
            {data ? (
                <>
                    <header className="case-head">
                        <h1>{data.symbol}</h1>
                        <p className="muted">
                            {data.status === "running" ? "Hearing in progress" : `Hearing ${data.status}`}. Model {data.model || "unknown"}.{" "}
                            <Link to={`/receipt/${data.id}`}>Open the shareable receipt</Link>
                        </p>
                    </header>
                    <VerdictPanel verdict={data.verdict} status={data.status} error={data.error} />
                    {data.status === "running" || data.crossexams.some((exam) => exam.status === "running") ? (
                        <Timeline events={events} live={live} />
                    ) : null}
                    <div className="columns">
                        <ArgumentPanel stance="bull" arguments={argumentsFor(data, "bull")} />
                        <ArgumentPanel stance="bear" arguments={argumentsFor(data, "bear")} />
                    </div>
                    <CrossExamLog exams={data.crossexams} />
                    <EvidenceList evidence={data.evidence} highlight={newEvidence(data)} />
                </>
            ) : null}
            <InterruptBar disabledReason={blockedReason(data)} onSubmit={challenge} />
        </div>
    );
}
