import { Link } from "react-router-dom";
import { DIRECTION_LABEL, relativeTime } from "../../lib/format";
import type { BoardItem } from "../../lib/types";

interface Props {
    item: BoardItem;
    changed: boolean;
    onOpen: (item: BoardItem) => void;
}

export function CaseRow({ item, changed, onOpen }: Props) {
    const call = item.direction ? `${DIRECTION_LABEL[item.direction]} at ${item.conviction}` : item.status;
    return (
        <li className={`row ${changed ? "row-changed" : ""}`}>
            <Link to={`/case/${item.id}`} onClick={() => onOpen(item)}>
                <span className="row-symbol">{item.symbol}</span>
                <span className="row-call">{call}</span>
                <span className="row-summary">{item.change_summary ?? "No change recorded yet."}</span>
                <span className="row-meta">
                    {changed ? <strong>Changed since you looked. </strong> : null}
                    {item.crossexam_count} {item.crossexam_count === 1 ? "challenge" : "challenges"}, {relativeTime(item.updated_at)}
                </span>
            </Link>
        </li>
    );
}
