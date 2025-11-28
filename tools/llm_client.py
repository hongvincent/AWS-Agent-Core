import os
from typing import Optional, Dict, Any

try:
    from openai import OpenAI
except Exception as e:  # pragma: no cover
    OpenAI = None  # type: ignore


class LLMClient:
    """
    Minimal LLM client using OpenAI's Responses API.

    Configuration via environment variables:
    - OPENAI_API_KEY: API key (required)
    - OPENAI_MODEL: model name (default: gpt-4o-mini)
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")

        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is not set. Set env var or pass api_key.")
        if OpenAI is None:
            raise RuntimeError("openai package is not installed. Add it to requirements and install.")

        # Do not persist the key; client reads from env by default
        os.environ.setdefault("OPENAI_API_KEY", self.api_key)
        self.client = OpenAI()

    def generate_text(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        temperature: float = 0.2,
        max_output_tokens: int = 256,
        extra: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate a text completion for a single prompt.

        Uses the Responses API for a simple, non-streamed call.
        """
        input_blocks = []
        if system:
            input_blocks.append({"role": "system", "content": system})
        input_blocks.append({"role": "user", "content": prompt})

        params: Dict[str, Any] = {
            "model": self.model,
            "input": input_blocks,
            "temperature": temperature,
            "max_output_tokens": max_output_tokens,
        }
        if extra:
            params.update(extra)

        resp = self.client.responses.create(**params)
        # openai>=1.3 exposes convenience property output_text
        text = getattr(resp, "output_text", None)
        if text is None:
            # Fallback: try to extract from output array
            try:
                outputs = resp.output or []  # type: ignore[attr-defined]
                for item in outputs:
                    if getattr(item, "type", None) == "message":
                        for part in getattr(item, "content", []) or []:
                            if getattr(part, "type", None) == "output_text":
                                return getattr(part, "text", "").strip()
            except Exception:
                pass
            # As a last resort, stringify
            text = str(resp)
        return text.strip()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Quick LLM sanity check")
    parser.add_argument("prompt", nargs="?", default="안녕하세요! 간단히 인사해 주세요.")
    parser.add_argument("--model", dest="model", default=os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    args = parser.parse_args()

    client = LLMClient(model=args.model)
    out = client.generate_text(args.prompt)
    print(out)
