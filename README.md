# AWS AgentCore - Test Scenarios Repository

> AWS Bedrock AgentCore 기능별 테스트 시나리오 및 샘플 구현

이 리포지토리는 AWS Bedrock AgentCore의 주요 기능들을 **개별적으로 테스트하고 검증**하기 위한 실습용 프로젝트입니다.

## 📋 목차

- [AgentCore 개요](#agentcore-개요)
- [프로젝트 구조](#프로젝트-구조)
- [설치 및 설정](#설치-및-설정)
- [테스트 시나리오](#테스트-시나리오)
- [실행 방법](#실행-방법)
- [참고 자료](#참고-자료)

## 🎯 AgentCore 개요

AWS Bedrock AgentCore는 AI 에이전트를 프로덕션 환경에서 안전하고 확장 가능하게 배포·운영하기 위한 서비스입니다.

### 주요 컴포넌트

1. **Runtime** - MicroVM 기반 세션 격리, 장기 실행 지원 (최대 8시간)
2. **Gateway** - OpenAPI/Lambda를 MCP 호환 도구로 자동 변환
3. **Memory** - 단기/장기 메모리 관리 및 컨텍스트 유지
4. **Observability** - OpenTelemetry 기반 추적, 디버깅, 모니터링
5. **Identity** - IAM 기반 접근 제어 및 도구별 권한 관리

### 특징

- ✅ **프레임워크 무관**: LangGraph, CrewAI, LlamaIndex 등 모든 프레임워크 지원
- ✅ **모델 무관**: Bedrock 내외 모든 LLM 모델 사용 가능
- ✅ **엔터프라이즈급 보안**: VPC, PrivateLink, IAM 통합
- ✅ **자동 스케일링**: 서버리스 아키텍처로 자동 확장

## 📁 프로젝트 구조

```
AWS-Agent-Core/
├── agents/                      # 에이전트 구현
│   ├── echo_agent.py           # Runtime 테스트용 Echo 에이전트
│   ├── timer_agent.py          # 장기 실행 테스트용 Timer 에이전트
│   └── memory_manager.py       # Memory 관리 시스템
│
├── tools/                       # Gateway 도구
│   ├── lambda_functions/
│   │   └── hello_lambda.py     # 샘플 Lambda 함수
│   ├── openapi/
│   │   └── calculator_api.yaml # Calculator OpenAPI 스펙
│   └── calculator_service.py   # Calculator HTTP 서비스
│
├── tests/                       # 테스트 스위트
│   ├── 01-runtime/             # Runtime 테스트
│   │   ├── test_echo.py
│   │   ├── test_long_running.py
│   │   └── test_session_isolation.py
│   ├── 02-gateway/             # Gateway 테스트
│   │   ├── test_lambda_tool.py
│   │   ├── test_openapi_tool.py
│   │   └── test_validation.py
│   ├── 03-memory/              # Memory 테스트
│   │   ├── test_short_term.py
│   │   ├── test_long_term.py
│   │   └── test_summary.py
│   ├── 04-observability/       # Observability 테스트
│   │   └── test_trace.py
│   ├── 05-identity/            # Identity 테스트
│   │   └── test_permissions.py
│   └── 06-integration/         # 통합 테스트
│       └── test_rag_appointment.py
│
├── config/                      # 설정 파일
│   └── example.env
│
├── docs/                        # 문서
│   └── test_scenarios.md       # 상세 테스트 시나리오 가이드
│
├── requirements.txt             # Python 의존성
├── pytest.ini                   # Pytest 설정
├── conftest.py                  # Pytest fixtures
└── README.md                    # 이 파일
```

## 🚀 설치 및 설정

### 1. 사전 요구사항

- Python 3.9 이상
- AWS 계정 (AgentCore 활성화)
- AWS CLI 설정
- 선택사항: Docker (서비스 테스트용)

### 2. 설치

```bash
# 리포지토리 클론
git clone https://github.com/hongvincent/AWS-Agent-Core.git
cd AWS-Agent-Core

# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

### 3. 환경 설정

```bash
# 환경 변수 파일 생성
cp config/example.env .env

# .env 파일을 열어 AWS 계정 정보 입력
# AWS_REGION, AWS_ACCOUNT_ID 등 설정
```

## 🧪 테스트 시나리오

### 1. Runtime - 세션 실행/격리

**목적**: MicroVM 기반 세션 격리와 장기 실행 검증

```bash
# Echo 테스트 (기본 세션 기능)
pytest tests/01-runtime/test_echo.py -v

# 장기 실행 테스트 (slow 테스트 제외)
pytest tests/01-runtime/test_long_running.py -v -m "not slow"

# 세션 격리 테스트
pytest tests/01-runtime/test_session_isolation.py -v
```

**주요 시나리오**:
- ✓ 단순 Echo 실행 및 응답 확인
- ✓ 5분간 장기 실행 세션 유지
- ✓ 세션 간 파일시스템 격리

### 2. Gateway - 도구 연동

**목적**: Lambda/OpenAPI를 도구로 등록하고 호출 검증

```bash
# Lambda 도구 테스트
pytest tests/02-gateway/test_lambda_tool.py -v

# OpenAPI 도구 테스트
pytest tests/02-gateway/test_openapi_tool.py -v

# Validation 테스트
pytest tests/02-gateway/test_validation.py -v
```

**주요 시나리오**:
- ✓ Lambda 함수를 도구로 등록 및 호출
- ✓ OpenAPI 스펙 기반 도구 자동 생성
- ✓ 파라미터 검증 및 에러 처리

**Calculator 서비스 실행** (OpenAPI 테스트용):

```bash
# 별도 터미널에서 서비스 실행
python tools/calculator_service.py

# 서비스 테스트 포함하여 실행
pytest tests/02-gateway/test_openapi_tool.py --run-service-tests
```

### 3. Memory - 단기/장기 메모리

**목적**: 세션 내 컨텍스트와 사용자 프로필 유지 검증

```bash
# 단기 메모리 테스트
pytest tests/03-memory/test_short_term.py -v

# 장기 메모리 테스트
pytest tests/03-memory/test_long_term.py -v

# 요약 기능 테스트
pytest tests/03-memory/test_summary.py -v
```

**주요 시나리오**:
- ✓ 세션 내 이름/선호도 기억
- ✓ 세션 간 사용자 프로필 유지
- ✓ 대화 요약 및 핵심 정보 추출

### 4. Observability - 추적/모니터링

**목적**: 실행 흐름 추적 및 메트릭 수집 검증

```bash
pytest tests/04-observability/ -v
```

**주요 시나리오**:
- ✓ Step-by-step 실행 trace
- ✓ 토큰 사용량 및 지연시간 분석
- ✓ 에러 케이스 분류 및 재현

### 5. Identity - 권한 관리

**목적**: IAM 기반 도구별 접근 제어 검증

```bash
pytest tests/05-identity/ -v
```

**주요 시나리오**:
- ✓ Full 권한 에이전트: 모든 도구 접근 가능
- ✓ Restricted 에이전트: 일부 도구만 접근
- ✓ 자격 증명 미노출 검증

### 6. 통합 테스트 - RAG + 예약 PoC

**목적**: 모든 컴포넌트 통합 시나리오 검증

```bash
pytest tests/06-integration/ -v
```

**주요 시나리오**:
- ✓ RAG로 정보 검색 → Gateway로 예약 API 호출 → Memory에 저장
- ✓ 후속 대화에서 장기 메모리 활용하여 예약 취소

## 🏃 실행 방법

### 전체 테스트 실행

```bash
# 모든 테스트 (slow 테스트 제외)
pytest -v -m "not slow"

# 모든 테스트 (slow 포함)
pytest -v

# 특정 컴포넌트만
pytest tests/01-runtime/ -v
pytest tests/02-gateway/ -v
pytest tests/03-memory/ -v
```

### 마커별 실행

```bash
# 통합 테스트만
pytest -m integration -v

# 단위 테스트만
pytest -m unit -v

# Runtime 테스트만
pytest -m runtime -v
```

### 개별 에이전트 로컬 실행

```bash
# Echo 에이전트
python agents/echo_agent.py

# Timer 에이전트
python agents/timer_agent.py

# Memory 관리자
python agents/memory_manager.py
```

## 📊 체크리스트

테스트 완료 여부를 확인하세요:

- [ ] **Runtime**
  - [ ] Echo/타이머/세션 격리 확인
- [ ] **Gateway**
  - [ ] Lambda tool 호출
  - [ ] OpenAPI tool 호출
  - [ ] Validation 에러 처리
- [ ] **Memory**
  - [ ] 세션 내 이름/정보 기억
  - [ ] 세션 간 장기 선호도 유지
- [ ] **Observability**
  - [ ] 세션 trace 확인
  - [ ] 토큰/지연 지표 확인
  - [ ] 에러 케이스 분석
- [ ] **Identity**
  - [ ] IAM Role 별 도구 접근 제어
  - [ ] 민감 API 차단 동작 확인

## 🔧 개발 가이드

### 새 테스트 추가

```python
# tests/XX-component/test_new_feature.py
import pytest

def test_new_feature():
    """Test description"""
    # Arrange
    setup_data = {...}

    # Act
    result = perform_action(setup_data)

    # Assert
    assert result == expected_value
```

### 새 에이전트 추가

```python
# agents/my_agent.py
def handler(event, context):
    """AgentCore Runtime handler"""
    return {
        'statusCode': 200,
        'body': json.dumps({'result': 'success'})
    }
```

## 📚 참고 자료

### 공식 문서

- [AWS Bedrock AgentCore 공식 문서](https://docs.aws.amazon.com/bedrock-agentcore/)
- [AgentCore 샘플 리포지토리](https://github.com/awslabs/amazon-bedrock-agentcore-samples)
- [AWS 블로그 - AgentCore 소개](https://aws.amazon.com/blogs/aws/introducing-amazon-bedrock-agentcore-securely-deploy-and-operate-ai-agents-at-any-scale/)

### 관련 기술

- [Model Context Protocol (MCP)](https://modelcontextprotocol.io/)
- [OpenTelemetry](https://opentelemetry.io/)
- [LangGraph](https://langchain-ai.github.io/langgraph/)
- [CrewAI](https://www.crewai.com/)

## 🤝 기여

이슈 및 PR은 언제든 환영합니다!

## 📝 라이선스

MIT License

## 💬 문의

- GitHub Issues: [이슈 생성](https://github.com/hongvincent/AWS-Agent-Core/issues)
- AWS Support: AWS 계정을 통해 기술 지원 문의

---

**Last Updated**: 2025-11-18
**Version**: 1.0.0
**Maintainer**: @hongvincent
