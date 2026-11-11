import type { Argument, Stance } from "../../lib/types";
import { ClaimList, Rejections } from "../common/ClaimList";

const TITLE: Record<Stance, string> = { bull: "Bull", bear: "Bear" };
const ROUND: Record<Argument["round"], string> = {
    opening: "Opening",
    rebuttal: "Rebuttal",
    crossexam: "Under challenge",
};

export function ArgumentPanel({ stance, arguments: items }: { stance: Stance; arguments: Argument[] }) {
    return (
        <section className={`panel panel-${stance}`} aria-labelledby={`panel-${stance}`}>
            <h2 id={`panel-${stance}`}>{TITLE[stance]}</h2>
            {items.length === 0 ? <p className="muted">Waiting for the opening argument.</p> : null}
            {items.map((argument, index) => (
                <article key={index} className="argument">
                    <h3>
                        {ROUND[argument.round]}: {argument.headline}
                    </h3>
                    <p className="muted small">Conviction {argument.conviction}</p>
                    <ClaimList claims={argument.claims} />
                    {argument.concessions.length > 0 ? (
                        <details>
                            <summary>Concedes</summary>
                            <ul className="claims">
                                {argument.concessions.map((item, position) => (
                                    <li key={position}>{item}</li>
                                ))}
                            </ul>
                        </details>
                    ) : null}
                    <Rejections items={argument.rejected} />
                </article>
            ))}
        </section>
    );
}
