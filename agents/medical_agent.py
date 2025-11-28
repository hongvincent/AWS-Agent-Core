"""
Medical Agent for Healthcare Service Management

전문 의료 서비스 에이전트:
- 병원 예약 및 진료 일정 관리
- 증상 기반 진료과 추천
- 의료진 정보 및 전문 분야 안내
- 건강 상담 및 응급 상황 트리아지
"""

import json
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

# Ensure project root is on sys.path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from tools.llm_provider import get_llm_provider

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/medical_agent.log')
    ]
)
logger = logging.getLogger(__name__)


class MedicalAgent:
    """의료 서비스 전문 AI 에이전트"""

    def __init__(self, session_id: str = None):
        self.session_id = session_id or self._generate_session_id()
        self.llm_provider = get_llm_provider()
        self.conversation_history = []
        self.patient_context = {}
        
        # 의료진 및 진료과 정보
        self.departments = {
            "내과": {"의사": "김내과", "전문분야": "당뇨, 고혈압, 감기", "예약가능": True},
            "외과": {"의사": "이외과", "전문분야": "수술, 외상, 상처치료", "예약가능": True},
            "소아과": {"의사": "박소아", "전문분야": "아동질환, 예방접종", "예약가능": True},
            "산부인과": {"의사": "최산부", "전문분야": "임신, 출산, 부인과질환", "예약가능": True},
            "정형외과": {"의사": "정정형", "전문분야": "관절, 근골격계", "예약가능": False},
            "피부과": {"의사": "윤피부", "전문분야": "아토피, 여드름, 피부질환", "예약가능": True},
            "안과": {"의사": "한안과", "전문분야": "시력, 안질환", "예약가능": True},
            "이비인후과": {"의사": "코이비", "전문분야": "코, 목, 귀 질환", "예약가능": True}
        }
        
        self.system_prompt = self._get_medical_system_prompt()
        
        logger.info(f"MedicalAgent initialized with session_id: {self.session_id}")

    def _generate_session_id(self) -> str:
        """Generate unique session ID"""
        import uuid
        return f"medical_{uuid.uuid4().hex}"

    def _get_medical_system_prompt(self) -> str:
        """의료 전문 시스템 프롬프트"""
        return f"""당신은 의료 서비스 전문 AI 어시스턴트입니다.

**역할**: 병원 예약, 증상 상담, 진료과 안내를 담당하는 의료 서비스 도우미

**주요 기능**:
1. 증상 청취 및 적절한 진료과 추천
2. 의료진 소개 및 예약 가능 여부 확인  
3. 응급상황 식별 및 응급실 안내
4. 건강 상담 및 일반적인 의료 정보 제공
5. 예약 일정 관리 및 변경

**진료과 정보**:
{json.dumps(self.departments, ensure_ascii=False, indent=2)}

**응답 원칙**:
- 친근하고 전문적인 tone으로 응답
- 의학적 진단은 하지 않고, 의료진 상담 권유
- 응급상황 시 즉시 응급실 방문 또는 119 신고 안내
- 예약 시 구체적인 날짜/시간 확인
- 개인정보는 안전하게 처리

**금지사항**:
- 구체적인 의학적 진단 제공
- 처방전이나 약물 추천  
- 의료진을 대체하려는 시도

한국어로 따뜻하고 신뢰할 수 있는 응답을 제공하세요."""

    def process_message(self, message: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """의료 상담 메시지 처리"""
        logger.info(f"Processing medical consultation: {message}")

        try:
            # 응급상황 우선 체크
            emergency_check = self._check_emergency_symptoms(message)
            if emergency_check["is_emergency"]:
                return self._handle_emergency(message, emergency_check)

            # 대화 컨텍스트 구성
            messages = [{"role": "system", "content": self.system_prompt}]
            
            # 환자 컨텍스트 추가
            if self.patient_context:
                context_str = f"환자 정보: {json.dumps(self.patient_context, ensure_ascii=False)}"
                messages.append({"role": "system", "content": context_str})
            
            # 대화 히스토리 추가 (최근 10턴)
            messages.extend(self.conversation_history[-10:])
            
            # 현재 메시지 추가
            messages.append({"role": "user", "content": message})

            # LLM 응답 생성
            response = self.llm_provider.chat(
                messages=messages,
                temperature=0.3,  # 의료 상담이므로 일관성 중시
                max_tokens=800
            )

            # 의료 정보 추출 및 저장
            self._extract_medical_info(message, response)

            # 대화 히스토리 업데이트
            self.conversation_history.append({"role": "user", "content": message})
            self.conversation_history.append({"role": "assistant", "content": response})

            result = {
                "session_id": self.session_id,
                "input": message,
                "output": response,
                "department_recommended": self._extract_department_recommendation(response),
                "urgency_level": self._assess_urgency(message),
                "provider": self.llm_provider.provider_name,
                "timestamp": datetime.now().isoformat(),
                "status": "success",
                "medical_context": self.patient_context
            }

            logger.info(f"Medical consultation completed successfully")
            return result

        except Exception as e:
            logger.error(f"Error in medical consultation: {str(e)}")
            fallback_response = "죄송합니다. 일시적인 오류가 발생했습니다. 응급상황이시면 119에 신고하시고, 그렇지 않다면 잠시 후 다시 시도해 주세요."
            
            return {
                "session_id": self.session_id,
                "input": message,
                "output": fallback_response,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "status": "error"
            }

    def _check_emergency_symptoms(self, message: str) -> Dict[str, Any]:
        """응급상황 키워드 체크"""
        emergency_keywords = [
            "가슴이 아파", "숨이 막혀", "의식을 잃", "심한 출혈", "출혈",
            "골절", "화상", "중독", "급성 복통", "119", "응급",
            "쓰러져", "경련", "호흡곤란", "심장이 아파", "가슴이 너무 아파",
            "숨도 잘 안 쉬어져", "숨쉬기 어려워", "가슴 통증", "배가 아파",
            "배가 너무 아파", "갑자기 아파", "너무 아파"
        ]
        
        message_lower = message.lower()
        detected_keywords = [kw for kw in emergency_keywords if kw in message_lower]
        
        return {
            "is_emergency": len(detected_keywords) > 0,
            "detected_keywords": detected_keywords,
            "urgency_score": min(len(detected_keywords) * 2, 10)
        }

    def _handle_emergency(self, message: str, emergency_info: Dict) -> Dict[str, Any]:
        """응급상황 처리"""
        emergency_response = f"""🚨 응급상황이 의심됩니다!

즉시 다음 조치를 취하세요:

1️⃣ **119 신고** - 생명이 위험하다고 판단되면 즉시 119에 신고하세요
2️⃣ **응급실 방문** - 가까운 응급실로 즉시 이동하세요  
3️⃣ **안전한 자세** - 의식이 있다면 안전한 자세를 유지하세요

📍 **24시간 응급실**:
- 서울대병원 응급의료센터: 02-2072-2345
- 삼성서울병원 응급실: 02-3410-2345  
- 응급의료정보센터: 1339

⚠️ 이 AI 상담은 응급치료를 대체할 수 없습니다. 즉시 전문 의료진의 도움을 받으세요!

현재 증상: {message}
감지된 응급 키워드: {', '.join(emergency_info['detected_keywords'])}"""

        return {
            "session_id": self.session_id,
            "input": message,
            "output": emergency_response,
            "is_emergency": True,
            "urgency_level": "CRITICAL",
            "emergency_info": emergency_info,
            "timestamp": datetime.now().isoformat(),
            "status": "emergency_detected"
        }

    def _extract_medical_info(self, user_input: str, ai_response: str) -> None:
        """의료 정보 추출 및 환자 컨텍스트 업데이트"""
        try:
            # LLM으로 의료 정보 추출
            extraction_prompt = f"""다음 의료 상담에서 환자 정보를 추출해 주세요:

환자 입력: {user_input}
AI 응답: {ai_response}

다음 정보를 JSON으로 추출하세요:
{{
  "age": "나이 (숫자만, 알 수 없으면 null)",
  "gender": "성별 (남성/여성/null)", 
  "symptoms": ["증상1", "증상2"],
  "department": "추천 진료과 (null if not mentioned)",
  "urgency": "응급도 (low/medium/high)",
  "allergies": ["알레르기 정보"],
  "medications": ["복용중인 약물"],
  "medical_history": ["과거 병력"]
}}

정보가 없으면 null이나 빈 배열을 사용하세요."""

            extraction_response = self.llm_provider.generate(
                extraction_prompt, 
                temperature=0.1, 
                max_tokens=300
            )
            
            # JSON 파싱 (마크다운 블록 제거)
            clean_response = extraction_response.strip()
            if clean_response.startswith("```json"):
                clean_response = clean_response[7:]
            if clean_response.endswith("```"):
                clean_response = clean_response[:-3]
            clean_response = clean_response.strip()
            
            extracted_info = json.loads(clean_response)
            
            # 환자 컨텍스트 업데이트 (기존 정보 유지하면서 새 정보 추가)
            for key, value in extracted_info.items():
                if value and value != "null":
                    if key in ["symptoms", "allergies", "medications", "medical_history"]:
                        # 리스트 타입은 기존 항목과 합치기
                        existing = self.patient_context.get(key, [])
                        if isinstance(value, list):
                            self.patient_context[key] = list(set(existing + value))
                    else:
                        # 단일 값은 덮어쓰기
                        self.patient_context[key] = value
            
            logger.info(f"Updated patient context: {self.patient_context}")
                        
        except Exception as e:
            logger.warning(f"Failed to extract medical info: {e}")

    def _extract_department_recommendation(self, response: str) -> Optional[str]:
        """응답에서 추천 진료과 추출"""
        for dept in self.departments.keys():
            if dept in response:
                return dept
        return None

    def _assess_urgency(self, message: str) -> str:
        """메시지 기반 응급도 평가"""
        high_urgency = ["심한", "급성", "갑자기", "응급", "위험", "심각"]
        medium_urgency = ["아파", "불편", "걱정", "며칠째"]
        
        message_lower = message.lower()
        
        if any(keyword in message_lower for keyword in high_urgency):
            return "high"
        elif any(keyword in message_lower for keyword in medium_urgency):
            return "medium"
        else:
            return "low"

    def get_available_appointments(self, department: str, date_preference: str = None) -> Dict[str, Any]:
        """예약 가능한 시간 조회"""
        if department not in self.departments:
            return {"error": f"'{department}' 진료과를 찾을 수 없습니다."}
        
        if not self.departments[department]["예약가능"]:
            return {"error": f"{department}는 현재 예약을 받지 않습니다."}
        
        # 예시 예약 시간 생성 (실제로는 병원 시스템과 연동)
        tomorrow = datetime.now() + timedelta(days=1)
        available_slots = []
        
        for hour in [9, 10, 11, 14, 15, 16]:
            slot_time = tomorrow.replace(hour=hour, minute=0)
            available_slots.append({
                "time": slot_time.strftime("%Y-%m-%d %H:%M"),
                "doctor": self.departments[department]["의사"],
                "available": True
            })
        
        return {
            "department": department,
            "doctor": self.departments[department]["의사"],
            "specialty": self.departments[department]["전문분야"],
            "available_slots": available_slots
        }

    def book_appointment(self, department: str, datetime_str: str, patient_info: Dict) -> Dict[str, Any]:
        """예약 접수"""
        try:
            appointment_time = datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
            
            booking_result = {
                "booking_id": f"BOOK_{self.session_id}_{int(datetime.now().timestamp())}",
                "department": department,
                "doctor": self.departments[department]["의사"],
                "appointment_time": appointment_time.isoformat(),
                "patient_name": patient_info.get("name", "Unknown"),
                "patient_phone": patient_info.get("phone", ""),
                "status": "confirmed",
                "notes": "예약이 완료되었습니다. 예약 시간 10분 전까지 도착해 주세요."
            }
            
            logger.info(f"Appointment booked: {booking_result}")
            return booking_result
            
        except Exception as e:
            return {"error": f"예약 중 오류가 발생했습니다: {str(e)}"}


def handler(event: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    """Medical Agent Lambda/AgentCore handler"""
    try:
        message = event.get('message', '')
        session_id = event.get('session_id')
        action = event.get('action', 'consult')
        
        agent = MedicalAgent(session_id=session_id)
        
        if action == 'consult':
            result = agent.process_message(message, context=event.get('context'))
        elif action == 'appointments':
            department = event.get('department', '')
            result = agent.get_available_appointments(department)
        elif action == 'book':
            department = event.get('department', '')
            datetime_str = event.get('datetime', '')
            patient_info = event.get('patient_info', {})
            result = agent.book_appointment(department, datetime_str, patient_info)
        else:
            result = {"error": f"Unknown action: {action}"}
        
        return {
            'statusCode': 200,
            'body': json.dumps(result, ensure_ascii=False, default=str)
        }
        
    except Exception as e:
        logger.error(f"Handler error: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'type': type(e).__name__
            }, ensure_ascii=False)
        }


if __name__ == "__main__":
    # 의료 에이전트 테스트 시나리오
    agent = MedicalAgent()
    
    test_scenarios = [
        "안녕하세요. 며칠째 열이 나고 목이 아픈데 어떤 과에 가야 할까요?",
        "아이가 계속 기침을 하고 열이 38도까지 올라가요. 응급실에 가야 할까요?",
        "무릎이 아프고 계단 오르내리기가 힘들어요. 어디서 봐야 하나요?",
        "임신 12주인데 정기 검진을 받고 싶어요.",
        "가슴이 너무 아파요! 숨도 잘 안 쉬어져요!" # 응급상황 테스트
    ]
    
    print("=== 의료 상담 AI 에이전트 테스트 ===\n")
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"🏥 상담 {i}: {scenario}")
        result = agent.process_message(scenario)
        print(f"📋 응답: {result['output']}")
        
        if result.get('is_emergency'):
            print("🚨 응급상황 감지!")
        
        if result.get('department_recommended'):
            print(f"🏥 추천 진료과: {result['department_recommended']}")
            
        print(f"⚡ 응급도: {result.get('urgency_level', 'N/A')}")
        print("-" * 80)
    
    print(f"\n📊 환자 컨텍스트: {json.dumps(agent.patient_context, ensure_ascii=False, indent=2)}")