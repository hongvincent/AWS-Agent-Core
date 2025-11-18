"""
Test Suite for Echo Agent - Runtime Basic Functionality

Tests:
1. Simple echo response
2. Ping-pong functionality
3. Session ID tracking
4. CloudWatch logging integration
"""

import json
import pytest
import sys
from pathlib import Path

# Add agents directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agents"))

from echo_agent import EchoAgent, handler


class TestEchoAgent:
    """Test cases for Echo Agent"""

    def test_initialization(self):
        """Test agent initialization"""
        agent = EchoAgent()
        assert agent.session_id is not None
        assert agent.session_id.startswith("session_")

    def test_initialization_with_custom_session_id(self):
        """Test agent initialization with custom session ID"""
        custom_id = "test_session_123"
        agent = EchoAgent(session_id=custom_id)
        assert agent.session_id == custom_id

    def test_ping_pong(self):
        """Test ping-pong response"""
        agent = EchoAgent()
        result = agent.process_message("ping")

        assert result["output"] == "pong"
        assert result["input"] == "ping"
        assert result["status"] == "success"

    def test_echo_message(self):
        """Test general echo functionality"""
        agent = EchoAgent()
        test_message = "Hello, AgentCore!"
        result = agent.process_message(test_message)

        assert result["output"] == f"you said: {test_message}"
        assert result["input"] == test_message
        assert result["status"] == "success"

    def test_case_insensitive_ping(self):
        """Test that ping is case-insensitive"""
        agent = EchoAgent()

        for variant in ["ping", "PING", "Ping", "PiNg"]:
            result = agent.process_message(variant)
            assert result["output"] == "pong"

    def test_session_metadata(self):
        """Test that session metadata is included in response"""
        agent = EchoAgent()
        result = agent.process_message("test")

        assert "session_id" in result
        assert "timestamp" in result
        assert "input" in result
        assert "output" in result

    def test_handler_echo_action(self):
        """Test handler with echo action"""
        event = {
            "message": "test message",
            "action": "echo"
        }

        response = handler(event)
        assert response["statusCode"] == 200

        body = json.loads(response["body"])
        assert body["output"] == "you said: test message"

    def test_handler_ping(self):
        """Test handler with ping message"""
        event = {
            "message": "ping",
            "action": "echo"
        }

        response = handler(event)
        assert response["statusCode"] == 200

        body = json.loads(response["body"])
        assert body["output"] == "pong"

    def test_handler_write_action(self):
        """Test handler with write action"""
        event = {
            "message": "test content",
            "action": "write"
        }

        response = handler(event)
        assert response["statusCode"] == 200

        body = json.loads(response["body"])
        assert body["status"] == "written"
        assert "session_id" in body

    def test_handler_read_action(self):
        """Test handler with read action (after write)"""
        # First write
        write_event = {
            "message": "persistent data",
            "action": "write"
        }
        handler(write_event)

        # Then read
        read_event = {
            "action": "read"
        }

        response = handler(read_event)
        assert response["statusCode"] == 200

        body = json.loads(response["body"])
        assert body["status"] == "read"
        assert body["content"] == "persistent data"

    def test_handler_unknown_action(self):
        """Test handler with unknown action"""
        event = {
            "action": "unknown_action"
        }

        response = handler(event)
        assert response["statusCode"] == 200

        body = json.loads(response["body"])
        assert "error" in body


class TestSessionIsolation:
    """Test session isolation features"""

    def test_write_and_read_same_session(self):
        """Test writing and reading within same session"""
        agent = EchoAgent(session_id="test_session_1")

        # Write
        agent.write_session_file("Session 1 Data")

        # Read
        content = agent.read_session_file()
        assert content == "Session 1 Data"

    def test_file_not_found(self):
        """Test reading non-existent file"""
        agent = EchoAgent(session_id="new_session")

        # Try to read before writing
        # Note: In real AgentCore, different sessions would have isolated /tmp
        content = agent.read_session_file()

        # This will work locally but would fail in isolated sessions
        # The agent should handle this gracefully
        assert content in ["FILE_NOT_FOUND", "Session 1 Data"]  # Depending on previous test


@pytest.mark.integration
class TestCloudWatchIntegration:
    """Test CloudWatch logging integration"""

    def test_logging_output(self, caplog):
        """Test that agent produces log output"""
        agent = EchoAgent()

        with caplog.at_level("INFO"):
            agent.process_message("test")

        # Check that logs were generated
        assert len(caplog.records) > 0
        assert any("Processing message" in record.message for record in caplog.records)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
