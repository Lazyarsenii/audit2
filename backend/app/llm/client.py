"""
LLM Client - Unified interface with smart routing
"""
import logging
from typing import Optional, Dict

from .models import LLMRequest, LLMResponse, Provider, TaskType, TASK_ROUTING
from .providers import (
    BaseLLMProvider,
    OllamaProvider,
    AnthropicProvider,
    OpenAIProvider,
    GoogleProvider,
)

logger = logging.getLogger(__name__)

# Singleton instance
_llm_client: Optional['LLMClient'] = None


class LLMClient:
    """
    Unified LLM Client with smart routing.

    Routes tasks to optimal provider based on:
    - Task type (local vs API)
    - Provider availability
    - Fallback chain
    """

    def __init__(self):
        self.providers: Dict[Provider, BaseLLMProvider] = {
            Provider.OLLAMA: OllamaProvider(),
            Provider.ANTHROPIC: AnthropicProvider(),
            Provider.OPENAI: OpenAIProvider(),
            Provider.GOOGLE: GoogleProvider(),
        }
        self._availability_cache: Dict[Provider, bool] = {}

    async def _check_availability(self, provider: Provider) -> bool:
        """Check and cache provider availability"""
        if provider not in self._availability_cache:
            self._availability_cache[provider] = await self.providers[provider].is_available()
        return self._availability_cache[provider]

    def _get_providers_for_task(self, task_type: TaskType) -> list:
        """Get ordered list of providers for task type"""
        return TASK_ROUTING.get(task_type, [Provider.OLLAMA, Provider.GOOGLE])

    async def query(self, request: LLMRequest) -> LLMResponse:
        """
        Send query to LLM with smart routing.

        1. If provider specified, use it directly
        2. Otherwise, route based on task_type
        3. Use fallback chain if preferred provider unavailable
        """
        # Direct provider specified
        if request.provider:
            if await self._check_availability(request.provider):
                return await self.providers[request.provider].query(request)
            logger.warning(f"Requested provider {request.provider} not available")

        # Get providers for task type
        providers = self._get_providers_for_task(request.task_type)

        # Try each provider in order
        for provider in providers:
            if await self._check_availability(provider):
                logger.info(f"Using {provider.value} for {request.task_type.value}")
                response = await self.providers[provider].query(request)
                if response.success:
                    return response
                logger.warning(f"{provider.value} failed: {response.error}")

        # All failed
        return LLMResponse(
            text="",
            model="",
            provider="none",
            success=False,
            error="No LLM providers available",
        )

    async def query_simple(
        self,
        prompt: str,
        task_type: TaskType = TaskType.SIMPLE_ANALYSIS,
        system_prompt: str = "",
    ) -> str:
        """Simple query returning just text"""
        request = LLMRequest(
            system_prompt=system_prompt,
            user_prompt=prompt,
            task_type=task_type,
        )
        response = await self.query(request)
        return response.text if response.success else ""

    async def get_available_providers(self) -> Dict[str, bool]:
        """Check which providers are available"""
        result = {}
        for provider in Provider:
            result[provider.value] = await self._check_availability(provider)
        return result

    def reset_cache(self):
        """Reset availability cache"""
        self._availability_cache.clear()


def get_llm_client() -> LLMClient:
    """Get singleton LLM client"""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
