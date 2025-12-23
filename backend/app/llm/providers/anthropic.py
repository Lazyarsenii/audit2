"""
Anthropic Provider - Claude API
"""
import time
import logging
import os
from typing import Optional

from .base import BaseLLMProvider
from ..models import LLMRequest, LLMResponse, Provider, MODEL_PRICING

logger = logging.getLogger(__name__)

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude provider"""

    provider = Provider.ANTHROPIC
    default_model = "claude-3-haiku-20240307"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self._client = None

    def _get_client(self):
        if self._client is None and ANTHROPIC_AVAILABLE and self.api_key:
            self._client = anthropic.Anthropic(api_key=self.api_key)
        return self._client

    async def is_available(self) -> bool:
        """Check if Anthropic API is configured"""
        return ANTHROPIC_AVAILABLE and bool(self.api_key)

    async def query(self, request: LLMRequest) -> LLMResponse:
        """Query Claude model"""
        client = self._get_client()
        if not client:
            return self._error_response("Anthropic not configured")

        model = request.model or self.default_model
        start_time = time.time()

        try:
            message = client.messages.create(
                model=model,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                system=request.system_prompt or "",
                messages=[{"role": "user", "content": request.user_prompt}],
            )

            latency = (time.time() - start_time) * 1000
            text = message.content[0].text if message.content else ""

            # Calculate cost
            input_tokens = message.usage.input_tokens
            output_tokens = message.usage.output_tokens
            pricing = MODEL_PRICING.get(model, {"input": 0.003, "output": 0.015})
            cost = (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1000

            return LLMResponse(
                text=text,
                model=model,
                provider=self.provider.value,
                tokens_used=input_tokens + output_tokens,
                cost_usd=cost,
                latency_ms=latency,
                success=True,
            )

        except Exception as e:
            logger.error(f"Anthropic error: {e}")
            return self._error_response(str(e), model)
