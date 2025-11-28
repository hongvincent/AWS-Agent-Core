"""
LLM-Powered Agent for AWS Bedrock AgentCore Runtime Testing

This agent uses configurable LLM providers (OpenAI/Bedrock/Mock) to:
- Generate intelligent responses instead of simple echoes
- Test AgentCore Runtime with realistic AI interactions
- Support session management and context awareness
"""

import json
import logging
import os
import sys
from datetime import datetime
import uuid
from typing import Any, Dict

# Ensure project root is on sys.path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from tools.llm_provider import get_llm_provider

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/llm_agent.log')
    ]
)
logger = logging.getLogger(__name__)


class LLMAgent:
    """LLM-powered agent for testing AgentCore Runtime with intelligent responses"""

    def __init__(self, session_id: str = None, system_prompt: str = None):
        self.session_id = session_id or self._generate_session_id()
        self.llm_provider = get_llm_provider()
        self.system_prompt = system_prompt or self._default_system_prompt()
        self.conversation_history = []
        logger.info(f"LLMAgent initialized with session_id: {self.session_id}, provider: {self.llm_provider.provider_name}")

    def _generate_session_id(self) -> str:
        """Generate a unique session ID"""
        # Use UUID to avoid collisions when created within the same second
        return f"session_{uuid.uuid4().hex}"

    def _default_system_prompt(self) -> str:
        """Default system prompt for AgentCore testing context"""
        return (
            "당신은 AWS AgentCore 테스트를 위한 AI 어시스턴트입니다. "
            "사용자와 자연스럽게 대화하며 다음 기능을 테스트합니다:\n"
            "- 세션 관리 및 컨텍스트 유지\n"
            "- 메모리 저장 및 사용자 선호도 학습\n"
            "- 도구 호출 및 외부 서비스 연동\n"
            "한국어로 친근하고 도움이 되는 응답을 제공하세요."
        )

    def process_message(self, message: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process incoming message and generate LLM-powered response

        Args:
            message: Input message from user
            context: Optional context from memory/tools

        Returns:
            Dict containing LLM response and metadata
        """
        logger.info(f"Processing message with LLM: {message}")

        try:
            # Build conversation context
            messages = [{"role": "system", "content": self.system_prompt}]
            
            # Add conversation history (last 5 turns for context)
            messages.extend(self.conversation_history[-10:])
            
            # Add current message
            messages.append({"role": "user", "content": message})
            
            # Add context information if available
            if context:
                context_str = f"컨텍스트 정보: {json.dumps(context, ensure_ascii=False)}"
                messages.append({"role": "system", "content": context_str})

            # Generate LLM response
            response = self.llm_provider.chat(
                messages=messages,
                temperature=0.7,
                max_tokens=512
            )

            # Update conversation history
            self.conversation_history.append({"role": "user", "content": message})
            self.conversation_history.append({"role": "assistant", "content": response})

            result = {
                "session_id": self.session_id,
                "input": message,
                "output": response,
                "provider": self.llm_provider.provider_name,
                "model": self.llm_provider.model_name,
                "timestamp": datetime.now().isoformat(),
                "status": "success"
            }

            logger.info(f"LLM response generated: {response[:100]}...")
            return result

        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            fallback_response = f"죄송합니다. 처리 중 오류가 발생했습니다: {str(e)}"
            return {
                "session_id": self.session_id,
                "input": message,
                "output": fallback_response,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "status": "error"
            }

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
        agent = LLMAgent(session_id=session_id)

        # Perform action
        if action == 'echo':
            result = agent.process_message(message, context=event.get('context'))
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
    # Test the LLM agent locally
    test_events = [
        {"message": "안녕하세요! 오늘 처음 방문했어요.", "action": "echo"},
        {"message": "제 이름은 김민수이고, 강남점을 자주 이용합니다.", "action": "echo", "context": {"user_id": "user_123"}},
        {"message": "다음 주에 예약하고 싶은데 도와주세요.", "action": "echo"},
        {"message": "Session A Data", "action": "write"},
        {"action": "read"},
    ]

    for event in test_events:
        print(f"\n{'='*60}")
        print(f"Testing: {event}")
        result = handler(event)
        print(f"Result: {json.dumps(json.loads(result['body']), indent=2)}")
