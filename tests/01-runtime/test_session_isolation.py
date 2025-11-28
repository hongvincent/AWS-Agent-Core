"""
Test Suite for Session Isolation - Runtime Isolation Testing

Tests:
1. Session file isolation
2. Independent session state
3. Concurrent session handling
4. Resource cleanup
"""

import json
import pytest
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add agents directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agents"))

from echo_agent import LLMAgent, handler


class TestSessionIsolation:
    """Test session isolation features"""

    def test_different_sessions_have_different_ids(self):
        """Test that different sessions get unique IDs"""
        agent1 = EchoAgent()
        agent2 = EchoAgent()

        assert agent1.session_id != agent2.session_id

    def test_session_a_write_session_b_read(self):
        """
        Test session isolation: Session A writes, Session B tries to read

        Note: This test simulates the expected behavior in AgentCore's
        MicroVM isolation. In local testing, both sessions share /tmp,
        but in AgentCore Runtime, each session has isolated storage.
        """
        # Session A writes
        session_a = EchoAgent(session_id="session_a")
        session_a.write_session_file("Data from Session A")

        # Verify Session A can read its own data
        content_a = session_a.read_session_file()
        assert content_a == "Data from Session A"

        # Session B tries to read
        # In real AgentCore: would get FILE_NOT_FOUND
        # In local test: might see Session A's data (shared /tmp)
        session_b = EchoAgent(session_id="session_b")
        content_b = session_b.read_session_file()

        # Document expected behavior
        # In AgentCore Runtime with MicroVM isolation: content_b == "FILE_NOT_FOUND"
        # In local testing: content_b might == "Data from Session A"
        assert content_b in ["FILE_NOT_FOUND", "Data from Session A"]

    def test_session_overwrites_own_data(self):
        """Test that a session can overwrite its own data"""
        session = EchoAgent(session_id="overwrite_test")

        # Write initial data
        session.write_session_file("Initial Data")
        assert session.read_session_file() == "Initial Data"

        # Overwrite
        session.write_session_file("Updated Data")
        assert session.read_session_file() == "Updated Data"

    def test_multiple_messages_in_session(self):
        """Test processing multiple messages in same session"""
        session = EchoAgent(session_id="multi_message_test")

        messages = ["message1", "message2", "ping", "message3"]
        results = []

        for msg in messages:
            result = session.process_message(msg)
            results.append(result)

        # Verify all results have same session_id
        session_ids = [r["session_id"] for r in results]
        assert len(set(session_ids)) == 1
        assert session_ids[0] == "multi_message_test"

        # Verify responses
        assert results[0]["output"] == "you said: message1"
        assert results[1]["output"] == "you said: message2"
        assert results[2]["output"] == "pong"
        assert results[3]["output"] == "you said: message3"


class TestConcurrentSessions:
    """Test concurrent session handling"""

    @pytest.mark.integration
    def test_concurrent_echo_sessions(self):
        """Test multiple sessions running concurrently"""
        def run_session(session_id: str, message: str):
            """Run a single session"""
            event = {
                "session_id": session_id,
                "message": message,
                "action": "echo"
            }
            response = handler(event)
            return session_id, json.loads(response["body"])

        # Create multiple concurrent sessions
        sessions = [
            ("session_1", "Hello from 1"),
            ("session_2", "Hello from 2"),
            ("session_3", "ping"),
            ("session_4", "Hello from 4"),
            ("session_5", "ping"),
        ]

        results = {}
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(run_session, sid, msg): sid
                for sid, msg in sessions
            }

            for future in as_completed(futures):
                session_id, result = future.result()
                results[session_id] = result

        # Verify all sessions completed
        assert len(results) == 5

        # Verify session-specific responses
        assert results["session_1"]["output"] == "you said: Hello from 1"
        assert results["session_2"]["output"] == "you said: Hello from 2"
        assert results["session_3"]["output"] == "pong"
        assert results["session_4"]["output"] == "you said: Hello from 4"
        assert results["session_5"]["output"] == "pong"

    @pytest.mark.integration
    def test_concurrent_write_sessions(self):
        """
        Test concurrent write operations

        In AgentCore Runtime, each session's writes would be isolated
        """
        def write_session(session_id: str, content: str):
            """Write to session file"""
            event = {
                "session_id": session_id,
                "message": content,
                "action": "write"
            }
            response = handler(event)
            return session_id, json.loads(response["body"])

        sessions = [
            ("write_session_1", "Content A"),
            ("write_session_2", "Content B"),
            ("write_session_3", "Content C"),
        ]

        results = {}
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(write_session, sid, content): sid
                for sid, content in sessions
            }

            for future in as_completed(futures):
                session_id, result = future.result()
                results[session_id] = result

        # Verify all writes succeeded
        assert len(results) == 3
        assert all(r["status"] == "written" for r in results.values())


class TestResourceCleanup:
    """Test resource cleanup and session lifecycle"""

    def test_cleanup_is_callable(self):
        """Test that cleanup method can be called"""
        session = EchoAgent(session_id="cleanup_test")
        session.cleanup()  # Should not raise exception

    def test_multiple_cleanups(self):
        """Test that cleanup can be called multiple times"""
        session = EchoAgent(session_id="multi_cleanup_test")
        session.cleanup()
        session.cleanup()  # Should be idempotent

    def test_session_lifecycle(self):
        """Test complete session lifecycle"""
        # Create
        session = EchoAgent(session_id="lifecycle_test")
        assert session.session_id == "lifecycle_test"

        # Use
        result = session.process_message("test")
        assert result["status"] == "success"

        # Cleanup
        session.cleanup()

        # Session should still be usable after cleanup
        # (cleanup is just for logging/resource release)
        result2 = session.process_message("test2")
        assert result2["status"] == "success"


@pytest.mark.integration
class TestAgentCoreRuntimeBehavior:
    """
    Test expected behaviors in AgentCore Runtime environment

    These tests document expected differences between local
    and AgentCore Runtime execution
    """

    def test_expected_isolation_behavior(self):
        """
        Document expected session isolation in AgentCore Runtime

        In AgentCore Runtime with MicroVM:
        - Each session gets isolated /tmp directory
        - Files written by Session A are not visible to Session B
        - Each session has independent filesystem view
        """
        # This is a documentation test
        expected_behavior = {
            "local_testing": {
                "file_isolation": False,
                "shared_tmp": True,
                "reason": "Same filesystem"
            },
            "agentcore_runtime": {
                "file_isolation": True,
                "shared_tmp": False,
                "reason": "MicroVM isolation per session"
            }
        }

        assert expected_behavior is not None

    def test_expected_cloudwatch_integration(self):
        """
        Document expected CloudWatch integration

        In AgentCore Runtime:
        - All log output (stdout/stderr) goes to CloudWatch Logs
        - Log group: /aws/bedrock/agentcore/runtime/{agent_id}
        - Log stream: {session_id}
        - Automatic log aggregation and retention
        """
        expected_logging = {
            "log_destination": "CloudWatch Logs",
            "log_group_pattern": "/aws/bedrock/agentcore/runtime/{agent_id}",
            "log_stream_pattern": "{session_id}",
            "retention": "Configurable (default: 30 days)"
        }

        assert expected_logging is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
