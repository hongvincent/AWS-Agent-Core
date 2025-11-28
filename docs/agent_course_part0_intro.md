# Part 0. AWS AgentCore Deep-Dive 강의 안내 및 로드맵

> 이 문서는 `agent_course_part1~4`를 어떻게 따라가야 하는지, 어떤 선행 지식과 실습 환경이 필요한지, 그리고 어떤 학습 결과를 기대할 수 있는지를 안내하는 인트로입니다.

## 1. 이 강의의 대상

이 강의는 다음과 같은 분들을 대상으로 설계되었습니다.

- 이미 Python 개발 경험이 있고, pytest 로 간단한 테스트를 실행해 본 적이 있는 분
- LLM API(OpenAI, Bedrock 등)를 대략 알고 있으나, **엔터프라이즈급 에이전트 아키텍처**를 체계적으로 배우고 싶은 분
- AWS Bedrock AgentCore의 개념은 들어봤지만, 최소 예제로 전체 기능(Runtime/Gateway/Memory/Observability/Identity)을 실습해 보고 싶은 분

완전한 입문보다는, "기본기는 있고 에이전트 아키텍처를 깊게 이해하고 싶은" 개발자를 주요 대상으로 합니다.

## 2. 필요 선행 지식 및 환경

### 2.1 기술 스택

- Python 3.9 이상
- 가상환경(venv) 사용 경험
- Git/GitHub 기초

선택사항(있으면 좋음):

- OpenAI 또는 Bedrock LLM 사용 경험
- REST API / OpenAPI 스펙 이해
- AWS 기초 서비스(CloudWatch, IAM, Lambda 등)에 대한 개념

### 2.2 로컬 환경 준비 요약

```bash
# 1) 리포지토리 클론
git clone https://github.com/hongvincent/AWS-Agent-Core.git
cd AWS-Agent-Core

# 2) 가상환경 생성 및 활성화
python3 -m venv .venv
source .venv/bin/activate

# 3) 의존성 설치
pip install -r requirements.txt

# 4) (선택) .env 생성
cp config/example.env .env
```

LLM 관련 실습(Part 1~2)에서 실제 OpenAI를 사용하려면 다음 환경 변수를 설정합니다.

```bash
export OPENAI_API_KEY="<your-openai-key>"
export OPENAI_MODEL="gpt-4o-mini"  # 선택
```

## 3. 전체 로드맵 한눈에 보기

이 강의는 총 5개의 Part(0~4)로 구성됩니다.

1. **Part 0 – 인트로 & 로드맵** (이 문서)
2. **Part 1 – Runtime 에이전트 개요**
3. **Part 2 – LLM 기반 메모리 시스템**
4. **Part 3 – Gateway & Tools (OpenAPI/Lambda)**
5. **Part 4 – Observability, Identity, 통합 시나리오**

### 3.1 추천 진행 순서

1. README와 `docs/test_scenarios.md`를 훑어 전체 레포 목적 파악
2. 이 문서(Part 0)를 읽고 환경을 셋업
3. Part 1~4를 순서대로 읽으면서, 각 Part 말미의 **퀴즈/실습**을 직접 수행
4. 필요 시 `PLAYBOOK.md` 로 돌아가 LLM 연동 실습을 병행

### 3.2 각 Part의 핵심 질문

- **Part 1**: "Runtime 관점에서 에이전트란 정확히 무엇인가? 세션, handler, LLM 호출은 어떻게 설계해야 하나?"
- **Part 2**: "에이전트가 사용자를 *기억*하고 *학습*하려면 어떤 메모리 레이어가 필요할까?"
- **Part 3**: "에이전트가 실제 시스템(HTTP/Lambda/OpenAPI)과 안전하게 통신하려면 어떤 Gateway/Tool 패턴이 필요할까?"
- **Part 4**: "이 모든 것을 운영/보안 관점에서 감시·제어하고, 하나의 유스케이스로 통합하려면 무엇을 추가해야 할까?"

각 Part 문서는 위 질문들에 답을 주는 방향으로 구성되어 있습니다.

## 4. 강의 활용 팁

### 4.1 읽는 것보다 **테스트를 돌리는 것**을 우선

이 강의는 "문서"이기도 하지만 동시에 **테스트 스위트를 해설하는 가이드**입니다. 가능한 한 자주 pytest를 돌려 보세요.

```bash
# 느린 테스트 제외 전체
pytest -v -m "not slow"

# 특정 축만
pytest tests/01-runtime/ -v
pytest tests/02-gateway/ -v
pytest tests/03-memory/ -v
pytest tests/04-observability/ -v
pytest tests/05-identity/ -v
pytest tests/06-integration/ -v
```

### 4.2 "읽기 → 실행 → 수정" 루프를 돌리기

각 Part에는 다음 세 가지 요소가 항상 함께 등장합니다.

1. **개념 설명** – 아키텍처/패턴/배경 이론
2. **코드 스니펫** – 실제 `agents/`, `tools/`, `tests/` 코드 일부
3. **실습/퀴즈** – 직접 수정/추가해서 검증해 보는 과제

권장 학습 루프는 다음과 같습니다.

1. Part 내용을 한 번 읽는다.
2. 해당 Part의 테스트를 실행해 본다.
3. 실습 과제를 코드로 구현해 보고, 테스트가 여전히 통과하는지 확인한다.

## 5. 예상 학습 결과

이 강의를 끝까지 따라가면, 다음을 할 수 있게 되는 것을 목표로 합니다.

- AWS Bedrock AgentCore 아키텍처의 다섯 축(Runtime/Gateway/Memory/Observability/Identity)을 코드 레벨로 설명할 수 있다.
- Python 기반으로 **Runtime handler + LLM 기반 에이전트**를 직접 설계/구현할 수 있다.
- OpenAPI/Lambda 기반의 도구를 정의하고, 에이전트가 이를 안전하게 호출하도록 Gateway/Validation를 구성할 수 있다.
- 메모리 시스템(단기/장기/요약/선호도 추출)을 LLM과 결합해 설계할 수 있다.
- Trace/로그/권한/통합 테스트까지 고려한 **프로덕션 수준 에이전트**의 뼈대를 만들 수 있다.

## 6. 다음 단계

이제 `docs/agent_course_part1_overview_runtime.md` 부터 순서대로 읽으면서, 각 Part 하단의 **퀴즈/실습 과제**를 하나씩 해결해 보세요. 모든 실습을 완료했다면, 이미 조직 내에서 AgentCore 기반 에이전트 PoC를 이끌어 갈 수 있는 수준에 가까이 와 있을 것입니다.
