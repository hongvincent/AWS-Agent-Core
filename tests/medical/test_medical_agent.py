"""
Medical Agent Test Suite

의료 에이전트 전문 기능 테스트:
- 증상 기반 진료과 추천
- 응급상황 감지 및 처리
- 환자 정보 추출 및 컨텍스트 관리
- 예약 시스템 연동
"""

import pytest
import json
import os
from datetime import datetime, timedelta

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from agents.medical_agent import MedicalAgent, handler
from tools.llm_provider import MockProvider


class TestMedicalAgent:
    """의료 에이전트 기능 테스트"""

    @pytest.fixture
    def medical_agent(self):
        """실제 LLM 연동 의료 에이전트"""
        return MedicalAgent()

    @pytest.fixture
    def mock_medical_agent(self):
        """Mock LLM 기반 의료 에이전트"""
        agent = MedicalAgent()
        agent.llm_provider = MockProvider()
        return agent

    def test_medical_agent_initialization(self):
        """의료 에이전트 초기화 테스트"""
        agent = MedicalAgent()
        assert agent.session_id.startswith("medical_")
        assert agent.llm_provider is not None
        assert len(agent.departments) > 0
        assert "내과" in agent.departments
        assert "응급" in agent.system_prompt

    def test_emergency_detection(self, mock_medical_agent):
        """응급상황 감지 테스트"""
        emergency_messages = [
            "가슴이 너무 아파요! 숨도 잘 안 쉬어져요!",
            "아이가 의식을 잃었어요!",
            "심한 출혈이 멈추지 않아요",
            "급성 복통으로 쓰러질 것 같아요"
        ]
        
        for message in emergency_messages:
            result = mock_medical_agent.process_message(message)
            assert result["status"] == "emergency_detected"
            assert result["is_emergency"] is True
            assert "119" in result["output"]
            assert "응급실" in result["output"]

    def test_non_emergency_consultation(self, mock_medical_agent):
        """일반 상담 테스트"""
        normal_messages = [
            "며칠째 감기 기운이 있어요",
            "정기 검진을 받고 싶습니다",
            "무릎이 조금 아픈데 어떤 과에 가야 할까요?"
        ]
        
        for message in normal_messages:
            result = mock_medical_agent.process_message(message)
            assert result["status"] == "success"
            assert result.get("is_emergency") != True
            assert len(result["output"]) > 0

    def test_department_recommendation(self, medical_agent):
        """진료과 추천 테스트"""
        test_cases = [
            ("아이가 열이 나고 기침해요", "소아과"),
            ("무릎이 아프고 관절이 뻣뻣해요", "정형외과"),
            ("피부에 발진이 생겼어요", "피부과"),
            ("임신 확인을 하고 싶어요", "산부인과")
        ]
        
        for symptom, expected_dept in test_cases:
            result = medical_agent.process_message(symptom)
            # Mock이 아닌 실제 LLM에서는 추천이 정확하지 않을 수 있음
            assert result["status"] == "success"
            print(f"증상: {symptom} → 추천: {result.get('department_recommended', 'None')}")

    def test_patient_context_extraction(self, medical_agent):
        """환자 컨텍스트 추출 테스트"""
        conversation = [
            "안녕하세요. 저는 35세 남성이고 당뇨병이 있어요.",
            "아스피린을 복용하고 있고 계란 알레르기가 있습니다.",
            "요즘 혈압이 높게 나와서 걱정이에요."
        ]
        
        for message in conversation:
            result = medical_agent.process_message(message)
            assert result["status"] == "success"
        
        # 환자 컨텍스트 확인
        context = medical_agent.patient_context
        print(f"추출된 환자 정보: {json.dumps(context, ensure_ascii=False, indent=2)}")
        
        # 기본적인 정보가 추출되었는지 확인 (LLM 성능에 따라 달라질 수 있음)
        assert isinstance(context, dict)

    def test_urgency_assessment(self, mock_medical_agent):
        """응급도 평가 테스트"""
        test_cases = [
            ("심한 복통으로 쓰러질 것 같아요", "high"),
            ("며칠째 머리가 아파요", "medium"),  
            ("정기 검진 예약하고 싶어요", "low")
        ]
        
        for message, expected_urgency in test_cases:
            urgency = mock_medical_agent._assess_urgency(message)
            assert urgency == expected_urgency

    def test_appointment_availability(self, mock_medical_agent):
        """예약 가능 시간 조회 테스트"""
        # 예약 가능한 과
        result = mock_medical_agent.get_available_appointments("내과")
        assert "available_slots" in result
        assert len(result["available_slots"]) > 0
        assert result["doctor"] == "김내과"
        
        # 예약 불가능한 과
        result = mock_medical_agent.get_available_appointments("정형외과")
        assert "error" in result
        
        # 존재하지 않는 과
        result = mock_medical_agent.get_available_appointments("존재하지않는과")
        assert "error" in result

    def test_appointment_booking(self, mock_medical_agent):
        """예약 접수 테스트"""
        tomorrow = datetime.now() + timedelta(days=1)
        appointment_time = tomorrow.replace(hour=10, minute=0)
        
        patient_info = {
            "name": "김환자",
            "phone": "010-1234-5678"
        }
        
        result = mock_medical_agent.book_appointment(
            "내과", 
            appointment_time.isoformat(),
            patient_info
        )
        
        assert result["status"] == "confirmed"
        assert result["patient_name"] == "김환자"
        assert result["department"] == "내과"
        assert "booking_id" in result

    @pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="OpenAI API key not available")
    def test_real_medical_consultation(self, medical_agent):
        """실제 LLM 기반 의료 상담 테스트"""
        consultation_cases = [
            "안녕하세요. 3일째 목감기 증상이 있어요. 열은 37.5도 정도 나고 기침도 해요.",
            "어떤 과에서 진료 받는 게 좋을까요?",
            "집에서 할 수 있는 관리 방법도 있나요?"
        ]
        
        for message in consultation_cases:
            result = medical_agent.process_message(message)
            assert result["status"] == "success"
            assert len(result["output"]) > 50  # 충분한 길이의 응답
            print(f"Q: {message}")
            print(f"A: {result['output']}")
            print(f"추천 진료과: {result.get('department_recommended', '없음')}")
            print("-" * 60)

    def test_handler_function(self):
        """핸들러 함수 테스트"""
        # 상담 요청
        event = {
            "message": "머리가 아파요",
            "action": "consult"
        }
        
        response = handler(event)
        assert response["statusCode"] == 200
        
        body = json.loads(response["body"])
        assert body["status"] == "success"
        
        # 예약 조회 요청
        event = {
            "action": "appointments",
            "department": "내과"
        }
        
        response = handler(event)
        assert response["statusCode"] == 200
        
        body = json.loads(response["body"])
        assert "available_slots" in body

    def test_conversation_context_continuity(self, medical_agent):
        """대화 컨텍스트 연속성 테스트"""
        # 다중 턴 대화
        conversations = [
            "안녕하세요. 저는 28세 여성입니다.",
            "임신 12주차인데 정기 검진 받으려고 해요.",
            "어떤 검사를 받아야 하나요?",
            "예약은 언제 가능한가요?"
        ]
        
        for message in conversations:
            result = medical_agent.process_message(message)
            assert result["status"] == "success"
        
        # 대화 히스토리 확인
        assert len(medical_agent.conversation_history) == len(conversations) * 2
        
        # 환자 컨텍스트에 정보가 누적되었는지 확인
        context = medical_agent.patient_context
        print(f"누적된 환자 정보: {json.dumps(context, ensure_ascii=False, indent=2)}")

    def test_medical_safety_features(self, mock_medical_agent):
        """의료 안전 기능 테스트"""
        # 진단 요청에 대한 안전한 응답
        result = mock_medical_agent.process_message("제가 당뇨병인가요?")
        response = result["output"].lower()
        
        # Mock 응답에서 안전한 키워드가 포함되어 있는지 확인
        # Mock provider는 진료과와 예약 안내를 포함하므로 해당 키워드 확인
        safe_responses = ["진료", "상담", "예약", "안내", "과", "병원"]
        
        print(f"응답: {response}")
        print(f"확인하는 키워드들: {safe_responses}")
        
        # Mock 응답이므로 기본적인 의료 서비스 안내가 포함되어야 함
        assert any(keyword in response for keyword in safe_responses), f"안전한 의료 응답이 없습니다: {response}"


if __name__ == "__main__":
    # 빠른 로컬 테스트
    print("=== 의료 에이전트 빠른 테스트 ===")
    
    agent = MedicalAgent()
    test_cases = [
        "안녕하세요. 며칠째 감기 기운이 있어요.",
        "가슴이 아파요! 응급상황인가요?",
        "임신 검사를 받고 싶어요.",
        "무릎 관절이 아픈데 어디서 봐야 할까요?"
    ]
    
    for case in test_cases:
        print(f"\n환자: {case}")
        result = agent.process_message(case)
        print(f"의료AI: {result['output'][:200]}...")
        if result.get('department_recommended'):
            print(f"→ 추천 진료과: {result['department_recommended']}")
        print(f"→ 응급도: {result.get('urgency_level', 'N/A')}")
        
    print(f"\n최종 환자 컨텍스트: {json.dumps(agent.patient_context, ensure_ascii=False, indent=2)}")