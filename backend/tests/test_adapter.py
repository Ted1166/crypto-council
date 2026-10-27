import pytest

from app.ryo.adapter import ArgumentMappingError, adapt


def test_maps_symbol_to_token_input():
    schema = {"properties": {"token": {"type": "string"}}, "required": ["token"]}
    assert adapt(schema, {"symbol": "SOL"}) == {"token": "SOL"}


def test_wraps_symbol_when_input_is_an_array():
    schema = {"properties": {"tokens": {"type": "array", "items": {"type": "string"}}}, "required": ["tokens"]}
    assert adapt(schema, {"symbol": "SOL"}) == {"tokens": ["SOL"]}


def test_joins_symbols_when_input_is_a_string():
    schema = {"properties": {"symbols": {"type": "string"}}, "required": ["symbols"]}
    assert adapt(schema, {"symbols": ["SOL", "ETH"]}) == {"symbols": "SOL,ETH"}


def test_keeps_list_for_array_input_inside_anyof():
    schema = {"properties": {"symbols": {"anyOf": [{"type": "array"}, {"type": "null"}]}}}
    assert adapt(schema, {"symbols": ["SOL", "ETH"]}) == {"symbols": ["SOL", "ETH"]}


def test_missing_required_input_raises():
    schema = {"properties": {"mode": {"type": "string"}}, "required": ["mode"]}
    with pytest.raises(ArgumentMappingError):
        adapt(schema, {})


def test_unknown_required_symbol_input_raises():
    schema = {"properties": {"foo": {"type": "string"}}, "required": []}
    with pytest.raises(ArgumentMappingError):
        adapt(schema, {"symbol": "SOL"})


def test_optional_inputs_are_skipped_when_absent():
    schema = {"properties": {"theme": {"type": "string"}}}
    assert adapt(schema, {"theme": "ai", "limit": 5}, optional={"theme", "limit"}) == {"theme": "ai"}


def test_query_is_not_reused_for_two_canonical_keys():
    schema = {"properties": {"query": {"type": "string"}}}
    with pytest.raises(ArgumentMappingError):
        adapt(schema, {"symbol": "SOL", "theme": "ai"})


def test_limit_is_cast_to_integer():
    schema = {"properties": {"limit": {"type": "integer"}}}
    assert adapt(schema, {"limit": "7"}) == {"limit": 7}
