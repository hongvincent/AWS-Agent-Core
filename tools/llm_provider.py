"""
Unified LLM Provider Interface for AWS AgentCore

Supports multiple LLM providers (OpenAI, Bedrock) with a common interface.
Provider selection via environment variables or explicit configuration.
"""

import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
import json
import logging

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 512,
        **kwargs
    ) -> str:
        """Generate text completion"""
        pass

    @abstractmethod
    def chat(
        self,
        messages: List[Dict[str, str]],
        *,
        temperature: float = 0.2,
        max_tokens: int = 512,
        **kwargs
    ) -> str:
        """Chat completion with message history"""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider identifier"""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Current model name"""
        pass


class OpenAIProvider(LLMProvider):
    """OpenAI provider implementation"""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        try:
            from openai import OpenAI
        except ImportError:
            raise RuntimeError("openai package required. Install with: pip install openai>=1.51.0")

        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")

        if not self.api_key:
            raise ValueError("OPENAI_API_KEY required")

        self.client = OpenAI(api_key=self.api_key)

    def generate(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 512,
        **kwargs
    ) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return f"[OpenAI Error: {str(e)}]"

    def chat(
        self,
        messages: List[Dict[str, str]],
        *,
        temperature: float = 0.2,
        max_tokens: int = 512,
        **kwargs
    ) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"OpenAI chat error: {e}")
            return f"[OpenAI Chat Error: {str(e)}]"

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self.model


class BedrockProvider(LLMProvider):
    """AWS Bedrock provider implementation"""

    def __init__(self, region: Optional[str] = None, model: Optional[str] = None):
        try:
            import boto3
        except ImportError:
            raise RuntimeError("boto3 package required. Install with: pip install boto3>=1.34.0")

        self.region = region or os.getenv("AWS_REGION", "us-east-1")
        self.model = model or os.getenv("BEDROCK_MODEL", "anthropic.claude-3-haiku-20240307-v1:0")

        try:
            self.client = boto3.client("bedrock-runtime", region_name=self.region)
        except Exception as e:
            logger.error(f"Bedrock client initialization failed: {e}")
            raise

    def generate(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 512,
        **kwargs
    ) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        return self.chat(messages, temperature=temperature, max_tokens=max_tokens, **kwargs)

    def chat(
        self,
        messages: List[Dict[str, str]],
        *,
        temperature: float = 0.2,
        max_tokens: int = 512,
        **kwargs
    ) -> str:
        try:
            # Format for Claude-3 Anthropic models
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": messages
            }

            response = self.client.invoke_model(
                modelId=self.model,
                body=json.dumps(body)
            )

            result = json.loads(response['body'].read())
            return result['content'][0]['text'].strip()

        except Exception as e:
            logger.error(f"Bedrock API error: {e}")
            return f"[Bedrock Error: {str(e)}]"

    @property
    def provider_name(self) -> str:
        return "bedrock"

    @property
    def model_name(self) -> str:
        return self.model


class MockProvider(LLMProvider):
    """Mock provider for testing without API calls"""

    def __init__(self, model: str = "mock-model"):
        self.model = model

    def generate(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 512,
        **kwargs
    ) -> str:
        # Simple rule-based responses for deterministic testing
        prompt_lower = prompt.lower()
        if "안녕" in prompt_lower or "hello" in prompt_lower:
            return "안녕하세요! 반갑습니다."
        elif "이름" in prompt_lower or "name" in prompt_lower:
            return "저는 AgentCore 테스트용 AI 어시스턴트입니다."
        elif "강남" in prompt_lower:
            return "강남점에 대한 정보를 도와드리겠습니다."
        elif "예약" in prompt_lower or "appointment" in prompt_lower:
            return "예약 관련 도움을 제공하겠습니다."
        elif "당뇨병" in prompt_lower or "진단" in prompt_lower:
            return "의학적 진단은 전문 의료진과 상담하시길 권합니다. 내과 진료를 받아보세요."
        elif "의료" in prompt_lower or "병원" in prompt_lower or "증상" in prompt_lower:
            return "의료 상담을 위해 적절한 진료과에서 전문의와 상담받으시기 바랍니다."
        else:
            return f"[Mock Response] 입력하신 내용: {prompt[:50]}..."

    def chat(
        self,
        messages: List[Dict[str, str]],
        *,
        temperature: float = 0.2,
        max_tokens: int = 512,
        **kwargs
    ) -> str:
        if not messages:
            return "[Mock] 메시지가 없습니다."

        last_message = messages[-1].get("content", "")
        return self.generate(last_message, temperature=temperature, max_tokens=max_tokens, **kwargs)

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def model_name(self) -> str:
        return self.model


class LLMFactory:
    """Factory for creating LLM providers based on configuration"""

    @staticmethod
    def create_provider(
        provider_type: Optional[str] = None,
        **kwargs
    ) -> LLMProvider:
        """
        Create LLM provider based on environment or explicit type

        Args:
            provider_type: "openai", "bedrock", "mock", or None for auto-detection
            **kwargs: Provider-specific configuration

        Returns:
            Configured LLM provider instance
        """
        # Auto-detect if not specified
        if provider_type is None:
            provider_type = os.getenv("LLM_PROVIDER", "").lower()

            # Fallback detection logic
            if not provider_type:
                if os.getenv("OPENAI_API_KEY"):
                    provider_type = "openai"
                elif os.getenv("AWS_REGION") and os.getenv("AWS_ACCESS_KEY_ID"):
                    provider_type = "bedrock"
                else:
                    provider_type = "mock"

        # Create provider
        if provider_type == "openai":
            return OpenAIProvider(**kwargs)
        elif provider_type == "bedrock":
            return BedrockProvider(**kwargs)
        elif provider_type == "mock":
            return MockProvider(**kwargs)
        else:
            raise ValueError(f"Unknown LLM provider: {provider_type}")


# Convenience singleton for global access
_default_provider: Optional[LLMProvider] = None


def get_llm_provider() -> LLMProvider:
    """Get or create default LLM provider"""
    global _default_provider
    if _default_provider is None:
        _default_provider = LLMFactory.create_provider()
    return _default_provider


def set_llm_provider(provider: LLMProvider) -> None:
    """Set global default LLM provider"""
    global _default_provider
    _default_provider = provider


if __name__ == "__main__":
    # Quick test of provider selection
    import argparse

    parser = argparse.ArgumentParser(description="Test LLM providers")
    parser.add_argument("--provider", choices=["openai", "bedrock", "mock"], help="Provider type")
    parser.add_argument("--prompt", default="안녕하세요! 간단히 인사해 주세요.", help="Test prompt")
    args = parser.parse_args()

    try:
        provider = LLMFactory.create_provider(args.provider)
        print(f"Provider: {provider.provider_name} ({provider.model_name})")
        response = provider.generate(args.prompt)
        print(f"Response: {response}")
    except Exception as e:
        print(f"Error: {e}")