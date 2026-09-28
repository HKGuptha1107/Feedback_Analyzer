"""Groq LLM Client module.
Provides resilient chat completions, automatic fallback models, and structured tool handling.
"""

import time
import json
import logging
from typing import List, Dict, Any, Optional
from groq import Groq, APIError
from app.config import settings

logger = logging.getLogger(__name__)


class GroqClient:
    """Production-grade wrapper for Groq LLM API with automated model fallback."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        fallback_model: Optional[str] = None,
    ):
        self.api_key = api_key or settings.GROQ_API_KEY
        self.primary_model = model or settings.GROQ_MODEL
        self.fallback_model = fallback_model or settings.GROQ_FALLBACK_MODEL
        self._client: Optional[Groq] = None

        if self.api_key:
            try:
                self._client = Groq(api_key=self.api_key)
            except Exception as e:
                logger.error(f"Failed to initialize Groq client: {e}")

    @property
    def is_configured(self) -> bool:
        """Check whether the client has an initialized Groq instance."""
        return self._client is not None and bool(self.api_key)

    def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Any] = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
        response_format: Optional[Dict[str, str]] = None,
    ) -> Any:
        """Execute chat completion with automatic fallback if primary model is unavailable."""
        if not self.is_configured:
            raise RuntimeError("Groq API key is not configured. Please set GROQ_API_KEY.")

        target_model = model or self.primary_model

        # Ensure reasoning models (gpt-oss-120b) have sufficient token budget for reasoning tokens
        effective_max_tokens = max(max_tokens, 256) if "gpt-oss" in target_model else max_tokens

        # Build kwargs
        kwargs: Dict[str, Any] = {
            "model": target_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": effective_max_tokens,
        }
        if tools:
            kwargs["tools"] = tools
            if tool_choice:
                kwargs["tool_choice"] = tool_choice
        if response_format:
            kwargs["response_format"] = response_format

        try:
            return self._client.chat.completions.create(**kwargs)
        except Exception as primary_err:
            logger.warning(
                f"Groq primary model '{target_model}' failed ({primary_err}). "
                f"Attempting fallback to '{self.fallback_model}'..."
            )
            if target_model != self.fallback_model:
                try:
                    kwargs["model"] = self.fallback_model
                    effective_fallback_tokens = (
                        max(max_tokens, 256) if "gpt-oss" in self.fallback_model else max_tokens
                    )
                    kwargs["max_tokens"] = effective_fallback_tokens
                    return self._client.chat.completions.create(**kwargs)
                except Exception as fallback_err:
                    logger.error(f"Groq fallback model '{self.fallback_model}' also failed: {fallback_err}")
                    raise fallback_err
            raise primary_err

    def chat_completion_text(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> str:
        """Convenience method returning text content of the assistant message."""
        res = self.chat_completion(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        msg = res.choices[0].message
        return msg.content or ""

    def chat_completion_json(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: float = 0.1,
    ) -> Dict[str, Any]:
        """Convenience method to retrieve and safely parse a JSON response."""
        content = self.chat_completion_text(
            messages=messages,
            model=model,
            temperature=temperature,
        )
        clean = content.strip()
        if clean.startswith("```json"):
            clean = clean[7:]
        if clean.startswith("```"):
            clean = clean[3:]
        if clean.endswith("```"):
            clean = clean[:-3]
        return json.loads(clean.strip())

    def test_connection(self) -> Dict[str, Any]:
        """Test live connectivity and latency with the Groq API."""
        if not self.is_configured:
            return {
                "status": "unconfigured",
                "message": "GROQ_API_KEY is not set.",
                "model": self.primary_model,
            }

        start_time = time.time()
        try:
            text = self.chat_completion_text(
                messages=[{"role": "user", "content": "Respond with 'ready'."}],
                max_tokens=256,
            )
            elapsed_ms = round((time.time() - start_time) * 1000, 2)
            return {
                "status": "connected",
                "model": self.primary_model,
                "fallback_model": self.fallback_model,
                "latency_ms": elapsed_ms,
                "response": text.strip(),
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "model": self.primary_model,
            }


# Global singleton instance
groq_client = GroqClient()
