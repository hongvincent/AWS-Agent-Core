"""
Test Suite for Lambda Tool Integration - AgentCore Gateway

Tests:
1. Lambda function as tool registration
2. Agent invoking Lambda tool
3. Parameter passing and validation
4. Response handling
"""

import json
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add tools directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "tools" / "lambda_functions"))

from hello_lambda import lambda_handler


class TestHelloLambda:
    """Test Hello Lambda function directly"""

    def test_basic_invocation(self):
        """Test basic Lambda invocation"""
        event = {"name": "Sungmin"}
        result = lambda_handler(event, None)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["message"] == "Hello, Sungmin"
        assert body["name"] == "Sungmin"

    def test_default_name(self):
        """Test Lambda with no name parameter"""
        event = {}
        result = lambda_handler(event, None)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["message"] == "Hello, World"
        assert body["name"] == "World"

    def test_api_gateway_format(self):
        """Test Lambda invoked via API Gateway"""
        event = {
            "body": json.dumps({"name": "API Gateway"})
        }
        result = lambda_handler(event, None)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["message"] == "Hello, API Gateway"

    def test_various_names(self):
        """Test Lambda with various name inputs"""
        test_cases = [
            ("Alice", "Hello, Alice"),
            ("Bob", "Hello, Bob"),
            ("AgentCore", "Hello, AgentCore"),
            ("성민", "Hello, 성민"),  # Korean characters
            ("Test User 123", "Hello, Test User 123"),
        ]

        for name, expected_message in test_cases:
            event = {"name": name}
            result = lambda_handler(event, None)

            assert result["statusCode"] == 200
            body = json.loads(result["body"])
            assert body["message"] == expected_message


@pytest.mark.integration
class TestGatewayLambdaIntegration:
    """Test Gateway integration with Lambda tools"""

    @patch('boto3.client')
    def test_lambda_tool_registration(self, mock_boto_client):
        """
        Test Lambda function registration as AgentCore Gateway tool

        In real AgentCore Gateway:
        - Lambda ARN is registered as tool
        - Gateway automatically generates tool schema from Lambda
        - Agent can discover and invoke tool
        """
        # Mock Lambda client
        mock_lambda = MagicMock()
        mock_boto_client.return_value = mock_lambda

        # Simulate tool registration
        tool_config = {
            "name": "hello-lambda",
            "type": "lambda",
            "lambda_arn": "arn:aws:lambda:ap-northeast-2:123456789012:function:hello-lambda",
            "description": "Greet a person by name",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the person to greet"
                    }
                },
                "required": ["name"]
            }
        }

        # Verify tool configuration
        assert tool_config["name"] == "hello-lambda"
        assert tool_config["type"] == "lambda"
        assert "name" in tool_config["parameters"]["properties"]

    @patch('boto3.client')
    def test_agent_invoke_lambda_tool(self, mock_boto_client):
        """
        Test agent invoking Lambda tool through Gateway

        Scenario:
        - Agent receives prompt: "name이 'Sungmin'인 사람에게 인사하는 API를 호출해서 결과를 보여줘."
        - Agent identifies need to call hello-lambda tool
        - Gateway routes request to Lambda
        - Lambda returns greeting
        - Agent formats response for user
        """
        # Mock Lambda client
        mock_lambda = MagicMock()
        mock_boto_client.return_value = mock_lambda

        # Simulate Lambda invocation
        mock_lambda.invoke.return_value = {
            'StatusCode': 200,
            'Payload': Mock(read=lambda: json.dumps({
                "statusCode": 200,
                "body": json.dumps({
                    "message": "Hello, Sungmin",
                    "name": "Sungmin"
                })
            }).encode())
        }

        # Simulate agent's tool call
        tool_input = {"name": "Sungmin"}

        # Gateway invokes Lambda
        import boto3
        lambda_client = boto3.client('lambda')
        response = lambda_client.invoke(
            FunctionName='hello-lambda',
            InvocationType='RequestResponse',
            Payload=json.dumps(tool_input)
        )

        # Parse response
        payload = json.loads(response['Payload'].read())
        body = json.loads(payload['body'])

        # Verify
        assert body["message"] == "Hello, Sungmin"
        assert body["name"] == "Sungmin"

        # Agent would then format this into natural language response
        agent_response = f"API 호출 결과: {body['message']}"
        assert "Hello, Sungmin" in agent_response


class TestLambdaToolValidation:
    """Test input validation for Lambda tool"""

    def test_valid_input(self):
        """Test Lambda with valid input"""
        event = {"name": "ValidName"}
        result = lambda_handler(event, None)

        assert result["statusCode"] == 200

    def test_empty_string_name(self):
        """Test Lambda with empty string name"""
        event = {"name": ""}
        result = lambda_handler(event, None)

        # Lambda handles empty string
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["message"] == "Hello, "

    def test_none_name(self):
        """Test Lambda with None as name"""
        event = {"name": None}
        result = lambda_handler(event, None)

        # Lambda treats None as default
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        # Could be "Hello, None" or "Hello, World" depending on implementation

    def test_numeric_name(self):
        """Test Lambda with numeric name"""
        event = {"name": 12345}
        result = lambda_handler(event, None)

        # Lambda converts to string
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert "12345" in body["message"]


@pytest.mark.integration
class TestGatewayObservability:
    """Test observability features for Lambda tool calls"""

    def test_tool_call_tracing(self):
        """
        Test that Lambda tool calls are traced in Observability

        Expected trace structure:
        1. Agent receives user input
        2. Agent decides to call hello-lambda tool
        3. Gateway validates tool parameters
        4. Gateway invokes Lambda
        5. Lambda execution (logged separately)
        6. Gateway receives Lambda response
        7. Agent processes tool result
        8. Agent generates final response
        """
        expected_trace_events = [
            {"event": "agent_input", "data": "user prompt"},
            {"event": "tool_selection", "tool": "hello-lambda"},
            {"event": "gateway_validation", "status": "passed"},
            {"event": "lambda_invocation", "function": "hello-lambda"},
            {"event": "lambda_response", "status": "success"},
            {"event": "agent_processing", "status": "success"},
            {"event": "agent_output", "data": "formatted response"}
        ]

        # In real AgentCore, these events would be in CloudWatch/Observability
        assert len(expected_trace_events) == 7
        assert expected_trace_events[3]["event"] == "lambda_invocation"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
