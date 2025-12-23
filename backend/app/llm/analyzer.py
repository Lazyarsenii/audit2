"""
LLM-Enhanced Analyzer for Repo Auditor
Uses LLM for intelligent code analysis
"""
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path

from .client import get_llm_client
from .models import LLMRequest, TaskType
from .prompts import (
    README_QUALITY_SYSTEM, README_QUALITY_PROMPT,
    CODE_QUALITY_SYSTEM, CODE_QUALITY_PROMPT,
    TECH_DEBT_SYSTEM, TECH_DEBT_PROMPT,
    TZ_GENERATION_SYSTEM, TZ_GENERATION_PROMPT,
    RECOMMENDATIONS_SYSTEM, RECOMMENDATIONS_PROMPT,
    SECURITY_REVIEW_SYSTEM, SECURITY_REVIEW_PROMPT,
    ARCHITECTURE_SYSTEM, ARCHITECTURE_PROMPT,
)

logger = logging.getLogger(__name__)


class LLMAnalyzer:
    """LLM-powered code analyzer"""

    def __init__(self):
        self.client = get_llm_client()

    async def analyze_readme(self, readme_content: str) -> Dict[str, Any]:
        """Analyze README quality using LLM"""
        if not readme_content or len(readme_content) < 50:
            return {
                "overall_score": 0,
                "scores": {},
                "missing_sections": ["No README found"],
                "improvements": ["Create a comprehensive README"],
            }

        request = LLMRequest(
            system_prompt=README_QUALITY_SYSTEM,
            user_prompt=README_QUALITY_PROMPT.format(readme_content=readme_content[:8000]),
            task_type=TaskType.README_QUALITY,
            max_tokens=1000,
        )

        response = await self.client.query(request)
        if not response.success:
            logger.error(f"README analysis failed: {response.error}")
            return {"overall_score": 50, "error": response.error}

        return self._parse_json_response(response.text, {
            "overall_score": 50,
            "scores": {},
            "improvements": [],
        })

    async def analyze_code_quality(
        self,
        code_content: str,
        language: str,
        filename: str,
    ) -> Dict[str, Any]:
        """Analyze code quality for a single file"""
        if not code_content:
            return {"error": "No code content"}

        request = LLMRequest(
            system_prompt=CODE_QUALITY_SYSTEM,
            user_prompt=CODE_QUALITY_PROMPT.format(
                code_content=code_content[:6000],
                language=language,
                filename=filename,
            ),
            task_type=TaskType.CODE_REVIEW,
            max_tokens=1500,
        )

        response = await self.client.query(request)
        if not response.success:
            return {"error": response.error}

        return self._parse_json_response(response.text, {
            "complexity": {"score": 5, "issues": []},
            "maintainability": {"score": 5, "issues": []},
            "code_smells": [],
            "suggestions": [],
        })

    async def analyze_tech_debt(
        self,
        repo_name: str,
        languages: list,
        structure: str,
        known_issues: str = "",
    ) -> Dict[str, Any]:
        """Analyze technical debt in repository"""
        request = LLMRequest(
            system_prompt=TECH_DEBT_SYSTEM,
            user_prompt=TECH_DEBT_PROMPT.format(
                repo_name=repo_name,
                languages=", ".join(languages),
                structure=structure[:4000],
                known_issues=known_issues[:2000],
            ),
            task_type=TaskType.TECH_DEBT_ANALYSIS,
            max_tokens=2000,
        )

        response = await self.client.query(request)
        if not response.success:
            return {"error": response.error}

        return self._parse_json_response(response.text, {
            "debt_items": [],
            "total_debt_hours": 0,
            "critical_items": [],
            "quick_wins": [],
        })

    async def generate_tz(
        self,
        project_name: str,
        repo_health: int,
        tech_debt: int,
        readiness: int,
        issues: str,
        project_type: str,
        required_repo_health: int,
        required_tech_debt: int,
        required_readiness: int,
    ) -> str:
        """Generate Technical Specification (ТЗ)"""
        request = LLMRequest(
            system_prompt=TZ_GENERATION_SYSTEM,
            user_prompt=TZ_GENERATION_PROMPT.format(
                project_name=project_name,
                repo_health=repo_health,
                tech_debt=tech_debt,
                readiness=readiness,
                issues=issues[:4000],
                project_type=project_type,
                required_repo_health=required_repo_health,
                required_tech_debt=required_tech_debt,
                required_readiness=required_readiness,
            ),
            task_type=TaskType.TZ_GENERATION,
            max_tokens=3000,
        )

        response = await self.client.query(request)
        if not response.success:
            return f"Error generating TZ: {response.error}"

        return response.text

    async def generate_recommendations(
        self,
        project_name: str,
        analysis_summary: str,
        health_gap: int,
        debt_gap: int,
        readiness_gap: int,
    ) -> Dict[str, Any]:
        """Generate prioritized recommendations"""
        request = LLMRequest(
            system_prompt=RECOMMENDATIONS_SYSTEM,
            user_prompt=RECOMMENDATIONS_PROMPT.format(
                project_name=project_name,
                analysis_summary=analysis_summary[:4000],
                health_gap=health_gap,
                debt_gap=debt_gap,
                readiness_gap=readiness_gap,
            ),
            task_type=TaskType.RECOMMENDATIONS,
            max_tokens=2000,
        )

        response = await self.client.query(request)
        if not response.success:
            return {"error": response.error}

        return self._parse_json_response(response.text, {
            "immediate_actions": [],
            "short_term": [],
            "long_term": [],
            "priority_order": [],
        })

    async def security_review(
        self,
        code_content: str,
        language: str,
        filename: str,
    ) -> Dict[str, Any]:
        """Review code for security issues"""
        request = LLMRequest(
            system_prompt=SECURITY_REVIEW_SYSTEM,
            user_prompt=SECURITY_REVIEW_PROMPT.format(
                code_content=code_content[:6000],
                language=language,
                filename=filename,
            ),
            task_type=TaskType.SECURITY_REVIEW,
            max_tokens=1500,
        )

        response = await self.client.query(request)
        if not response.success:
            return {"error": response.error}

        return self._parse_json_response(response.text, {
            "vulnerabilities": [],
            "security_score": 5,
            "recommendations": [],
        })

    async def analyze_architecture(
        self,
        project_name: str,
        structure: str,
        dependencies: str,
    ) -> Dict[str, Any]:
        """Analyze project architecture"""
        request = LLMRequest(
            system_prompt=ARCHITECTURE_SYSTEM,
            user_prompt=ARCHITECTURE_PROMPT.format(
                project_name=project_name,
                structure=structure[:4000],
                dependencies=dependencies[:2000],
            ),
            task_type=TaskType.ARCHITECTURE_ANALYSIS,
            max_tokens=1500,
        )

        response = await self.client.query(request)
        if not response.success:
            return {"error": response.error}

        return self._parse_json_response(response.text, {
            "architecture_type": "unknown",
            "patterns_detected": [],
            "layers": [],
            "strengths": [],
            "weaknesses": [],
            "recommendations": [],
        })

    def _parse_json_response(self, text: str, default: Dict) -> Dict[str, Any]:
        """Parse JSON from LLM response"""
        try:
            # Try to extract JSON from text
            text = text.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                text = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

            # Find JSON object
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(text[start:end])
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON: {e}")
        except Exception as e:
            logger.error(f"Error parsing response: {e}")

        return default


# Singleton
_analyzer: Optional[LLMAnalyzer] = None


def get_llm_analyzer() -> LLMAnalyzer:
    """Get singleton LLM analyzer"""
    global _analyzer
    if _analyzer is None:
        _analyzer = LLMAnalyzer()
    return _analyzer
