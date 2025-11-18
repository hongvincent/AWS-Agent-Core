# claude.md — AWS AgentCore 기능별 테스트 시나리오

> 목적: AgentCore의 Gateway / Runtime / Memory / Observability / Identity 기능을 **각각 분리해서** 실습·검증하기 위한 테스트 안내용 문서.

---

## 0. 공통 사전 준비

- 전제:
  - AWS 계정 + AgentCore / Bedrock 활성화
  - `ap-northeast-2` 또는 사용 리전에 AgentCore 사용 가능 여부 확인
- 공통 리소스:
  - 테스트용 S3 버킷(로그/샘플 데이터)
  - 샘플 내부 API (또는 임시 Lambda)
  - CloudWatch Logs / Metrics 확인 권한

---

## 1. Runtime — 세션 실행/격리 테스트

### 1.1 목적
- MicroVM 기반 세션 격리, 장기 실행, 프레임워크 무관 실행을 실제로 확인.

### 1.2 테스트 준비
- 간단한 Python 에이전트 스크립트 준비:
  - 입력 프롬프트를 Echo + 간단한 계산 수행
  - 로컬 파일(`/tmp/`)에 로그 쓰기
- LangGraph 또는 단순 while loop 기반 "tool-less" 에이전트 코드로 구성

### 1.3 테스트 시나리오

1) 단순 Echo 실행
- 액션:
  - 에이전트에 `message="ping"` 입력 후 응답 확인
- 기대 결과:
  - "pong" 또는 "you said: ping" 형태 응답
  - 세션 생성 및 종료 로그가 CloudWatch에 기록

2) 장기 실행(타이머)
- 코드:
  - 5분 동안 1분마다 현재 시각을 로그에 기록하는 루프
- 액션:
  - 세션 실행 후 5분 뒤 로그 확인
- 기대 결과:
  - 세션이 중간에 끊기지 않고 일정 시간 실행
  - 로그에 5개의 타임스탬프 기록

3) 세션 격리 확인
- 코드:
  - 세션 A: `/tmp/session.txt`에 `A` 기록
  - 세션 B: `/tmp/session.txt` 읽기 시도
- 기대 결과:
  - 각 세션의 `/tmp/` 파일이 서로 보이지 않음(읽기 실패/빈 결과)

---

## 2. Gateway — 도구(툴) 연동 테스트

### 2.1 목적
- OpenAPI / Lambda / HTTP 서비스를 "툴"로 등록하고, 에이전트가 호출하는 흐름 검증.

### 2.2 테스트 준비

1) 샘플 Lambda 함수 (`hello-lambda`)
- 입력: `{ "name": "string" }`
- 출력: `{ "message": "Hello, <name>" }`

2) 샘플 HTTP API (API Gateway 혹은 임시 서버)
- `POST /add` → `{ "a": number, "b": number }` → `{ "sum": a+b }`

3) OpenAPI 스키마 작성
- `/hello` (Lambda 프록시)
- `/add` (HTTP 서비스)

### 2.3 테스트 시나리오

1) Lambda Tool 테스트
- 설정:
  - Gateway에 `hello-lambda`를 tool로 등록
- 액션:
  - 에이전트 프롬프트:
    `"name이 'Sungmin'인 사람에게 인사하는 API를 호출해서 결과를 보여줘."`
- 기대 결과:
  - 에이전트가 Lambda tool 호출
  - 응답 텍스트에 `Hello, Sungmin` 포함
  - Observability에서 tool call trace 확인 가능

2) OpenAPI Tool 테스트
- 설정:
  - `/add` 엔드포인트 포함 OpenAPI를 Gateway에 등록
- 액션:
  - 에이전트 프롬프트:
    `"3과 5를 더하기 위해 제공된 계산 API를 사용해줘."`
- 기대 결과:
  - Tool 입력: `{ "a": 3, "b": 5 }`
  - Tool 출력: `{ "sum": 8 }`
  - 최종 응답: `3 + 5 = 8`

3) Validation 테스트
- 액션:
  - 에이전트 프롬프트: `"문자열 'abc'와 숫자 2를 더해달라"` 등 잘못된 입력 유도
- 기대 결과:
  - Gateway Validation 에러 발생
  - 에이전트가 에러 메시지를 사용자 친화적으로 재표현

---

## 3. Memory — 단기/장기 메모리 테스트

### 3.1 목적
- 세션 내 단기 메모리 유지와, 사용자별 장기 메모리 저장/재활용 여부 검증.

### 3.2 테스트 준비
- 에이전트에 Memory 모듈 활성화
- Memory 저장 키: `user_id` 또는 `session_id`

### 3.3 테스트 시나리오

1) 단기 메모리(컨텍스트 유지)
- 액션:
  - ① "내 이름은 성민이야."
  - ② "내 이름이 뭐였지?"
- 기대 결과:
  - ②에 대해 "성민"이라고 답변
  - Observability에서 메모리 read/write 확인

2) 장기 메모리(프로필 저장)
- 액션:
  - 세션 #1: "나는 주로 강남점에 방문해. 다음에 예약할 때도 강남점이 기본이었으면 좋겠어."
  - 세션 종료
  - 세션 #2: "다음주 진료 예약 도와줘."
- 기대 결과:
  - 세션 #2에서 별도 지점 언급 없어도 강남점 우선 추천
  - Memory store에 `preferred_branch = "강남"` 형태 데이터 존재

3) 메모리 요약/압축 테스트
- 액션:
  - 긴 대화를 일부러 생성(10~20 turn)
  - 중간에 "지금까지 내가 말한 중요한 내용만 요약해줘"
- 기대 결과:
  - Memory가 자동 생성한 요약과 유사한 내용 응답
  - Observability에서 "summary" 관련 로그 확인

---

## 4. Observability — 추적/로그/지표 테스트

### 4.1 목적
- 세션별 실행 흐름, 도구 호출, 토큰/지연 시간 메트릭 확인.

### 4.2 테스트 시나리오

1) 단일 세션 Trace 확인
- 액션:
  - Gateway/Lambda tool을 활용하는 복합 질의 실행
- 기대 결과:
  - Observability 콘솔에서:
    - LLM 응답 단계
    - Tool 호출 단계
    - Memory read/write 단계
  - Step-by-step trace 확인

2) Latency/Token 분석
- 액션:
  - 짧은 질문/긴 질문/복수 도구 호출 세션 각각 실행
- 기대 결과:
  - CloudWatch Metrics에서:
    - 토큰 사용량 차이
    - 응답 시간(LLM vs Tool 호출 시간) 비교 가능

3) 오류 케이스 조사
- 액션:
  - 의도적으로 잘못된 파라미터 전달(Validation 에러)
  - 존재하지 않는 리소스로 API 호출
- 기대 결과:
  - Observability에 에러 유형 분류
  - 재현(Replay) 가능 여부 확인

---

## 5. Identity — 권한/보안 테스트

### 5.1 목적
- IAM Role 기반 권한 제어, 도구별 접근 제한 검증.

### 5.2 테스트 준비
- 두 개의 IAM Role:
  - `AgentRole-Full`: 예약/CRM API 모두 호출 가능
  - `AgentRole-Restricted`: 예약 API만 가능, CRM API deny
- Gateway에서 두 종류의 도구 그룹 구성:
  - 예약 관련 Tool
  - CRM 민감정보 조회 Tool

### 5.3 테스트 시나리오

1) Full 권한 에이전트
- 설정:
  - 에이전트 A → `AgentRole-Full`
- 액션:
  - "고객 010-XXXX-XXXX의 최근 예약 이력과 기본 정보 모두 알려줘."
- 기대 결과:
  - 예약 + CRM 양쪽 툴 호출 가능
  - 요청 결과 정상 응답

2) 제한 권한 에이전트
- 설정:
  - 에이전트 B → `AgentRole-Restricted`
- 액션:
  - 동일 질의 실행
- 기대 결과:
  - 예약 정보는 제공되지만
  - CRM 세부 정보는 호출 권한 부족 오류
  - 에이전트가 이를 사용자 친화적으로 설명

3) 자격 증명 미노출 검증
- 코드/로그 확인:
  - LLM 입력/출력에 AWS Access Key, Secret Key, 토큰 등이 노출되지 않음

---

## 6. TalkCRM RAG + 예약 PoC에 직접 연결하는 테스트

### 6.1 RAG + 예약 통합 시나리오

1) 병원 안내 + 예약
- 액션:
  - "부산점 위치랑 주차 안내 알려주고, 이번 주 토요일 오후에 가능한 시간에 예약까지 잡아줘."
- 기대 결과:
  - RAG: FAQ/안내문에서 위치+주차 정보 검색 → 응답
  - Gateway: 예약 API tool로 슬롯 조회 & 예약 생성
  - Memory: 해당 예약 정보/선호 지점 저장
  - Observability: 전체 플로우 trace 가능

2) 후속 대화에서 장기 메모리 활용
- 액션:
  - 며칠 뒤: "지난번에 잡았던 예약 취소해줘."
- 기대 결과:
  - Memory에서 최신 예약 ID 검색
  - Gateway → 예약 취소 API 호출
  - 취소 결과 요약 응답

---

## 7. 요약용 체크리스트

- Runtime
  - [ ] Echo/타이머/세션 격리 확인
- Gateway
  - [ ] Lambda tool 호출
  - [ ] OpenAPI tool 호출
  - [ ] Validation 에러 처리
- Memory
  - [ ] 세션 내 이름/정보 기억
  - [ ] 세션 간 장기 선호도 유지
- Observability
  - [ ] 세션 trace 확인
  - [ ] 토큰/지연 지표 확인
  - [ ] 에러 케이스 분석
- Identity
  - [ ] IAM Role 별 도구 접근 제어
  - [ ] 민감 API 차단 동작 확인
