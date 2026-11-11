import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { CaseRow } from "../components/board/CaseRow";
import { api, messageOf } from "../lib/api";
import type { BoardItem } from "../lib/types";

const STORAGE_KEY = "council.seen";

function readSeen(): Record<string, string> {
    try {
        const raw = window.localStorage.getItem(STORAGE_KEY);
        return raw ? (JSON.parse(raw) as Record<string, string>) : {};
    } catch {
        return {};
    }
}

function writeSeen(seen: Record<string, string>) {
    try {
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(seen));
    } catch {
        return;
    }
}

export default function CaseBoard() {
    const [items, setItems] = useState<BoardItem[] | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [seen, setSeen] = useState<Record<string, string>>(readSeen);

    useEffect(() => {
        api
            .board()
            .then(setItems)
            .catch((failure) => setError(messageOf(failure)));
    }, []);

    const ordered = useMemo(() => {
        const changed = (item: BoardItem) => seen[item.id] !== item.updated_at;
        return (items ?? []).slice().sort((a, b) => {
            if (changed(a) !== changed(b)) return changed(a) ? -1 : 1;
            return b.change_score - a.change_score;
        });
    }, [items, seen]);

    const open = (item: BoardItem) => {
        const next = { ...seen, [item.id]: item.updated_at };
        setSeen(next);
        writeSeen(next);
    };

    return (
        <div className="page">
            <h1>Case board</h1>
            <p className="muted">Hearings ordered by what changed. Cases that moved since you last opened them come first.</p>
            {error ? (
                <p className="failure" role="alert">
                    {error}
                </p>
            ) : null}
            {items && items.length === 0 ? (
                <p className="empty">
                    No hearings yet. <Link to="/">Open the first one.</Link>
                </p>
            ) : null}
            <ul className="rows">
                {ordered.map((item) => (
                    <CaseRow key={item.id} item={item} changed={seen[item.id] !== item.updated_at} onOpen={open} />
                ))}
            </ul>
        </div>
    );
}
