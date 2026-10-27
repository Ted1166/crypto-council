from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.agents.llm import LLM, LLMError, extract_json

T = TypeVar("T", bound=BaseModel)


async def ask(llm: LLM, system: str, user: str, model: type[T], attempts: int = 2) -> T:
    prompt = user
    last: Exception | None = None
    for _ in range(attempts):
        raw = await llm.complete(system, prompt)
        try:
            return model.model_validate(extract_json(raw))
        except (LLMError, ValidationError) as exc:
            last = exc
            prompt = (
                f"{user}\n\nYour previous reply could not be used: {str(exc)[:400]}\n"
                "Reply again with only the JSON object."
            )
    raise LLMError(f"the model did not return usable JSON: {last}")
