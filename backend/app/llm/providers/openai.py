"""
OpenAI Provider - GPT API
"""
import time
import logging
import os
from typing import Optional

from .base import BaseLLMProvider
from ..models import LLMRequest, LLMResponse, Provider, MODEL_PRICING

logger = logging.getLogger(__name__)

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class OpenAIProvider(BaseLLMProvider):
    """OpenAI GPT provider"""

    provider = Provider.OPENAI
    default_model = "gpt-4o-mini"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._client = None

    def _get_client(self):
        if self._client is None and OPENAI_AVAILABLE and self.api_key:
            self._client = openai.OpenAI(api_key=self.api_key)
        return self._client

    async def is_available(self) -> bool:
        """Check if OpenAI API is configured"""
        return OPENAI_AVAILABLE and bool(self.api_key)

    async def query(self, request: LLMRequest) -> LLMResponse:
        """Query GPT model"""
        client = self._get_client()
        if not client:
            return self._error_response("OpenAI not configured")

        model = request.model or self.default_model
        start_time = time.time()

        try:
            messages = self._build_messages(request)

            response = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
            )

            latency = (time.time() - start_time) * 1000
            text = response.choices[0].message.content if response.choices else ""

            # Calculate cost
            input_tokens = response.usage.prompt_tokens if response.usage else 0
            output_tokens = response.usage.completion_tokens if response.usage else 0
            pricing = MODEL_PRICING.get(model, {"input": 0.00015, "output": 0.0006})
            cost = (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1000

            return LLMResponse(
                text=text or "",
                model=model,
                provider=self.provider.value,
                tokens_used=input_tokens + output_tokens,
                cost_usd=cost,
                latency_ms=latency,
                success=True,
            )

        except Exception as e:
            logger.error(f"OpenAI error: {e}")
            return self._error_response(str(e), model)
