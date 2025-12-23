"""
LLM Models and Task Types for Repo Auditor
"""
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime, timezone


class TaskType(str, Enum):
    """Task types for routing to optimal model"""
    # Local model tasks (Ollama - fast, free, private)
    README_QUALITY = "readme_quality"
    CODE_SUMMARY = "code_summary"
    SIMPLE_ANALYSIS = "simple_analysis"

    # API model tasks (Claude/GPT - complex, accurate)
    CODE_REVIEW = "code_review"
    ARCHITECTURE_ANALYSIS = "architecture_analysis"
    TZ_GENERATION = "tz_generation"
    RECOMMENDATIONS = "recommendations"
    SECURITY_REVIEW = "security_review"

    # Hybrid (try local first, fallback to API)
    TECH_DEBT_ANALYSIS = "tech_debt_analysis"
    DOCUMENTATION_REVIEW = "documentation_review"

    # Document extraction (structured data from contracts/policies)
    CONTRACT_EXTRACTION = "contract_extraction"
    POLICY_EXTRACTION = "policy_extraction"


class Provider(str, Enum):
    """Available LLM providers"""
    OLLAMA = "ollama"
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GOOGLE = "google"  # Free tier available


@dataclass
class LLMRequest:
    """Request to LLM"""
    system_prompt: str
    user_prompt: str
    task_type: TaskType = TaskType.SIMPLE_ANALYSIS
    max_tokens: int = 2000
    temperature: float = 0.3
    model: Optional[str] = None  # Override default model
    provider: Optional[Provider] = None  # Override default provider
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMResponse:
    """Response from LLM"""
    text: str
    model: str
    provider: str
    tokens_used: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    success: bool = True
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_local(self) -> bool:
        return self.provider == Provider.OLLAMA.value


# Model pricing (approximate USD per 1K tokens)
MODEL_PRICING = {
    "ollama": {"input": 0.0, "output": 0.0},
    "claude-3-haiku-20240307": {"input": 0.00025, "output": 0.00125},
    "claude-3-5-sonnet-20241022": {"input": 0.003, "output": 0.015},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-4o": {"input": 0.005, "output": 0.015},
    "gemini-1.5-flash": {"input": 0.0, "output": 0.0},  # Free tier
}


# Task to preferred provider mapping
TASK_ROUTING = {
    # Local tasks
    TaskType.README_QUALITY: [Provider.OLLAMA, Provider.GOOGLE],
    TaskType.CODE_SUMMARY: [Provider.OLLAMA, Provider.GOOGLE],
    TaskType.SIMPLE_ANALYSIS: [Provider.OLLAMA, Provider.GOOGLE],

    # API tasks
    TaskType.CODE_REVIEW: [Provider.ANTHROPIC, Provider.OPENAI],
    TaskType.ARCHITECTURE_ANALYSIS: [Provider.ANTHROPIC, Provider.OPENAI],
    TaskType.TZ_GENERATION: [Provider.ANTHROPIC, Provider.OPENAI],
    TaskType.RECOMMENDATIONS: [Provider.ANTHROPIC, Provider.GOOGLE],
    TaskType.SECURITY_REVIEW: [Provider.ANTHROPIC, Provider.OPENAI],

    # Hybrid
    TaskType.TECH_DEBT_ANALYSIS: [Provider.OLLAMA, Provider.ANTHROPIC],
    TaskType.DOCUMENTATION_REVIEW: [Provider.OLLAMA, Provider.GOOGLE],

    # Document extraction (prefer Claude for accuracy)
    TaskType.CONTRACT_EXTRACTION: [Provider.ANTHROPIC, Provider.GOOGLE, Provider.OLLAMA],
    TaskType.POLICY_EXTRACTION: [Provider.ANTHROPIC, Provider.GOOGLE, Provider.OLLAMA],
}
