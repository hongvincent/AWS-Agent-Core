"""
Pytest configuration and fixtures for AWS AgentCore tests
"""

import pytest
import sys
from datetime import datetime


def pytest_configure(config):
    """Configure pytest with custom settings"""
    config.addinivalue_line(
        "markers", "service_tests: tests that require external services running"
    )


@pytest.fixture(scope="session")
def aws_region():
    """AWS region for tests"""
    return "ap-northeast-2"


@pytest.fixture(scope="function")
def mock_session_id():
    """Generate mock session ID"""
    return "test_session_123"


@pytest.fixture(scope="function")
def mock_user_id():
    """Generate mock user ID"""
    return "test_user_123"


def pytest_collection_modifyitems(config, items):
    """Modify test collection"""
    # Auto-mark slow tests
    for item in items:
        if "long_running" in item.nodeid or "full_duration" in item.nodeid:
            item.add_marker(pytest.mark.slow)


def pytest_sessionstart(session):
    """Compatibility shim for older test code expecting pytest.config.

    pytest 7+ deprecated and pytest 9 removed the global `pytest.config`.
    Some tests in this repo reference `pytest.config.getoption(...)`.
    This hook reintroduces a compatible attribute pointing to session.config.
    """
    if not hasattr(pytest, "config"):
        pytest.config = session.config


def pytest_addoption(parser):
    """Global CLI options for learning/teaching mode"""
    parser.addoption(
        "--teach",
        action="store_true",
        default=False,
        help="Show step-by-step learning logs (fixtures, docstrings, outcomes)",
    )


def _teach_enabled(config) -> bool:
    try:
        return bool(config.getoption("--teach"))
    except Exception:
        return False


def pytest_runtest_setup(item):
    """Print setup context when teach mode is enabled"""
    if _teach_enabled(item.config):
        doc = getattr(getattr(item, "function", None), "__doc__", None)
        doc_line = (doc or "").strip().splitlines()[0] if doc else ""
        fixtures = ", ".join(item.fixturenames) if getattr(item, "fixturenames", None) else "-"
        print(f"[TEACH] ▶ Setup: {item.nodeid}")
        if doc_line:
            print(f"[TEACH]    Doc: {doc_line}")
        print(f"[TEACH]    Fixtures: {fixtures}")


def pytest_runtest_call(item):
    """Indicate test call start in teach mode"""
    if _teach_enabled(item.config):
        print(f"[TEACH] ▶ Call:   {item.name} at {datetime.now().isoformat(timespec='seconds')}")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Report test outcome in teach mode"""
    outcome = yield
    rep = outcome.get_result()
    if _teach_enabled(item.config) and rep.when == "call":
        status = "PASSED" if rep.passed else ("SKIPPED" if rep.skipped else "FAILED")
        dur_ms = int(rep.duration * 1000)
        print(f"[TEACH] ▶ Result: {status} ({dur_ms} ms) :: {item.nodeid}")
    return rep
