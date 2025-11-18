"""
Test Suite for Short-Term Memory - Session Context

Tests:
1. Conversation history tracking
2. Context extraction
3. Name/preference recall within session
4. Turn management
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agents"))

from memory_manager import ShortTermMemory, MemoryManager


class TestShortTermMemory:
    """Test short-term memory functionality"""

    def test_initialization(self):
        """Test memory initialization"""
        memory = ShortTermMemory("test_session")
        assert memory.session_id == "test_session"
        assert len(memory.conversation_history) == 0
        assert len(memory.context) == 0

    def test_add_turn(self):
        """Test adding conversation turn"""
        memory = ShortTermMemory("test_session")

        memory.add_turn("Hello", "Hi there!")
        assert len(memory.conversation_history) == 1

        turn = memory.conversation_history[0]
        assert turn["user"] == "Hello"
        assert turn["agent"] == "Hi there!"
        assert "timestamp" in turn

    def test_multiple_turns(self):
        """Test multiple conversation turns"""
        memory = ShortTermMemory("test_session")

        for i in range(10):
            memory.add_turn(f"Message {i}", f"Response {i}")

        assert len(memory.conversation_history) == 10

    def test_max_turns_limit(self):
        """Test that memory respects max turns limit"""
        memory = ShortTermMemory("test_session", max_turns=5)

        # Add more than max
        for i in range(10):
            memory.add_turn(f"Message {i}", f"Response {i}")

        # Should only keep last 5
        assert len(memory.conversation_history) == 5
        assert memory.conversation_history[0]["user"] == "Message 5"

    def test_get_recent_context(self):
        """Test retrieving recent context"""
        memory = ShortTermMemory("test_session")

        for i in range(10):
            memory.add_turn(f"Message {i}", f"Response {i}")

        recent = memory.get_recent_context(num_turns=3)
        assert len(recent) == 3
        assert recent[0]["user"] == "Message 7"
        assert recent[2]["user"] == "Message 9"

    def test_extract_information(self):
        """Test extracting contextual information"""
        memory = ShortTermMemory("test_session")

        memory.extract_information("user_name", "성민")
        memory.extract_information("preferred_branch", "강남")

        assert memory.get_context("user_name") == "성민"
        assert memory.get_context("preferred_branch") == "강남"

    def test_get_all_context(self):
        """Test retrieving all context"""
        memory = ShortTermMemory("test_session")

        memory.extract_information("key1", "value1")
        memory.extract_information("key2", "value2")

        context = memory.get_all_context()
        assert len(context) == 2
        assert context["key1"] == "value1"
        assert context["key2"] == "value2"


class TestShortTermMemoryScenarios:
    """Test real-world scenarios"""

    def test_scenario_name_recall(self):
        """
        Scenario: 단기 메모리 - 이름 기억

        ① "내 이름은 성민이야."
        ② "내 이름이 뭐였지?"

        Expected: ②에서 "성민" 정보 조회 가능
        """
        manager = MemoryManager()

        # Turn 1: User introduces name
        manager.process_turn(
            "session_1", "user_1",
            "내 이름은 성민이야.",
            "안녕하세요, 성민님!"
        )

        # Verify name extracted
        session_memory = manager.get_session_memory("session_1")
        user_name = session_memory.get_context("user_name")
        assert user_name == "성민"

        # Turn 2: User asks about name
        manager.process_turn(
            "session_1", "user_1",
            "내 이름이 뭐였지?",
            "성민님이라고 하셨습니다."
        )

        # Name should still be in context
        assert session_memory.get_context("user_name") == "성민"

    def test_scenario_context_persistence(self):
        """Test that context persists throughout session"""
        memory = ShortTermMemory("test_session")

        # Set context early
        memory.extract_information("topic", "appointment")
        memory.add_turn("예약하고 싶어요", "어느 지점에 예약하시겠어요?")

        # Add more turns
        memory.add_turn("강남점이요", "강남점 예약 가능 시간을 확인하겠습니다")
        memory.add_turn("토요일 오후", "토요일 오후 2시는 어떠세요?")

        # Context should still exist
        assert memory.get_context("topic") == "appointment"
        assert len(memory.conversation_history) == 3

    def test_scenario_summary_generation(self):
        """Test conversation summary generation"""
        memory = ShortTermMemory("test_session")

        memory.add_turn("내 이름은 성민이야", "안녕하세요 성민님")
        memory.extract_information("user_name", "성민")

        memory.add_turn("강남점에 예약하고 싶어", "강남점 예약 진행하겠습니다")
        memory.extract_information("preferred_branch", "강남")

        summary = memory.summarize()

        assert summary["session_id"] == "test_session"
        assert summary["total_turns"] == 2
        assert "user_name" in summary["context"]
        assert "preferred_branch" in summary["context"]


@pytest.mark.integration
class TestMemoryManagerShortTerm:
    """Test MemoryManager's short-term functionality"""

    def test_session_memory_creation(self):
        """Test automatic session memory creation"""
        manager = MemoryManager()

        memory = manager.get_session_memory("new_session")
        assert memory is not None
        assert memory.session_id == "new_session"

        # Getting again should return same instance
        memory2 = manager.get_session_memory("new_session")
        assert memory is memory2

    def test_multiple_sessions(self):
        """Test managing multiple sessions"""
        manager = MemoryManager()

        manager.process_turn("session_1", "user_1", "Hello from 1", "Response 1")
        manager.process_turn("session_2", "user_2", "Hello from 2", "Response 2")

        memory1 = manager.get_session_memory("session_1")
        memory2 = manager.get_session_memory("session_2")

        assert len(memory1.conversation_history) == 1
        assert len(memory2.conversation_history) == 1
        assert memory1.conversation_history[0]["user"] == "Hello from 1"
        assert memory2.conversation_history[0]["user"] == "Hello from 2"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
