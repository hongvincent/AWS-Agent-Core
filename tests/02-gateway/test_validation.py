"""
Test Suite for Gateway Validation - Parameter and Schema Validation

Tests:
1. Schema validation
2. Type checking
3. Required parameter validation
4. Error message formatting
5. Agent error handling
"""

import json
import pytest
from typing import Any, Dict
from pydantic import BaseModel, ValidationError, Field


class ToolParameter(BaseModel):
    """Model for tool parameter definition"""
    name: str
    type: str
    description: str = ""
    required: bool = False


class ToolInput(BaseModel):
    """Model for validating tool inputs"""
    a: float = Field(..., description="First number")
    b: float = Field(..., description="Second number")


class TestSchemaValidation:
    """Test schema-based validation"""

    def test_valid_input(self):
        """Test validation with valid input"""
        try:
            tool_input = ToolInput(a=10, b=5)
            assert tool_input.a == 10
            assert tool_input.b == 5
        except ValidationError:
            pytest.fail("Valid input should not raise ValidationError")

    def test_missing_required_field(self):
        """Test validation fails for missing required field"""
        with pytest.raises(ValidationError) as exc_info:
            ToolInput(a=10)  # Missing 'b'

        error = exc_info.value
        assert "b" in str(error)

    def test_invalid_type(self):
        """Test validation fails for invalid type"""
        with pytest.raises(ValidationError) as exc_info:
            ToolInput(a="not_a_number", b=5)

        error = exc_info.value
        assert "type" in str(error).lower() or "number" in str(error).lower()

    def test_type_coercion(self):
        """Test that valid type coercion works"""
        tool_input = ToolInput(a="10", b="5")  # Strings that can be converted
        assert tool_input.a == 10.0
        assert tool_input.b == 5.0

    def test_invalid_type_no_coercion(self):
        """Test that invalid strings cannot be coerced"""
        with pytest.raises(ValidationError):
            ToolInput(a="abc", b=5)


class GatewayValidator:
    """Simulates AgentCore Gateway validation logic"""

    @staticmethod
    def validate_parameters(
        parameters: Dict[str, Any],
        schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate parameters against schema

        Args:
            parameters: Input parameters
            schema: Parameter schema

        Returns:
            Validation result with errors if any
        """
        errors = []
        required = schema.get("required", [])
        properties = schema.get("properties", {})

        # Check required parameters
        for req_param in required:
            if req_param not in parameters:
                errors.append({
                    "parameter": req_param,
                    "error": "MissingRequiredParameter",
                    "message": f"Required parameter '{req_param}' is missing"
                })

        # Check types
        for param_name, param_value in parameters.items():
            if param_name not in properties:
                errors.append({
                    "parameter": param_name,
                    "error": "UnknownParameter",
                    "message": f"Parameter '{param_name}' is not defined in schema"
                })
                continue

            expected_type = properties[param_name].get("type")
            if not GatewayValidator._check_type(param_value, expected_type):
                errors.append({
                    "parameter": param_name,
                    "error": "TypeMismatch",
                    "message": f"Parameter '{param_name}' must be {expected_type}, got {type(param_value).__name__}"
                })

        if errors:
            return {
                "valid": False,
                "errors": errors
            }

        return {"valid": True}

    @staticmethod
    def _check_type(value: Any, expected_type: str) -> bool:
        """Check if value matches expected type"""
        type_map = {
            "string": str,
            "number": (int, float),
            "integer": int,
            "boolean": bool,
            "array": list,
            "object": dict
        }

        expected_python_type = type_map.get(expected_type)
        if expected_python_type is None:
            return True  # Unknown type, skip validation

        return isinstance(value, expected_python_type)


class TestGatewayValidator:
    """Test Gateway validation logic"""

    @pytest.fixture
    def calculator_schema(self):
        """Sample schema for calculator tool"""
        return {
            "type": "object",
            "properties": {
                "a": {"type": "number", "description": "First number"},
                "b": {"type": "number", "description": "Second number"}
            },
            "required": ["a", "b"]
        }

    def test_valid_parameters(self, calculator_schema):
        """Test validation passes for valid parameters"""
        params = {"a": 10, "b": 5}
        result = GatewayValidator.validate_parameters(params, calculator_schema)

        assert result["valid"] is True
        assert "errors" not in result

    def test_missing_required_parameter(self, calculator_schema):
        """Test validation fails for missing required parameter"""
        params = {"a": 10}
        result = GatewayValidator.validate_parameters(params, calculator_schema)

        assert result["valid"] is False
        assert len(result["errors"]) == 1
        assert result["errors"][0]["parameter"] == "b"
        assert result["errors"][0]["error"] == "MissingRequiredParameter"

    def test_wrong_type_parameter(self, calculator_schema):
        """Test validation fails for wrong type"""
        params = {"a": "not_a_number", "b": 5}
        result = GatewayValidator.validate_parameters(params, calculator_schema)

        assert result["valid"] is False
        assert any(e["parameter"] == "a" for e in result["errors"])
        assert any(e["error"] == "TypeMismatch" for e in result["errors"])

    def test_unknown_parameter(self, calculator_schema):
        """Test validation fails for unknown parameter"""
        params = {"a": 10, "b": 5, "c": 15}
        result = GatewayValidator.validate_parameters(params, calculator_schema)

        assert result["valid"] is False
        assert any(e["parameter"] == "c" for e in result["errors"])
        assert any(e["error"] == "UnknownParameter" for e in result["errors"])

    def test_multiple_errors(self, calculator_schema):
        """Test validation collects multiple errors"""
        params = {"a": "invalid", "c": 20}  # Wrong type + unknown param + missing param
        result = GatewayValidator.validate_parameters(params, calculator_schema)

        assert result["valid"] is False
        assert len(result["errors"]) >= 2  # At least type error and missing 'b'


class TestAgentErrorHandling:
    """Test how agents handle validation errors"""

    def test_agent_receives_validation_error(self):
        """
        Test agent receiving and processing validation error

        Scenario:
        - Agent tries to call tool with invalid parameters
        - Gateway returns validation error
        - Agent should handle error gracefully
        """
        # Agent's tool call
        tool_call = {
            "tool": "calculator_add",
            "parameters": {"a": "abc", "b": 2}
        }

        # Gateway validation error
        gateway_error = {
            "status": "error",
            "error_type": "ValidationError",
            "message": "Parameter validation failed",
            "details": [
                {
                    "parameter": "a",
                    "error": "TypeMismatch",
                    "message": "Parameter 'a' must be number, got str"
                }
            ]
        }

        # Agent processes error
        assert gateway_error["status"] == "error"
        assert gateway_error["error_type"] == "ValidationError"

        # Agent should be able to extract error details
        param_errors = gateway_error["details"]
        assert len(param_errors) > 0
        assert param_errors[0]["parameter"] == "a"

    def test_agent_formats_user_friendly_error(self):
        """Test agent formats technical error for user"""
        validation_error = {
            "parameter": "a",
            "error": "TypeMismatch",
            "message": "Parameter 'a' must be number, got str"
        }

        # Agent transforms technical error to user-friendly message
        def format_error_for_user(error: Dict[str, str]) -> str:
            """Format validation error for end user"""
            param = error["parameter"]
            error_type = error["error"]

            if error_type == "TypeMismatch":
                return f"'{param}' 파라미터는 숫자여야 합니다."
            elif error_type == "MissingRequiredParameter":
                return f"필수 파라미터 '{param}'가 누락되었습니다."
            else:
                return f"파라미터 '{param}'에 오류가 있습니다: {error['message']}"

        user_message = format_error_for_user(validation_error)

        assert "'a'" in user_message
        assert "숫자" in user_message

    def test_agent_retries_with_corrected_parameters(self):
        """
        Test agent can retry after validation error

        Scenario:
        - First call fails validation
        - Agent analyzes error
        - Agent retries with corrected parameters
        """
        # First attempt
        attempt1 = {"a": "abc", "b": 2}
        schema = {
            "type": "object",
            "properties": {
                "a": {"type": "number"},
                "b": {"type": "number"}
            },
            "required": ["a", "b"]
        }

        result1 = GatewayValidator.validate_parameters(attempt1, schema)
        assert result1["valid"] is False

        # Agent analyzes error and corrects
        # In real scenario, agent would use LLM to understand and fix error
        # Here we simulate the correction
        attempt2 = {"a": 10, "b": 2}  # Corrected

        result2 = GatewayValidator.validate_parameters(attempt2, schema)
        assert result2["valid"] is True


class TestValidationScenarios:
    """Test real-world validation scenarios"""

    def test_scenario_invalid_string_in_number_field(self):
        """
        Scenario: User asks "문자열 'abc'와 숫자 2를 더해달라"

        Expected flow:
        1. Agent tries to call calculator_add(a="abc", b=2)
        2. Gateway validation fails
        3. Agent receives validation error
        4. Agent explains to user that strings cannot be added numerically
        """
        tool_input = {"a": "abc", "b": 2}
        schema = {
            "type": "object",
            "properties": {
                "a": {"type": "number"},
                "b": {"type": "number"}
            },
            "required": ["a", "b"]
        }

        result = GatewayValidator.validate_parameters(tool_input, schema)

        # Validation should fail
        assert result["valid"] is False

        # Should have type mismatch error
        errors = result["errors"]
        assert any(
            e["error"] == "TypeMismatch" and e["parameter"] == "a"
            for e in errors
        )

        # Agent's response to user
        agent_response = """
        죄송합니다. 계산기 API는 숫자 간의 연산만 지원합니다.
        'abc'는 문자열이므로 숫자 연산에 사용할 수 없습니다.
        두 개의 숫자를 제공해 주시면 계산해 드리겠습니다.
        """

        assert "숫자" in agent_response
        assert "abc" in agent_response


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
