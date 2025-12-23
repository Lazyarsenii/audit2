"""
Tests for LLM Module
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.llm.models import TaskType, Provider, LLMRequest, LLMResponse, TASK_ROUTING
from app.llm.client import LLMClient
from app.llm.analyzer import LLMAnalyzer
from app.llm.providers.base import BaseLLMProvider
from app.llm.providers.ollama import OllamaProvider


class TestModels:
    """Test LLM models and data classes"""

    def test_task_types_exist(self):
        """Test that all task types are defined"""
        assert TaskType.README_QUALITY
        assert TaskType.CODE_REVIEW
        assert TaskType.TZ_GENERATION
        assert TaskType.RECOMMENDATIONS

    def test_providers_exist(self):
        """Test that all providers are defined"""
        assert Provider.OLLAMA
        assert Provider.ANTHROPIC
        assert Provider.OPENAI
        assert Provider.GOOGLE

    def test_task_routing_complete(self):
        """Test that all task types have routing"""
        for task_type in TaskType:
            assert task_type in TASK_ROUTING, f"Missing routing for {task_type}"

    def test_llm_request_defaults(self):
        """Test LLMRequest default values"""
        request = LLMRequest(
            system_prompt="System",
            user_prompt="User",
        )
        assert request.task_type == TaskType.SIMPLE_ANALYSIS
        assert request.max_tokens == 2000
        assert request.temperature == 0.3

    def test_llm_response_creation(self):
        """Test LLMResponse creation"""
        response = LLMResponse(
            text="Test response",
            model="test-model",
            provider="test-provider",
            tokens_used=100,
            cost_usd=0.01,
            latency_ms=500.0,
        )
        assert response.text == "Test response"
        assert response.success is True


class TestOllamaProvider:
    """Test Ollama provider"""

    @pytest.mark.asyncio
    async def test_ollama_not_available_by_default(self):
        """Test Ollama is not available when server not running"""
        provider = OllamaProvider(base_url="http://localhost:99999")
        is_available = await provider.is_available()
        assert is_available is False

    def test_ollama_default_model(self):
        """Test Ollama default model"""
        provider = OllamaProvider()
        assert provider.default_model == "llama3.1:8b"

    @pytest.mark.asyncio
    async def test_ollama_query_without_server(self):
        """Test Ollama query fails gracefully without server"""
        provider = OllamaProvider(base_url="http://localhost:99999")
        request = LLMRequest(
            system_prompt="Test",
            user_prompt="Hello",
        )
        response = await provider.query(request)
        assert response.success is False
        assert response.error is not None


class TestLLMClient:
    """Test LLM client"""

    @pytest.mark.asyncio
    async def test_client_initialization(self):
        """Test client initializes with all providers"""
        client = LLMClient()
        assert Provider.OLLAMA in client.providers
        assert Provider.ANTHROPIC in client.providers
        assert Provider.OPENAI in client.providers
        assert Provider.GOOGLE in client.providers

    @pytest.mark.asyncio
    async def test_client_get_available_providers(self):
        """Test getting available providers"""
        client = LLMClient()
        available = await client.get_available_providers()
        assert "ollama" in available
        assert "anthropic" in available
        assert "openai" in available
        assert "google" in available

    @pytest.mark.asyncio
    async def test_client_query_no_providers(self):
        """Test query when no providers available"""
        client = LLMClient()
        # Mock all providers as unavailable
        for provider in client.providers.values():
            provider.is_available = AsyncMock(return_value=False)

        request = LLMRequest(
            system_prompt="Test",
            user_prompt="Hello",
        )
        response = await client.query(request)
        assert response.success is False
        assert "No LLM providers available" in response.error

    @pytest.mark.asyncio
    async def test_client_query_with_mock_provider(self):
        """Test query with mocked provider"""
        client = LLMClient()

        # Mock Ollama as available and working
        mock_response = LLMResponse(
            text="Test response",
            model="llama3.1:8b",
            provider="ollama",
            tokens_used=10,
        )
        client.providers[Provider.OLLAMA].is_available = AsyncMock(return_value=True)
        client.providers[Provider.OLLAMA].query = AsyncMock(return_value=mock_response)

        request = LLMRequest(
            system_prompt="Test",
            user_prompt="Hello",
            task_type=TaskType.SIMPLE_ANALYSIS,
        )
        response = await client.query(request)
        assert response.success is True
        assert response.text == "Test response"


class TestLLMAnalyzer:
    """Test LLM analyzer"""

    @pytest.mark.asyncio
    async def test_analyze_readme_empty(self):
        """Test README analysis with empty content"""
        analyzer = LLMAnalyzer()
        result = await analyzer.analyze_readme("")
        assert result["overall_score"] == 0
        assert "No README found" in result["missing_sections"]

    @pytest.mark.asyncio
    async def test_analyze_readme_short(self):
        """Test README analysis with short content"""
        analyzer = LLMAnalyzer()
        result = await analyzer.analyze_readme("Short")
        assert result["overall_score"] == 0

    @pytest.mark.asyncio
    async def test_parse_json_response(self):
        """Test JSON parsing from LLM response"""
        analyzer = LLMAnalyzer()

        # Valid JSON
        result = analyzer._parse_json_response(
            '{"score": 10, "items": ["a", "b"]}',
            {"score": 0, "items": []}
        )
        assert result["score"] == 10
        assert len(result["items"]) == 2

        # JSON in markdown code block
        result = analyzer._parse_json_response(
            '```json\n{"score": 5}\n```',
            {"score": 0}
        )
        assert result["score"] == 5

        # Invalid JSON returns default
        result = analyzer._parse_json_response(
            'not valid json',
            {"default": True}
        )
        assert result["default"] is True


class TestProviderRouting:
    """Test task-based provider routing"""

    def test_readme_routes_to_local(self):
        """README quality should route to local first"""
        providers = TASK_ROUTING[TaskType.README_QUALITY]
        assert providers[0] == Provider.OLLAMA

    def test_code_review_routes_to_api(self):
        """Code review should route to API first"""
        providers = TASK_ROUTING[TaskType.CODE_REVIEW]
        assert providers[0] == Provider.ANTHROPIC

    def test_tz_generation_routes_to_api(self):
        """TZ generation should route to API"""
        providers = TASK_ROUTING[TaskType.TZ_GENERATION]
        assert providers[0] == Provider.ANTHROPIC

    def test_all_tasks_have_fallback(self):
        """All tasks should have at least 2 providers for fallback"""
        for task_type, providers in TASK_ROUTING.items():
            assert len(providers) >= 2, f"{task_type} needs fallback provider"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
