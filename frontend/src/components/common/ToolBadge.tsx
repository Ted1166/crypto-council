import type { ToolStatus } from "../../lib/types";

const LABEL: Record<ToolStatus, string> = {
    ok: "Live data",
    unavailable: "Unavailable",
    error: "Tool error",
};

export function ToolBadge({ status, cached }: { status: ToolStatus; cached?: boolean }) {
    return (
        <span className={`badge badge-${status}`}>
            {LABEL[status]}
            {cached ? ", cached" : ""}
        </span>
    );
}
