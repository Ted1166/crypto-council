import asyncio
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.api.deps import get_container
from app.receipts.schema import Event

router = APIRouter(prefix="/api")

HEARTBEAT_SECONDS = 15


def frame(event: Event) -> str:
    return f"id: {event.seq}\ndata: {event.model_dump_json()}\n\n"


@router.get("/cases/{case_id}/stream")
async def stream(case_id: str, request: Request, after: int = 0) -> StreamingResponse:
    container = get_container(request)
    if await container.store.get_case(case_id) is None:
        raise HTTPException(404, "No hearing exists with that id.")
    header = request.headers.get("last-event-id", "")
    cursor = int(header) if header.isdigit() else after

    async def generate() -> AsyncIterator[str]:
        last = cursor
        async with container.bus.subscribe(case_id) as queue:
            for event in await container.store.events_after(case_id, last):
                last = event.seq
                yield frame(event)
            while not await request.is_disconnected():
                try:
                    event = await asyncio.wait_for(queue.get(), HEARTBEAT_SECONDS)
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
                    continue
                if event.seq <= last:
                    continue
                last = event.seq
                yield frame(event)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
