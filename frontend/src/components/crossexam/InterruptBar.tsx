import { useRef, useState } from "react";
import type { FormEvent } from "react";
import { useSlashFocus } from "../../hooks/useHotKeys";

const PRESETS = [
    "What if funding flips against this position?",
    "How has market sentiment shifted this week?",
    "What if the broader market drops 10 percent?",
    "What are the biggest risks you have not covered?",
    "Compare this token with ETH.",
];

interface Props {
    disabledReason: string | null;
    onSubmit: (challenge: string) => Promise<void>;
}

export function InterruptBar({ disabledReason, onSubmit }: Props) {
    const [text, setText] = useState("");
    const [sending, setSending] = useState(false);
    const [failure, setFailure] = useState<string | null>(null);
    const input = useRef<HTMLInputElement | null>(null);
    useSlashFocus(input);

    const send = async (challenge: string) => {
        const trimmed = challenge.trim();
        if (trimmed.length < 3 || sending || disabledReason) return;
        setSending(true);
        setFailure(null);
        try {
            await onSubmit(trimmed);
            setText("");
        } catch (error) {
            setFailure(error instanceof Error ? error.message : "The challenge could not be sent.");
        } finally {
            setSending(false);
        }
    };

    const submit = (event: FormEvent) => {
        event.preventDefault();
        void send(text);
    };

    const blocked = Boolean(disabledReason) || sending;

    return (
        <form className="interrupt" onSubmit={submit} aria-label="Cross-examine the hearing">
            <div className="presets" role="group" aria-label="Suggested challenges">
                {PRESETS.map((preset) => (
                    <button key={preset} type="button" className="preset" disabled={blocked} onClick={() => void send(preset)}>
                        {preset}
                    </button>
                ))}
            </div>
            <div className="interrupt-row">
                <label htmlFor="challenge" className="visually-hidden">
                    Challenge the agents
                </label>
                <input
                    id="challenge"
                    ref={input}
                    value={text}
                    maxLength={400}
                    disabled={blocked}
                    placeholder={disabledReason ?? "Interrupt with a challenge. Press / to focus."}
                    onChange={(event) => setText(event.target.value)}
                    onKeyDown={(event) => {
                        if (event.key === "Escape") input.current?.blur();
                    }}
                />
                <button type="submit" className="primary" disabled={blocked || text.trim().length < 3}>
                    {sending ? "Sending" : "Cross-examine"}
                </button>
            </div>
            {failure ? (
                <p className="failure" role="alert">
                    {failure}
                </p>
            ) : null}
        </form>
    );
}
