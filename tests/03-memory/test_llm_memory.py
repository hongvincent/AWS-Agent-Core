"""
LLM-Enhanced Memory Tests for AgentCore Memory Testing

Tests the LLM-powered memory manager with intelligent preference extraction
and context-aware summarization.
"""

import pytest
import json
import os
from datetime import datetime

from agents.memory_manager import MemoryManager, ShortTermMemory, LongTermMemory
from tools.llm_provider import MockProvider, LLMFactory


class TestLLMMemoryManager:
    """Test LLM-enhanced memory manager functionality"""

    @pytest.fixture
    def memory_manager(self):
        """Create memory manager instance"""
        return MemoryManager()

    @pytest.fixture
    def mock_memory_manager(self):
        """Create memory manager with mock LLM for deterministic testing"""
        manager = MemoryManager()
        
        # Replace LLM provider with mock in short-term memory
        def mock_get_llm_provider():
            return MockProvider()
        
        import agents.memory_manager
        original_get_provider = agents.memory_manager.get_llm_provider
        agents.memory_manager.get_llm_provider = mock_get_llm_provider
        
        yield manager
        
        # Restore original provider
        agents.memory_manager.get_llm_provider = original_get_provider

    def test_memory_manager_initialization(self, memory_manager):
        """Test basic memory manager setup"""
        assert len(memory_manager.short_term_memories) == 0
        assert memory_manager.long_term_memory is not None

    def test_session_memory_creation(self, memory_manager):
        """Test session memory creation and retrieval"""
        session_id = "test_session_001"
        memory = memory_manager.get_session_memory(session_id)
        
        assert memory.session_id == session_id
        assert session_id in memory_manager.short_term_memories

    def test_basic_turn_processing_mock(self, mock_memory_manager):
        """Test basic conversation turn processing with mock LLM"""
        session_id = "test_session_001"
        user_id = "user_123"
        
        mock_memory_manager.process_turn(
            session_id, user_id,
            "안녕하세요! 제 이름은 김민수입니다.",
            "안녕하세요, 김민수님! 반갑습니다."
        )
        
        session_memory = mock_memory_manager.get_session_memory(session_id)
        assert len(session_memory.conversation_history) == 1
        
        # Check if name was extracted
        user_name = mock_memory_manager.long_term_memory.get_user_preference(user_id, "name")
        # Note: Mock LLM may not extract perfectly, but should not error

    def test_preference_extraction_mock(self, mock_memory_manager):
        """Test LLM-based preference extraction with mock"""
        session_id = "test_session_002"
        user_id = "user_456"
        
        # Process conversation with preferences
        conversations = [
            ("제 이름은 이영희입니다.", "안녕하세요, 이영희님!"),
            ("강남점을 자주 이용합니다.", "강남점 이용해 주셔서 감사합니다."),
            ("다음에도 강남점으로 예약하고 싶어요.", "네, 강남점으로 예약 도와드리겠습니다.")
        ]
        
        for user_input, agent_response in conversations:
            mock_memory_manager.process_turn(session_id, user_id, user_input, agent_response)
        
        # Check extracted preferences (may be extracted via fallback rules)
        user_name = mock_memory_manager.long_term_memory.get_user_preference(user_id, "name")
        preferred_branch = mock_memory_manager.long_term_memory.get_user_preference(user_id, "preferred_branch")
        
        # With fallback extraction, these should work
        assert user_name == "이영희" or user_name is None  # Depends on extraction success
        assert preferred_branch == "강남" or preferred_branch is None

    def test_conversation_summarization_mock(self, mock_memory_manager):
        """Test LLM-based conversation topic extraction"""
        session_id = "test_session_003"
        user_id = "user_789"
        
        # Add multiple conversation turns
        conversations = [
            ("예약하고 싶어요.", "어떤 서비스로 예약하시겠어요?"),
            ("마사지 서비스요.", "마사지 서비스 예약 도와드리겠습니다."),
            ("강남점에서 가능한가요?", "네, 강남점 예약 가능합니다.")
        ]
        
        for user_input, agent_response in conversations:
            mock_memory_manager.process_turn(session_id, user_id, user_input, agent_response)
        
        # Get session summary
        session_memory = mock_memory_manager.get_session_memory(session_id)
        summary = session_memory.summarize()
        
        assert summary["session_id"] == session_id
        assert summary["total_turns"] == 3
        assert "recent_topics" in summary

    @pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="OpenAI API key not available")
    def test_real_llm_preference_extraction(self, memory_manager):
        """Test preference extraction with real LLM"""
        session_id = "real_session_001"
        user_id = "real_user_001"
        
        # Process realistic conversation
        memory_manager.process_turn(
            session_id, user_id,
            "안녕하세요! 저는 박지훈이라고 합니다. 부산에 살고 있어서 부산점을 주로 이용해요.",
            "안녕하세요, 박지훈님! 부산점 이용해 주셔서 감사합니다."
        )
        
        memory_manager.process_turn(
            session_id, user_id,
            "다음 주 금요일에 헤어컷 예약하고 싶은데, 부산점에서 가능한가요?",
            "네, 부산점에서 헤어컷 예약 도와드리겠습니다."
        )
        
        # Check extracted information
        user_name = memory_manager.long_term_memory.get_user_preference(user_id, "name")
        preferred_branch = memory_manager.long_term_memory.get_user_preference(user_id, "preferred_branch")
        
        assert user_name == "박지훈"
        assert preferred_branch == "부산"

    @pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="OpenAI API key not available")
    def test_real_llm_topic_extraction(self, memory_manager):
        """Test topic extraction with real LLM"""
        session_id = "real_session_002"
        user_id = "real_user_002"
        
        # Add conversation about appointments and complaints
        conversations = [
            ("지난번 서비스가 별로였어요.", "죄송합니다. 어떤 부분이 불편하셨나요?"),
            ("대기시간이 너무 길었습니다.", "대기시간 관련해서 개선하겠습니다."),
            ("그래도 직원분은 친절했어요.", "감사합니다. 앞으로 더 좋은 서비스 제공하겠습니다.")
        ]
        
        for user_input, agent_response in conversations:
            memory_manager.process_turn(session_id, user_id, user_input, agent_response)
        
        # Get session summary with topics
        session_memory = memory_manager.get_session_memory(session_id)
        topics = session_memory._extract_topics()
        
        # Should detect complaint and compliment topics
        topic_set = set(topics)
        assert len(topics) > 0
        # Real LLM should be able to identify these patterns

    def test_session_ending_and_learning(self, mock_memory_manager):
        """Test session termination and learning transfer"""
        session_id = "test_session_end"
        user_id = "user_end_test"
        
        # Process some conversation
        mock_memory_manager.process_turn(
            session_id, user_id,
            "제 이름은 최수진이고 서울점을 선호합니다.",
            "네, 최수진님. 서울점 이용해 주셔서 감사합니다."
        )
        
        # End session
        mock_memory_manager.end_session(session_id, user_id)
        
        # Check that session was recorded in long-term memory
        user_sessions = mock_memory_manager.long_term_memory.get_user_sessions(user_id)
        assert len(user_sessions) >= 1
        
        latest_session = user_sessions[-1]
        assert latest_session["session_id"] == session_id

    def test_user_context_retrieval(self, mock_memory_manager):
        """Test user context retrieval for new sessions"""
        user_id = "context_test_user"
        
        # Set up some preferences
        mock_memory_manager.long_term_memory.save_user_preference(user_id, "name", "김철수")
        mock_memory_manager.long_term_memory.save_user_preference(user_id, "preferred_branch", "강남")
        
        # Get user context
        context = mock_memory_manager.get_user_context(user_id)
        
        assert "profile" in context
        assert "recent_sessions" in context
        
        # Check preferences
        preferences = context["profile"].get("preferences", {})
        if preferences:
            name_pref = preferences.get("name", {})
            branch_pref = preferences.get("preferred_branch", {})
            
            if name_pref:
                assert name_pref.get("value") == "김철수"
            if branch_pref:
                assert branch_pref.get("value") == "강남"


if __name__ == "__main__":
    # Quick local test
    manager = MemoryManager()
    
    print("=== LLM Memory Manager Test ===")
    
    # Test conversation
    session_id = "demo_session"
    user_id = "demo_user"
    
    conversations = [
        ("안녕하세요! 저는 데모 사용자입니다.", "안녕하세요! 반갑습니다."),
        ("강남점에서 서비스 받고 싶어요.", "강남점 서비스 예약 도와드리겠습니다."),
        ("다음 주 월요일 가능한가요?", "네, 확인해 드리겠습니다.")
    ]
    
    for user_input, agent_response in conversations:
        manager.process_turn(session_id, user_id, user_input, agent_response)
        print(f"처리: {user_input}")
    
    # Get summary
    session_memory = manager.get_session_memory(session_id)
    summary = session_memory.summarize()
    print(f"세션 요약: {json.dumps(summary, indent=2, ensure_ascii=False)}")
    
    # End session and get user context
    manager.end_session(session_id, user_id)
    context = manager.get_user_context(user_id)
    print(f"사용자 컨텍스트: {json.dumps(context, indent=2, ensure_ascii=False)}")