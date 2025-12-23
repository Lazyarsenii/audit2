"""
Base LLM Provider Interface
"""
from abc import ABC, abstractmethod
from typing import Optional
import logging

from ..models import LLMRequest, LLMResponse, Provider

logger = logging.getLogger(__name__)


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers"""

    provider: Provider
    default_model: str

    @abstractmethod
    async def query(self, request: LLMRequest) -> LLMResponse:
        """Send query to LLM and get response"""
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if provider is available"""
        pass

    def _build_messages(self, request: LLMRequest) -> list:
        """Build standard message format"""
        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.user_prompt})
        return messages

    def _error_response(self, error: str, model: str = "") -> LLMResponse:
        """Create error response"""
        return LLMResponse(
            text="",
            model=model or self.default_model,
            provider=self.provider.value,
            success=False,
            error=error,
        )
