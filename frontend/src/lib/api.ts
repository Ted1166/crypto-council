import type { BoardItem, CouncilCase, CrossExam, Health } from "./types";

export class ApiError extends Error {
    status: number;

    constructor(status: number, message: string) {
        super(message);
        this.status = status;
    }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
    const response = await fetch(`/api${path}`, {
        headers: { "Content-Type": "application/json" },
        ...init,
    });
    if (!response.ok) {
        const body = await response.json().catch(() => null);
        const detail = body && typeof body.detail === "string" ? body.detail : response.statusText;
        throw new ApiError(response.status, detail);
    }
    return response.json() as Promise<T>;
}

export const api = {
    health: () => request<Health>("/health"),
    createCase: (symbol: string) =>
        request<{ id: string }>("/cases", { method: "POST", body: JSON.stringify({ symbol }) }),
    getCase: (id: string) => request<CouncilCase>(`/cases/${id}`),
    crossExam: (id: string, challenge: string) =>
        request<CrossExam>(`/cases/${id}/crossexam`, { method: "POST", body: JSON.stringify({ challenge }) }),
    board: () => request<BoardItem[]>("/board"),
};

export function messageOf(error: unknown): string {
    return error instanceof Error ? error.message : "Something went wrong.";
}
