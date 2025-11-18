"""
Pytest configuration and fixtures for AWS AgentCore tests
"""

import pytest


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
