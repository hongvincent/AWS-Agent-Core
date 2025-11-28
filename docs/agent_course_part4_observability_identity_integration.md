# Part 4. Observability, Identity, 그리고 통합 시나리오

> 이 파트에서는 지금까지 구축한 Runtime / Memory / Gateway 구조 위에 **운영(Observability)과 보안(Identity)** 관점을 얹습니다. 마지막으로, 이 모든 축이 하나의 사용자 시나리오에서 어떻게 연결되는지 통합 테스트를 통해 살펴봅니다.

---

## 1. Observability: 에이전트를 "보이는" 상태로 만들기

### 1.1 왜 Observability 가 필요한가?

에이전트 시스템은 내부적으로 다음과 같은 복잡한 작업을 수행합니다.

- 여러 LLM 호출 (리트라이, 모델 변경 등)
- 다양한 도구 호출 (HTTP, Lambda, DB, RAG 등)
- 메모리 읽기/쓰기

문제가 발생했을 때, 우리는 다음 질문에 빠르게 답할 수 있어야 합니다.

- 어떤 세션에서 어떤 도구가 어떤 파라미터로 호출되었는가?
- LLM 응답이 이상해진 지점은 어디인가?
- 토큰 사용량, 응답 지연 시간은 어느 구간에서 급증했는가?

이를 위해 AgentCore 는 OpenTelemetry 기반의 **Trace / Metrics / Logs** 를 지원합니다. 이 레포에서는 주로 **Trace 관점**을 단위 테스트로 시뮬레이션합니다.

---

## 2. Trace 테스트: `tests/04-observability/test_trace.py`

### 2.1 Trace 테스트의 목표

`tests/04-observability/test_trace.py` 는 다음을 검증합니다.

- 에이전트 요청 → LLM 호출 → 도구 호출 → 메모리 업데이트까지의 **전체 플로우가 Trace 로 기록**되는지
- 각 단계가 고유한 span 으로 분리되어, 나중에 CloudWatch / X-Ray / OTEL backend 에서 시각화할 수 있는지

테스트는 보통 다음과 같은 패턴을 따릅니다.

```python
def test_trace_flow(otel_exporter, agent_client):
	# 1) 하나의 세션 요청을 실행
	response = agent_client.invoke({"message": "테스트 메시지"})

	# 2) OTEL exporter 가 보관한 span 들을 조회
	spans = otel_exporter.get_finished_spans()

	# 3) 기대한 span 구조 확인
	assert any(s.name == "agent.request" for s in spans)
	assert any(s.name == "llm.call" for s in spans)
	assert any(s.name == "tool.call" for s in spans)
```

실제 코드에서는 구체적인 span 이름/속성이 이 레포의 최소 예제를 위해 단순화되어 있을 수 있지만, 핵심 아이디어는 **"에이전트의 한 요청이 트리 구조의 Trace 로 남아야 한다"** 입니다.

### 2.2 로그와 Trace 의 관계

이 레포의 에이전트 코드들 (`echo_agent.py`, `llm_agent.py`, `timer_agent.py`, `medical_agent.py`) 는 모두 Python `logging` 을 사용해 `/tmp/*.log` 에 로그를 남깁니다.

```python
logging.basicConfig(
	level=logging.INFO,
	format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
	handlers=[
		logging.StreamHandler(sys.stdout),
		logging.FileHandler('/tmp/llm_agent.log')
	]
)
```

AgentCore Runtime 환경에서는 이러한 로그들이 CloudWatch Logs 로 자동 전송되며, Trace 와 함께 사용하면 다음이 가능합니다.

- 특정 span 이 생성한 로그만 필터링
- 세션 ID / agent ID 기준으로 로그 그룹핑

이 레포의 Trace 테스트는 이러한 실제 환경의 **축소판 시뮬레이션** 으로 이해하면 좋습니다.

---

## 3. Identity: 도구별 권한과 안전한 에이전트

### 3.1 Identity 테스트: `tests/05-identity/test_permissions.py`

에이전트가 사용할 수 있는 도구는 모두 같은 권한을 가져서는 안 됩니다. 예를 들어:

- **읽기 전용 도구**: 제품 조회, 공지사항, FAQ 등
- **민감 도구**: 결제, 환불, 계정 변경, 의료 정보 조회

`tests/05-identity/test_permissions.py` 는 다음 개념을 검증합니다.

- **Full 권한 에이전트** – 모든 도구에 접근 가능
- **Restricted 에이전트** – 일부 도구만 사용 가능
- **민감 API 차단** – 권한이 없는 에이전트가 민감 도구를 호출하면 실패해야 함

의사 코드는 다음과 같은 구조를 가집니다.

```python
def test_restricted_agent_cannot_call_sensitive_tool(permission_client):
	agent = permission_client.create_agent(role="restricted")

	with pytest.raises(PermissionError):
		agent.call_tool("payment_refund", {...})
```

AgentCore 실제 환경에서는 IAM 정책, resource-based policy, condition key 등을 통해 이 권한 구분이 이루어집니다. 이 레포의 테스트는 **그 논리를 코드 레벨에서 이해하고 검증하는 연습**이라고 볼 수 있습니다.

### 3.2 Identity 와 Gateway 의 결합

Part 3 에서 본 Gateway & Tools 레이어와 Identity 레이어가 결합되면 다음과 같은 아키텍처가 됩니다.

1. Gateway: OpenAPI / Lambda 로부터 모든 도구 목록과 스키마를 인식
2. Identity: 각 에이전트/세션의 역할(Role)에 따라, 도구 접근 허용/거부
3. Runtime: LLM 이 제안한 도구 호출 중, 허용된 것만 실제로 실행

이 구조 덕분에 **에이전트 코드가 아무리 복잡해져도, 보안 경계는 중앙집중적으로 관리**할 수 있습니다.

---

## 4. 통합 시나리오: RAG + 예약 PoC (`tests/06-integration/test_rag_appointment.py`)

### 4.1 통합 테스트의 목표

`tests/06-integration/test_rag_appointment.py` 는 지금까지의 모든 축을 하나의 유스케이스로 묶어 검증합니다.

상상해 볼 수 있는 시나리오는 다음과 같습니다.

1. 사용자가 "다음 주 화요일 강남점에서 예약하고 싶다"고 말함
2. 에이전트는 RAG 를 통해 **지점 정보, 영업시간, 예약 정책**을 검색
3. Gateway 도구를 통해 **실제 예약 API** 를 호출
4. Memory 시스템에 **예약 정보와 선호 지점**을 저장
5. Observability 레이어가 전체 플로우를 Trace 로 기록

테스트 스위트는 보통 다음을 검증합니다.

- 전체 시나리오가 에러 없이 끝까지 수행되는지
- 최종 상태(예: 예약이 생성되었다는 메모리/도구 응답)가 기대값과 일치하는지

```python
@pytest.mark.integration
def test_rag_appointment_flow(rag_agent_client):
	event = {"message": "다음 주 화요일 강남점에서 커트 예약하고 싶어요."}
	resp = rag_agent_client.invoke(event)

	body = json.loads(resp["body"])
	assert body["status"] == "success"
	assert body["appointment"]["branch"] == "강남"
```

### 4.2 전체 플로우를 머릿속에 그려보기

이 테스트를 읽을 때, 다음 흐름을 함께 상상해 보세요.

1. **Runtime** – `handler(event)` 가 세션을 생성하고, LLM 에 첫 응답을 요청함
2. **RAG** – 내부 또는 외부 지식베이스에서 관련 문서를 검색
3. **Gateway** – 예약 API 도구를 호출해 실제 예약을 생성/시뮬레이션
4. **Memory** – 이 모든 과정을 요약하고, 사용자의 선호/예약 이력을 업데이트
5. **Observability** – 위 전체 단계가 Trace + Logs 로 기록
6. **Identity** – 에이전트가 호출 가능한 도구 범위를 제한

이 플로우는 실제 프로덕션 환경에서의 AI 에이전트 구현과 거의 1:1 로 대응되는 구조입니다.

---

## 5. 의료 도메인 에이전트까지 확장 (`agents/medical_agent.py`)

### 5.1 도메인 특화 에이전트의 구조

`agents/medical_agent.py` 는 의료 도메인에 특화된 에이전트로, 다음 기능을 예시로 보여줍니다.

- 증상 기반 진료과 추천
- 병원 예약 및 일정 관리
- 의료진 정보 안내
- 응급 상황 트리아지 (긴급도 분류)

클래스 구조는 Runtime/Memory/Gateway 레이어에서 살펴본 패턴을 그대로 따르면서, **프롬프트와 도구 구성이 도메인에 맞게 특화**되어 있습니다.

### 5.2 의료 에이전트 테스트: `tests/medical/test_medical_agent.py`

이 테스트는 다음을 검증합니다.

- 기본적인 의료 상담 플로우가 오류 없이 동작하는지
- 특정 증상/질문에 대해 적절한 진료과/대응을 제안하는지
- 민감한 의료 정보가 안전하게 처리되는지 (필요 시 마스킹/비식별화)

이 파트까지 이해했다면, 여러분은 이미 **도메인 특화 AgentCore 에이전트를 설계·구현·테스트할 수 있는 수준**에 도달한 것입니다.

---

## 6. 실습: 전체 테스트 스위트 실행

마지막으로, 지금까지의 내용을 실제로 체험해 보기 위해 전체 테스트를 한 번에 돌려 봅니다.

```bash
# 느린(slow) 테스트를 제외한 전체 테스트
pytest -v -m "not slow"

# 또는 모든 테스트 (slow 포함)
pytest -v
```

특히 다음 디렉터리들의 로그/결과를 주의 깊게 살펴보세요.

- `tests/04-observability/` – Trace/로그 관점
- `tests/05-identity/` – 권한/보안 관점
- `tests/06-integration/` – 전체 유스케이스 관점

---

## 7. 전체 정리 및 다음 단계

이 Part 4를 끝으로, 이 레포지토리가 의도한 **AgentCore 학습 여정**의 큰 그림이 완성됩니다.

1. **Part 1 – Runtime**: 세션 단위 에이전트와 핸들러 패턴 이해
2. **Part 2 – Memory**: LLM 기반 단기/장기 메모리 설계
3. **Part 3 – Gateway & Tools**: 외부 시스템과의 안전한 통합
4. **Part 4 – Observability & Identity & Integration**: 운영/보안/통합 유스케이스

이제 여러분은:

- 자체 도메인에 맞는 Runtime 에이전트를 설계하고,
- LLM 기반 메모리/도구/권한 체계를 붙여,
- Observability 를 고려한 프로덕션 수준의 에이전트 시스템을 설계·검증할 수 있는 상태입니다.

다음 단계로는 실제 AWS Bedrock AgentCore 환경에 이 패턴들을 옮겨 적용하고, 조직의 인프라/보안 정책에 맞게 튜닝하는 작업이 남아 있습니다. 이 레포는 그 여정을 위한 **실습용 지도와 체크리스트** 역할을 하도록 설계되어 있습니다.

---

## 8. 퀴즈 & 실습 과제

### 8.1 개념 퀴즈

1. Trace, Logs, Metrics 세 가지 Observability 축이 각각 어떤 질문에 답하도록 도와주는지 예를 들어 설명해 보세요.
2. 세션 ID 가 Trace/로그에 포함되지 않으면, 운영 중에 어떤 어려움이 생길까요?
3. "Full 권한" 에이전트와 "Restricted" 에이전트의 차이를, 도구 목록/권한 관점에서 설명해 보세요.
4. 통합 테스트(`tests/06-integration/test_rag_appointment.py`)가 단일 유닛 테스트들보다 더 중요한 이유는 무엇일까요?

### 8.2 코드/운영 실습

1. **추적 로그에 세션 정보 추가하기**
	- `echo_agent.py` 또는 `llm_agent.py` 의 logging 부분을 수정해, 모든 로그 레코드에 `session_id` 를 포함하도록 포맷을 바꾸거나, 로그 메시지에 명시적으로 추가해 보세요.
	- 간단한 시나리오(여러 세션 ID로 handler 호출)를 실행한 뒤, 로그 파일(`/tmp/*.log`)을 열어 세션별로 로그를 필터링해 봅니다.

2. **권한 시나리오 추가하기**
	- `tests/05-identity/test_permissions.py` 에 새로운 역할(예: `read_only`) 을 추가하고, 특정 도구(예: 예약 생성)는 호출할 수 없지만 조회 도구는 사용할 수 있는 시나리오를 설계해 보세요.
	- 역할별 허용/차단 규칙이 코드에 명확히 드러나도록, 테스트 이름과 assert 메시지를 잘 작성해 둡니다.

3. **통합 시나리오 확장**
	- `tests/06-integration/test_rag_appointment.py` 와 유사하게, "예약 취소" 또는 "예약 변경" 시나리오를 추가해 보세요.
	- 기존 예약 생성 시나리오에서 생성한 데이터를 재사용하도록 설계하고, Memory 시스템이 이전 예약 정보를 어떻게 활용하는지에 대한 기대값을 테스트로 표현합니다.


