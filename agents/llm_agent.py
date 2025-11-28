"""
LLM-backed Agent for AWS AgentCore-style Runtime Testing

Provides a simple handler that generates responses using an LLM (OpenAI).
This is optional and only used when you provide OPENAI_API_KEY.
"""

import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, Optional

# Ensure project root is on sys.path so 'tools' is importable when run as script
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from tools.llm_client import LLMClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/llm_agent.log')
    ]
)
logger = logging.getLogger(__name__)


class LLMRuntime:
    def __init__(self, model: Optional[str] = None):
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.client = LLMClient(model=self.model)

    def respond(self, prompt: str, system: Optional[str] = None) -> str:
        return self.client.generate_text(prompt, system=system)


def handler(event: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    """
    Runtime-style handler that calls an LLM with a user message.

    event fields:
      - message: required user input
      - system: optional system instruction
      - model: optional model name (overrides OPENAI_MODEL)
    """
    try:
        message = event.get("message") or ""
        system = event.get("system")
        model = event.get("model")
        if not message:
            return {"statusCode": 400, "body": json.dumps({"error": "message is required"})}

        runtime = LLMRuntime(model=model)
        output = runtime.respond(message, system=system)
        result = {
            "input": message,
            "output": output,
            "model": runtime.model,
            "timestamp": datetime.now().isoformat(),
            "status": "success",
        }
        return {"statusCode": 200, "body": json.dumps(result, ensure_ascii=False)}
    except Exception as e:
        logger.error("LLM handler error: %s", str(e), exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e), "type": type(e).__name__})
        }


if __name__ == "__main__":
    # Simple local run example
    payload = {
        "message": os.getenv("LLM_TEST_PROMPT", "한 문장으로 자기소개 해줘."),
        "system": os.getenv("LLM_TEST_SYSTEM"),
        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    }
    resp = handler(payload)
    print(json.dumps({"statusCode": resp["statusCode"], "body": json.loads(resp["body"])}, indent=2, ensure_ascii=False))
