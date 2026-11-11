import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArgumentPanel } from "../components/debate/ArgumentPanel";
import { EvidenceList } from "../components/debate/EvidenceList";
import { VerdictPanel } from "../components/debate/VerdictPanel";
import { CrossExamLog } from "../components/crossexam/CrossExamLog";
import { useCase } from "../hooks/useCase";

export default function Receipt() {
    const { id } = useParams();
    const { data, error } = useCase(id, false);
    const [copied, setCopied] = useState(false);

    const copy = async () => {
        try {
            await navigator.clipboard.writeText(window.location.href);
            setCopied(true);
        } catch {
            setCopied(false);
        }
    };

    if (error) {
        return (
            <div className="page">
                <p className="failure" role="alert">
                    {error}
                </p>
                <Link to="/">Back to the trial room</Link>
            </div>
        );
    }
    if (!data) return <div className="page muted">Loading the receipt.</div>;

    return (
        <div className="page">
            <header className="case-head">
                <h1>{data.symbol} decision receipt</h1>
                <p className="muted">
                    Receipt {data.id}. Opened {new Date(data.created_at).toLocaleString()}. Model {data.model || "unknown"}. Every
                    claim links to the live RYO result it came from.
                </p>
                <button type="button" onClick={() => void copy()}>
                    {copied ? "Link copied" : "Copy link"}
                </button>
            </header>
            <VerdictPanel verdict={data.verdict} status={data.status} error={data.error} />
            <div className="columns">
                <ArgumentPanel stance="bull" arguments={data.arguments.filter((item) => item.stance === "bull")} />
                <ArgumentPanel stance="bear" arguments={data.arguments.filter((item) => item.stance === "bear")} />
            </div>
            <CrossExamLog exams={data.crossexams} />
            <EvidenceList evidence={data.evidence} />
        </div>
    );
}
