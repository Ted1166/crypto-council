import asyncio
import logging

from app.agents.debater import argue
from app.agents.judge import judge
from app.agents.llm import LLM, LLMError
from app.config import Settings
from app.crossexam.diff import change_score, diff_verdicts
from app.crossexam.intent import plan_crossexam
from app.receipts.bus import EventBus
from app.receipts.schema import Argument, Case, CrossExam, Stance
from app.receipts.store import Store
from app.ryo.ledger import Ledger
from app.ryo.result import ToolResult, utcnow
from app.ryo.tools import RyoTools

logger = logging.getLogger("council")

LABELS = {"long": "long", "short": "short", "stand_aside": "stand aside"}


def _evidence_line(result: ToolResult) -> str:
    if result.status == "ok":
        suffix = " (cached)" if result.cached else ""
        return f"{result.id} {result.tool} returned data in {result.latency_ms} ms{suffix}"
    return f"{result.id} {result.tool} was {result.status}: {result.error or 'no detail'}"


def _latest(case: Case, stance: Stance) -> Argument | None:
    for exam in reversed(case.crossexams):
        for argument in reversed(exam.arguments):
            if argument.stance == stance:
                return argument
    for argument in reversed(case.arguments):
        if argument.stance == stance:
            return argument
    return None


class Orchestrator:
    def __init__(self, settings: Settings, tools: RyoTools, llm: LLM, store: Store, bus: EventBus) -> None:
        self._settings = settings
        self._tools = tools
        self._llm = llm
        self._store = store
        self._bus = bus
        self._locks: dict[str, asyncio.Lock] = {}

    def _lock(self, case_id: str) -> asyncio.Lock:
        return self._locks.setdefault(case_id, asyncio.Lock())

    async def _emit(self, case_id: str, kind: str, message: str) -> None:
        event = await self._store.append_event(case_id, kind, message)
        await self._bus.publish(event)

    async def _fail(self, case: Case, message: str) -> None:
        case.status = "failed"
        case.error = message
        await self._store.save_case(case)
        await self._emit(case.id, "error", message)

    async def run_case(self, case_id: str) -> None:
        async with self._lock(case_id):
            case = await self._store.get_case(case_id)
            if case is None:
                return
            try:
                await self._debate(case)
            except LLMError as exc:
                await self._fail(case, f"The model could not complete the hearing: {exc}")
            except Exception as exc:
                logger.exception("hearing failed for %s", case_id)
                await self._fail(case, f"The hearing stopped unexpectedly: {type(exc).__name__}")

    async def _debate(self, case: Case) -> None:
        ledger = Ledger(case.evidence)
        await self._emit(case.id, "stage", f"Collecting live evidence for {case.symbol}")
        results = await asyncio.gather(
            self._tools.market_overview(ledger),
            self._tools.analyze_token(ledger, case.symbol),
            self._tools.deep_analysis(ledger, case.symbol),
            self._tools.check_safety(ledger, case.symbol),
        )
        case.evidence = ledger.all()
        await self._store.save_case(case)
        for result in results:
            await self._emit(case.id, "evidence", _evidence_line(result))
        if ledger.latest_ok("analyze_token", "deep_analysis") is None:
            await self._fail(
                case,
                "RYO returned no market data for this token, so there is nothing to argue from. "
                "The failed calls are listed under evidence.",
            )
            return

        await self._emit(case.id, "stage", "Bull and bear are preparing opening arguments")
        bull, bear = await asyncio.gather(
            argue(self._llm, "bull", "opening", case.symbol, ledger),
            argue(self._llm, "bear", "opening", case.symbol, ledger),
        )
        case.arguments.extend([bull, bear])
        await self._store.save_case(case)
        await self._emit(case.id, "argument", f"Bull opens: {bull.headline}")
        await self._emit(case.id, "argument", f"Bear opens: {bear.headline}")

        await self._emit(case.id, "stage", "Rebuttals")
        bull, bear = await asyncio.gather(
            argue(self._llm, "bull", "rebuttal", case.symbol, ledger, opponent=bear),
            argue(self._llm, "bear", "rebuttal", case.symbol, ledger, opponent=bull),
        )
        case.arguments.extend([bull, bear])
        await self._store.save_case(case)
        await self._emit(case.id, "argument", f"Bull answers: {bull.headline}")
        await self._emit(case.id, "argument", f"Bear answers: {bear.headline}")

        await self._emit(case.id, "stage", "The judge is weighing the evidence")
        verdict = await judge(self._llm, case.symbol, ledger, bull, bear)
        case.verdict = verdict
        case.model = self._llm.name
        case.status = "complete"
        await self._store.save_case(
            case,
            change_score=30,
            change_summary=f"New call: {LABELS[verdict.direction]} at {verdict.conviction}.",
        )
        await self._emit(case.id, "verdict", verdict.radio_call)

    async def run_crossexam(self, case_id: str, exam_id: str) -> None:
        async with self._lock(case_id):
            case = await self._store.get_case(case_id)
            if case is None:
                return
            exam = next((item for item in case.crossexams if item.id == exam_id), None)
            if exam is None:
                return
            try:
                await self._crossexam(case, exam)
            except Exception as exc:
                if not isinstance(exc, LLMError):
                    logger.exception("cross-examination failed for %s", case_id)
                exam.status = "failed"
                exam.error = (
                    f"The model could not complete the cross-examination: {exc}"
                    if isinstance(exc, LLMError)
                    else f"The cross-examination stopped unexpectedly: {type(exc).__name__}"
                )
                exam.completed_at = utcnow()
                await self._store.save_case(case)
                await self._emit(case.id, "error", exam.error)

    async def _crossexam(self, case: Case, exam: CrossExam) -> None:
        ledger = Ledger(case.evidence)
        exam.verdict_before = case.verdict
        await self._emit(case.id, "stage", "Planning which tools to run again")
        offered = await self._tools.offered()
        calls, reading, dropped = await plan_crossexam(self._llm, exam.challenge, case, offered)
        exam.plan = calls
        exam.reading = reading
        exam.dropped_calls = dropped
        await self._store.save_case(case)

        if calls:
            await self._emit(case.id, "stage", f"Re-running {len(calls)} RYO tool call(s) live")
        else:
            await self._emit(case.id, "stage", "The existing evidence already covers this challenge")
        results = await asyncio.gather(
            *[self._tools.call(ledger, call.tool, call.arguments, fresh=True) for call in calls]
        )
        exam.new_evidence = [result.id for result in results]
        case.evidence = ledger.all()
        await self._store.save_case(case)
        for result in results:
            await self._emit(case.id, "evidence", _evidence_line(result))

        new_ids = set(exam.new_evidence)
        last_bull = _latest(case, "bull")
        last_bear = _latest(case, "bear")
        await self._emit(case.id, "stage", "Bull and bear are answering the challenge")
        bull, bear = await asyncio.gather(
            argue(self._llm, "bull", "crossexam", case.symbol, ledger, last_bear, exam.challenge, new_ids),
            argue(self._llm, "bear", "crossexam", case.symbol, ledger, last_bull, exam.challenge, new_ids),
        )
        exam.arguments = [bull, bear]
        await self._store.save_case(case)
        await self._emit(case.id, "argument", f"Bull answers: {bull.headline}")
        await self._emit(case.id, "argument", f"Bear answers: {bear.headline}")

        await self._emit(case.id, "stage", "The judge is re-weighing the call")
        verdict = await judge(
            self._llm, case.symbol, ledger, bull, bear, exam.challenge, case.verdict, new_ids
        )
        before = case.verdict
        exam.verdict_after = verdict
        if before is not None:
            exam.diff = diff_verdicts(before, verdict, list(results))
        case.verdict = verdict
        exam.status = "complete"
        exam.completed_at = utcnow()
        summary = exam.diff.summary if exam.diff else "Call updated after challenge."
        score = change_score(exam.diff) if exam.diff else 10
        await self._store.save_case(case, change_score=score, change_summary=summary)
        await self._emit(case.id, "verdict", summary)
