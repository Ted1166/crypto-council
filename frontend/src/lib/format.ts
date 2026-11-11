import type { Direction } from "./types";

export const DIRECTION_LABEL: Record<Direction, string> = {
    long: "Long",
    short: "Short",
    stand_aside: "Stand aside",
};

export function formatPrice(value: number): string {
    const digits = value >= 100 ? 2 : value >= 1 ? 3 : 6;
    return value.toLocaleString("en-US", { maximumFractionDigits: digits });
}

export function formatClock(iso: string): string {
    return new Date(iso).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

export function relativeTime(iso: string): string {
    const seconds = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 1000));
    if (seconds < 60) return "just now";
    const minutes = Math.round(seconds / 60);
    if (minutes < 60) return `${minutes} min ago`;
    const hours = Math.round(minutes / 60);
    if (hours < 24) return `${hours} h ago`;
    return `${Math.round(hours / 24)} d ago`;
}

export function previewJson(data: unknown): string {
    return JSON.stringify(data, null, 2);
}
