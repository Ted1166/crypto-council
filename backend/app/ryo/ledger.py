import json

from app.ryo.result import ToolResult


def _index(result_id: str) -> int:
    digits = "".join(ch for ch in result_id if ch.isdigit())
    return int(digits) if digits else 0


class Ledger:
    def __init__(self, results: list[ToolResult] | None = None) -> None:
        self._results: dict[str, ToolResult] = {}
        self._counter = 0
        for result in results or []:
            self._results[result.id] = result
            self._counter = max(self._counter, _index(result.id))

    def reserve(self) -> str:
        self._counter += 1
        return f"E{self._counter}"

    def add(self, result: ToolResult) -> None:
        self._results[result.id] = result

    def get(self, result_id: str) -> ToolResult | None:
        return self._results.get(result_id)

    def all(self) -> list[ToolResult]:
        return sorted(self._results.values(), key=lambda item: _index(item.id))

    def latest_ok(self, *tools: str) -> ToolResult | None:
        for result in reversed(self.all()):
            if result.status == "ok" and result.tool in tools:
                return result
        return None

    def has_ok(self, tool: str) -> bool:
        return self.latest_ok(tool) is not None

    def unavailable_tools(self) -> list[str]:
        latest: dict[str, ToolResult] = {}
        for result in self.all():
            latest[result.tool] = result
        return [tool for tool, result in latest.items() if result.status != "ok"]

    def render(self, new_ids: set[str] | None = None, limit: int = 7000) -> str:
        blocks: list[str] = []
        for result in self.all():
            marker = " NEW" if new_ids and result.id in new_ids else ""
            header = (
                f"[{result.id}]{marker} {result.tool} "
                f"args={json.dumps(result.arguments, sort_keys=True, default=str)} "
                f"status={result.status} fetched_at={result.fetched_at.isoformat()}"
            )
            if result.status != "ok":
                blocks.append(f"{header}\nUNAVAILABLE: {result.error or 'no detail given'}")
                continue
            body = json.dumps(result.data, separators=(",", ":"), default=str)
            if len(body) > limit:
                body = body[:limit] + " ...[truncated]"
            blocks.append(f"{header}\n{body}")
        return "\n\n".join(blocks)
