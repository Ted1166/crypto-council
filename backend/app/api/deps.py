import asyncio
from dataclasses import dataclass, field
from typing import Any, Coroutine

from fastapi import Request

from app.agents.llm import LLM
from app.config import Settings
from app.orchestrator import Orchestrator
from app.receipts.bus import EventBus
from app.receipts.store import Store
from app.ryo.client import RyoClient
from app.ryo.tools import RyoTools


@dataclass
class Container:
    settings: Settings
    store: Store
    bus: EventBus
    client: RyoClient
    tools: RyoTools
    llm: LLM | None
    orchestrator: Orchestrator | None
    tasks: set[asyncio.Task[Any]] = field(default_factory=set)

    async def emit(self, case_id: str, kind: str, message: str) -> None:
        event = await self.store.append_event(case_id, kind, message)
        await self.bus.publish(event)

    def spawn(self, coroutine: Coroutine[Any, Any, None]) -> None:
        task = asyncio.create_task(coroutine)
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)


def get_container(request: Request) -> Container:
    return request.app.state.container
