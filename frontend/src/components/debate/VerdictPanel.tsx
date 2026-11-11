import { DIRECTION_LABEL, formatPrice } from "../../lib/format";
import type { CaseStatus, Verdict } from "../../lib/types";
import { ClaimList, Rejections } from "../common/ClaimList";
import { EvidenceChips } from "../common/EvidenceChip";

interface Props {
    verdict: Verdict | null;
    status: CaseStatus;
    error: string | null;
}

export function VerdictPanel({ verdict, status, error }: Props) {
    if (!verdict) {
        const failed = status === "failed" || status === "interrupted";
        return (
            <section className="verdict verdict-pending" aria-labelledby="verdict-title">
                <h2 id="verdict-title" className="verdict-direction">
                    {failed ? "No verdict" : "The judge has not ruled yet"}
                </h2>
                <p className="radio">{failed ? error : "Evidence is being gathered and argued. The call appears here."}</p>
            </section>
        );
    }
    return (
        <section className={`verdict verdict-${verdict.direction}`} aria-labelledby="verdict-title">
            <h2 id="verdict-title" className="verdict-direction">
                {DIRECTION_LABEL[verdict.direction]}
            </h2>
            <p className="radio">{verdict.radio_call}</p>
            <div
                className="meter"
                role="meter"
                aria-label="Conviction"
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={verdict.conviction}
            >
                <span style={{ width: `${verdict.conviction}%` }} />
            </div>
            <p className="meter-label">Conviction {verdict.conviction} of 100</p>

            {verdict.plan ? (
                <dl className="plan">
                    <div>
                        <dt>Practice entry</dt>
                        <dd>{formatPrice(verdict.plan.entry)}</dd>
                    </div>
                    <div>
                        <dt>Stop</dt>
                        <dd>{formatPrice(verdict.plan.stop)}</dd>
                    </div>
                    <div>
                        <dt>Target</dt>
                        <dd>{formatPrice(verdict.plan.target)}</dd>
                    </div>
                    <div>
                        <dt>Reward to risk</dt>
                        <dd>{verdict.plan.risk_reward.toFixed(1)}</dd>
                    </div>
                </dl>
            ) : verdict.plan_note ? (
                <p className="muted">{verdict.plan_note}</p>
            ) : null}
            {verdict.plan ? (
                <p className="muted small">
                    {verdict.plan.basis} Based on <EvidenceChips ids={verdict.plan.evidence} />. Practice only, no funds move.
                </p>
            ) : null}

            <h3>Why</h3>
            <ClaimList claims={verdict.rationale} />
            <Rejections items={verdict.rejected} />

            {verdict.unresolved.length > 0 ? (
                <>
                    <h3>Could not be checked</h3>
                    <ul className="claims">
                        {verdict.unresolved.map((item, index) => (
                            <li key={index}>{item}</li>
                        ))}
                    </ul>
                </>
            ) : null}
        </section>
    );
}
