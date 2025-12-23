# LLM Integration for Repo Auditor
# Simplified version - Ollama (local) + API (complex tasks)

from .client import LLMClient, get_llm_client
from .models import LLMRequest, LLMResponse, TaskType, Provider
from .analyzer import LLMAnalyzer, get_llm_analyzer

__all__ = [
    'LLMClient',
    'get_llm_client',
    'LLMRequest',
    'LLMResponse',
    'TaskType',
    'Provider',
    'LLMAnalyzer',
    'get_llm_analyzer',
]
