import { useEffect } from "react";
import type { RefObject } from "react";

function isTyping(target: EventTarget | null): boolean {
    if (!(target instanceof HTMLElement)) return false;
    return target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName);
}

export function useSlashFocus(ref: RefObject<HTMLInputElement | null>) {
    useEffect(() => {
        const handler = (event: KeyboardEvent) => {
            if (event.key === "/" && !event.metaKey && !event.ctrlKey && !event.altKey && !isTyping(event.target)) {
                event.preventDefault();
                ref.current?.focus();
            }
        };
        window.addEventListener("keydown", handler);
        return () => window.removeEventListener("keydown", handler);
    }, [ref]);
}
