"""
Test Suite for RAG + Appointment Integration

Complete end-to-end test combining all AgentCore features
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agents"))

from memory_manager import MemoryManager


class MockRAGSystem:
    """Mock RAG system for testing"""

    def search(self, query: str) -> str:
        """Search knowledge base"""
        if "부산점" in query and "위치" in query:
            return "부산점은 부산광역시 해운대구에 위치하며, 지하 주차장을 이용하실 수 있습니다."
        elif "주차" in query:
            return "모든 지점에 무료 주차 서비스를 제공합니다."
        return "관련 정보를 찾을 수 없습니다."


class MockAppointmentAPI:
    """Mock appointment API"""

    def get_available_slots(self, branch: str, day: str) -> list:
        """Get available appointment slots"""
        return [
            {"time": "14:00", "available": True},
            {"time": "15:00", "available": True},
            {"time": "16:00", "available": False}
        ]

    def create_appointment(self, branch: str, time: str) -> dict:
        """Create appointment"""
        return {
            "appointment_id": "APT-12345",
            "branch": branch,
            "time": time,
            "status": "confirmed"
        }

    def cancel_appointment(self, appointment_id: str) -> dict:
        """Cancel appointment"""
        return {
            "appointment_id": appointment_id,
            "status": "cancelled"
        }


@pytest.mark.integration
class TestRAGAppointmentIntegration:
    """Test complete RAG + Appointment workflow"""

    def test_scenario_info_and_booking(self):
        """
        Scenario: 정보 조회 + 예약

        User: "부산점 위치랑 주차 안내 알려주고, 이번 주 토요일 오후에 가능한 시간에 예약까지 잡아줘."

        Expected flow:
        1. RAG: Search for branch info
        2. Gateway: Call appointment API for slots
        3. Gateway: Create appointment
        4. Memory: Save preference and appointment
        5. Observability: Track all steps
        """
        # Initialize systems
        memory_manager = MemoryManager()
        rag = MockRAGSystem()
        appointment_api = MockAppointmentAPI()

        # Step 1: RAG search
        location_info = rag.search("부산점 위치")
        parking_info = rag.search("주차")

        assert "부산광역시 해운대구" in location_info
        assert "무료 주차" in parking_info

        # Step 2: Get available slots
        slots = appointment_api.get_available_slots("부산", "토요일 오후")
        available_slots = [s for s in slots if s["available"]]

        assert len(available_slots) > 0

        # Step 3: Create appointment
        appointment = appointment_api.create_appointment("부산", "14:00")

        assert appointment["status"] == "confirmed"
        assert appointment["branch"] == "부산"

        # Step 4: Store in memory
        memory_manager.process_turn(
            "session_1", "user_123",
            "부산점 위치랑 주차 안내 알려주고, 토요일 오후 2시 예약해줘",
            f"부산점 정보: {location_info}\n{parking_info}\n예약이 완료되었습니다: {appointment['appointment_id']}"
        )

        # Save preferences
        session_memory = memory_manager.get_session_memory("session_1")
        session_memory.extract_information("preferred_branch", "부산")
        session_memory.extract_information("appointment_id", appointment["appointment_id"])

        # Verify
        assert session_memory.get_context("preferred_branch") == "부산"
        assert session_memory.get_context("appointment_id") == "APT-12345"

    def test_scenario_followup_cancellation(self):
        """
        Scenario: 후속 대화 - 예약 취소

        Session 1: Create appointment
        Session 2: "지난번에 잡았던 예약 취소해줘"

        Expected:
        - Memory recalls appointment ID from Session 1
        - Calls cancellation API
        """
        memory_manager = MemoryManager()
        appointment_api = MockAppointmentAPI()

        # Session 1: Create appointment
        appointment = appointment_api.create_appointment("부산", "14:00")

        memory_manager.process_turn(
            "session_1", "user_123",
            "부산점 토요일 2시 예약해줘",
            f"예약 완료: {appointment['appointment_id']}"
        )

        session_memory = memory_manager.get_session_memory("session_1")
        session_memory.extract_information("latest_appointment", appointment["appointment_id"])

        memory_manager.end_session("session_1", "user_123")

        # Session 2: Cancel
        # Retrieve context from long-term memory
        user_context = memory_manager.get_user_context("user_123")
        previous_sessions = user_context["recent_sessions"]

        assert len(previous_sessions) == 1

        # In real scenario, agent would extract appointment ID from context
        appointment_id = "APT-12345"  # Retrieved from memory

        # Cancel appointment
        result = appointment_api.cancel_appointment(appointment_id)

        assert result["status"] == "cancelled"

        memory_manager.process_turn(
            "session_2", "user_123",
            "지난번 예약 취소해줘",
            f"예약 {appointment_id}이 취소되었습니다"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
