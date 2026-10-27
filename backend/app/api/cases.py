import re
import uuid

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.api.deps import get_container
from app.receipts.schema import BoardItem, Case, CrossExam

router = APIRouter(prefix="/api")

SYMBOL = re.compile(r"^[A-Za-z0-9]{1,15}$")


class NewCase(BaseModel):
    symbol: str


class NewCrossExam(BaseModel):
    challenge: str


@router.post("/cases", status_code=201)
async def create_case(body: NewCase, request: Request) -> dict[str, str]:
    container = get_container(request)
    symbol = body.symbol.strip().upper()
    if not SYMBOL.match(symbol):
        raise HTTPException(422, "Enter a token symbol such as SOL. Wallet addresses are not accepted.")
    if container.orchestrator is None or container.llm is None:
        raise HTTPException(503, "No model is configured. Set LLM_MODEL and LLM_API_KEY, then restart the server.")
    case = Case(id=uuid.uuid4().hex[:10], symbol=symbol, model=container.llm.name)
    await container.store.save_case(case)
    await container.emit(case.id, "created", f"Hearing opened for {symbol}")
    container.spawn(container.orchestrator.run_case(case.id))
    return {"id": case.id}


@router.get("/cases/{case_id}")
async def read_case(case_id: str, request: Request) -> Case:
    case = await get_container(request).store.get_case(case_id)
    if case is None:
        raise HTTPException(404, "No hearing exists with that id.")
    return case


@router.post("/cases/{case_id}/crossexam", status_code=202)
async def create_crossexam(case_id: str, body: NewCrossExam, request: Request) -> CrossExam:
    container = get_container(request)
    if container.orchestrator is None:
        raise HTTPException(503, "No model is configured.")
    challenge = body.challenge.strip()
    if not 3 <= len(challenge) <= 400:
        raise HTTPException(422, "A challenge must be between 3 and 400 characters.")
    case = await container.store.get_case(case_id)
    if case is None:
        raise HTTPException(404, "No hearing exists with that id.")
    if case.status != "complete":
        raise HTTPException(409, "The hearing must finish before it can be cross-examined.")
    if any(exam.status == "running" for exam in case.crossexams):
        raise HTTPException(409, "Another cross-examination is still running.")
    if len(case.crossexams) >= container.settings.max_crossexams_per_case:
        raise HTTPException(429, "This hearing has reached its cross-examination limit.")
    exam = CrossExam(id=uuid.uuid4().hex[:8], challenge=challenge)
    case.crossexams.append(exam)
    await container.store.save_case(case)
    await container.emit(case.id, "challenge", f"Challenge: {challenge}")
    container.spawn(container.orchestrator.run_crossexam(case.id, exam.id))
    return exam


@router.get("/board")
async def read_board(request: Request) -> list[BoardItem]:
    return await get_container(request).store.board()
