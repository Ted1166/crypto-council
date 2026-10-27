import asyncio
import sys
import uuid

from app.agents.llm import build_llm
from app.config import get_settings
from app.orchestrator import Orchestrator
from app.receipts.bus import EventBus
from app.receipts.schema import Case
from app.receipts.store import Store
from app.ryo.client import RyoClient
from app.ryo.tools import RyoTools


async def main(symbols: list[str]) -> None:
    settings = get_settings()
    llm = build_llm(settings)
    if llm is None:
        raise SystemExit("Set LLM_MODEL and LLM_API_KEY before seeding.")
    if not settings.ryo_configured:
        raise SystemExit("Set RYO_MCP_URL before seeding.")
    store = Store(settings.database_path)
    await store.init()
    orchestrator = Orchestrator(settings, RyoTools(RyoClient(settings), settings), llm, store, EventBus())
    for symbol in symbols:
        case = Case(id=uuid.uuid4().hex[:10], symbol=symbol.upper(), model=llm.name)
        await store.save_case(case)
        await orchestrator.run_case(case.id)
        finished = await store.get_case(case.id)
        outcome = finished.verdict.radio_call if finished and finished.verdict else (finished.error if finished else "")
        print(f"{case.symbol} {case.id} {finished.status if finished else 'missing'}: {outcome}")
    await llm.aclose()


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:] or ["BTC", "ETH", "SOL"]))
