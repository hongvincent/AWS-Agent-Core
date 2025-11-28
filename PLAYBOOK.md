# AWS AgentCore LLM 연동 실습 플레이북 

> **학습 목표**: AWS AgentCore의 핵심 기능들을 OpenAI LLM 연동을 통해 실제 AI 에이전트로 구현하고 테스트하는 완전한 워크플로우를 익힙니다.

## 📋 개요

이 플레이북은 단순한 룰 기반 시뮬레이션을 넘어서 실제 LLM을 활용한 지능형 에이전트로 AWS AgentCore 기능을 학습할 수 있도록 구성되었습니다.

### ⚡ 핵심 학습 포인트

- **🧠 LLM Provider 패턴**: OpenAI/Bedrock/Mock 공용 인터페이스 설계
- **💬 지능형 대화**: 룰 기반이 아닌 실제 LLM 기반 자연어 대화
- **🧠 컨텍스트 관리**: 대화 히스토리 및 세션 상태 유지
- **📝 메모리 시스템**: LLM 기반 사용자 선호도 추출 및 학습
- **🔍 테스트 전략**: Mock/Real LLM 환경 분리 테스트

---

## 🚀 1단계: 환경 설정 및 기본 실행

### 1.1 프로젝트 설정
```bash
# 1) 의존성 설치
source .venv/bin/activate
pip install -r requirements.txt

# 2) 환경 변수 설정 (.env에 추가됨)
# OPENAI_API_KEY=sk-proj-...
# OPENAI_MODEL=gpt-4o-mini

# 3) 기본 동작 확인
python tools/llm_provider.py --prompt "안녕하세요! 간단히 인사해 주세요."
```

**✅ 예상 결과**: OpenAI gpt-4o-mini 모델이 한국어로 자연스럽게 인사

### 1.2 LLM Provider 아키텍처 이해

**핵심 컴포넌트**:
- `LLMProvider` (추상 클래스): 공통 인터페이스
- `OpenAIProvider`: OpenAI API 연동
- `BedrockProvider`: AWS Bedrock 연동 (선택적)
- `MockProvider`: 테스트용 결정적 응답
- `LLMFactory`: 환경에 따른 자동 프로바이더 선택

**설계 철학**:
```python
# 환경에 따른 자동 선택
provider = LLMFactory.create_provider()  # OPENAI_API_KEY 있으면 OpenAI

# 명시적 선택
provider = LLMFactory.create_provider("openai")
provider = LLMFactory.create_provider("bedrock") 
provider = LLMFactory.create_provider("mock")
```

---

## 🤖 2단계: 지능형 Runtime Agent

### 2.1 LLMAgent vs 기존 EchoAgent 비교

| 기능 | EchoAgent (룰 기반) | LLMAgent (LLM 기반) |
|------|---------------------|---------------------|
| **응답 방식** | `"you said: {input}"` | LLM 생성 자연어 응답 |
| **컨텍스트** | 단발성 | 대화 히스토리 유지 |
| **언어 이해** | 키워드 매칭 | 자연어 이해 |
| **개인화** | 없음 | 시스템 프롬프트 + 컨텍스트 |

### 2.2 실습: 지능형 에이전트 테스트

```bash
# 단일 메시지 테스트
python agents/echo_agent.py

# 대화형 테스트 (컨텍스트 유지 확인)
python -c "
from agents.echo_agent import LLMAgent
agent = LLMAgent()
print('1:', agent.process_message('제 이름은 김민수입니다.'))
print('2:', agent.process_message('제 이름을 기억하시나요?'))
print('3:', agent.process_message('강남점에서 예약하고 싶어요.'))
"
```

**✅ 학습 포인트**: 
- 에이전트가 이전 대화 내용을 기억하는지 확인
- 한국어 자연어 처리가 정상 작동하는지 확인
- 시스템 프롬프트에 따라 AgentCore 역할을 수행하는지 확인

### 2.3 시스템 프롬프트 엔지니어링

`agents/echo_agent.py`의 `_default_system_prompt()` 참조:

```python
"""당신은 AWS AgentCore 테스트를 위한 AI 어시스턴트입니다. 
사용자와 자연스럽게 대화하며 다음 기능을 테스트합니다:
- 세션 관리 및 컨텍스트 유지
- 메모리 저장 및 사용자 선호도 학습  
- 도구 호출 및 외부 서비스 연동
한국어로 친근하고 도움이 되는 응답을 제공하세요."""
```

**💡 개선 아이디어**: 더 구체적인 도메인(예: 헤어샵, 병원 예약)으로 특화 가능

---

## 🧠 3단계: 지능형 Memory System

### 3.1 LLM 기반 선호도 추출

기존 룰 기반:
```python
if "강남점" in user_input:
    preferred_branch = "강남"
```

LLM 기반:
```python
prompt = f"""다음 대화에서 사용자의 개인정보와 선호도를 추출해 주세요.

사용자 입력: {user_input}
어시스턴트 응답: {agent_response}

결과를 JSON으로 반환하세요.
예: {{"name": "김민수", "preferred_branch": "강남", "service_preference": null}}"""

preferences = llm_provider.generate(prompt, temperature=0.1)
```

### 3.2 실습: 메모리 시스템 테스트

```bash
# 메모리 추출 테스트
python agents/memory_manager.py

# 전체 메모리 테스트 실행
python -m pytest tests/03-memory/test_llm_memory.py -v
```

**✅ 학습 체크리스트**:
- [ ] 사용자 이름이 정확히 추출되는가?
- [ ] 지점 선호도가 올바르게 정규화되는가? 
- [ ] 대화 토픽이 적절히 분류되는가?
- [ ] 세션 간 정보가 장기 메모리에 전달되는가?

### 3.3 고급 기능: 토픽 분류

```bash
# 토픽 추출 확인
python -c "
from agents.memory_manager import MemoryManager
manager = MemoryManager()

# 불만 + 칭찬이 섞인 복잡한 대화
manager.process_turn('session_1', 'user_1', 
    '지난번 대기시간이 너무 길었어요. 그래도 직원분은 친절했습니다.',
    '죄송합니다. 개선하겠습니다.')

memory = manager.get_session_memory('session_1')
topics = memory._extract_topics()
print('추출된 토픽:', topics)
"
```

**💡 예상 토픽**: `["complaint", "compliment", "service_inquiry"]`

---

## 🧪 4단계: 통합 테스트 및 검증

### 4.1 Mock vs Real LLM 테스트 전략

**Mock Provider 테스트** (빠름, 결정적):
```bash
python -m pytest tests/01-runtime/test_llm_agent.py::TestLLMAgent::test_basic_message_processing_mock -v
```

**Real LLM 테스트** (느림, 비용 발생, 현실적):
```bash
python -m pytest tests/01-runtime/test_llm_agent.py::TestLLMAgent::test_real_llm_integration -v
```

### 4.2 전체 워크플로우 테스트

```bash
# 1) Runtime 기능 (LLM 에이전트)
python -m pytest tests/01-runtime/test_llm_agent.py -v

# 2) Memory 기능 (LLM 메모리)  
python -m pytest tests/03-memory/test_llm_memory.py -v

# 3) 기존 기능 호환성 (업데이트된 테스트)
python -m pytest tests/01-runtime/test_echo.py tests/01-runtime/test_session_isolation.py -v
```

### 4.3 성능 및 비용 최적화

**비용 절약 팁**:
- 개발/테스트: `gpt-4o-mini` (저비용)
- 프로덕션: `gpt-4o` (고품질)
- 대용량: Mock provider로 개발 후 Real LLM 최종 검증

**토큰 최적화**:
```python
# 대화 히스토리 제한 (메모리 vs 비용 트레이드오프)
messages.extend(self.conversation_history[-10:])  # 최근 10개만

# 응답 길이 제한
max_tokens=512  # 적절한 길이로 제한
```

---

## 📊 5단계: 실행 결과 분석

### 5.1 테스트 결과 요약

**✅ 성공한 기능들**:
1. **LLM Provider 통합**: OpenAI/Mock 프로바이더 정상 작동
2. **지능형 대화**: 한국어 자연어 처리 및 컨텍스트 유지 
3. **메모리 추출**: LLM 기반 사용자 정보 및 선호도 추출
4. **세션 관리**: 독립적인 세션별 컨텍스트 격리
5. **오류 처리**: LLM API 실패 시 Fallback 메커니즘

**⚠️ 개선 필요한 영역**:
1. **JSON 파싱**: LLM이 마크다운 블록으로 감싸는 경우 처리 (✅ 수정됨)
2. **선호도 추출 정확도**: 복잡한 문장에서의 정보 추출 개선 여지
3. **토큰 관리**: 긴 대화에서의 컨텍스트 윈도우 관리

### 5.2 비즈니스 임팩트

**Before (룰 기반)**:
```
사용자: "다음 주 화요일 강남점에서 커트 예약하고 싶어요"
시스템: "you said: 다음 주 화요일 강남점에서 커트 예약하고 싶어요"
```

**After (LLM 기반)**:
```
사용자: "다음 주 화요일 강남점에서 커트 예약하고 싶어요"
시스템: "네, 강남점에서 헤어컷 예약을 도와드리겠습니다. 다음 주 화요일 원하시는 시간대가 있으신가요?"
메모리: {"preferred_branch": "강남", "service_preference": "헤어컷"}
```

---

## 🎯 6단계: 실제 프로덕션 확장

### 6.1 Bedrock 연동 (AWS 네이티브)

```bash
# AWS 자격증명 설정 후
export LLM_PROVIDER=bedrock
export BEDROCK_MODEL=anthropic.claude-3-haiku-20240307-v1:0
export AWS_REGION=us-east-1

# Bedrock으로 동일한 테스트 실행
python tools/llm_provider.py --provider bedrock --prompt "안녕하세요!"
```

### 6.2 멀티모달 확장

**향후 로드맵**:
- 이미지 입력: 제품 사진으로 예약
- 음성 입력: STT → LLM → TTS 파이프라인
- 도구 연동: Function Calling으로 실제 예약 시스템 연동

### 6.3 프로덕션 체크리스트

- [ ] **보안**: API 키 AWS Secrets Manager 관리
- [ ] **모니터링**: CloudWatch로 LLM 호출 추적
- [ ] **비용 제어**: 토큰 사용량 모니터링 및 알림
- [ ] **품질 보장**: LLM 응답 품질 메트릭 수집
- [ ] **A/B 테스트**: 다른 모델/프롬프트 성능 비교

---

## 🔍 7단계: 학습 검증 및 다음 스텝

### 7.1 핵심 개념 체크

완주하신 분은 이제 다음을 이해하고 구현할 수 있습니다:

- [ ] **추상화 패턴**: Provider 인터페이스로 여러 LLM 통합
- [ ] **상태 관리**: 세션별 컨텍스트 및 크로스 세션 메모리
- [ ] **LLM 엔지니어링**: 프롬프트 설계 및 응답 파싱
- [ ] **테스트 전략**: Mock과 Real 환경의 균형잡힌 활용
- [ ] **확장성**: 새로운 프로바이더/기능 추가 방법

### 7.2 실전 프로젝트 아이디어

1. **도메인 특화 에이전트**: 의료/법률/교육 등 전문 분야 특화
2. **멀티 에이전트 협업**: 여러 전문 에이전트가 협력하는 시스템  
3. **실시간 학습**: 사용자 피드백을 통한 지속적 개선
4. **엣지 배포**: Lambda@Edge로 글로벌 저지연 서비스

---

## 📚 추가 학습 자료

### 공식 문서
- [AWS Bedrock AgentCore 문서](https://docs.aws.amazon.com/bedrock-agentcore/)
- [OpenAI API 문서](https://platform.openai.com/docs/)
- [LangChain AgentCore 통합](https://docs.langchain.com/docs/use-cases/agents/)

### 코드 예제
- [AgentCore 샘플 리포지토리](https://github.com/awslabs/amazon-bedrock-agentcore-samples)
- [LLM Provider 패턴 예제](./tools/llm_provider.py)
- [메모리 시스템 구현](./agents/memory_manager.py)

---

## 🎉 완주 인증

이 플레이북을 완주하셨다면 **AWS AgentCore + LLM 통합 개발자**로서 다음을 달성하신 것입니다:

✅ **아키텍처 이해**: 확장 가능한 LLM 에이전트 시스템 설계  
✅ **실무 구현**: 실제 OpenAI API 연동 및 오류 처리  
✅ **테스트 전략**: 효율적이고 비용 효과적인 테스트 방법론  
✅ **프로덕션 준비**: 보안/모니터링/비용 최적화 고려사항  

**다음 도전**: 이제 실제 비즈니스 요구사항에 맞는 전문 에이전트를 구축해 보세요! 🚀

---

*📝 이 플레이북은 지속적으로 업데이트됩니다. 피드백이나 개선 제안은 언제든 환영합니다.*