# Part 1. AgentCore와 Runtime 에이전트 개요

> 이 파트에서는 **AgentCore 아키텍처 전체 그림**과 함께, 이 레포지토리의 `Runtime` 레이어를 담당하는 **에이전트(handler) 구조**를 깊이 있게 해부합니다. 모든 파트의 공통 기반이 되는 개념이므로, 천천히 읽으면서 코드와 테스트를 직접 실행해 보는 것을 권장합니다.

---

## 1. 이 레포지토리로 보는 AgentCore 전체 그림

### 1.1 공식 아키텍처와 이 레포의 역할

공식 문서에서 정의하는 AgentCore의 핵심 컴포넌트는 다음 다섯 가지입니다.

1. **Runtime** – MicroVM 기반 세션 격리, 장기 실행 지원 (최대 8시간)
2. **Gateway** – OpenAPI/Lambda 를 MCP 호환 도구로 자동 변환
3. **Memory** – 단기/장기 메모리 관리 및 컨텍스트 유지
4. **Observability** – OpenTelemetry 기반 추적, 디버깅, 모니터링
5. **Identity** – IAM 기반 접근 제어 및 도구별 권한 관리

이 레포지토리는 위 다섯 축을 **테스트 가능한 최소 예제(minimal but complete scenarios)** 로 구현해 놓은 학습용 프로젝트입니다.

- `agents/` : Runtime 에이전트 구현 (이 파트의 주인공)
- `tools/` : Gateway 도구 (Lambda/OpenAPI/HTTP 서비스 래핑)
- `tests/` : Runtime / Gateway / Memory / Observability / Identity / Integration 테스트 스위트

이 문서(Part 1)는 그 중에서도 **Runtime + 에이전트 구조**에 집중합니다. 나머지 축은 Part 2~4에서 점진적으로 확장합니다.

---

## 2. Runtime 에이전트의 기본 형태: Handler 패턴

### 2.1 "에이전트"를 코드 레벨에서 정의하기

이 레포에서 **에이전트(Agent)** 는 크게 두 가지 레벨로 정의됩니다.

1. **도메인 로직을 가진 클래스** (예: `LLMAgent`, `TimerAgent`, `MedicalAgent` 등)
2. **Lambda/AgentCore Runtime 이 호출할 수 있는 `handler(event, context)` 함수**

즉, Runtime 입장에서의 에이전트는 결국 아래와 같은 시그니처를 가진 함수입니다.

```python
def handler(event: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
	...
```

이 함수는 AWS Lambda 와 완전히 동일한 인터페이스를 가지며, AgentCore Runtime 에도 동일한 방식으로 배포됩니다. 내부에서는 **세션 관리, LLM 호출, 파일 시스템 접근, 메모리 연동** 등이 모두 클래스 레벨에서 처리됩니다.

### 2.2 최소 Runtime 에이전트 예제: `agents/llm_agent.py`

`agents/llm_agent.py` 는 **가장 단순한 LLM Runtime 핸들러**의 예시입니다.

```python
class LLMRuntime:
	def __init__(self, model: Optional[str] = None):
		self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
		self.client = LLMClient(model=self.model)

	def respond(self, prompt: str, system: Optional[str] = None) -> str:
		return self.client.generate_text(prompt, system=system)


def handler(event: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
	"""Runtime-style handler that calls an LLM with a user message."""
	message = event.get("message") or ""
	system = event.get("system")
	model = event.get("model")

	if not message:
		return {"statusCode": 400, "body": json.dumps({"error": "message is required"})}

	runtime = LLMRuntime(model=model)
	output = runtime.respond(message, system=system)
	result = {
		"input": message,
		"output": output,
		"model": runtime.model,
		"timestamp": datetime.now().isoformat(),
		"status": "success",
	}
	return {"statusCode": 200, "body": json.dumps(result, ensure_ascii=False)}
```

여기서 볼 수 있는 **핵심 Runtime 패턴**은 다음과 같습니다.

- `event` 에서 **사용자 입력/파라미터를 추출**한다.
- 내부에서 **도메인 로직 클래스를 인스턴스화** 한다. (`LLMRuntime`)
- 필요한 연산을 수행한 후, **JSON 직렬화 가능한 dict** 를 `body` 로 감싸서 반환한다.

이 패턴은 이후 모든 에이전트(`echo_agent`, `timer_agent`, `medical_agent` 등)에 동일하게 적용됩니다.

---

## 3. LLM 기반 Runtime 에이전트 구조: `agents/echo_agent.py`

### 3.1 LLMAgent 클래스 구조

`agents/echo_agent.py` 에 정의된 `LLMAgent` 는 **AgentCore Runtime 을 실제 LLM 과 함께 테스트하기 위한 대표 에이전트** 입니다.

핵심 필드와 초기화 로직은 다음과 같습니다.

```python
class LLMAgent:
	"""LLM-powered agent for testing AgentCore Runtime with intelligent responses"""

	def __init__(self, session_id: str = None, system_prompt: str = None):
		self.session_id = session_id or self._generate_session_id()
		self.llm_provider = get_llm_provider()
		self.system_prompt = system_prompt or self._default_system_prompt()
		self.conversation_history = []
		logger.info(
			f"LLMAgent initialized with session_id: {self.session_id}, "
			f"provider: {self.llm_provider.provider_name}"
		)
```

여기서 눈여겨볼 점은:

- `session_id` – 세션 식별자. 명시적으로 넘기지 않으면 내부에서 UUID 기반으로 생성
- `llm_provider` – 실제 LLM 호출을 담당하는 추상화 (OpenAI/Bedrock/Mock 중 하나)
- `system_prompt` – 에이전트의 역할과 말투를 정의하는 시스템 지시문
- `conversation_history` – 대화 맥락을 유지하기 위한 히스토리 버퍼

이 구조를 통해 Runtime 은 **"세션 단위 에이전트"** 를 표현할 수 있고, 테스트 코드에서 세션 별 상태를 분리해서 검증할 수 있습니다.

### 3.2 메시지 처리 플로우: `process_message`

LLMAgent 의 핵심 메서드는 `process_message` 입니다.

```python
def process_message(self, message: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
	logger.info(f"Processing message with LLM: {message}")

	# 1) 대화 컨텍스트 구성
	messages = [{"role": "system", "content": self.system_prompt}]
	messages.extend(self.conversation_history[-10:])  # 최근 10개의 턴만 유지
	messages.append({"role": "user", "content": message})

	# 2) 추가 컨텍스트(메모리/도구 결과)가 있다면 system 메시지로 주입
	if context:
		context_str = f"컨텍스트 정보: {json.dumps(context, ensure_ascii=False)}"
		messages.append({"role": "system", "content": context_str})

	# 3) LLM 호출
	response = self.llm_provider.chat(
		messages=messages,
		temperature=0.7,
		max_tokens=512,
	)

	# 4) 대화 히스토리 업데이트
	self.conversation_history.append({"role": "user", "content": message})
	self.conversation_history.append({"role": "assistant", "content": response})

	# 5) Runtime 이 다루기 쉬운 결과 형태로 래핑
	return {
		"session_id": self.session_id,
		"input": message,
		"output": response,
		"provider": self.llm_provider.provider_name,
		"model": self.llm_provider.model_name,
		"timestamp": datetime.now().isoformat(),
		"status": "success",
	}
```

이 메서드는 Runtime 관점에서 다음을 보장합니다.

- **상태(Stateful)** : `conversation_history` 를 통해 LLM 호출 간의 컨텍스트가 유지됩니다.
- **추상화(Abstraction)** : 테스트/실운영 모두 `llm_provider` 의 구현만 바꾸면 동일한 인터페이스로 동작합니다.
- **표준 출력 형태** : `session_id / input / output / provider / model / timestamp / status` 필드를 항상 포함한 dict 를 반환합니다.

테스트 코드(`tests/01-runtime/test_llm_agent.py`)는 이 계약(contract)이 잘 지켜지는지 검증합니다.

---

## 4. Runtime handler: Lambda/AgentCore 시점에서 본 에이전트

### 4.1 Handler 시그니처와 액션 분기

Runtime 은 에이전트를 클래스가 아니라 **handler 함수**를 통해 호출합니다. `echo_agent.py` 의 하단에 정의된 `handler` 는 다음과 같은 구조를 가집니다.

```python
def handler(event: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
	"""Lambda/AgentCore Runtime handler function"""
	message = event.get('message', '')
	session_id = event.get('session_id')
	action = event.get('action', 'echo')

	agent = LLMAgent(session_id=session_id)

	if action == 'echo':
		result = agent.process_message(message, context=event.get('context'))
	elif action == 'write':
		agent.write_session_file(message)
		result = {"status": "written", "session_id": agent.session_id}
	elif action == 'read':
		content = agent.read_session_file()
		result = {"status": "read", "content": content, "session_id": agent.session_id}
	else:
		result = {"error": f"Unknown action: {action}"}

	return {
		'statusCode': 200,
		'body': json.dumps(result)
	}
```

핵심 포인트:

- `event` 는 JSON 형태로 들어온 요청 전체를 담습니다.
- `session_id` 를 event 에서 받아서 LLMAgent 에 넘김으로써 **세션을 외부에서 제어**할 수 있습니다.
- `action` 필드를 통해 **동일한 에이전트에서 여러 동작(echo / write / read)** 을 수행합니다.
- 최종 반환은 Lambda 규약과 동일한 `{statusCode, body}` 형태입니다.

### 4.2 세션 격리와 `/tmp` 파일 사용

Runtime 의 중요한 특징 중 하나는 **MicroVM 기반 세션 격리**입니다. 이를 간단히 시뮬레이션하기 위해 이 레포에서는 `/tmp/session.txt` 파일을 사용합니다.

```python
def write_session_file(self, content: str) -> None:
	file_path = f"/tmp/session.txt"
	with open(file_path, 'w') as f:
		f.write(content)

def read_session_file(self) -> str:
	file_path = f"/tmp/session.txt"
	try:
		with open(file_path, 'r') as f:
			return f.read()
	except FileNotFoundError:
		return "FILE_NOT_FOUND"
```

- **로컬 실행**에서는 모든 세션이 동일한 `/tmp/session.txt` 를 공유하므로 **완전한 격리**는 되지 않습니다.
- 하지만 **AgentCore Runtime** 의 MicroVM 환경에서는 세션별로 파일 시스템이 분리되므로, 세션 A 가 쓴 파일은 세션 B 에서 보이지 않습니다.
- 테스트 코드에서 이 차이를 **명시적으로 문서화**해 두었습니다.

---

## 5. Runtime 테스트로 보는 에이전트 행위

Runtime 관련 테스트는 `tests/01-runtime/` 에 모여 있습니다.

### 5.1 LLM 에이전트의 단위/통합 테스트: `tests/01-runtime/test_llm_agent.py`

이 파일은 `LLMAgent` 가 **설계한 대로 작동하는지**를 검증합니다. 주요 테스트 케이스는 다음과 같습니다.

- `test_agent_initialization` – 세션 ID, provider, system prompt, 히스토리 초기 상태 검증
- `test_basic_message_processing_mock` – MockProvider 를 사용해 결정적인 응답과 상태 필드 검증
- `test_conversation_context_mock` – 두 번의 메시지 처리 후 히스토리 길이와 컨텍스트 유지 검증
- `test_context_injection_mock` – `context` 파라미터를 통해 외부 정보를 LLM 에 전달하는지 검증
- `test_error_handling_mock` – LLM provider 에러 발생 시 fallback 응답과 status=`error` 반환 확인
- `test_real_llm_integration` (환경변수 필요) – 실제 OpenAI/Bedrock LLM 과의 통합 검증

예를 들어, Mock 기반 메시지 처리 테스트는 다음과 같은 식입니다.

```python
def test_basic_message_processing_mock(self, mock_agent):
	response = mock_agent.process_message("안녕하세요!")

	assert response["status"] == "success"
	assert response["session_id"] == mock_agent.session_id
	assert response["input"] == "안녕하세요!"
	assert response["provider"] == "mock"
	assert "output" in response
	assert len(mock_agent.conversation_history) == 2  # User + Assistant
```

이 테스트를 통해 **AgentCore Runtime 이 기대하는 응답 스키마**가 강하게 고정됩니다.

### 5.2 세션 격리 테스트: `tests/01-runtime/test_session_isolation.py`

`test_session_isolation.py` 는 주로 `EchoAgent` (룰 기반) 를 사용해 **세션 간 상태 격리, 동시성, 수명 주기**를 검증합니다. 여기서는 개념만 요약합니다.

- `test_session_a_write_session_b_read` – 세션 A 가 쓴 데이터를 세션 B 가 읽을 수 있는지 여부를 검증하면서, **로컬 vs AgentCore Runtime** 의 차이를 문서화
- `test_multiple_messages_in_session` – 동일 세션에서 여러 메시지 처리 시 세션 ID 가 일관되게 유지되는지 검증
- `TestConcurrentSessions` – `ThreadPoolExecutor` 로 여러 세션을 동시에 실행하여 핸들러의 동시성 동작을 확인
- `TestAgentCoreRuntimeBehavior` – 실제 AgentCore 환경에서 기대되는 격리/CloudWatch 로그 통합 동작을 문서화

이 테스트 파일은 실제 MicroVM 이 없는 로컬 환경에서도 **"AgentCore 에 배포했을 때 어떻게 동작해야 하는지"**를 팀 내에서 공유하는 살아있는 문서 역할을 합니다.

---

## 6. 직접 실행해 보는 Runtime 에이전트

### 6.1 로컬에서 handler 직접 호출하기

가장 빠른 실습 방법은 Python 원라이너로 핸들러를 직접 호출해 보는 것입니다.

```bash
python -c 'from agents.llm_agent import handler; import json; \
event = {"message": "오늘 날씨처럼 상쾌하게 인사해줘"}; \
print(json.dumps(json.loads(handler(event)["body"]), indent=2, ensure_ascii=False))'
```

**예상 결과 (요약)**

- `input` : 우리가 보낸 한국어 메시지
- `output` : LLM 이 생성한 자연어 응답
- `model` : `OPENAI_MODEL` 환경변수 또는 기본값
- `status` : `success`

### 6.2 LLMAgent 직접 사용해 보기

조금 더 깊게 들어가면, `LLMAgent` 를 직접 생성해서 **대화 히스토리**가 유지되는지 확인할 수 있습니다.

```bash
python - << 'PY'
from agents.echo_agent import LLMAgent

agent = LLMAgent()

msgs = [
	"제 이름은 김민수입니다.",
	"제 이름을 기억하시나요?",
	"강남점에서 예약하고 싶어요.",
]

for i, m in enumerate(msgs, start=1):
	r = agent.process_message(m)
	print(f"[{i}] 입력: {m}")
	print(f"    응답: {r['output'][:80]}...")
	print(f"    세션: {r['session_id']}, 상태: {r['status']}")

print("\n대화 히스토리 길이:", len(agent.conversation_history))
PY
```

이 실습을 통해 다음을 체감할 수 있습니다.

- 에이전트가 **이전 발화를 기억**하고 있는지
- 동일 `session_id` 아래에서 히스토리가 누적되는지
- LLM provider 를 교체해도 상위 API 는 그대로 유지되는지

---

## 7. 정리 및 다음 파트로 넘어가기

이 Part 1에서 우리는 다음을 다뤘습니다.

- AgentCore 의 다섯 축과 이 레포의 전체 구조
- Runtime 입장에서의 **에이전트(handler) 패턴**
- `LLMRuntime` / `LLMAgent` 를 중심으로 한 LLM 기반 에이전트 구조
- 세션 ID, 대화 히스토리, `/tmp` 파일을 이용한 **세션 격리 시뮬레이션**
- `tests/01-runtime/` 의 테스트들을 통해 Runtime 동작을 검증하는 방법

이제 Part 2에서는 여기서 다룬 Runtime 개념 위에 **Memory 시스템과 LLM 기반 선호도/프로필 추출**을 얹어서, 보다 "지능형" 에이전트로 확장해 보겠습니다.

> 추천 실습 순서
> 1. `pytest tests/01-runtime/test_llm_agent.py -v` 실행
> 2. 위의 원라이너/스크립트로 `handler` 와 `LLMAgent` 직접 호출
> 3. `echo_agent.py` 를 열어 system prompt 와 액션 분기를 스스로 수정해 보기

