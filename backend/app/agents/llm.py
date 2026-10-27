import asyncio
import json
import re
from typing import Any, Protocol

import httpx

from app.config import Settings


class LLMError(Exception):
    pass


class LLM(Protocol):
    name: str

    async def complete(self, system: str, user: str) -> str: ...

    async def aclose(self) -> None: ...


def extract_json(text: str) -> dict[str, Any]:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.IGNORECASE)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end <= start:
        raise LLMError("the reply did not contain a JSON object")
    try:
        parsed = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError as exc:
        raise LLMError(f"the reply was not valid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise LLMError("the reply was JSON but not an object")
    return parsed


async def _post(
    client: httpx.AsyncClient, url: str, headers: dict[str, str], body: dict[str, Any], attempts: int = 3
) -> dict[str, Any]:
    last = "no response"
    for attempt in range(attempts):
        try:
            response = await client.post(url, headers=headers, json=body)
        except httpx.HTTPError as exc:
            last = f"{type(exc).__name__}: {exc}"
        else:
            if response.status_code == 200:
                try:
                    return response.json()
                except ValueError as exc:
                    raise LLMError("the model API returned a body that was not JSON") from exc
            last = f"HTTP {response.status_code}: {response.text[:300]}"
            if response.status_code not in (408, 429) and response.status_code < 500:
                raise LLMError(last)
        if attempt < attempts - 1:
            await asyncio.sleep(1.0 * 2**attempt)
    raise LLMError(last)


class AnthropicLLM:
    def __init__(self, settings: Settings) -> None:
        self.name = f"anthropic:{settings.llm_model}"
        self._model = settings.llm_model
        self._max_tokens = settings.llm_max_tokens
        self._url = (settings.llm_base_url or "https://api.anthropic.com").rstrip("/") + "/v1/messages"
        self._headers = {
            "x-api-key": settings.llm_api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        self._client = httpx.AsyncClient(timeout=settings.llm_timeout_seconds)

    async def complete(self, system: str, user: str) -> str:
        body = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        data = await _post(self._client, self._url, self._headers, body)
        text = "".join(
            block.get("text", "") for block in data.get("content", []) if block.get("type") == "text"
        ).strip()
        if not text:
            raise LLMError("the model returned no text")
        return text

    async def aclose(self) -> None:
        await self._client.aclose()


class OpenAICompatibleLLM:
    def __init__(self, settings: Settings) -> None:
        self.name = f"{settings.llm_provider}:{settings.llm_model}"
        self._model = settings.llm_model
        self._max_tokens = settings.llm_max_tokens
        base = (settings.llm_base_url or "https://api.openai.com/v1").rstrip("/")
        self._url = f"{base}/chat/completions"
        self._headers = {
            "Authorization": f"Bearer {settings.llm_api_key}",
            "content-type": "application/json",
        }
        self._client = httpx.AsyncClient(timeout=settings.llm_timeout_seconds)

    async def complete(self, system: str, user: str) -> str:
        body = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        data = await _post(self._client, self._url, self._headers, body)
        try:
            text = (data["choices"][0]["message"]["content"] or "").strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError("the model API returned an unexpected shape") from exc
        if not text:
            raise LLMError("the model returned no text")
        return text

    async def aclose(self) -> None:
        await self._client.aclose()


def build_llm(settings: Settings) -> LLM | None:
    if not settings.llm_configured:
        return None
    if settings.llm_provider.lower() == "anthropic":
        return AnthropicLLM(settings)
    return OpenAICompatibleLLM(settings)
