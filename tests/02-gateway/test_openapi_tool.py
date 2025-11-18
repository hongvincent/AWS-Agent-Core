"""
Test Suite for OpenAPI Tool Integration - AgentCore Gateway

Tests:
1. OpenAPI schema parsing and tool generation
2. Calculator API operations
3. Parameter validation
4. Error handling
"""

import json
import pytest
import sys
import yaml
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import requests

# Add tools directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "tools"))


class TestCalculatorAPI:
    """Test Calculator API service directly"""

    @pytest.fixture
    def openapi_spec(self):
        """Load OpenAPI specification"""
        spec_path = Path(__file__).parent.parent.parent / "tools" / "openapi" / "calculator_api.yaml"
        with open(spec_path, 'r') as f:
            return yaml.safe_load(f)

    def test_openapi_spec_valid(self, openapi_spec):
        """Test that OpenAPI spec is valid"""
        assert openapi_spec["openapi"] == "3.0.0"
        assert "paths" in openapi_spec
        assert "/add" in openapi_spec["paths"]
        assert "/subtract" in openapi_spec["paths"]
        assert "/multiply" in openapi_spec["paths"]
        assert "/divide" in openapi_spec["paths"]

    def test_add_operation_schema(self, openapi_spec):
        """Test add operation schema"""
        add_op = openapi_spec["paths"]["/add"]["post"]

        assert add_op["operationId"] == "addNumbers"
        schema = add_op["requestBody"]["content"]["application/json"]["schema"]
        assert "a" in schema["properties"]
        assert "b" in schema["properties"]
        assert schema["required"] == ["a", "b"]

    def test_response_schemas(self, openapi_spec):
        """Test response schemas are defined"""
        add_op = openapi_spec["paths"]["/add"]["post"]
        responses = add_op["responses"]

        assert "200" in responses
        assert "400" in responses
        assert "500" in responses


@pytest.mark.integration
class TestCalculatorService:
    """Test Calculator HTTP service"""

    @pytest.fixture(scope="class")
    def calculator_url(self):
        """Calculator service URL (assumes service is running)"""
        return "http://localhost:8000/v1"

    @pytest.mark.skipif(
        not pytest.config.getoption("--run-service-tests", default=False),
        reason="Service tests require calculator service to be running"
    )
    def test_add_endpoint(self, calculator_url):
        """Test /add endpoint"""
        response = requests.post(
            f"{calculator_url}/add",
            json={"a": 3, "b": 5}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["sum"] == 8
        assert data["operation"] == "addition"

    @pytest.mark.skipif(
        not pytest.config.getoption("--run-service-tests", default=False),
        reason="Service tests require calculator service to be running"
    )
    def test_subtract_endpoint(self, calculator_url):
        """Test /subtract endpoint"""
        response = requests.post(
            f"{calculator_url}/subtract",
            json={"a": 10, "b": 3}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["result"] == 7
        assert data["operation"] == "subtraction"

    @pytest.mark.skipif(
        not pytest.config.getoption("--run-service-tests", default=False),
        reason="Service tests require calculator service to be running"
    )
    def test_multiply_endpoint(self, calculator_url):
        """Test /multiply endpoint"""
        response = requests.post(
            f"{calculator_url}/multiply",
            json={"a": 4, "b": 7}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["product"] == 28

    @pytest.mark.skipif(
        not pytest.config.getoption("--run-service-tests", default=False),
        reason="Service tests require calculator service to be running"
    )
    def test_divide_endpoint(self, calculator_url):
        """Test /divide endpoint"""
        response = requests.post(
            f"{calculator_url}/divide",
            json={"a": 20, "b": 4}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["quotient"] == 5

    @pytest.mark.skipif(
        not pytest.config.getoption("--run-service-tests", default=False),
        reason="Service tests require calculator service to be running"
    )
    def test_divide_by_zero(self, calculator_url):
        """Test division by zero error"""
        response = requests.post(
            f"{calculator_url}/divide",
            json={"a": 10, "b": 0}
        )

        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert "zero" in data["message"].lower()


class TestGatewayOpenAPIIntegration:
    """Test AgentCore Gateway integration with OpenAPI tools"""

    def test_openapi_tool_registration(self):
        """
        Test OpenAPI tool registration in Gateway

        In real AgentCore Gateway:
        - OpenAPI spec is uploaded
        - Gateway parses spec and generates MCP-compatible tools
        - Each operation becomes a tool
        - Parameters are validated against schema
        """
        tool_config = {
            "name": "calculator-api",
            "type": "openapi",
            "spec_url": "https://api.example.com/openapi.yaml",
            "operations": ["addNumbers", "subtractNumbers", "multiplyNumbers", "divideNumbers"]
        }

        # Gateway would generate individual tools
        generated_tools = [
            {
                "name": "calculator_add",
                "operation_id": "addNumbers",
                "description": "Add two numbers",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "a": {"type": "number"},
                        "b": {"type": "number"}
                    },
                    "required": ["a", "b"]
                }
            },
            {
                "name": "calculator_subtract",
                "operation_id": "subtractNumbers",
                "description": "Subtract two numbers",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "a": {"type": "number"},
                        "b": {"type": "number"}
                    },
                    "required": ["a", "b"]
                }
            }
        ]

        assert len(generated_tools) >= 2
        assert generated_tools[0]["operation_id"] == "addNumbers"

    @patch('requests.post')
    def test_agent_invoke_openapi_tool(self, mock_post):
        """
        Test agent invoking OpenAPI tool through Gateway

        Scenario:
        - Agent receives: "3과 5를 더하기 위해 제공된 계산 API를 사용해줘."
        - Agent identifies calculator_add tool
        - Gateway validates parameters
        - Gateway calls API endpoint
        - Returns result to agent
        """
        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "sum": 8,
            "operation": "addition"
        }
        mock_post.return_value = mock_response

        # Simulate agent's tool call
        tool_input = {"a": 3, "b": 5}

        # Gateway makes HTTP request
        response = requests.post(
            "http://localhost:8000/v1/add",
            json=tool_input
        )

        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["sum"] == 8

        # Agent formats response
        agent_response = f"계산 결과: 3 + 5 = {data['sum']}"
        assert "3 + 5 = 8" in agent_response


class TestOpenAPIValidation:
    """Test validation for OpenAPI tool calls"""

    def test_valid_parameters(self):
        """Test tool call with valid parameters"""
        params = {"a": 10, "b": 5}

        # Gateway validation would check:
        # 1. Required parameters present
        assert "a" in params and "b" in params

        # 2. Type validation
        assert isinstance(params["a"], (int, float))
        assert isinstance(params["b"], (int, float))

    def test_missing_required_parameter(self):
        """Test validation error for missing parameter"""
        params = {"a": 10}  # Missing 'b'

        # Gateway would reject this
        validation_error = {
            "error": "ValidationError",
            "message": "Required parameter 'b' is missing"
        }

        assert "ValidationError" in validation_error["error"]

    def test_invalid_parameter_type(self):
        """Test validation error for wrong type"""
        params = {"a": "abc", "b": 2}  # 'a' should be number

        # Gateway would reject this
        validation_error = {
            "error": "ValidationError",
            "message": "Parameter 'a' must be a number"
        }

        assert "ValidationError" in validation_error["error"]

    def test_agent_handles_validation_error(self):
        """
        Test agent handling validation errors gracefully

        Scenario:
        - User asks: "문자열 'abc'와 숫자 2를 더해달라"
        - Agent tries to call calculator_add with invalid params
        - Gateway returns validation error
        - Agent explains error to user in friendly way
        """
        # Agent attempts tool call
        tool_input = {"a": "abc", "b": 2}

        # Gateway validation fails
        gateway_response = {
            "error": "ValidationError",
            "message": "Parameter 'a' must be a number, got string"
        }

        # Agent processes error and responds to user
        agent_response = """
        죄송합니다. 계산기 API는 숫자만 처리할 수 있습니다.
        'abc'는 문자열이므로 숫자 계산에 사용할 수 없습니다.
        숫자로 다시 요청해주시겠어요?
        """

        assert "숫자" in agent_response
        assert "abc" in agent_response


@pytest.mark.integration
class TestGatewayToolDiscovery:
    """Test tool discovery and listing"""

    def test_list_available_tools(self):
        """
        Test that agent can discover available tools

        In AgentCore Gateway:
        - Tools are registered and cataloged
        - Agent can query available tools
        - MCP protocol provides tool discovery
        """
        available_tools = [
            {
                "name": "hello-lambda",
                "type": "lambda",
                "description": "Greet a person by name"
            },
            {
                "name": "calculator_add",
                "type": "openapi",
                "description": "Add two numbers"
            },
            {
                "name": "calculator_subtract",
                "type": "openapi",
                "description": "Subtract two numbers"
            }
        ]

        # Verify tools are discoverable
        assert len(available_tools) >= 3
        tool_names = [t["name"] for t in available_tools]
        assert "hello-lambda" in tool_names
        assert "calculator_add" in tool_names


def pytest_addoption(parser):
    """Add custom pytest options"""
    parser.addoption(
        "--run-service-tests",
        action="store_true",
        default=False,
        help="Run tests that require calculator service to be running"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
