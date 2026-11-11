import { useCallback, useEffect, useRef, useState } from "react";
import { api, apiUrl, messageOf } from "../lib/api";
import type { CaseEvent, CouncilCase } from "../lib/types";

interface Snapshot {
    id: string;
    data: CouncilCase | null;
    events: CaseEvent[];
    error: string | null;
    live: boolean;
}

function empty(id: string): Snapshot {
    return { id, data: null, events: [], error: null, live: false };
}

export function useCase(id: string | undefined, stream = true) {
    const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
    const refreshRef = useRef<() => Promise<void>>(() => Promise.resolve());

    useEffect(() => {
        if (!id) return undefined;
        let closed = false;
        let inflight = false;
        let dirty = false;

        const update = (change: (previous: Snapshot) => Snapshot) => {
            setSnapshot((previous) => change(previous && previous.id === id ? previous : empty(id)));
        };

        const load = async (): Promise<void> => {
            if (inflight) {
                dirty = true;
                return;
            }
            inflight = true;
            try {
                const loaded = await api.getCase(id);
                if (!closed) update((previous) => ({ ...previous, data: loaded, error: null }));
            } catch (failure) {
                if (!closed) update((previous) => ({ ...previous, error: messageOf(failure) }));
            } finally {
                inflight = false;
                if (dirty && !closed) {
                    dirty = false;
                    void load();
                }
            }
        };

        refreshRef.current = load;
        void load();
        if (!stream) {
            return () => {
                closed = true;
            };
        }

        const source = new EventSource(apiUrl(`/cases/${id}/stream`));
        source.onopen = () => update((previous) => ({ ...previous, live: true }));
        source.onerror = () => update((previous) => ({ ...previous, live: false }));
        source.onmessage = (message) => {
            const event = JSON.parse(message.data) as CaseEvent;
            update((previous) =>
                previous.events.some((item) => item.seq === event.seq)
                    ? previous
                    : { ...previous, events: [...previous.events, event] },
            );
            void load();
        };
        return () => {
            closed = true;
            source.close();
        };
    }, [id, stream]);

    const refresh = useCallback(() => refreshRef.current(), []);
    const current = id && snapshot && snapshot.id === id ? snapshot : null;

    return {
        data: current?.data ?? null,
        events: current?.events ?? [],
        error: current?.error ?? null,
        live: current?.live ?? false,
        refresh,
    };
}
