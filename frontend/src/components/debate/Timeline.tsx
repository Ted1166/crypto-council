import { formatClock } from "../../lib/format";
import type { CaseEvent } from "../../lib/types";

export function Timeline({ events, live }: { events: CaseEvent[]; live: boolean }) {
    const recent = events.slice(-6);
    return (
        <section className="timeline" aria-label="Hearing progress">
            <p className="muted small">{live ? "Connected to the live stream." : "Reconnecting to the live stream."}</p>
            <ol aria-live="polite">
                {recent.map((event) => (
                    <li key={event.seq} className={`event-${event.kind}`}>
                        <time dateTime={event.created_at}>{formatClock(event.created_at)}</time>
                        <span>{event.message}</span>
                    </li>
                ))}
            </ol>
        </section>
    );
}
