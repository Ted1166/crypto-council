from functools import lru_cache
from pathlib import Path


@lru_cache
def load_prompt(name: str) -> str:
    return (Path(__file__).parent / "prompts" / f"{name}.md").read_text(encoding="utf-8")
