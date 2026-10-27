import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agents.llm import build_llm
from app.api import cases, health, stream
from app.api.deps import Container
from app.config import get_settings
from app.orchestrator import Orchestrator
from app.receipts.bus import EventBus
from app.receipts.store import Store
from app.ryo.client import RyoClient
from app.ryo.result import utcnow
from app.ryo.tools import RyoTools

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


async def recover(store: Store) -> None:
    for case in await store.unfinished():
        if case.status == "running":
            case.status = "interrupted"
            case.error = "The server restarted before this hearing finished. Open a new hearing to run it again."
        for exam in case.crossexams:
            if exam.status == "running":
                exam.status = "failed"
                exam.error = "The server restarted before this cross-examination finished."
                exam.completed_at = utcnow()
        await store.save_case(case)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    store = Store(settings.database_path)
    await store.init()
    await recover(store)
    bus = EventBus()
    client = RyoClient(settings)
    tools = RyoTools(client, settings)
    llm = build_llm(settings)
    orchestrator = Orchestrator(settings, tools, llm, store, bus) if llm else None
    app.state.container = Container(
        settings=settings,
        store=store,
        bus=bus,
        client=client,
        tools=tools,
        llm=llm,
        orchestrator=orchestrator,
    )
    yield
    if llm:
        await llm.aclose()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Crypto Council", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_list,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(cases.router)
    app.include_router(stream.router)
    return app


app = create_app()
