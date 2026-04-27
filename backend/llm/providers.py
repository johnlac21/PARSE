"""
Unified LLM client (e.g. via LiteLLM) for multiple providers.
"""

import time
from typing import Any

import litellm


class UnifiedLLMClient:
    """Single client interface for multiple LLM providers using LiteLLM."""

    def __init__(self, provider: str, model: str, api_key: str | None = None, base_url: str | None = None):
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.base_url = base_url

    def _model_string(self) -> str:
        """LiteLLM model string: provider/model."""
        return f"{self.provider}/{self.model}"

    async def query(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.0,
        max_tokens: int = 150,
    ) -> dict:
        """
        Uses litellm.acompletion for unified API.
        Returns: {"raw_response": str, "latency_ms": int, "model": str, "error": str | None}
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        kwargs: dict[str, Any] = {
            "model": self._model_string(),
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "timeout": 120.0,  # seconds per request; avoid hanging forever
        }
        if self.api_key is not None:
            kwargs["api_key"] = self.api_key
        if self.base_url is not None:
            # LiteLLM acompletion expects base_url (not api_base)
            kwargs["base_url"] = self.base_url.rstrip("/")

        start = time.perf_counter()
        try:
            response = await litellm.acompletion(**kwargs)
            latency_ms = int((time.perf_counter() - start) * 1000)
            content = ""
            if response.choices and len(response.choices) > 0:
                delta = response.choices[0].message
                if hasattr(delta, "content") and delta.content is not None:
                    content = delta.content
            return {
                "raw_response": content,
                "latency_ms": latency_ms,
                "model": getattr(response, "model", self.model) or self.model,
                "error": None,
            }
        except Exception as e:
            latency_ms = int((time.perf_counter() - start) * 1000)
            status_code = getattr(e, "status_code", None) or getattr(e, "response", None) and getattr(
                getattr(e, "response"), "status_code", None
            )
            return {
                "raw_response": "",
                "latency_ms": latency_ms,
                "model": self.model,
                "error": str(e),
                "status_code": status_code,
            }

    @staticmethod
    def get_supported_models() -> list[dict]:
        """Returns list of common models with their provider prefixes."""
        return [
            {"provider": "openai", "model": "gpt-4o-mini", "display_name": "GPT-4o Mini"},
            {"provider": "openai", "model": "gpt-4o", "display_name": "GPT-4o"},
            {"provider": "anthropic", "model": "claude-sonnet-4-5-20250929", "display_name": "Claude 3.5 Sonnet"},
            {"provider": "anthropic", "model": "claude-haiku-4-5-20251001", "display_name": "Claude 3.5 Haiku"},
            {"provider": "ollama", "model": "llama3.2", "display_name": "Llama 3.2 (Local)"},
            {"provider": "ollama", "model": "deepseek-r1:7b", "display_name": "DeepSeek R1 7B (Local)"},
            {"provider": "gemini", "model": "gemini-1.5-flash", "display_name": "Gemini 1.5 Flash"},
        ]
