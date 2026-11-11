import { formatClock, previewJson } from "../../lib/format";
import type { ToolResult } from "../../lib/types";
import { ToolBadge } from "../common/ToolBadge";

export function EvidenceList({ evidence, highlight }: { evidence: ToolResult[]; highlight?: string[] }) {
    return (
        <section className="ledger" aria-labelledby="ledger-title">
            <h2 id="ledger-title">Evidence</h2>
            {evidence.length === 0 ? <p className="muted">No tool has returned yet.</p> : null}
            {evidence.map((item) => (
                <details key={item.id} id={`evidence-${item.id}`} className={highlight?.includes(item.id) ? "is-new" : ""}>
                    <summary>
                        <span className="evidence-id">{item.id}</span>
                        <span className="evidence-tool">{item.tool}</span>
                        <ToolBadge status={item.status} cached={item.cached} />
                        <span className="muted small">{formatClock(item.fetched_at)}</span>
                    </summary>
                    <p className="muted small">
                        Arguments {JSON.stringify(item.arguments)}. {item.latency_ms} ms.
                    </p>
                    {item.status === "ok" ? <pre>{previewJson(item.data)}</pre> : <p className="failure">{item.error}</p>}
                </details>
            ))}
        </section>
    );
}
