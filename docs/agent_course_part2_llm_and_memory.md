# Part 2. LLM 기반 에이전트와 메모리 시스템

> 이 파트에서는 **LLM 이 단순 응답 생성기를 넘어서 “기억하고 학습하는 에이전트”가 되기 위해 필요한 설계**를 다룹니다. `LLMAgent` 가 만든 대화 기록을 기반으로, `MemoryManager` 가 어떻게 **사용자 프로필, 선호도, 토픽**을 추출·저장하는지 코드와 테스트를 통해 깊이 있게 살펴봅니다.

---

## 1. 왜 메모리가 필요한가? (에이전트 관점의 Motivation)

### 1.1 Stateless LLM vs Stateful Agent

기본적인 LLM API 호출은 보통 다음과 같이 **완전히 무상태(stateless)** 입니다.

```python
response = llm("다음 주 화요일 강남점에서 커트 예약하고 싶어요.")
```

이 호출만으로는 다음과 같은 요구를 충족하기 어렵습니다.

- "이전 대화에서 제가 뭐라고 했는지 기억하나요?"
- "제가 자주 가는 지점이 어디였죠?"
- "지난번 불만 내용을 바탕으로 이번엔 더 좋은 경험을 주고 싶어요."

**에이전트**는 이러한 요구를 만족시키기 위해 다음 두 층을 필요로 합니다.

1. **단기 메모리 (Short-term)** – 현재 세션 내 대화 히스토리와 상태
2. **장기 메모리 (Long-term)** – 여러 세션에 걸쳐 유지되는 사용자 프로필, 선호도, 이력

이 레포에서는 `LLMAgent` 가 단기 메모리를, `MemoryManager` 가 장기 메모리와 요약/추론을 담당하도록 분리해 두었습니다.

---

## 2. LLM 기반 메모리의 설계 철학

### 2.1 규칙 기반 메모리의 한계

규칙 기반 메모리는 보통 다음과 같이 작성됩니다.

```python
if "강남점" in user_input:
	preferred_branch = "강남"
```

이 방식은 구현은 간단하지만, 다음과 같은 한계를 가집니다.

- 표현이 조금만 바뀌어도 인식하지 못함 ("강남에 있는 매장" 등)
- 여러 정보가 섞여 있을 때 우선순위/맥락을 이해하지 못함
- 새로운 패턴이 들어올 때마다 코드를 수정해야 함

### 2.2 LLM 을 이용한 메모리 추론

이 레포에서는 LLM 을 활용해 **"대화에서 구조화된 메모리 JSON"을 추출**합니다.

개략적인 패턴은 다음과 같습니다.

```python
prompt = f"""다음 대화에서 사용자의 개인정보와 선호도를 추출해 주세요.

사용자 입력: {user_input}
어시스턴트 응답: {agent_response}

결과를 JSON으로 반환하세요.
예: {{"name": "김민수", "preferred_branch": "강남", "service_preference": null}}"""

preferences_json = llm_provider.generate(prompt, temperature=0.1)
preferences = json.loads(preferences_json)
```

이렇게 하면:

- 다양한 표현을 LLM 이 스스로 정규화
- 누락 정보는 `null` 처리
- 새 필드가 필요하면 프롬프트/스키마만 확장

하는 구조로 메모리 시스템이 확장 가능합니다.

---

## 3. MemoryManager 구조 훑어보기

### 3.1 역할 정리

`agents/memory_manager.py` 의 `MemoryManager` 는 크게 세 가지 역할을 합니다.

1. **세션 단위 메모리 관리** – `session_id`, `user_id` 를 키로 대화 턴을 쌓음
2. **LLM 기반 요약/선호도 추출** – 대화 히스토리를 LLM 에 넘겨 구조화된 JSON 으로 변환
3. **단기 ↔ 장기 메모리 브리지** – 자주 나타나는 정보, 중요한 피드백을 장기 저장소에 반영

코드를 일부 축약하면 다음과 같은 형태를 가집니다.

```python
class MemoryManager:
	def __init__(self):
		self.sessions: Dict[str, SessionMemory] = {}
		self.llm_provider = get_llm_provider()

	def process_turn(self, session_id: str, user_id: str, user_input: str, agent_output: str):
		session = self._get_or_create_session(session_id, user_id)
		session.add_turn(user_input, agent_output)

		# 필요 시 LLM 기반 요약/선호도 추출
		if session.should_summarize():
			summary = self._summarize_session(session)
			preferences = self._extract_preferences(session)
			session.update_summary(summary, preferences)

	def _summarize_session(self, session: SessionMemory) -> str:
		...  # LLM 에게 히스토리를 넘겨 요약

	def _extract_preferences(self, session: SessionMemory) -> Dict[str, Any]:
		...  # LLM 에게 선호도/프로필 JSON 생성 요청
```

### 3.2 SessionMemory: 한 세션의 단위 메모리

`SessionMemory` (파일 내 클래스로 정의)는 한 세션의 상태를 캡슐화합니다.

- `turns` – 사용자/에이전트 턴의 리스트
- `summary` – LLM 이 만들어 준 요약 텍스트
- `preferences` – 이름/선호 지점/자주 하는 서비스 등 구조화 정보

의사 코드는 다음과 같습니다.

```python
class SessionMemory:
	def __init__(self, session_id: str, user_id: str):
		self.session_id = session_id
		self.user_id = user_id
		self.turns: List[Dict[str, str]] = []
		self.summary: Optional[str] = None
		self.preferences: Dict[str, Any] = {}

	def add_turn(self, user_input: str, agent_output: str):
		self.turns.append({"user": user_input, "agent": agent_output})

	def should_summarize(self) -> bool:
		return len(self.turns) >= 3 and self.summary is None

	def update_summary(self, summary: str, preferences: Dict[str, Any]):
		self.summary = summary
		self.preferences.update(preferences)
```

이 구조 덕분에 MemoryManager 는 **세션의 내부 구현을 몰라도**, 표준 메서드를 통해 상태를 관리할 수 있습니다.

---

## 4. LLM Memory 테스트 살펴보기

### 4.1 LLM 메모리 기능 테스트: `tests/03-memory/test_llm_memory.py`

이 테스트는 LLM 기반 메모리가 제대로 동작하는지 검증합니다. (파일 전체를 보면서 읽어보길 권장합니다.) 주요 포인트만 정리하면:

- **세션 단위 메모리 생성** – `process_turn` 호출 후 세션이 생성되었는지 확인
- **요약 생성 조건** – 일정 턴 이상 쌓였을 때만 요약이 생성되는지 확인
- **선호도 추출 정확성** – 이름/선호 지점/서비스 타입 등이 올바른 JSON 필드로 추출되는지 확인

예시적인 테스트 패턴은 다음과 같습니다.

```python
def test_extract_basic_profile(mock_memory_manager):
	manager = mock_memory_manager

	manager.process_turn("session_1", "user_1",
		"안녕하세요, 저는 김민수이고 강남점을 자주 이용합니다.",
		"반갑습니다, 김민수님. 강남점 선호로 기록해 둘게요.")

	session = manager.get_session_memory("session_1")
	prefs = session.preferences

	assert prefs["name"] == "김민수"
	assert prefs["preferred_branch"] == "강남"
```

### 4.2 단기/장기 메모리 분리 테스트들

`tests/03-memory/` 폴더에는 다음과 같은 테스트들이 있습니다.

- `test_short_term.py` – 세션 내에서만 유지되는 단기 메모리 (최근 대화 히스토리)
- `test_long_term.py` – 여러 세션에 걸쳐 유지되는 장기 선호도 및 프로필
- `test_summary.py` – 세션 요약 및 핵심 정보 추출 로직

이 테스트들을 차례대로 실행하면서, **"어디까지를 세션이 책임지고, 어디부터를 시스템 전체 메모리가 책임지는지"** 경계를 관찰해 보는 것이 좋습니다.

```bash
pytest tests/03-memory/test_short_term.py -v
pytest tests/03-memory/test_long_term.py -v
pytest tests/03-memory/test_summary.py -v
pytest tests/03-memory/test_llm_memory.py -v
```

---

## 5. LLMAgent + MemoryManager 통합 사고 실험

이 레포에서 Runtime(Part 1) 과 Memory(Part 2)는 코드상으로는 분리되어 있지만, 실전 에이전트에서는 다음과 같은 **통합 플로우**를 갖게 됩니다.

1. 사용자가 Runtime 에이전트에 메시지를 보냅니다. (`LLMAgent.process_message`)
2. 에이전트는 LLM 응답을 생성하고, `conversation_history` 에 턴을 쌓습니다.
3. 같은 이벤트를 `MemoryManager.process_turn` 에도 전달하여, 메모리에 대화를 기록합니다.
4. `MemoryManager` 가 필요 시 요약/선호도 추출을 수행하고, 그 결과를 후속 요청의 `context` 로 다시 Runtime 에이전트에 주입합니다.

이를 코드로 표현하면 다음과 같은 형태가 됩니다.

```python
def unified_handler(event, context=None):
	session_id = event.get("session_id")
	user_id = event.get("user_id")
	message = event.get("message", "")

	# 1) Runtime 에이전트 호출
	agent = LLMAgent(session_id=session_id)
	agent_result = agent.process_message(message)

	# 2) 메모리 시스템 업데이트
	memory_manager = MemoryManager()
	memory_manager.process_turn(
		session_id=session_id,
		user_id=user_id,
		user_input=message,
		agent_output=agent_result["output"],
	)

	# 3) 필요 시 메모리 결과를 함께 반환하거나, 다음 요청의 context 로 활용
	session_mem = memory_manager.get_session_memory(session_id)

	return {
		"statusCode": 200,
		"body": json.dumps({
			"agent": agent_result,
			"memory": {
				"summary": session_mem.summary,
				"preferences": session_mem.preferences,
			},
		}, ensure_ascii=False),
	}
```

이 통합 패턴은 후속 Part (통합 테스트, RAG, 의료 도메인 에이전트) 에서 점점 현실적인 형태로 구현됩니다.

---

## 6. 직접 실행해 보는 메모리 시스템

### 6.1 MemoryManager 미니 실습

아래 스니펫은 하나의 세션에서 여러 턴을 쌓고, 그 결과로 어떤 메모리가 만들어지는지 확인하는 예시입니다.

```bash
python - << 'PY'
from agents.memory_manager import MemoryManager

manager = MemoryManager()

turns = [
	("session_1", "user_1", "안녕하세요, 저는 김민수이고 강남점을 자주 이용합니다.",
	 "반갑습니다, 김민수님. 강남점을 선호 지점으로 기록해 두겠습니다."),
	("session_1", "user_1", "다음 주 화요일 오후에 커트 예약하고 싶어요.",
	 "네, 다음 주 화요일 오후에 강남점 커트 예약 도와드리겠습니다."),
	("session_1", "user_1", "지난번에는 대기 시간이 조금 길었어요.",
	 "불편을 드려 죄송합니다. 다음 방문 시 더 빠르게 안내해 드리겠습니다."),
]

for s_id, u_id, u_in, a_out in turns:
	manager.process_turn(s_id, u_id, u_in, a_out)

session = manager.get_session_memory("session_1")
print("요약:", session.summary)
print("선호도:", session.preferences)
PY
```

실제 출력 내용은 사용 중인 LLM/Mock 구성에 따라 달라지지만, 이상적인 형태는 다음과 같습니다.

- 요약: "김민수라는 사용자가 강남점을 자주 이용하며, 커트 서비스를 예약했고, 이전 방문에서 대기 시간이 길었던 경험이 있다" 정도의 문장
- 선호도: `{ "name": "김민수", "preferred_branch": "강남", "service_preference": "커트", "pain_points": ["긴 대기 시간"] }`

### 6.2 테스트를 통한 검증 루틴

메모리 관련 실습을 마무리할 때는 아래 테스트들을 한 번에 돌려 보는 것을 추천합니다.

```bash
pytest tests/03-memory/ -v
```

테스트들이 모두 통과한다면, **메모리 시스템이 설계된 계약대로 동작하고 있으며, Runtime 에이전트와 결합될 준비가 되었다**는 의미입니다.

---

## 7. 정리 및 다음 파트 예고

이 Part 2에서 우리는 다음을 살펴보았습니다.

- LLM 을 활용해 **규칙 기반을 넘어서는 메모리 시스템**을 설계하는 이유
- `MemoryManager` 와 `SessionMemory` 구조를 통한 단기/장기 메모리 관리
- `tests/03-memory/` 를 통해 메모리 기능을 검증하는 방법
- `LLMAgent` 와 Memory 시스템을 통합하는 전형적인 플로우

다음 Part 3 에서는 이렇게 기억하고 학습하는 에이전트가 **외부 시스템(HTTP API, Lambda, OpenAPI)과 상호작용하는 방식**, 즉 **Gateway & Tools** 개념을 깊게 파고들겠습니다.

---

## 8. 퀴즈 & 실습 과제

### 8.1 개념 퀴즈

1. 단기 메모리(short-term)와 장기 메모리(long-term)의 **책임 범위 차이**를 한 줄씩 정리해 보세요.
2. 규칙 기반 메모리와 LLM 기반 메모리의 장단점을 각각 2개씩 적어보세요.
3. `SessionMemory.should_summarize()` 가 어떤 기준으로 True 를 반환하는지 설명해 보세요. 왜 그런 기준을 선택했을까요?
4. LLM 이 반환한 JSON 문자열을 파싱할 때 주의해야 할 점(예: 마크다운 코드 블록, 잘못된 따옴표 등)을 적어보세요.

### 8.2 코드 실습

1. **선호도 스키마 확장하기**
	- `SessionMemory.preferences` 에 `"pain_points"` (불편 사항 리스트) 필드를 추가해 보세요.
	- LLM 프롬프트를 수정해, 대화 중 불만/불편을 감지하면 `pain_points` 배열에 자연어 텍스트로 채우도록 유도합니다.
	- 이에 맞는 테스트를 `tests/03-memory/test_llm_memory.py` 에 추가해, 특정 불만 문장이 들어갔을 때 `pain_points` 에 값이 들어가는지 확인합니다.

2. **요약 빈도 조절하기**
	- `SessionMemory.should_summarize()` 로직을 수정해, 처음 한 번은 3턴 후, 이후에는 5턴마다 요약되도록 바꾸어 보세요.
	- 변경 후, 세션에 10개 이상의 턴을 넣어가며 요약이 몇 번 생성되는지 확인하는 테스트를 작성합니다.

3. **장기 메모리 저장소 추상화**
	- 현재 in-memory 구조를 유지하되, `MemoryManager` 에 `save_long_term(user_id, data)` / `load_long_term(user_id)` 메서드를 추가해 보세요.
	- 첫 단계에서는 단순히 내부 dict 에 저장하고 불러오는 수준으로 구현하되, 메서드 docstring 에 "추후 DynamoDB/Redis 등으로 교체 가능"하다는 의도를 명시합니다.
	- 이 두 메서드를 사용하는 작은 통합 테스트를 작성해, 한 세션에서 추출된 선호도가 다른 세션에서도 재사용되는지 확인합니다.


