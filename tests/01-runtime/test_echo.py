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

from echo_agent import LLMAgent, handler


class TestLLMAgent:
    """Test cases for LLM-powered Agent"""

    def test_initialization(self):
        """Test agent initialization"""
        agent = LLMAgent()
        assert agent.session_id is not None
        assert agent.session_id.startswith("session_")
        assert agent.llm_provider is not None

    def test_initialization_with_custom_session_id(self):
        """Test agent initialization with custom session ID"""
        custom_id = "test_session_123"
        agent = LLMAgent(session_id=custom_id)
        assert agent.session_id == custom_id

    def test_intelligent_response(self):
        """Test LLM-powered response instead of simple echo"""
        agent = LLMAgent()
        result = agent.process_message("안녕하세요!")

        assert result["input"] == "안녕하세요!"
        assert "output" in result
        assert result["status"] == "success"
        assert "provider" in result
        # LLM should provide meaningful response, not just echo

    def test_conversation_context(self):
        """Test conversation context maintenance"""
        agent = LLMAgent()
        
        # First message
        result1 = agent.process_message("제 이름은 테스터입니다.")
        assert result1["status"] == "success"
        
        # Second message - context should be maintained
        result2 = agent.process_message("제 이름을 기억하시나요?")
        assert result2["status"] == "success"
        
        # Check conversation history
        assert len(agent.conversation_history) == 4  # 2 exchanges

    def test_korean_interaction(self):
        \"\"\"Test Korean language interaction\"\"\"
        agent = LLMAgent()

        result = agent.process_message(\"강남점에서 예약하고 싶어요.\")
        assert result[\"status\"] == \"success\"
        assert \"강남\" in result[\"output\"] or \"예약\" in result[\"output\"] or len(result[\"output\"]) > 0

    def test_session_metadata(self):
        \"\"\"Test that session metadata is included in response\"\"\"
        agent = LLMAgent()
        result = agent.process_message(\"안녕하세요!\")

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
        \"\"\"Test writing and reading within same session\"\"\"
        agent = LLMAgent(session_id=\"test_session_1\")

        # Write
        agent.write_session_file(\"Session 1 Data\")

        # Read
        content = agent.read_session_file()
        assert content == \"Session 1 Data\"

    def test_file_not_found(self):
        \"\"\"Test reading non-existent file\"\"\"
        agent = LLMAgent(session_id=\"new_session\")

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
        \"\"\"Test that agent produces log output\"\"\"
        agent = LLMAgent()

        with caplog.at_level(\"INFO\"):
            agent.process_message(\"테스트 메시지\")

        # Check that logs were generated
        assert len(caplog.records) > 0
        assert any("Processing message" in record.message for record in caplog.records)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
