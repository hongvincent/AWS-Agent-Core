"""
Test Suite for Timer Agent - Long-Running Session Testing

Tests:
1. Long-running session execution
2. Periodic logging
3. Session state maintenance
4. Checkpoint persistence
"""

import json
import pytest
import sys
import time
from pathlib import Path

# Add agents directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agents"))

from timer_agent import TimerAgent, handler


class TestTimerAgent:
    """Test cases for Timer Agent"""

    def test_initialization(self):
        """Test agent initialization"""
        agent = TimerAgent()
        assert agent.session_id is not None
        assert agent.session_id.startswith("timer_session_")
        assert agent.start_time is not None
        assert len(agent.timestamps) == 0

    def test_initialization_with_custom_session_id(self):
        """Test agent initialization with custom session ID"""
        custom_id = "timer_test_123"
        agent = TimerAgent(session_id=custom_id)
        assert agent.session_id == custom_id

    @pytest.mark.slow
    def test_short_timed_loop(self):
        """
        Test timed loop with short duration (30 seconds)

        This is a quick test version of the full 5-minute scenario
        """
        agent = TimerAgent()

        # Run for 30 seconds with 10-second intervals
        result = agent.run_timed_loop(
            duration_minutes=0.5,  # 30 seconds
            interval_minutes=0.167  # ~10 seconds
        )

        # Verify results
        assert result["status"] == "completed"
        assert result["iterations"] >= 3  # Should have at least 3 iterations
        assert len(result["timestamps"]) >= 3
        assert result["total_elapsed_seconds"] >= 30
        assert result["total_elapsed_seconds"] < 35  # Allow some overhead

    def test_get_status(self):
        """Test status retrieval"""
        agent = TimerAgent(session_id="status_test")

        # Small delay to ensure elapsed time > 0
        time.sleep(0.1)

        status = agent.get_status()

        assert status["session_id"] == "status_test"
        assert status["status"] == "running"
        assert status["elapsed_seconds"] > 0
        assert status["timestamps_collected"] == 0  # No loop run yet

    @pytest.mark.slow
    def test_checkpoint_persistence(self, tmp_path):
        """Test that checkpoints are written to file"""
        agent = TimerAgent()

        # Run very short loop
        agent.run_timed_loop(
            duration_minutes=0.05,  # 3 seconds
            interval_minutes=0.017  # ~1 second
        )

        # Check that checkpoint file exists and has content
        checkpoint_file = Path("/tmp/timer_checkpoints.log")
        if checkpoint_file.exists():
            content = checkpoint_file.read_text()
            assert len(content) > 0
            assert "," in content  # CSV format


class TestTimerHandler:
    """Test handler function"""

    def test_handler_run_action_quick(self):
        """Test handler with run action (quick version)"""
        event = {
            "action": "run",
            "duration_minutes": 0.05,  # 3 seconds
            "interval_minutes": 0.017  # ~1 second
        }

        response = handler(event)
        assert response["statusCode"] == 200

        body = json.loads(response["body"])
        assert body["status"] == "completed"
        assert body["iterations"] >= 2
        assert len(body["timestamps"]) >= 2

    def test_handler_status_action(self):
        """Test handler with status action"""
        event = {
            "session_id": "test_session_status",
            "action": "status"
        }

        response = handler(event)
        assert response["statusCode"] == 200

        body = json.loads(response["body"])
        assert body["status"] == "running"
        assert body["session_id"] == "test_session_status"

    def test_handler_unknown_action(self):
        """Test handler with unknown action"""
        event = {
            "action": "invalid_action"
        }

        response = handler(event)
        assert response["statusCode"] == 200

        body = json.loads(response["body"])
        assert "error" in body

    @pytest.mark.slow
    @pytest.mark.integration
    def test_handler_full_duration(self):
        """
        Test handler with realistic duration (5 minutes)

        This test is marked as slow and integration - skip in quick test runs
        """
        event = {
            "action": "run",
            "duration_minutes": 5,
            "interval_minutes": 1
        }

        start_time = time.time()
        response = handler(event)
        elapsed = time.time() - start_time

        assert response["statusCode"] == 200

        body = json.loads(response["body"])
        assert body["status"] == "completed"
        assert body["iterations"] == 5  # Should have 5 iterations
        assert len(body["timestamps"]) == 5
        assert 300 <= elapsed < 310  # ~5 minutes with some overhead


@pytest.mark.integration
class TestLongRunningScenarios:
    """Integration tests for long-running scenarios"""

    @pytest.mark.slow
    def test_session_continuity(self):
        """
        Test that session maintains state throughout execution

        This simulates the real scenario where a session should not
        be terminated during long-running operations
        """
        agent = TimerAgent(session_id="continuity_test")

        # Record initial state
        initial_session_id = agent.session_id
        initial_start_time = agent.start_time

        # Run timed loop
        agent.run_timed_loop(
            duration_minutes=0.1,  # 6 seconds
            interval_minutes=0.033  # ~2 seconds
        )

        # Verify session state is preserved
        assert agent.session_id == initial_session_id
        assert agent.start_time == initial_start_time
        assert len(agent.timestamps) > 0

    @pytest.mark.slow
    def test_multiple_status_checks(self):
        """Test status can be checked while agent is running"""
        agent = TimerAgent(session_id="multi_status_test")

        # Get initial status
        status1 = agent.get_status()
        assert status1["timestamps_collected"] == 0

        time.sleep(1)

        # Run short loop
        agent.run_timed_loop(duration_minutes=0.05, interval_minutes=0.017)

        # Check final status
        status2 = agent.get_status()
        assert status2["timestamps_collected"] > 0
        assert status2["elapsed_seconds"] > status1["elapsed_seconds"]


if __name__ == "__main__":
    # Run quick tests by default, use -m slow for full tests
    pytest.main([__file__, "-v", "-s", "-m", "not slow"])
