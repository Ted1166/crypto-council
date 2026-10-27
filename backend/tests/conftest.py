import pytest

from tests.support.mcp_server import run_server


@pytest.fixture(scope="session")
def mcp_url():
    with run_server() as url:
        yield url


@pytest.fixture(scope="session")
def bare_mcp_url():
    with run_server(include_safety=False) as url:
        yield url
