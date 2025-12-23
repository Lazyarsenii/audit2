"""
Google Provider - Gemini API (Free tier available)
"""
import time
import logging
import os
from typing import Optional

from .base import BaseLLMProvider
from ..models import LLMRequest, LLMResponse, Provider

logger = logging.getLogger(__name__)

try:
    import google.generativeai as genai
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False


class GoogleProvider(BaseLLMProvider):
    """Google Gemini provider"""

    provider = Provider.GOOGLE
    default_model = "gemini-1.5-flash"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        self._configured = False
        if GOOGLE_AVAILABLE and self.api_key:
            genai.configure(api_key=self.api_key)
            self._configured = True

    async def is_available(self) -> bool:
        """Check if Google API is configured"""
        return GOOGLE_AVAILABLE and self._configured

    async def query(self, request: LLMRequest) -> LLMResponse:
        """Query Gemini model"""
        if not self._configured:
            return self._error_response("Google not configured")

        model_name = request.model or self.default_model
        start_time = time.time()

        try:
            model = genai.GenerativeModel(model_name)

            # Build prompt
            prompt = ""
            if request.system_prompt:
                prompt = f"{request.system_prompt}\n\n"
            prompt += request.user_prompt

            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=request.max_tokens,
                    temperature=request.temperature,
                ),
            )

            latency = (time.time() - start_time) * 1000
            text = response.text if response else ""

            return LLMResponse(
                text=text,
                model=model_name,
                provider=self.provider.value,
                tokens_used=0,  # Gemini doesn't always return token count
                cost_usd=0.0,  # Free tier
                latency_ms=latency,
                success=True,
            )

        except Exception as e:
            logger.error(f"Google error: {e}")
            return self._error_response(str(e), model_name)
