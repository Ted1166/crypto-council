import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import type { Health } from "../../lib/types";

function problems(health: Health): string[] {
    const found: string[] = [];
    if (!health.llm.configured) {
        found.push("No model is configured. Set LLM_MODEL and LLM_API_KEY in the backend environment, then restart it.");
    }
    if (!health.ryo.configured) {
        found.push("RYO_MCP_URL is not set, so no market evidence can be gathered.");
    } else if (!health.ryo.reachable) {
        found.push(`The RYO server could not be reached${health.ryo.error ? `: ${health.ryo.error}` : "."}`);
    } else if (health.ryo.missing.length > 0) {
        found.push(
            `The RYO server does not offer ${health.ryo.missing.join(", ")}. Hearings still run, and those gaps are shown as unavailable.`,
        );
    }
    return found;
}

export function HealthNotice() {
    const [health, setHealth] = useState<Health | null>(null);
    const [unreachable, setUnreachable] = useState(false);

    useEffect(() => {
        api
            .health()
            .then(setHealth)
            .catch(() => setUnreachable(true));
    }, []);

    if (unreachable) {
        return (
            <p className="notice" role="alert">
                The Crypto Council server did not respond. Start the backend and reload this page.
            </p>
        );
    }
    if (!health) return null;
    const found = problems(health);
    if (found.length === 0) return null;
    return (
        <div className="notice" role="status">
            {found.map((line) => (
                <p key={line}>{line}</p>
            ))}
        </div>
    );
}
