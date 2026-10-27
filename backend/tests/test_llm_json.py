import pytest

from app.agents.llm import LLMError, extract_json


def test_plain_object():
    assert extract_json('{"a": 1}') == {"a": 1}


def test_fenced_object_with_chatter():
    assert extract_json('Here you go:\n```json\n{"a": [1, 2]}\n```') == {"a": [1, 2]}


def test_no_object_raises():
    with pytest.raises(LLMError):
        extract_json("nothing to see")


def test_broken_json_raises():
    with pytest.raises(LLMError):
        extract_json('{"a": }')
