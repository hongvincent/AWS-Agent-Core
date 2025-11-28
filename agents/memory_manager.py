"""
LLM-Enhanced Memory Manager for AWS Bedrock AgentCore Memory Testing

This implements intelligent memory functionality using LLM providers:
- Short-term: Session-specific conversation context with LLM summarization
- Long-term: User profile extraction and preference learning via LLM analysis
- Smart context retrieval and preference inference
"""

import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional
from collections import defaultdict

# Ensure project root is on sys.path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from tools.llm_provider import get_llm_provider

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ShortTermMemory:
    """
    Short-term memory for single session context

    Maintains conversation history within a session
    """

    def __init__(self, session_id: str, max_turns: int = 50):
        self.session_id = session_id
        self.max_turns = max_turns
        self.conversation_history: List[Dict[str, Any]] = []
        self.context: Dict[str, Any] = {}
        logger.info(f"ShortTermMemory initialized for session {session_id}")

    def add_turn(self, user_input: str, agent_response: str, metadata: Dict[str, Any] = None) -> None:
        """Add a conversation turn to memory"""
        turn = {
            "timestamp": datetime.now().isoformat(),
            "user": user_input,
            "agent": agent_response,
            "metadata": metadata or {}
        }

        self.conversation_history.append(turn)

        # Keep only recent turns
        if len(self.conversation_history) > self.max_turns:
            self.conversation_history = self.conversation_history[-self.max_turns:]

        logger.info(f"Added turn to memory. Total turns: {len(self.conversation_history)}")

    def get_recent_context(self, num_turns: int = 5) -> List[Dict[str, Any]]:
        """Get recent conversation turns"""
        return self.conversation_history[-num_turns:]

    def extract_information(self, key: str, value: Any) -> None:
        """Extract and store contextual information"""
        self.context[key] = value
        logger.info(f"Extracted context: {key} = {value}")

    def get_context(self, key: str) -> Optional[Any]:
        """Retrieve contextual information"""
        return self.context.get(key)

    def get_all_context(self) -> Dict[str, Any]:
        """Get all extracted context"""
        return self.context.copy()

    def summarize(self) -> Dict[str, Any]:
        """Generate summary of conversation"""
        return {
            "session_id": self.session_id,
            "total_turns": len(self.conversation_history),
            "context": self.context,
            "recent_topics": self._extract_topics()
        }

    def _extract_topics(self) -> List[str]:
        """Extract main topics from conversation using LLM analysis"""
        if not self.conversation_history:
            return []

        try:
            # Get LLM provider for topic extraction
            llm_provider = get_llm_provider()
            
            # Prepare conversation text for analysis
            conversation_text = ""
            for turn in self.conversation_history[-5:]:  # Analyze last 5 turns
                conversation_text += f"사용자: {turn['user']}\n"
                conversation_text += f"어시스턴트: {turn['agent']}\n"

            # LLM prompt for topic extraction
            prompt = f"""다음 대화에서 주요 토픽을 추출해 주세요. 각 토픽을 영어 키워드로 반환하세요.

대화:
{conversation_text}

토픽 카테고리:
- user_identity: 사용자 신원/이름 관련
- appointment: 예약/일정 관련  
- location_preference: 지점/위치 선호도
- service_inquiry: 서비스 문의
- complaint: 불만/문제
- compliment: 칭찬/만족
- general: 일반 대화

주요 토픽 3개를 JSON 배열로 반환하세요 (예: ["user_identity", "appointment", "location_preference"])"""

            response = llm_provider.generate(prompt, temperature=0.1, max_tokens=100)
            
            # Parse LLM response (handle markdown code blocks)  
            try:
                # Clean response - remove markdown code blocks if present
                clean_response = response.strip()
                if clean_response.startswith("```json"):
                    clean_response = clean_response[7:]
                if clean_response.endswith("```"):
                    clean_response = clean_response[:-3]
                clean_response = clean_response.strip()
                
                topics = json.loads(clean_response)
                if isinstance(topics, list):
                    return topics[:3]  # Limit to 3 topics
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse LLM topic response: {response}")
                pass

        except Exception as e:
            logger.error(f"LLM topic extraction failed: {e}")

        # Fallback to rule-based extraction
        topics = set()
        for turn in self.conversation_history:
            if "이름" in turn["user"]:
                topics.add("user_identity")
            if "예약" in turn["user"]:
                topics.add("appointment")
            if "지점" in turn["user"] or "강남" in turn["user"] or "부산" in turn["user"]:
                topics.add("location_preference")

        return list(topics)


class LongTermMemory:
    """
    Long-term memory for user profiles and preferences

    Persists across sessions for the same user
    """

    def __init__(self):
        # In real implementation, this would be backed by DynamoDB or similar
        self.user_profiles: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self.user_sessions: Dict[str, List[str]] = defaultdict(list)
        logger.info("LongTermMemory initialized")

    def save_user_preference(self, user_id: str, key: str, value: Any) -> None:
        """Save user preference"""
        if user_id not in self.user_profiles:
            self.user_profiles[user_id] = {
                "created_at": datetime.now().isoformat(),
                "preferences": {}
            }

        self.user_profiles[user_id]["preferences"][key] = {
            "value": value,
            "updated_at": datetime.now().isoformat()
        }

        logger.info(f"Saved preference for user {user_id}: {key} = {value}")

    def get_user_preference(self, user_id: str, key: str) -> Optional[Any]:
        """Get user preference"""
        if user_id not in self.user_profiles:
            return None

        pref = self.user_profiles[user_id].get("preferences", {}).get(key)
        return pref["value"] if pref else None

    def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Get complete user profile"""
        if user_id not in self.user_profiles:
            return {}

        return self.user_profiles[user_id].copy()

    def record_session(self, user_id: str, session_id: str, summary: Dict[str, Any]) -> None:
        """Record session summary for user"""
        self.user_sessions[user_id].append({
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "summary": summary
        })

        logger.info(f"Recorded session {session_id} for user {user_id}")

    def get_user_sessions(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent sessions for user"""
        sessions = self.user_sessions.get(user_id, [])
        return sessions[-limit:]

    def extract_preferences_from_session(self, user_id: str, session_summary: Dict[str, Any]) -> None:
        """
        Extract long-term preferences from session

        Analyzes conversation to identify user preferences
        """
        context = session_summary.get("context", {})

        # Extract preferences
        if "preferred_branch" in context:
            self.save_user_preference(user_id, "preferred_branch", context["preferred_branch"])

        if "user_name" in context:
            self.save_user_preference(user_id, "name", context["user_name"])

        logger.info(f"Extracted preferences from session for user {user_id}")


class MemoryManager:
    """
    Unified memory manager combining short-term and long-term memory
    """

    def __init__(self):
        self.short_term_memories: Dict[str, ShortTermMemory] = {}
        self.long_term_memory = LongTermMemory()
        logger.info("MemoryManager initialized")

    def get_session_memory(self, session_id: str) -> ShortTermMemory:
        """Get or create short-term memory for session"""
        if session_id not in self.short_term_memories:
            self.short_term_memories[session_id] = ShortTermMemory(session_id)

        return self.short_term_memories[session_id]

    def process_turn(
        self,
        session_id: str,
        user_id: str,
        user_input: str,
        agent_response: str,
        metadata: Dict[str, Any] = None
    ) -> None:
        """
        Process a conversation turn through memory system

        Stores in short-term and updates long-term as needed
        """
        # Store in short-term memory
        session_memory = self.get_session_memory(session_id)
        session_memory.add_turn(user_input, agent_response, metadata)

        # Extract any preferences for long-term storage
        self._extract_and_store_preferences(session_id, user_id, user_input, agent_response)

    def _extract_and_store_preferences(
        self,
        session_id: str,
        user_id: str,
        user_input: str,
        agent_response: str
    ) -> None:
        """Extract preferences from conversation using LLM analysis"""
        try:
            # Get LLM provider for preference extraction
            llm_provider = get_llm_provider()
            
            # LLM prompt for preference extraction
            prompt = f"""다음 대화에서 사용자의 개인정보와 선호도를 추출해 주세요.

사용자 입력: {user_input}
어시스턴트 응답: {agent_response}

추출할 정보:
1. 이름 (name): 사용자가 언급한 자신의 이름
2. 선호 지점 (preferred_branch): 강남/부산/서울/대전 중 선호하는 지점
3. 서비스 선호도 (service_preference): 선호하는 서비스나 요구사항
4. 기타 개인정보 (other): 나이, 직업 등 기타 정보

결과를 JSON으로 반환하세요. 정보가 없으면 null을 사용하세요.
예: {{"name": "김민수", "preferred_branch": "강남", "service_preference": null, "other": null}}"""

            response = llm_provider.generate(prompt, temperature=0.1, max_tokens=200)
            
            # Parse LLM response (handle markdown code blocks)
            try:
                # Clean response - remove markdown code blocks if present
                clean_response = response.strip()
                if clean_response.startswith("```json"):
                    clean_response = clean_response[7:]
                if clean_response.endswith("```"):
                    clean_response = clean_response[:-3]
                clean_response = clean_response.strip()
                
                preferences = json.loads(clean_response)
                
                session_memory = self.get_session_memory(session_id)
                
                # Store extracted preferences
                if preferences.get("name"):
                    session_memory.extract_information("user_name", preferences["name"])
                    self.long_term_memory.save_user_preference(user_id, "name", preferences["name"])
                    logger.info(f"Extracted user name: {preferences['name']}")
                
                if preferences.get("preferred_branch"):
                    # Normalize branch names
                    branch_map = {"강남": "강남", "부산": "부산", "서울": "서울", "대전": "대전"}
                    normalized_branch = branch_map.get(preferences["preferred_branch"])
                    if normalized_branch:
                        session_memory.extract_information("preferred_branch", normalized_branch)
                        self.long_term_memory.save_user_preference(user_id, "preferred_branch", normalized_branch)
                        logger.info(f"Extracted preferred branch: {normalized_branch}")
                
                if preferences.get("service_preference"):
                    session_memory.extract_information("service_preference", preferences["service_preference"])
                    self.long_term_memory.save_user_preference(user_id, "service_preference", preferences["service_preference"])
                
                if preferences.get("other"):
                    session_memory.extract_information("other_info", preferences["other"])

            except json.JSONDecodeError:
                logger.warning(f"Failed to parse LLM preference response: {response}")
                # Fall back to rule-based extraction
                self._fallback_preference_extraction(session_id, user_id, user_input)

        except Exception as e:
            logger.error(f"LLM preference extraction failed: {e}")
            # Fall back to rule-based extraction
            self._fallback_preference_extraction(session_id, user_id, user_input)

    def _fallback_preference_extraction(self, session_id: str, user_id: str, user_input: str) -> None:
        """Fallback rule-based preference extraction"""
        # Extract name
        if "내 이름은" in user_input or "이름은" in user_input:
            parts = user_input.split("이름은")
            if len(parts) > 1:
                name = parts[1].strip().replace("이야", "").replace(".", "").strip()
                if name:
                    session_memory = self.get_session_memory(session_id)
                    session_memory.extract_information("user_name", name)
                    self.long_term_memory.save_user_preference(user_id, "name", name)

        # Extract location preference
        branch_candidates = [
            ("강남점", "강남"), ("부산점", "부산"), ("서울점", "서울"), ("대전점", "대전"),
        ]

        matched_branch = None
        for phrase, normalized in branch_candidates:
            if phrase in user_input:
                matched_branch = normalized
                break

        if not matched_branch:
            for normalized in ["강남", "부산", "서울", "대전"]:
                if normalized in user_input:
                    matched_branch = normalized
                    break

        if matched_branch:
            session_memory = self.get_session_memory(session_id)
            session_memory.extract_information("preferred_branch", matched_branch)
            self.long_term_memory.save_user_preference(user_id, "preferred_branch", matched_branch)

    def end_session(self, session_id: str, user_id: str) -> None:
        """End session and transfer learnings to long-term memory"""
        if session_id not in self.short_term_memories:
            return

        session_memory = self.short_term_memories[session_id]
        summary = session_memory.summarize()

        # Record session in long-term memory
        self.long_term_memory.record_session(user_id, session_id, summary)

        # Extract any additional preferences
        self.long_term_memory.extract_preferences_from_session(user_id, summary)

        logger.info(f"Ended session {session_id} for user {user_id}")

    def get_user_context(self, user_id: str) -> Dict[str, Any]:
        """Get user's long-term context for new session"""
        profile = self.long_term_memory.get_user_profile(user_id)
        recent_sessions = self.long_term_memory.get_user_sessions(user_id, limit=3)

        return {
            "profile": profile,
            "recent_sessions": recent_sessions
        }


if __name__ == "__main__":
    # Test memory manager
    manager = MemoryManager()

    # Session 1
    print("\n=== Session 1 ===")
    manager.process_turn(
        "session_1", "user_123",
        "내 이름은 성민이야.",
        "안녕하세요, 성민님!"
    )

    manager.process_turn(
        "session_1", "user_123",
        "내 이름이 뭐였지?",
        "성민님이라고 하셨습니다."
    )

    manager.process_turn(
        "session_1", "user_123",
        "나는 주로 강남점에 방문해. 다음에 예약할 때도 강남점이 기본이었으면 좋겠어.",
        "네, 강남점을 선호하시는 것으로 기억하겠습니다."
    )

    manager.end_session("session_1", "user_123")

    # Session 2
    print("\n=== Session 2 (Same User) ===")
    user_context = manager.get_user_context("user_123")
    print(f"User context: {json.dumps(user_context, indent=2, ensure_ascii=False)}")

    preferred_branch = manager.long_term_memory.get_user_preference("user_123", "preferred_branch")
    print(f"Preferred branch: {preferred_branch}")
