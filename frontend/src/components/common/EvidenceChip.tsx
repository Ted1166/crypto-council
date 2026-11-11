export function EvidenceChip({ id }: { id: string }) {
    const reveal = () => {
        const target = document.getElementById(`evidence-${id}`);
        if (!(target instanceof HTMLDetailsElement)) return;
        target.open = true;
        target.scrollIntoView({ block: "center" });
        target.querySelector("summary")?.focus();
    };
    return (
        <button type="button" className="chip" onClick={reveal} aria-label={`Show evidence ${id}`}>
            {id}
        </button>
    );
}

export function EvidenceChips({ ids }: { ids: string[] }) {
    if (ids.length === 0) return null;
    return (
        <span className="chips">
            {ids.map((id) => (
                <EvidenceChip key={id} id={id} />
            ))}
        </span>
    );
}
