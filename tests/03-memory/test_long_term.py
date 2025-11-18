"""
Test Suite for Long-Term Memory - User Profiles and Preferences

Tests:
1. User profile storage
2. Preference persistence across sessions
3. Session history tracking
4. Preference extraction from conversations
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agents"))

from memory_manager import LongTermMemory, MemoryManager


class TestLongTermMemory:
    """Test long-term memory functionality"""

    def test_initialization(self):
        """Test memory initialization"""
        memory = LongTermMemory()
        assert len(memory.user_profiles) == 0
        assert len(memory.user_sessions) == 0

    def test_save_user_preference(self):
        """Test saving user preference"""
        memory = LongTermMemory()

        memory.save_user_preference("user_1", "preferred_branch", "강남")

        pref = memory.get_user_preference("user_1", "preferred_branch")
        assert pref == "강남"

    def test_multiple_preferences(self):
        """Test saving multiple preferences"""
        memory = LongTermMemory()

        memory.save_user_preference("user_1", "name", "성민")
        memory.save_user_preference("user_1", "preferred_branch", "강남")
        memory.save_user_preference("user_1", "preferred_time", "오후")

        assert memory.get_user_preference("user_1", "name") == "성민"
        assert memory.get_user_preference("user_1", "preferred_branch") == "강남"
        assert memory.get_user_preference("user_1", "preferred_time") == "오후"

    def test_get_user_profile(self):
        """Test retrieving complete user profile"""
        memory = LongTermMemory()

        memory.save_user_preference("user_1", "name", "성민")
        memory.save_user_preference("user_1", "preferred_branch", "강남")

        profile = memory.get_user_profile("user_1")

        assert "created_at" in profile
        assert "preferences" in profile
        assert "name" in profile["preferences"]
        assert "preferred_branch" in profile["preferences"]

    def test_nonexistent_user(self):
        """Test retrieving profile for nonexistent user"""
        memory = LongTermMemory()

        pref = memory.get_user_preference("nonexistent", "name")
        assert pref is None

        profile = memory.get_user_profile("nonexistent")
        assert profile == {}

    def test_record_session(self):
        """Test recording session summary"""
        memory = LongTermMemory()

        summary = {
            "total_turns": 5,
            "context": {"user_name": "성민"},
            "topics": ["appointment"]
        }

        memory.record_session("user_1", "session_1", summary)

        sessions = memory.get_user_sessions("user_1")
        assert len(sessions) == 1
        assert sessions[0]["session_id"] == "session_1"
        assert sessions[0]["summary"]["total_turns"] == 5

    def test_multiple_sessions(self):
        """Test recording multiple sessions"""
        memory = LongTermMemory()

        for i in range(5):
            memory.record_session(
                "user_1",
                f"session_{i}",
                {"total_turns": i}
            )

        sessions = memory.get_user_sessions("user_1")
        assert len(sessions) == 5

    def test_session_limit(self):
        """Test session retrieval limit"""
        memory = LongTermMemory()

        # Record 20 sessions
        for i in range(20):
            memory.record_session(
                "user_1",
                f"session_{i}",
                {"total_turns": i}
            )

        # Get only last 5
        sessions = memory.get_user_sessions("user_1", limit=5)
        assert len(sessions) == 5
        assert sessions[0]["session_id"] == "session_15"


class TestLongTermMemoryScenarios:
    """Test real-world scenarios"""

    def test_scenario_preference_persistence(self):
        """
        Scenario: 장기 메모리 - 선호도 유지

        Session 1: "나는 주로 강남점에 방문해. 다음에도 강남점이 기본이었으면 좋겠어."
        Session 2: "다음주 진료 예약 도와줘."

        Expected: Session 2에서 강남점 선호도 기억
        """
        manager = MemoryManager()

        # Session 1
        manager.process_turn(
            "session_1", "user_123",
            "나는 주로 강남점에 방문해. 다음에 예약할 때도 강남점이 기본이었으면 좋겠어.",
            "네, 강남점을 선호하시는 것으로 기억하겠습니다."
        )

        manager.end_session("session_1", "user_123")

        # Verify preference saved
        preferred_branch = manager.long_term_memory.get_user_preference("user_123", "preferred_branch")
        assert preferred_branch == "강남"

        # Session 2 (different session, same user)
        user_context = manager.get_user_context("user_123")
        assert "profile" in user_context
        assert user_context["profile"]["preferences"]["preferred_branch"]["value"] == "강남"

        # Agent can now use this preference
        manager.process_turn(
            "session_2", "user_123",
            "다음주 진료 예약 도와줘.",
            f"강남점으로 예약을 진행하시겠어요? (선호 지점: 강남)"
        )

    def test_scenario_multiple_users(self):
        """Test preferences for multiple users don't interfere"""
        manager = MemoryManager()

        # User 1 prefers 강남
        manager.process_turn(
            "session_1", "user_1",
            "강남점이 좋아요",
            "강남점 선호도를 기억하겠습니다"
        )

        # User 2 prefers 부산
        manager.process_turn(
            "session_2", "user_2",
            "부산점으로 해주세요",
            "부산점 선호도를 기억하겠습니다"
        )

        # Verify separate preferences
        user1_pref = manager.long_term_memory.get_user_preference("user_1", "preferred_branch")
        user2_pref = manager.long_term_memory.get_user_preference("user_2", "preferred_branch")

        assert user1_pref == "강남"
        assert user2_pref == "부산"

    def test_scenario_preference_update(self):
        """Test that preferences can be updated"""
        memory = LongTermMemory()

        # Initial preference
        memory.save_user_preference("user_1", "preferred_branch", "강남")
        assert memory.get_user_preference("user_1", "preferred_branch") == "강남"

        # Update preference
        memory.save_user_preference("user_1", "preferred_branch", "부산")
        assert memory.get_user_preference("user_1", "preferred_branch") == "부산"


@pytest.mark.integration
class TestMemoryManagerLongTerm:
    """Test MemoryManager's long-term functionality"""

    def test_end_session_stores_summary(self):
        """Test that ending session stores summary in long-term"""
        manager = MemoryManager()

        manager.process_turn(
            "session_1", "user_1",
            "내 이름은 테스트야",
            "안녕하세요 테스트님"
        )

        manager.end_session("session_1", "user_1")

        # Verify session recorded
        sessions = manager.long_term_memory.get_user_sessions("user_1")
        assert len(sessions) == 1
        assert sessions[0]["session_id"] == "session_1"

    def test_preferences_extracted_from_session(self):
        """Test automatic preference extraction"""
        manager = MemoryManager()

        # Session with preference info
        manager.process_turn(
            "session_1", "user_1",
            "내 이름은 성민이야",
            "안녕하세요 성민님"
        )

        manager.end_session("session_1", "user_1")

        # Verify name extracted to long-term
        name = manager.long_term_memory.get_user_preference("user_1", "name")
        assert name == "성민"

    def test_user_context_for_new_session(self):
        """Test retrieving user context for new session"""
        manager = MemoryManager()

        # Previous session
        manager.process_turn(
            "session_1", "user_1",
            "내 이름은 성민이고 강남점을 선호해",
            "성민님, 강남점 선호 기억하겠습니다"
        )

        manager.end_session("session_1", "user_1")

        # New session - get context
        context = manager.get_user_context("user_1")

        assert "profile" in context
        assert "recent_sessions" in context
        assert len(context["recent_sessions"]) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
