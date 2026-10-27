from typing import Any

ALIASES: dict[str, tuple[str, ...]] = {
    "symbol": (
        "symbol",
        "token",
        "ticker",
        "coin",
        "asset",
        "token_symbol",
        "name",
        "query",
        "symbols",
        "tokens",
    ),
    "symbols": ("symbols", "tokens", "tickers", "coins", "assets", "token_symbols", "list"),
    "theme": ("theme", "topic", "category", "query"),
    "limit": ("limit", "top_n", "count", "max_results", "n"),
}


class ArgumentMappingError(Exception):
    pass


def _kinds(prop: dict[str, Any]) -> set[str]:
    kinds: set[str] = set()
    declared = prop.get("type")
    if isinstance(declared, str):
        kinds.add(declared)
    elif isinstance(declared, list):
        kinds.update(item for item in declared if isinstance(item, str))
    for option in list(prop.get("anyOf", [])) + list(prop.get("oneOf", [])):
        if isinstance(option, dict):
            kinds.update(_kinds(option))
    return kinds


def _shape(key: str, value: Any, prop: dict[str, Any]) -> Any:
    kinds = _kinds(prop)
    if key in ("symbol", "symbols"):
        values = list(value) if isinstance(value, (list, tuple)) else [value]
        if "array" in kinds:
            return values
        return ",".join(str(item) for item in values)
    if key == "limit":
        if "integer" in kinds or "number" in kinds:
            return int(value)
        return str(value)
    return value


def adapt(
    schema: dict[str, Any] | None,
    canonical: dict[str, Any],
    optional: frozenset[str] | set[str] = frozenset(),
) -> dict[str, Any]:
    schema = schema or {}
    properties: dict[str, Any] = schema.get("properties") or {}
    required: list[str] = list(schema.get("required") or [])
    arguments: dict[str, Any] = {}
    used: set[str] = set()
    for key, value in canonical.items():
        if value is None or key not in ALIASES:
            continue
        match = next((name for name in ALIASES[key] if name in properties and name not in used), None)
        if match is None:
            if key in optional:
                continue
            raise ArgumentMappingError(
                f"no input resembling '{key}' among {sorted(properties) or 'no declared inputs'}"
            )
        used.add(match)
        arguments[match] = _shape(key, value, properties[match])
    missing = [
        name
        for name in required
        if name not in arguments and "default" not in properties.get(name, {})
    ]
    if missing:
        raise ArgumentMappingError(f"required inputs could not be filled: {missing}")
    return arguments
