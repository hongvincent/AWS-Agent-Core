# Part 3. Gateway, Tools, 그리고 OpenAPI/Lambda 연동

> 이 파트에서는 에이전트가 **실제 시스템과 상호작용**하기 위해 사용하는 "도구(Tool)" 개념을 다룹니다. Calculator HTTP 서비스, Lambda 함수, OpenAPI 스펙을 예제로 사용해, AgentCore Gateway 가 어떻게 **외부 API 를 안전하게 에이전트의 액션으로 노출**하는지 이해합니다.

---

## 1. Gateway & Tool 개념 정리

### 1.1 왜 "도구"가 필요한가?

LLM 에이전트는 자연어를 이해하고 생성하는 데 뛰어나지만, 다음과 같은 일에는 약합니다.

- 실제 DB 조회, 결제, 예약 시스템 호출
- 사내 HTTP API 호출 (인증/권한 포함)
- AWS Lambda, 내부 마이크로서비스 호출

이런 작업들은 **"도구(tool)"** 라는 명시적인 인터페이스로 분리하고, 에이전트는 도구를 호출하는 형태로 동작해야 합니다.

AgentCore Gateway 는:

- **OpenAPI 스펙 / Lambda 함수 정의** 를 읽어
- **도구 목록**으로 변환하고
- LLM 이 안전하게 호출할 수 있도록 **스키마, 파라미터 검증, 권한 제어**를 제공합니다.

이 레포에서는 `tools/` 폴더가 이러한 도구의 예시 구현을 담고 있습니다.

---

## 2. Calculator 서비스: HTTP + OpenAPI 기반 도구

### 2.1 Calculator HTTP 서비스 (`tools/calculator_service.py`)

이 서비스는 매우 단순한 사칙연산 API 이지만, 도구 설계의 전체 흐름을 보여주는 좋은 예제입니다.

핵심 구조는 다음과 같습니다.

```python
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/add", methods=["POST"])
def add():
		data = request.get_json()
		a = data.get("a")
		b = data.get("b")
		return jsonify({"result": a + b})

if __name__ == "__main__":
		app.run(host="0.0.0.0", port=8000)
```

에이전트 입장에서는 이 API 를 직접 호출하지 않고, **Gateway 가 노출한 도구 인터페이스**만 사용하게 됩니다.

### 2.2 OpenAPI 스펙 (`tools/openapi/calculator_api.yaml`)

동일한 기능을 OpenAPI 로 정의한 스펙이 `tools/openapi/calculator_api.yaml` 에 있습니다. 예를 들어, `/add` 엔드포인트는 다음과 유사한 정의를 가집니다.

```yaml
paths:
	/add:
		post:
			summary: "Add two numbers"
			requestBody:
				required: true
				content:
					application/json:
						schema:
							type: object
							properties:
								a:
									type: number
								b:
									type: number
							required: [a, b]
			responses:
				"200":
					description: "Result of addition"
					content:
						application/json:
							schema:
								type: object
								properties:
									result:
										type: number
```

Gateway 는 이 스펙을 기반으로 다음을 자동으로 제공합니다.

- 도구 이름: `calculator_add`
- 입력 스키마: `{ "a": number, "b": number }`
- 출력 스키마: `{ "result": number }`

LLM 에이전트는 자연어 요청을 다음과 같이 도구 호출로 매핑할 수 있습니다.

> 사용자: "10 더하기 5 계산해줘"
>
> 에이전트 내부 계획: `calculator_add({"a": 10, "b": 5})` 호출 후 결과를 자연어로 설명

---

## 3. Lambda 기반 도구: `tools/lambda_functions/hello_lambda.py`

### 3.1 Lambda 함수 구조

Lambda 도구는 단일 함수 형태로 정의됩니다.

```python
def handler(event, context):
		name = event.get("name", "World")
		return {
				"statusCode": 200,
				"body": json.dumps({"message": f"Hello, {name}!"})
		}
```

AgentCore Gateway 는 이 함수를 읽어 **MCP 호환 도구**로 래핑합니다.

- 도구 이름: `hello_lambda`
- 입력 스키마: `{ "name": string }`
- 출력: `{"message": "Hello, ..."}`

### 3.2 Lambda 도구 테스트: `tests/02-gateway/test_lambda_tool.py`

이 테스트는 Lambda 기반 도구가 예상대로 동작하는지 검증합니다.

- 올바른 파라미터로 호출 시 정상 응답 / 상태 코드 검증
- 누락/잘못된 파라미터일 때 적절한 검증 오류 발생 여부 확인

의사 코드는 다음과 비슷한 형태입니다.

```python
def test_hello_lambda_tool():
		client = LambdaToolClient(function_name="hello_lambda")
		result = client.invoke({"name": "AgentCore"})

		assert result["statusCode"] == 200
		body = json.loads(result["body"])
		assert body["message"].startswith("Hello, AgentCore")
```

이를 통해, **에이전트가 Lambda 함수를 직접 호출하는 것이 아니라, Gateway 가 제공하는 클라이언트를 통해 간접 호출**한다는 개념을 익힐 수 있습니다.

---

## 4. Gateway 검증 테스트들

### 4.1 OpenAPI 도구 테스트: `tests/02-gateway/test_openapi_tool.py`

이 테스트는 Calculator OpenAPI 스펙을 기반으로 생성된 도구가 올바르게 동작하는지 검증합니다.

테스트 스위트는 보통 다음을 확인합니다.

- **정상 호출** – 올바른 바디로 `/add`, `/sub`, `/mul`, `/div` 등을 호출했을 때 기대한 결과가 나오는지
- **서비스 통합** – 실제 HTTP 서비스(`calculator_service.py`)를 띄우고 요청이 제대로 전달되는지 (`--run-service-tests` 옵션)
- **에러 케이스** – 0 으로 나누기, 누락 파라미터 등

명령 예시는 다음과 같습니다.

```bash
# 1) 별도 터미널 A에서 서비스 실행
python tools/calculator_service.py

# 2) 터미널 B에서 OpenAPI 도구 테스트
pytest tests/02-gateway/test_openapi_tool.py --run-service-tests -v
```

### 4.2 Validation 테스트: `tests/02-gateway/test_validation.py`

Gateway 의 중요한 역할 중 하나는 **LLM 이 잘못된 파라미터를 생성하더라도, 백엔드에 전달되기 전에 걸러내는 것**입니다.

`test_validation.py` 는 대략 다음을 검증합니다.

- 필수 필드가 없는 요청에 대해 **명확한 Validation 에러**를 반환하는지
- 타입이 잘못된 경우 (예: 문자열 대신 숫자) 오류를 감지하는지
- 스키마에 정의되지 않은 필드를 거부하는지

의사 코드 예시는 다음과 같습니다.

```python
def test_missing_required_field(openapi_tool_client):
		with pytest.raises(ValidationError):
				openapi_tool_client.invoke({"a": 1})  # "b" 누락
```

이러한 검증 덕분에, LLM 이 완벽하지 않아도 **Gateway 레이어에서 안전하게 잘못된 호출을 차단**할 수 있습니다.

---

## 5. 에이전트 관점에서 본 "도구 호출" 시나리오

### 5.1 자연어 → 도구 호출 → 자연어 응답

실제 에이전트의 내부 플로우는 다음과 같이 정리할 수 있습니다.

1. 사용자: "10 더하기 5 계산해줘"
2. LLM: 이 요청을 해석해 `calculator_add` 도구를 사용해야 한다고 판단
3. LLM: 도구 호출 인자 `{"a": 10, "b": 5}` 를 생성
4. Gateway: OpenAPI 스펙에 따라 요청을 검증하고, HTTP 서비스에 전달
5. 서비스 응답: `{ "result": 15 }`
6. LLM: 이 결과를 자연어로 재구성
	 - "10 더하기 5의 결과는 15입니다."

### 5.2 안전한 도구 호출을 위한 베스트 프랙티스

- **스키마 설계**: OpenAPI / Lambda 인터페이스에 가능한 한 정확한 타입과 제약조건을 명시합니다.
- **Validation 계층**: Gateway 에서 모든 입력을 검증해, 백엔드에 잘못된 데이터가 도달하지 않도록 합니다.
- **권한 제어(Identity 연계)**: 민감한 도구는 IAM 역할/권한에 따라 노출 여부와 파라미터를 제한합니다. (자세한 내용은 Part 4 에서 다룹니다.)

---

## 6. 직접 실행해 보는 Gateway & Tools

### 6.1 Calculator OpenAPI 도구 전체 플로우 실습

```bash
# 1) 의존성 설치 및 환경 준비 (이미 했다면 생략)
pip install -r requirements.txt

# 2) 터미널 A: Calculator 서비스 실행
python tools/calculator_service.py

# 3) 터미널 B: OpenAPI 도구 테스트 (서비스 통합 포함)
pytest tests/02-gateway/test_openapi_tool.py --run-service-tests -v
```

테스트 로그를 보며 다음을 체크해 보세요.

- 요청 URL / 바디가 OpenAPI 스펙과 일치하는지
- 성공/실패 케이스에서 Validation 로직이 어떻게 동작하는지

### 6.2 Lambda 도구 간단 호출 실습 (로컬 시뮬레이션)

```bash
python - << 'PY'
from tools.lambda_functions.hello_lambda import handler
import json

event = {"name": "AgentCore Learner"}
resp = handler(event, None)
print(json.dumps(json.loads(resp["body"]), indent=2, ensure_ascii=False))
PY
``+

출력 예시는 다음과 비슷할 것입니다.

```json
{
	"message": "Hello, AgentCore Learner!"
}
```

---

## 7. 정리 및 다음 파트 예고

이 Part 3에서 우리는 다음을 배웠습니다.

- LLM 에이전트가 **실제 시스템과 상호작용**하기 위해서는 Gateway & Tools 레이어가 필요함
- HTTP 서비스 + OpenAPI + Lambda 로 구성된 도구 예시와, 이를 검증하는 테스트들
- Validation 을 통해 LLM 이 생성한 잘못된 요청으로부터 백엔드를 보호하는 방법

다음 Part 4 에서는 이러한 Runtime/Memory/Gateway 구조에 **Observability(추적/로그)와 Identity(권한/보안) 레이어를 더해**, 운영 가능한 프로덕션급 에이전트 시스템으로 확장하는 방법을 살펴봅니다.

---

## 8. 퀴즈 & 실습 과제

### 8.1 개념 퀴즈

1. Gateway 레이어가 없을 때, LLM 이 직접 HTTP API 를 호출하게 두면 어떤 문제가 발생할 수 있을까요? (보안/안정성/운영 측면에서 각각 1개 이상)
2. OpenAPI 스펙에서 **요청 스키마**와 **응답 스키마**를 구분해서 정의하는 이유는 무엇인가요?
3. Lambda 기반 도구와 HTTP(OpenAPI) 기반 도구의 공통점과 차이점을 각각 2개씩 적어보세요.
4. `tests/02-gateway/test_validation.py` 와 같은 Validation 테스트가 없으면, 장기적으로 어떤 문제가 생길 수 있을까요?

### 8.2 코드 실습

1. **새 Calculator 연산 추가하기**
	- `calculator_service.py` 에서 새로운 연산(예: 제곱, 모듈로 등)을 하나 추가해 보세요. 예: `/pow`, `/mod` 등.
	- 동일한 연산을 `calculator_api.yaml` OpenAPI 스펙에도 반영합니다.
	- 새 도구 엔드포인트를 검증하는 테스트를 `tests/02-gateway/test_openapi_tool.py` 에 추가합니다.

2. **Validation 강화하기**
	- OpenAPI 스펙에 파라미터 제약조건(예: `minimum`, `maximum`, `enum`)을 추가해 보세요.
	- 예: 나눗셈 `/div` 에서 분모 `b` 가 0이 될 수 없도록 `minimum: 0.0001` 같은 제약을 추가하거나, 별도 Validation 로직을 두어 0일 때는 명시적 에러를 반환하도록 수정합니다.
	- 이에 대한 실패 테스트를 `tests/02-gateway/test_validation.py` 에 추가합니다.

3. **도구 이름/설명 개선하기**
	- OpenAPI 스펙의 `summary` / `description` 필드를 더 풍부하게 채워, LLM 이 도구의 목적을 더 잘 이해하도록 돕습니다.
	- 변경 전/후에 LLM 에게 "사용 가능한 도구를 설명해 달라"는 프롬프트를 보내 보고(실제 LLM 환경이라면), 어떤 차이가 있는지 관찰해 보세요.


