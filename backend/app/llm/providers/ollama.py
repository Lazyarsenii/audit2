"""
Ollama Provider - Local LLM (free, private)
"""
import httpx
import time
import logging
import os
from typing import Optional

from .base import BaseLLMProvider
from ..models import LLMRequest, LLMResponse, Provider

logger = logging.getLogger(__name__)


class OllamaProvider(BaseLLMProvider):
    """Ollama local LLM provider for document analysis"""

    provider = Provider.OLLAMA
    default_model = "qwen2.5:7b"  # Best for document analysis, multilingual

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self._available: Optional[bool] = None

    async def is_available(self) -> bool:
        """Check if Ollama is running"""
        if self._available is not None:
            return self._available

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                self._available = response.status_code == 200
        except Exception:
            self._available = False

        return self._available

    async def query(self, request: LLMRequest) -> LLMResponse:
        """Query Ollama model"""
        model = request.model or self.default_model
        start_time = time.time()

        try:
            # Build prompt
            prompt = ""
            if request.system_prompt:
                prompt = f"System: {request.system_prompt}\n\n"
            prompt += f"User: {request.user_prompt}"

            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": request.temperature,
                    "num_predict": request.max_tokens,
                }
            }

            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                )
                response.raise_for_status()

            data = response.json()
            latency = (time.time() - start_time) * 1000

            return LLMResponse(
                text=data.get("response", ""),
                model=model,
                provider=self.provider.value,
                tokens_used=data.get("eval_count", 0),
                cost_usd=0.0,  # Free
                latency_ms=latency,
                success=True,
            )

        except httpx.TimeoutException:
            return self._error_response("Ollama timeout", model)
        except httpx.HTTPStatusError as e:
            return self._error_response(f"HTTP error: {e.response.status_code}", model)
        except Exception as e:
            logger.error(f"Ollama error: {e}")
            return self._error_response(str(e), model)

    async def list_models(self) -> list:
        """List available Ollama models"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    return [m["name"] for m in data.get("models", [])]
        except (httpx.RequestError, httpx.TimeoutException):
            logger.debug("Failed to list Ollama models")
        return []
