import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator

from app.receipts.schema import Event


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue[Event]]] = {}

    async def publish(self, event: Event) -> None:
        for queue in list(self._subscribers.get(event.case_id, ())):
            queue.put_nowait(event)

    @asynccontextmanager
    async def subscribe(self, case_id: str) -> AsyncIterator[asyncio.Queue[Event]]:
        queue: asyncio.Queue[Event] = asyncio.Queue()
        self._subscribers.setdefault(case_id, set()).add(queue)
        try:
            yield queue
        finally:
            self._subscribers[case_id].discard(queue)
            if not self._subscribers[case_id]:
                del self._subscribers[case_id]
