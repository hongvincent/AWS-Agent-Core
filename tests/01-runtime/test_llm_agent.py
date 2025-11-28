"""
LLM-Enhanced Tests for AgentCore Runtime

Tests the LLM-powered agent with various scenarios including:
- Natural language interaction
- Context awareness
- Memory integration
- Error handling
"""

import pytest
import asyncio
import json
import os
from datetime import datetime

from agents.echo_agent import LLMAgent
from tools.llm_provider import LLMFactory, MockProvider


class TestLLMAgent:
    """Test LLM-powered agent functionality"""

    @pytest.fixture
    def mock_agent(self):
        """Create agent with mock LLM provider for deterministic testing"""
        mock_provider = MockProvider()
        agent = LLMAgent()
        agent.llm_provider = mock_provider
        return agent

    @pytest.fixture
    def real_agent(self):
        """Create agent with real LLM provider (if available)"""
        return LLMAgent()

    def test_agent_initialization(self):
        """Test basic agent initialization"""
        agent = LLMAgent()
        assert agent.session_id.startswith("session_")
        assert agent.llm_provider is not None
        assert agent.system_prompt is not None
        assert len(agent.conversation_history) == 0

    def test_custom_system_prompt(self):
        """Test agent with custom system prompt"""
        custom_prompt = "You are a test assistant."
        agent = LLMAgent(system_prompt=custom_prompt)
        assert agent.system_prompt == custom_prompt

    def test_basic_message_processing_mock(self, mock_agent):
        """Test message processing with mock provider"""
        response = mock_agent.process_message("안녕하세요!")
        
        assert response["status"] == "success"
        assert response["session_id"] == mock_agent.session_id
        assert response["input"] == "안녕하세요!"
        assert response["provider"] == "mock"
        assert "output" in response
        assert len(mock_agent.conversation_history) == 2  # User + Assistant

    def test_conversation_context_mock(self, mock_agent):
        """Test conversation context maintenance"""
        # First message
        response1 = mock_agent.process_message("제 이름은 김민수입니다.")
        assert response1["status"] == "success"
        
        # Second message referencing context
        response2 = mock_agent.process_message("제 이름이 뭐였죠?")
        assert response2["status"] == "success"
        
        # Check conversation history
        assert len(mock_agent.conversation_history) == 4  # 2 exchanges

    def test_context_injection_mock(self, mock_agent):
        """Test processing with additional context"""
        context = {"user_id": "user_123", "preferred_branch": "강남"}
        response = mock_agent.process_message("예약하고 싶어요.", context=context)
        
        assert response["status"] == "success"
        assert response["input"] == "예약하고 싶어요."

    def test_error_handling_mock(self, mock_agent):
        """Test error handling in message processing"""
        # Simulate error by breaking the LLM provider
        original_chat = mock_agent.llm_provider.chat
        mock_agent.llm_provider.chat = lambda *args, **kwargs: None.__getattribute__("nonexistent")
        
        response = mock_agent.process_message("Test error handling")
        
        assert response["status"] == "error"
        assert "error" in response
        assert "처리 중 오류가 발생했습니다" in response["output"]
        
        # Restore original method
        mock_agent.llm_provider.chat = original_chat

    @pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="OpenAI API key not available")
    def test_real_llm_integration(self, real_agent):
        """Test with real LLM provider (OpenAI)"""
        response = real_agent.process_message("안녕하세요! 간단히 인사해 주세요.")
        
        assert response["status"] == "success"
        assert response["provider"] in ["openai", "bedrock", "mock"]
        assert len(response["output"]) > 0
        assert "안녕" in response["output"] or "hello" in response["output"].lower()

    @pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="OpenAI API key not available")
    def test_korean_conversation_real(self, real_agent):
        """Test Korean conversation with real LLM"""
        messages = [
            "안녕하세요! 저는 김민수라고 합니다.",
            "강남점에서 서비스를 받고 싶은데요.",
            "다음 주 화요일 오후 2시에 예약 가능한가요?"
        ]
        
        for message in messages:
            response = real_agent.process_message(message)
            assert response["status"] == "success"
            assert len(response["output"]) > 0
        
        # Check conversation history accumulation
        assert len(real_agent.conversation_history) == len(messages) * 2

    def test_session_isolation(self):
        """Test that different agents have isolated sessions"""
        agent1 = LLMAgent()
        agent2 = LLMAgent()
        
        assert agent1.session_id != agent2.session_id
        
        # Process messages in both agents
        agent1.process_message("Agent 1 message")
        agent2.process_message("Agent 2 message")
        
        assert len(agent1.conversation_history) == 2
        assert len(agent2.conversation_history) == 2
        assert agent1.conversation_history != agent2.conversation_history


@pytest.mark.asyncio
class TestLLMAgentAsync:
    """Async tests for LLM agent"""

    async def test_concurrent_message_processing(self):
        """Test concurrent message processing"""
        agent = LLMAgent()
        
        # Create multiple concurrent tasks
        tasks = []
        for i in range(3):
            task = asyncio.create_task(
                asyncio.to_thread(agent.process_message, f"Message {i}")
            )
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks)
        
        # All should succeed
        for response in responses:
            assert response["status"] == "success"
        
        # Check that all messages were processed
        assert len(agent.conversation_history) == 6  # 3 exchanges * 2 messages each


if __name__ == "__main__":
    # Quick local test
    agent = LLMAgent()
    test_messages = [
        "안녕하세요!",
        "제 이름은 테스터입니다.",
        "강남점에 관심이 있어요."
    ]
    
    print("=== LLM Agent Test ===")
    for msg in test_messages:
        response = agent.process_message(msg)
        print(f"입력: {msg}")
        print(f"응답: {response['output']}")
        print(f"상태: {response['status']}")
        print("-" * 40)