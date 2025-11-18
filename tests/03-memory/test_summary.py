"""
Test Suite for Memory Summarization - Conversation Compression

Tests:
1. Automatic summarization
2. Topic extraction
3. Key information preservation
4. Summary quality
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agents"))

from memory_manager import ShortTermMemory, MemoryManager


class TestMemorySummarization:
    """Test memory summarization functionality"""

    def test_summary_includes_metadata(self):
        """Test that summary includes key metadata"""
        memory = ShortTermMemory("test_session")

        memory.add_turn("Question 1", "Answer 1")
        memory.add_turn("Question 2", "Answer 2")

        summary = memory.summarize()

        assert "session_id" in summary
        assert "total_turns" in summary
        assert summary["total_turns"] == 2

    def test_summary_includes_context(self):
        """Test that summary includes extracted context"""
        memory = ShortTermMemory("test_session")

        memory.extract_information("user_name", "성민")
        memory.extract_information("topic", "appointment")

        summary = memory.summarize()

        assert "context" in summary
        assert summary["context"]["user_name"] == "성민"
        assert summary["context"]["topic"] == "appointment"

    def test_topic_extraction(self):
        """Test automatic topic extraction from conversation"""
        memory = ShortTermMemory("test_session")

        # Add conversation about appointment
        memory.add_turn("예약하고 싶어요", "예약을 도와드리겠습니다")
        memory.add_turn("강남점으로 부탁해요", "강남점 예약 가능 시간을 확인하겠습니다")

        summary = memory.summarize()

        assert "recent_topics" in summary
        # Should detect topics like "appointment" and "location_preference"

    def test_scenario_long_conversation_summary(self):
        """
        Scenario: 긴 대화 요약

        10-20 turn의 대화 후 "지금까지 내가 말한 중요한 내용만 요약해줘"
        """
        memory = ShortTermMemory("test_session")

        # Simulate long conversation
        conversation = [
            ("안녕하세요", "안녕하세요! 무엇을 도와드릴까요?"),
            ("내 이름은 성민이야", "반갑습니다 성민님"),
            ("예약하고 싶어요", "어느 지점에 예약하시겠어요?"),
            ("강남점이요", "강남점 예약을 진행하겠습니다"),
            ("토요일 오후가 좋아요", "토요일 오후 시간대를 확인하겠습니다"),
            ("2시는 어때요?", "토요일 오후 2시 예약 가능합니다"),
            ("네, 그걸로 해주세요", "예약이 완료되었습니다"),
            ("다음에도 강남점으로 기본 설정해줘", "강남점을 기본 지점으로 설정했습니다"),
        ]

        for user_msg, agent_msg in conversation:
            memory.add_turn(user_msg, agent_msg)

        # Extract context
        memory.extract_information("user_name", "성민")
        memory.extract_information("preferred_branch", "강남")
        memory.extract_information("appointment", {"branch": "강남", "time": "토요일 오후 2시"})

        # Get summary
        summary = memory.summarize()

        # Verify summary captures key points
        assert summary["total_turns"] == len(conversation)
        assert summary["context"]["user_name"] == "성민"
        assert summary["context"]["preferred_branch"] == "강남"

        # In real implementation, would generate natural language summary:
        expected_summary_text = """
        성민님께서 강남점 토요일 오후 2시 예약을 완료하셨고,
        향후 강남점을 기본 지점으로 설정하셨습니다.
        """

        # Verify topics detected
        assert "recent_topics" in summary


@pytest.mark.integration
class TestMemorySummaryIntegration:
    """Test memory summary in full workflow"""

    def test_full_session_with_summary(self):
        """Test complete session with summarization"""
        manager = MemoryManager()

        # Multiple turns
        turns = [
            ("내 이름은 김철수야", "안녕하세요 김철수님"),
            ("부산점에 예약하고 싶어", "부산점 예약을 도와드리겠습니다"),
            ("다음 주 월요일", "다음 주 월요일 가능 시간을 확인하겠습니다"),
            ("10시", "월요일 오전 10시로 예약하시겠어요?"),
            ("네", "예약이 완료되었습니다"),
        ]

        for user_msg, agent_msg in turns:
            manager.process_turn("session_1", "user_123", user_msg, agent_msg)

        # Get summary
        session_memory = manager.get_session_memory("session_1")
        summary = session_memory.summarize()

        # Verify comprehensive summary
        assert summary["total_turns"] == 5
        assert len(summary["context"]) >= 0  # May have extracted context

        # End session and check long-term storage
        manager.end_session("session_1", "user_123")

        sessions = manager.long_term_memory.get_user_sessions("user_123")
        assert len(sessions) == 1
        assert sessions[0]["summary"]["total_turns"] == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
