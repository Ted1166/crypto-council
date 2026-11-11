import { DIRECTION_LABEL } from "../../lib/format";
import type { CrossExam } from "../../lib/types";
import { ClaimList, Rejections } from "../common/ClaimList";
import { EvidenceChips } from "../common/EvidenceChip";

function Entry({ exam }: { exam: CrossExam }) {
    const diff = exam.diff;
    return (
        <li className={`exam exam-${exam.status}`}>
            <h3>{exam.challenge}</h3>
            {exam.reading ? <p className="muted">{exam.reading}</p> : null}
            {exam.status === "running" ? (
                <p role="status">The agents are answering. Tools are being run again.</p>
            ) : null}
            {exam.error ? <p className="failure">{exam.error}</p> : null}

            {exam.plan.length > 0 ? (
                <p className="small">
                    Tools run again: {exam.plan.map((call) => call.tool).join(", ")}. New evidence{" "}
                    <EvidenceChips ids={exam.new_evidence} />
                </p>
            ) : exam.status !== "running" ? (
                <p className="small muted">No tool was re-run. The existing evidence already covered this.</p>
            ) : null}
            {exam.dropped_calls.length > 0 ? (
                <p className="small muted">Skipped: {exam.dropped_calls.join("; ")}.</p>
            ) : null}

            {diff ? (
                <div className={`diff ${diff.flipped ? "diff-flipped" : ""}`}>
                    <p className="diff-line">
                        <span>
                            {DIRECTION_LABEL[diff.direction_before]} at {diff.conviction_before}
                        </span>
                        <span aria-hidden="true"> to </span>
                        <span className="visually-hidden"> changed to </span>
                        <strong>
                            {DIRECTION_LABEL[diff.direction_after]} at {diff.conviction_after}
                        </strong>
                    </p>
                    <p>{diff.summary}</p>
                </div>
            ) : null}

            {exam.arguments.map((argument) => (
                <details key={argument.stance}>
                    <summary>
                        {argument.stance === "bull" ? "Bull" : "Bear"} answers: {argument.headline}
                    </summary>
                    <ClaimList claims={argument.claims} />
                    <Rejections items={argument.rejected} />
                </details>
            ))}
        </li>
    );
}

export function CrossExamLog({ exams }: { exams: CrossExam[] }) {
    if (exams.length === 0) return null;
    return (
        <section aria-labelledby="exam-title">
            <h2 id="exam-title">Cross-examination</h2>
            <ol className="exams">
                {exams
                    .slice()
                    .reverse()
                    .map((exam) => (
                        <Entry key={exam.id} exam={exam} />
                    ))}
            </ol>
        </section>
    );
}
