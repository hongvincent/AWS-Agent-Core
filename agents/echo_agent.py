"""
Echo Agent for AWS Bedrock AgentCore Runtime Testing

This agent implements a simple echo functionality to test basic Runtime features:
- Session creation and termination
- Message handling
- CloudWatch logging integration
"""

import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/echo_agent.log')
    ]
)
logger = logging.getLogger(__name__)


class EchoAgent:
    """Simple echo agent for testing AgentCore Runtime"""

    def __init__(self, session_id: str = None):
        self.session_id = session_id or self._generate_session_id()
        logger.info(f"EchoAgent initialized with session_id: {self.session_id}")

    def _generate_session_id(self) -> str:
        """Generate a unique session ID"""
        return f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    def process_message(self, message: str) -> Dict[str, Any]:
        """
        Process incoming message and return echo response

        Args:
            message: Input message to echo

        Returns:
            Dict containing response and metadata
        """
        logger.info(f"Processing message: {message}")

        # Special handling for "ping"
        if message.lower() == "ping":
            response = "pong"
        else:
            response = f"you said: {message}"

        result = {
            "session_id": self.session_id,
            "input": message,
            "output": response,
            "timestamp": datetime.now().isoformat(),
            "status": "success"
        }

        logger.info(f"Response generated: {response}")
        return result

    def write_session_file(self, content: str) -> None:
        """
        Write content to session-specific file for isolation testing

        Args:
            content: Content to write to file
        """
        file_path = f"/tmp/session.txt"
        with open(file_path, 'w') as f:
            f.write(content)
        logger.info(f"Wrote to {file_path}: {content}")

    def read_session_file(self) -> str:
        """
        Read content from session file

        Returns:
            File content or error message
        """
        file_path = f"/tmp/session.txt"
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            logger.info(f"Read from {file_path}: {content}")
            return content
        except FileNotFoundError:
            logger.warning(f"File not found: {file_path}")
            return "FILE_NOT_FOUND"

    def cleanup(self) -> None:
        """Cleanup session resources"""
        logger.info(f"Cleaning up session: {self.session_id}")


def handler(event: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    """
    Lambda/AgentCore Runtime handler function

    Args:
        event: Input event containing message and session_id
        context: Lambda context (optional)

    Returns:
        Response dict with status and result
    """
    try:
        # Extract parameters
        message = event.get('message', '')
        session_id = event.get('session_id')
        action = event.get('action', 'echo')

        # Initialize agent
        agent = EchoAgent(session_id=session_id)

        # Perform action
        if action == 'echo':
            result = agent.process_message(message)
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

    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'type': type(e).__name__
            })
        }


if __name__ == "__main__":
    # Test the agent locally
    test_events = [
        {"message": "ping", "action": "echo"},
        {"message": "Hello, AgentCore!", "action": "echo"},
        {"message": "Session A Data", "action": "write"},
        {"action": "read"},
    ]

    for event in test_events:
        print(f"\n{'='*60}")
        print(f"Testing: {event}")
        result = handler(event)
        print(f"Result: {json.dumps(json.loads(result['body']), indent=2)}")
