import type { Claim, RejectedClaim } from "../../lib/types";
import { EvidenceChips } from "./EvidenceChip";

export function ClaimList({ claims }: { claims: Claim[] }) {
    if (claims.length === 0) return <p className="muted">No claim survived the evidence check.</p>;
    return (
        <ul className="claims">
            {claims.map((claim, index) => (
                <li key={index}>
                    <span>{claim.text}</span> <EvidenceChips ids={claim.evidence} />
                </li>
            ))}
        </ul>
    );
}

export function Rejections({ items }: { items: RejectedClaim[] }) {
    if (items.length === 0) return null;
    return (
        <details className="rejections">
            <summary>
                {items.length} {items.length === 1 ? "claim was" : "claims were"} removed by the evidence check
            </summary>
            <ul>
                {items.map((item, index) => (
                    <li key={index}>
                        <span className="struck">{item.text}</span>
                        <span className="muted"> Removed because {item.reason}.</span>
                    </li>
                ))}
            </ul>
        </details>
    );
}
