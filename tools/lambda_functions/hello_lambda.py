"""
Hello Lambda Function for AgentCore Gateway Testing

This simple Lambda function is used to test Gateway's Lambda tool integration.

Input: { "name": "string" }
Output: { "message": "Hello, <name>" }
"""

import json
import logging
from typing import Any, Dict

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for hello function

    Args:
        event: Input event with 'name' parameter
        context: Lambda context

    Returns:
        Response with greeting message
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")

        # Extract name from event
        # Support both direct invocation and API Gateway formats
        if isinstance(event.get('body'), str):
            # API Gateway format
            body = json.loads(event['body'])
            name = body.get('name', 'World')
        else:
            # Direct invocation
            name = event.get('name', 'World')

        # Generate greeting
        message = f"Hello, {name}"

        logger.info(f"Generated message: {message}")

        # Return response
        response = {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'message': message,
                'name': name,
                'function': 'hello-lambda'
            })
        }

        return response

    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)

        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'error': str(e),
                'type': type(e).__name__
            })
        }


# For local testing
if __name__ == "__main__":
    # Test cases
    test_events = [
        {"name": "Sungmin"},
        {"name": "AgentCore"},
        {"body": json.dumps({"name": "API Gateway"})},
        {},  # Default case
    ]

    print("Testing hello-lambda function:\n")
    for i, event in enumerate(test_events, 1):
        print(f"Test {i}: {event}")
        result = lambda_handler(event, None)
        print(f"Result: {json.dumps(result, indent=2)}\n")
