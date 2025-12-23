"""
API routes for contract profiles and compliance checking.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

from app.services.contract_compliance import compliance_checker
from app.services.profile_loader import profile_loader


router = APIRouter(prefix="/contracts", tags=["contracts"])


# -------------------------------------------------------------------------
# Request/Response Models
# -------------------------------------------------------------------------

class ComplianceCheckRequest(BaseModel):
    contract_profile_id: str
    repo_health: Dict[str, int]
    tech_debt: Dict[str, int]


class ProfileListResponse(BaseModel):
    profiles: List[Dict[str, Any]]


# -------------------------------------------------------------------------
# Contract Profile Endpoints
# -------------------------------------------------------------------------

@router.get("/profiles")
async def list_contract_profiles() -> ProfileListResponse:
    """List all available contract profiles."""
    profiles = compliance_checker.list_profiles()
    return ProfileListResponse(profiles=profiles)


@router.get("/profiles/{profile_id}")
async def get_contract_profile(profile_id: str) -> Dict[str, Any]:
    """Get a specific contract profile."""
    profile = compliance_checker.load_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Contract profile '{profile_id}' not found")
    return profile


@router.post("/check")
async def check_compliance(request: ComplianceCheckRequest) -> Dict[str, Any]:
    """
    Check compliance against a contract profile.

    Provide repo_health and tech_debt scores, get compliance report.
    """
    report = compliance_checker.check_compliance(
        profile_id=request.contract_profile_id,
        repo_health=request.repo_health,
        tech_debt=request.tech_debt,
    )
    return compliance_checker.to_dict(report)


@router.post("/check/{profile_id}/remediation")
async def get_remediation_tasks(
    profile_id: str,
    request: ComplianceCheckRequest,
) -> Dict[str, Any]:
    """
    Get remediation tasks for a compliance check.

    Returns prioritized list of tasks to achieve compliance.
    """
    report = compliance_checker.check_compliance(
        profile_id=profile_id,
        repo_health=request.repo_health,
        tech_debt=request.tech_debt,
    )
    tasks = compliance_checker.get_remediation_tasks(report)

    return {
        "contract_profile_id": profile_id,
        "verdict": report.verdict,
        "compliance_percent": report.compliance_percent,
        "tasks": tasks,
        "total_estimated_hours": sum(t["estimated_hours"] for t in tasks),
    }


# -------------------------------------------------------------------------
# Scoring Template Endpoints
# -------------------------------------------------------------------------

@router.get("/scoring-templates")
async def list_scoring_templates() -> ProfileListResponse:
    """List all available scoring templates."""
    templates = profile_loader.list_scoring_templates()
    return ProfileListResponse(profiles=templates)


@router.get("/scoring-templates/{template_id}")
async def get_scoring_template(template_id: str) -> Dict[str, Any]:
    """Get a specific scoring template."""
    template = profile_loader.load_scoring_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail=f"Scoring template '{template_id}' not found")
    return {
        "id": template.id,
        "label": template.label,
        "description": template.description,
        "weights": template.weights,
        "thresholds": template.thresholds,
        "levels": template.levels,
        "notes": template.notes,
    }


# -------------------------------------------------------------------------
# Pricing Profile Endpoints
# -------------------------------------------------------------------------

@router.get("/pricing-profiles")
async def list_pricing_profiles() -> ProfileListResponse:
    """List all available pricing profiles."""
    profiles = profile_loader.list_pricing_profiles()
    return ProfileListResponse(profiles=profiles)


@router.get("/pricing-profiles/{profile_id}")
async def get_pricing_profile(profile_id: str) -> Dict[str, Any]:
    """Get a specific pricing profile."""
    profile = profile_loader.load_pricing_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Pricing profile '{profile_id}' not found")
    return {
        "id": profile.id,
        "label": profile.label,
        "description": profile.description,
        "regions": profile.regions,
        "discount_factor": profile.discount_factor,
        "overhead_multiplier": profile.overhead_multiplier,
        "notes": profile.notes,
    }


@router.post("/pricing-profiles/{profile_id}/calculate")
async def calculate_cost(
    profile_id: str,
    hours: int,
    region: str = "EU",
) -> Dict[str, Any]:
    """Calculate cost using a pricing profile."""
    result = profile_loader.calculate_cost(
        profile_id=profile_id,
        base_hours=hours,
        region=region,
    )
    return result
