"""
Readiness Assessment API endpoints.

Evaluates project readiness for formal evaluation before acceptance.
This is Step 1 of the workflow.
"""
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.core.database import get_db
from app.core.models.repository import AnalysisRepo
from app.services.readiness_assessor import readiness_assessor, ReadinessAssessment
from app.core.scoring.repo_health import RepoHealthScore
from app.core.scoring.tech_debt import TechDebtScore
from app.core.scoring.product_level import ProductLevel
from app.core.scoring.complexity import Complexity


router = APIRouter(prefix="/readiness", tags=["readiness"])


# =============================================================================
# Request/Response Models
# =============================================================================

class ReadinessCheckRequest(BaseModel):
    """Request for readiness assessment."""
    # Scores from analysis
    repo_health: Dict[str, int]
    tech_debt: Dict[str, int]
    product_level: str = "beta"
    complexity: str = "moderate"
    # Structure data
    structure_data: Dict[str, Any] = {}
    static_metrics: Dict[str, Any] = {}


class ReadinessResponse(BaseModel):
    """Response from readiness assessment."""
    readiness_level: str
    readiness_score: float
    category_scores: Dict[str, float]
    passed_checks: int
    failed_checks: int
    blockers_count: int
    estimated_fix_hours: int
    estimated_days_to_ready: int
    summary: str
    next_steps: list
    checks: list
    recommendations: list


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/check")
async def check_readiness(request: ReadinessCheckRequest) -> Dict[str, Any]:
    """
    Check project readiness for formal evaluation.

    This is the first step in the audit workflow.
    Returns readiness level, recommendations, and blockers.
    """
    # Convert dicts to dataclass objects
    repo_health = RepoHealthScore(
        documentation=request.repo_health.get("documentation", 0),
        structure=request.repo_health.get("structure", 0),
        runability=request.repo_health.get("runability", 0),
        commit_history=request.repo_health.get("history", request.repo_health.get("commit_history", 0)),
    )

    tech_debt = TechDebtScore(
        architecture=request.tech_debt.get("architecture", 0),
        code_quality=request.tech_debt.get("code_quality", 0),
        testing=request.tech_debt.get("testing", 0),
        infrastructure=request.tech_debt.get("infrastructure", 0),
        security_deps=request.tech_debt.get("security_deps", request.tech_debt.get("security", 0)),
    )

    # Parse enums with flexible input handling
    product_level_map = {
        "prototype": ProductLevel.PROTOTYPE,
        "Prototype": ProductLevel.PROTOTYPE,
        "beta": ProductLevel.PROTOTYPE,
        "internal_tool": ProductLevel.INTERNAL_TOOL,
        "Internal Tool": ProductLevel.INTERNAL_TOOL,
        "platform_module": ProductLevel.PLATFORM_MODULE,
        "Platform Module Candidate": ProductLevel.PLATFORM_MODULE,
        "near_product": ProductLevel.NEAR_PRODUCT,
        "Near-Product": ProductLevel.NEAR_PRODUCT,
        "production": ProductLevel.NEAR_PRODUCT,
        "rnd_spike": ProductLevel.RND_SPIKE,
        "R&D Spike": ProductLevel.RND_SPIKE,
    }
    product_level = product_level_map.get(request.product_level, ProductLevel.PROTOTYPE)

    complexity_map = {
        "S": Complexity.SMALL,
        "small": Complexity.SMALL,
        "low": Complexity.SMALL,
        "M": Complexity.MEDIUM,
        "medium": Complexity.MEDIUM,
        "moderate": Complexity.MEDIUM,
        "L": Complexity.LARGE,
        "large": Complexity.LARGE,
        "high": Complexity.LARGE,
        "XL": Complexity.XLARGE,
        "xlarge": Complexity.XLARGE,
        "very_high": Complexity.XLARGE,
    }
    complexity = complexity_map.get(request.complexity, Complexity.MEDIUM)

    # Add analysis_id if not present
    structure_data = request.structure_data.copy()
    if "analysis_id" not in structure_data:
        structure_data["analysis_id"] = "manual_check"

    # Run assessment
    assessment = readiness_assessor.assess(
        repo_health=repo_health,
        tech_debt=tech_debt,
        product_level=product_level,
        complexity=complexity,
        structure_data=structure_data,
        static_metrics=request.static_metrics,
    )

    return assessment.to_dict()


@router.get("/check/{analysis_id}")
async def check_readiness_by_analysis(
    analysis_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Check readiness for an existing analysis.

    Fetches analysis results from database and runs readiness check.
    """
    try:
        uuid = UUID(analysis_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid analysis ID format")

    analysis_repo = AnalysisRepo(db)
    analysis = await analysis_repo.get(uuid)

    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    if not analysis.metrics:
        raise HTTPException(status_code=400, detail="Analysis not completed yet")

    # Build scores from metrics
    repo_health_dict = analysis.metrics.repo_health or {}
    tech_debt_dict = analysis.metrics.tech_debt or {}

    repo_health = RepoHealthScore(
        documentation=repo_health_dict.get("documentation", 0),
        structure=repo_health_dict.get("structure", 0),
        runability=repo_health_dict.get("runability", 0),
        commit_history=repo_health_dict.get("history", repo_health_dict.get("commit_history", 0)),
    )

    tech_debt = TechDebtScore(
        architecture=tech_debt_dict.get("architecture", 0),
        code_quality=tech_debt_dict.get("code_quality", 0),
        testing=tech_debt_dict.get("testing", 0),
        infrastructure=tech_debt_dict.get("infrastructure", 0),
        security_deps=tech_debt_dict.get("security_deps", tech_debt_dict.get("security", 0)),
    )

    # Parse enums with flexible input handling
    product_level_map = {
        "prototype": ProductLevel.PROTOTYPE,
        "Prototype": ProductLevel.PROTOTYPE,
        "beta": ProductLevel.PROTOTYPE,
        "internal_tool": ProductLevel.INTERNAL_TOOL,
        "Internal Tool": ProductLevel.INTERNAL_TOOL,
        "platform_module": ProductLevel.PLATFORM_MODULE,
        "Platform Module Candidate": ProductLevel.PLATFORM_MODULE,
        "near_product": ProductLevel.NEAR_PRODUCT,
        "Near-Product": ProductLevel.NEAR_PRODUCT,
        "production": ProductLevel.NEAR_PRODUCT,
        "rnd_spike": ProductLevel.RND_SPIKE,
        "R&D Spike": ProductLevel.RND_SPIKE,
    }
    product_level = product_level_map.get(
        analysis.metrics.product_level or "prototype",
        ProductLevel.PROTOTYPE
    )

    complexity_map = {
        "S": Complexity.SMALL,
        "small": Complexity.SMALL,
        "low": Complexity.SMALL,
        "M": Complexity.MEDIUM,
        "medium": Complexity.MEDIUM,
        "moderate": Complexity.MEDIUM,
        "L": Complexity.LARGE,
        "large": Complexity.LARGE,
        "high": Complexity.LARGE,
        "XL": Complexity.XLARGE,
        "xlarge": Complexity.XLARGE,
        "very_high": Complexity.XLARGE,
    }
    complexity = complexity_map.get(
        analysis.metrics.complexity or "M",
        Complexity.MEDIUM
    )

    # Get structure data
    structure_data = analysis.metrics.structure_data or {}
    structure_data["analysis_id"] = str(analysis.id)
    structure_data["repo_url"] = analysis.repository.url

    static_metrics = analysis.metrics.static_metrics or {}

    # Run assessment
    assessment = readiness_assessor.assess(
        repo_health=repo_health,
        tech_debt=tech_debt,
        product_level=product_level,
        complexity=complexity,
        structure_data=structure_data,
        static_metrics=static_metrics,
    )

    return assessment.to_dict()


@router.get("/levels")
async def get_readiness_levels() -> Dict[str, Any]:
    """
    Get readiness level definitions.
    """
    return {
        "levels": [
            {
                "id": "not_ready",
                "label": "Not Ready",
                "min_score": 0,
                "max_score": 40,
                "description": "Needs significant work before evaluation",
                "action": "Address all blockers and critical issues",
            },
            {
                "id": "needs_work",
                "label": "Needs Work",
                "min_score": 40,
                "max_score": 60,
                "description": "Some issues to address before proceeding",
                "action": "Fix critical issues and improve documentation",
            },
            {
                "id": "almost_ready",
                "label": "Almost Ready",
                "min_score": 60,
                "max_score": 80,
                "description": "Minor improvements needed",
                "action": "Address remaining recommendations",
            },
            {
                "id": "ready",
                "label": "Ready",
                "min_score": 80,
                "max_score": 95,
                "description": "Ready for formal evaluation",
                "action": "Proceed to audit",
            },
            {
                "id": "exemplary",
                "label": "Exemplary",
                "min_score": 95,
                "max_score": 100,
                "description": "Exceeds expectations",
                "action": "Ready for immediate acceptance",
            },
        ],
        "categories": [
            "documentation",
            "runability",
            "code_quality",
            "infrastructure",
            "history",
        ],
        "priority_order": ["blocker", "critical", "important", "optional"],
    }


@router.get("/checks")
async def get_available_checks() -> Dict[str, Any]:
    """
    Get list of all readiness checks performed.
    """
    return {
        "checks": readiness_assessor.CHECKS,
        "total_weight": sum(c["weight"] for c in readiness_assessor.CHECKS),
        "categories": list(set(c["category"] for c in readiness_assessor.CHECKS)),
    }
