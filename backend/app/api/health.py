from typing import Any

from fastapi import APIRouter, Request

from app.api.deps import get_container
from app.ryo.client import RyoUnavailable
from app.ryo.tools import EXPECTED_TOOLS

router = APIRouter(prefix="/api")


@router.get("/health")
async def health(request: Request, refresh: bool = False) -> dict[str, Any]:
    container = get_container(request)
    settings = container.settings
    ryo: dict[str, Any] = {"configured": settings.ryo_configured, "reachable": False, "tools": [], "missing": []}
    if settings.ryo_configured:
        try:
            offered = await container.client.tools(refresh=refresh)
            ryo["reachable"] = True
            ryo["tools"] = sorted(offered)
            ryo["missing"] = [name for name in EXPECTED_TOOLS if name not in offered]
        except RyoUnavailable as exc:
            ryo["error"] = str(exc)
    return {
        "status": "ready" if ryo["reachable"] and container.llm is not None else "degraded",
        "ryo": ryo,
        "llm": {
            "configured": container.llm is not None,
            "provider": settings.llm_provider,
            "model": settings.llm_model or None,
        },
    }
