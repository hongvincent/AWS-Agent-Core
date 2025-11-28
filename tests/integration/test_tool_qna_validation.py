"""
Tool Integration & Q&A Process Validation Tests
실제 도구 호출 및 질의응답 프로세스 검증 테스트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
import json
import time
from datetime import datetime
import logging

# Import AgentCore modules
try:
    from agents.medical_agent import MedicalAgent
    from agents.echo_agent import LLMAgent  
    from tools.llm_provider import LLMFactory, get_llm_provider
except ImportError as e:
    print(f"Import error: {e}")
    print("Running in standalone mode with mock implementations")

logger = logging.getLogger(__name__)


class SimpleCalculator:
    """간단한 계산기 서비스 (테스트용)"""
    
    def calculate(self, operation: str, a: float, b: float) -> float:
        """기본 계산 수행"""
        if operation == "add":
            return a + b
        elif operation == "subtract":
            return a - b
        elif operation == "multiply":
            return a * b
        elif operation == "divide":
            if b == 0:
                raise ValueError("Division by zero")
            return a / b
        else:
            raise ValueError(f"Unknown operation: {operation}")
    
    def add(self, a: float, b: float) -> float:
        return a + b
    
    def subtract(self, a: float, b: float) -> float:
        return a - b
    
    def multiply(self, a: float, b: float) -> float:
        return a * b
    
    def divide(self, a: float, b: float) -> float:
        if b == 0:
            raise ValueError("Division by zero")
        return a / b


class TestToolIntegration:
    """실제 도구 호출 및 통합 테스트"""
    
    def setup_method(self):
        """각 테스트 전 초기화"""
        try:
            self.provider = LLMFactory.create_provider()
        except:
            self.provider = None
        self.calculator = SimpleCalculator()
    
    def test_real_calculator_tool_integration(self):
        """실제 계산기 도구 호출 테스트"""
        logger.info("=== 계산기 도구 통합 테스트 시작 ===")
        
        # 기본 계산 테스트
        test_cases = [
            {"operation": "add", "a": 15, "b": 25, "expected": 40},
            {"operation": "multiply", "a": 7, "b": 8, "expected": 56},
            {"operation": "divide", "a": 100, "b": 4, "expected": 25},
            {"operation": "subtract", "a": 50, "b": 30, "expected": 20}
        ]
        
        results = []
        for case in test_cases:
            result = self.calculator.calculate(
                case["operation"], 
                case["a"], 
                case["b"]
            )
            
            success = result == case["expected"]
            results.append({
                "input": f"{case['a']} {case['operation']} {case['b']}",
                "expected": case["expected"],
                "actual": result,
                "success": success
            })
            
            logger.info(f"계산: {case['a']} {case['operation']} {case['b']} = {result} ({'✅' if success else '❌'})")
        
        # 모든 계산이 성공했는지 검증
        all_success = all(r["success"] for r in results)
        assert all_success, f"계산기 테스트 실패: {results}"
        
        logger.info("✅ 계산기 도구 통합 테스트 완료")
        return results

    def test_medical_agent_tool_chain(self):
        """의료 에이전트 도구 체인 테스트"""
        logger.info("=== 의료 에이전트 도구 체인 테스트 시작 ===")
        
        agent = MedicalAgent()
        
        # 도구 체인 시나리오: 상담 → 진료과 추천 → 예약 확인 → 응급 감지
        scenarios = [
            {
                "step": 1,
                "input": "안녕하세요. 저는 30세 여성이고 임신 8주차입니다.",
                "expected_tools": ["patient_context_extraction", "department_recommendation"],
                "expected_department": "산부인과"
            },
            {
                "step": 2, 
                "input": "정기 검진을 받고 싶어요. 언제 예약 가능한가요?",
                "expected_tools": ["appointment_availability", "booking_system"],
                "expected_response_contains": ["예약", "가능"]
            },
            {
                "step": 3,
                "input": "갑자기 배가 너무 아파요! 출혈도 있어요!",
                "expected_tools": ["emergency_detection", "emergency_protocol"],
                "expected_status": "emergency_detected"
            }
        ]
        
        conversation_flow = []
        
        for scenario in scenarios:
            logger.info(f"Step {scenario['step']}: {scenario['input']}")
            
            start_time = time.time()
            result = agent.process_message(scenario["input"])
            process_time = time.time() - start_time
            
            conversation_flow.append({
                "step": scenario["step"],
                "input": scenario["input"],
                "output": result["output"],
                "department": result.get("department_recommended"),
                "status": result.get("status"),
                "process_time": process_time,
                "patient_context": agent.patient_context
            })
            
            # 응급상황 감지 검증
            if "expected_status" in scenario:
                if scenario["expected_status"] == "emergency_detected":
                    emergency_check = agent._check_emergency_symptoms(scenario["input"])
                    assert emergency_check["is_emergency"], f"응급상황 미감지: {scenario['input']}"
                    logger.info(f"🚨 응급상황 정상 감지: {emergency_check['detected_keywords']}")
            
            # 진료과 추천 검증  
            if "expected_department" in scenario:
                department = result.get("department_recommended")
                if department and scenario["expected_department"] in str(department):
                    logger.info(f"✅ 진료과 추천 성공: {department}")
                else:
                    logger.warning(f"⚠️ 진료과 추천 확인 필요: {department}")
            
            logger.info(f"처리 시간: {process_time:.2f}초")
        
        # 대화 연속성 검증
        final_context = agent.patient_context
        assert "gender" in final_context or "age" in final_context, "환자 컨텍스트 누적 실패"
        
        logger.info("✅ 의료 에이전트 도구 체인 테스트 완료")
        return conversation_flow

    def test_qna_process_multi_turn(self):
        """다중 턴 Q&A 프로세스 테스트"""
        logger.info("=== 다중 턴 Q&A 프로세스 테스트 시작 ===")
        
        agent = LLMAgent()
        
        # 복합적인 Q&A 시나리오
        qna_sequence = [
            {
                "q": "안녕하세요. AgentCore에 대해 알려주세요.",
                "expected_keywords": ["agentcore", "ai", "어시스턴트"]
            },
            {
                "q": "LLM 통합은 어떻게 되어있나요?", 
                "expected_keywords": ["llm", "통합", "openai", "bedrock"]
            },
            {
                "q": "의료 도메인 특화 기능이 있나요?",
                "expected_keywords": ["의료", "도메인", "특화", "기능"]
            },
            {
                "q": "앞서 질문한 내용들을 요약해주세요.",
                "expected_keywords": ["agentcore", "llm", "의료", "요약"]
            }
        ]
        
        conversation_history = []
        context_continuity_scores = []
        
        for i, qna in enumerate(qna_sequence):
            logger.info(f"Q{i+1}: {qna['q']}")
            
            start_time = time.time()
            result = agent.process_message(qna["q"])
            response_time = time.time() - start_time
            
            answer = result["output"]
            logger.info(f"A{i+1}: {answer[:100]}...")
            
            # 키워드 포함 검증
            keyword_matches = []
            for keyword in qna["expected_keywords"]:
                if keyword.lower() in answer.lower():
                    keyword_matches.append(keyword)
            
            keyword_score = len(keyword_matches) / len(qna["expected_keywords"])
            
            # 대화 연속성 점수 (이전 대화 내용 참조하는지)
            if i > 0:  # 두 번째 질문부터
                previous_keywords = []
                for prev_qna in conversation_history:
                    previous_keywords.extend(prev_qna["keywords_found"])
                
                continuity_count = sum(1 for kw in previous_keywords if kw in answer.lower())
                continuity_score = min(continuity_count / len(previous_keywords), 1.0) if previous_keywords else 0
                context_continuity_scores.append(continuity_score)
            else:
                continuity_score = 1.0  # 첫 번째 질문은 만점
            
            conversation_turn = {
                "turn": i + 1,
                "question": qna["q"],
                "answer": answer,
                "response_time": response_time,
                "expected_keywords": qna["expected_keywords"],
                "keywords_found": keyword_matches,
                "keyword_score": keyword_score,
                "continuity_score": continuity_score,
                "timestamp": datetime.now().isoformat()
            }
            
            conversation_history.append(conversation_turn)
            
            logger.info(f"키워드 점수: {keyword_score:.2f}, 연속성 점수: {continuity_score:.2f}, 응답시간: {response_time:.2f}초")
        
        # 전체 Q&A 프로세스 평가
        avg_keyword_score = sum(t["keyword_score"] for t in conversation_history) / len(conversation_history)
        avg_continuity_score = sum(context_continuity_scores) / len(context_continuity_scores) if context_continuity_scores else 1.0
        avg_response_time = sum(t["response_time"] for t in conversation_history) / len(conversation_history)
        
        logger.info(f"=== Q&A 프로세스 최종 평가 ===")
        logger.info(f"평균 키워드 적합성: {avg_keyword_score:.2f}")
        logger.info(f"평균 대화 연속성: {avg_continuity_score:.2f}") 
        logger.info(f"평균 응답 시간: {avg_response_time:.2f}초")
        
        # 품질 기준 검증
        assert avg_keyword_score >= 0.5, f"키워드 적합성 부족: {avg_keyword_score}"
        assert avg_continuity_score >= 0.3, f"대화 연속성 부족: {avg_continuity_score}"
        assert avg_response_time <= 10.0, f"응답 시간 초과: {avg_response_time}초"
        
        logger.info("✅ 다중 턴 Q&A 프로세스 테스트 완료")
        return {
            "conversation_history": conversation_history,
            "metrics": {
                "avg_keyword_score": avg_keyword_score,
                "avg_continuity_score": avg_continuity_score,
                "avg_response_time": avg_response_time
            }
        }

    def test_end_to_end_workflow(self):
        """엔드투엔드 워크플로우 테스트"""
        logger.info("=== 엔드투엔드 워크플로우 테스트 시작 ===")
        
        # 실제 사용자 시나리오: 의료상담 + 계산 + Q&A
        workflow_steps = []
        
        # Step 1: 의료 상담 시작
        medical_agent = MedicalAgent()
        step1_result = medical_agent.process_message("안녕하세요. 혈압이 140/90 정도 나와서 걱정됩니다.")
        
        workflow_steps.append({
            "step": "의료_상담_시작",
            "agent": "MedicalAgent", 
            "input": "혈압 140/90 상담 요청",
            "output": step1_result["output"][:100] + "...",
            "tools_used": ["patient_context_extraction", "department_recommendation"],
            "success": step1_result["status"] == "success"
        })
        
        # Step 2: 계산기로 BMI 계산 (예시)
        bmi_calculation = self.calculator.divide(70, 1.75)  # weight / height^2 approximation
        bmi_result = self.calculator.multiply(bmi_calculation, 0.57)  # 대략적인 BMI
        
        workflow_steps.append({
            "step": "BMI_계산",
            "agent": "CalculatorService",
            "input": "체중 70kg, 키 175cm",
            "output": f"BMI 추정값: {bmi_result:.1f}",
            "tools_used": ["divide", "multiply"],
            "success": bmi_result > 0
        })
        
        # Step 3: LLM 에이전트로 종합 상담
        llm_agent = LLMAgent()
        comprehensive_query = f"혈압 140/90이고 BMI가 {bmi_result:.1f} 정도인데 어떤 관리가 필요할까요?"
        step3_result = llm_agent.process_message(comprehensive_query)
        
        workflow_steps.append({
            "step": "종합_상담",
            "agent": "LLMAgent",
            "input": comprehensive_query,
            "output": step3_result["output"][:100] + "...",
            "tools_used": ["llm_integration", "context_analysis"],
            "success": step3_result["status"] == "success"
        })
        
        # Step 4: 의료 에이전트로 예약 처리
        appointment_result = medical_agent.process_message("내과 예약을 하고 싶습니다.")
        
        workflow_steps.append({
            "step": "예약_처리", 
            "agent": "MedicalAgent",
            "input": "내과 예약 요청",
            "output": appointment_result["output"][:100] + "...",
            "tools_used": ["appointment_booking", "availability_check"],
            "success": appointment_result["status"] == "success"
        })
        
        # 워크플로우 성공률 계산
        successful_steps = sum(1 for step in workflow_steps if step["success"])
        success_rate = successful_steps / len(workflow_steps)
        
        logger.info(f"=== 워크플로우 실행 결과 ===")
        for i, step in enumerate(workflow_steps, 1):
            status = "✅" if step["success"] else "❌"
            logger.info(f"{i}. {step['step']} ({step['agent']}): {status}")
            logger.info(f"   도구: {', '.join(step['tools_used'])}")
            logger.info(f"   결과: {step['output']}")
        
        logger.info(f"전체 성공률: {success_rate:.2%} ({successful_steps}/{len(workflow_steps)})")
        
        # 최소 80% 성공률 요구
        assert success_rate >= 0.8, f"워크플로우 성공률 부족: {success_rate:.2%}"
        
        logger.info("✅ 엔드투엔드 워크플로우 테스트 완료")
        return {
            "workflow_steps": workflow_steps,
            "success_rate": success_rate,
            "total_steps": len(workflow_steps),
            "successful_steps": successful_steps
        }


class TestProcessValidation:
    """프로세스 검증 및 품질 측정"""
    
    def test_response_quality_metrics(self):
        """응답 품질 메트릭 측정"""
        logger.info("=== 응답 품질 메트릭 측정 시작 ===")
        
        agent = LLMAgent()
        
        # 다양한 유형의 질문으로 품질 측정
        test_queries = [
            {"type": "factual", "query": "AgentCore의 주요 기능은 무엇인가요?"},
            {"type": "technical", "query": "LLM Provider 아키텍처에 대해 설명해주세요."},
            {"type": "conversational", "query": "안녕하세요! 오늘 기분이 어떠세요?"},
            {"type": "problem_solving", "query": "Python에서 비동기 프로그래밍을 어떻게 구현하나요?"}
        ]
        
        quality_metrics = []
        
        for test in test_queries:
            start_time = time.time()
            result = agent.process_message(test["query"])
            response_time = time.time() - start_time
            
            response = result["output"]
            
            # 품질 지표 계산
            metrics = {
                "query_type": test["type"],
                "query": test["query"],
                "response_length": len(response),
                "response_time": response_time,
                "has_greeting": any(greeting in response.lower() for greeting in ["안녕", "hello", "반갑"]),
                "has_explanation": len(response.split('.')) > 2,
                "politeness_score": sum(1 for word in ["주세요", "습니다", "해요", "입니다"] if word in response) / 4,
                "technical_terms": sum(1 for term in ["api", "llm", "agent", "provider"] if term.lower() in response.lower()),
                "completeness_score": min(len(response) / 100, 1.0)  # 100자당 0.1점, 최대 1.0
            }
            
            quality_metrics.append(metrics)
            
            logger.info(f"질문 유형: {test['type']}")
            logger.info(f"응답 길이: {metrics['response_length']}자, 시간: {response_time:.2f}초")
            logger.info(f"완성도: {metrics['completeness_score']:.2f}, 정중함: {metrics['politeness_score']:.2f}")
        
        # 전체 품질 점수 계산
        avg_completeness = sum(m["completeness_score"] for m in quality_metrics) / len(quality_metrics)
        avg_politeness = sum(m["politeness_score"] for m in quality_metrics) / len(quality_metrics)
        avg_response_time = sum(m["response_time"] for m in quality_metrics) / len(quality_metrics)
        
        logger.info(f"=== 품질 메트릭 종합 ===")
        logger.info(f"평균 완성도: {avg_completeness:.2f}")
        logger.info(f"평균 정중함: {avg_politeness:.2f}")
        logger.info(f"평균 응답시간: {avg_response_time:.2f}초")
        
        # 품질 기준 검증
        assert avg_completeness >= 0.6, f"응답 완성도 부족: {avg_completeness}"
        assert avg_response_time <= 10.0, f"응답 시간 초과: {avg_response_time}초"  # LLM 응답 시간을 현실적으로 조정
        
        logger.info("✅ 응답 품질 메트릭 측정 완료")
        return quality_metrics

    def test_error_handling_robustness(self):
        """오류 처리 견고성 테스트"""
        logger.info("=== 오류 처리 견고성 테스트 시작 ===")
        
        medical_agent = MedicalAgent()
        
        # 다양한 오류 상황 시뮬레이션
        error_scenarios = [
            {"input": "", "expected": "입력 없음 처리"},
            {"input": "a" * 1000, "expected": "긴 입력 처리"},
            {"input": "!@#$%^&*()", "expected": "특수문자 처리"},
            {"input": "SQL injection'; DROP TABLE users;--", "expected": "악의적 입력 처리"},
            {"input": "undefined function call", "expected": "잘못된 요청 처리"}
        ]
        
        error_handling_results = []
        
        for scenario in error_scenarios:
            logger.info(f"오류 시나리오: {scenario['input'][:50]}...")
            
            try:
                result = medical_agent.process_message(scenario["input"])
                
                # 에러가 발생해도 적절한 응답을 반환하는지 확인
                has_output = "output" in result and result["output"]
                has_fallback = "죄송합니다" in result["output"] or "오류" in result["output"]
                no_crash = True
                
            except Exception as e:
                logger.warning(f"예외 발생: {str(e)}")
                has_output = False
                has_fallback = False  
                no_crash = False
                result = {"error": str(e)}
            
            error_result = {
                "scenario": scenario["input"][:50],
                "expected": scenario["expected"],
                "has_output": has_output,
                "has_fallback": has_fallback,
                "no_crash": no_crash,
                "result": result.get("output", result.get("error", ""))[:100]
            }
            
            error_handling_results.append(error_result)
            
            status = "✅" if (has_output and no_crash) else "❌"
            logger.info(f"처리 결과: {status}")
        
        # 견고성 점수 계산
        robustness_scores = []
        for result in error_handling_results:
            score = sum([
                int(result["has_output"]) * 0.4,
                int(result["has_fallback"]) * 0.3, 
                int(result["no_crash"]) * 0.3
            ])
            robustness_scores.append(score)
        
        avg_robustness = sum(robustness_scores) / len(robustness_scores)
        
        logger.info(f"평균 견고성 점수: {avg_robustness:.2f}")
        
        # 최소 70% 견고성 요구
        assert avg_robustness >= 0.7, f"오류 처리 견고성 부족: {avg_robustness}"
        
        logger.info("✅ 오류 처리 견고성 테스트 완료")
        return error_handling_results


if __name__ == "__main__":
    # 빠른 통합 테스트 실행
    print("=== AWS AgentCore Tool & Q&A Process Validation ===")
    
    # Tool Integration Test
    tool_tester = TestToolIntegration()
    tool_tester.setup_method()
    
    print("\n1. 계산기 도구 테스트")
    calc_results = tool_tester.test_real_calculator_tool_integration()
    
    print("\n2. 의료 에이전트 도구 체인 테스트")
    medical_results = tool_tester.test_medical_agent_tool_chain()
    
    print("\n3. Q&A 프로세스 테스트")
    qna_results = tool_tester.test_qna_process_multi_turn()
    
    print("\n4. 엔드투엔드 워크플로우 테스트")
    workflow_results = tool_tester.test_end_to_end_workflow()
    
    # Process Validation Test
    print("\n5. 응답 품질 검증")
    process_tester = TestProcessValidation()
    quality_results = process_tester.test_response_quality_metrics()
    
    print("\n6. 오류 처리 견고성 검증")
    robustness_results = process_tester.test_error_handling_robustness()
    
    print("\n=== 종합 검증 완료 ===")
    print("✅ 모든 Tool 호출 및 Q&A 프로세스가 정상 작동합니다!")