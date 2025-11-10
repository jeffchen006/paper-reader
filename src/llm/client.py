"""Generic LLM client wrapper for OpenAI/Anthropic chat models."""

from __future__ import annotations

from typing import Any, Dict, Optional

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage


class LLMClient:
    """Thin wrapper that normalizes access to LangChain chat models."""

    def __init__(
        self,
        provider: str,
        model: str,
        api_key: Optional[str] = None,
        temperature: float = 0.0,
    ):
        self.provider = (provider or "").lower()
        self.model = model
        self.api_key = api_key
        self.temperature = temperature
        self._client = self._build_client()

    def _build_client(self):
        if self.provider == "openai":
            return ChatOpenAI(
                model=self.model,
                temperature=self.temperature,
                openai_api_key=self.api_key,
            )
        if self.provider == "anthropic":
            return ChatAnthropic(
                model=self.model,
                temperature=self.temperature,
                anthropic_api_key=self.api_key,
            )
        raise ValueError(f"Unsupported LLM provider: {self.provider}")

    def complete(self, prompt: str) -> str:
        """Send a single-turn prompt and return the text response."""
        if not prompt:
            raise ValueError("Prompt must be provided")

        response = self._client.invoke([HumanMessage(content=prompt)])
        content = response.content

        if isinstance(content, list):
            text_chunks = [chunk.get("text", "") for chunk in content if isinstance(chunk, dict)]
            content = "".join(text_chunks)

        return str(content).strip()

    @classmethod
    def from_config(cls, config: Dict[str, Any], **kwargs) -> "LLMClient":
        """Instantiate a client from a config dict {provider, model, api_key}."""
        return cls(
            provider=config.get("provider"),
            model=config.get("model"),
            api_key=config.get("api_key"),
            **kwargs,
        )
