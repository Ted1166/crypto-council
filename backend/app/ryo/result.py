from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ToolResult(BaseModel):
    id: str
    tool: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    status: Literal["ok", "unavailable", "error"]
    data: Any = None
    error: str | None = None
    fetched_at: datetime = Field(default_factory=utcnow)
    latency_ms: int = 0
    cached: bool = False
