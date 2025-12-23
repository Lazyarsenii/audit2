"""
Product Level classification module.

Classifies repository into maturity levels:
- R&D Spike
- Prototype
- Internal Tool
- Platform Module Candidate
- Near-Product
"""
from enum import Enum
from typing import Dict, Any

from .repo_health import RepoHealthScore
from .tech_debt import TechDebtScore


class ProductLevel(str, Enum):
    RND_SPIKE = "R&D Spike"
    PROTOTYPE = "Prototype"
    INTERNAL_TOOL = "Internal Tool"
    PLATFORM_MODULE = "Platform Module Candidate"
    NEAR_PRODUCT = "Near-Product"


def classify_product_level(
    repo_health: RepoHealthScore,
    tech_debt: TechDebtScore,
    structure_data: Dict[str, Any],
) -> ProductLevel:
    """
    Classify repository into a product maturity level.

    Args:
        repo_health: RepoHealthScore instance
        tech_debt: TechDebtScore instance
        structure_data: Additional structure data

    Returns:
        ProductLevel enum value
    """
    health_total = repo_health.total      # 0-12
    debt_total = tech_debt.total          # 0-15

    # Additional signals
    has_versioning = structure_data.get("has_version_file", False)
    has_api_docs = structure_data.get("has_api_docs", False)
    has_changelog = structure_data.get("has_changelog", False)

    # Near-Product: high scores + polish signals
    if health_total >= 10 and debt_total >= 12:
        if has_versioning or has_api_docs or has_changelog:
            return ProductLevel.NEAR_PRODUCT

    # Platform Module Candidate: good architecture + structure
    if health_total >= 8 and debt_total >= 10:
        if tech_debt.architecture >= 2 and repo_health.structure >= 2:
            return ProductLevel.PLATFORM_MODULE

    # Internal Tool: decent health + infra
    if health_total >= 6 and debt_total >= 7:
        if tech_debt.infrastructure >= 2:
            return ProductLevel.INTERNAL_TOOL

    # Prototype: basic functionality
    if health_total >= 4 or debt_total >= 4:
        return ProductLevel.PROTOTYPE

    # R&D Spike: everything else
    return ProductLevel.RND_SPIKE


def get_product_level_description(level: ProductLevel) -> str:
    """Get description for a product level."""
    descriptions = {
        ProductLevel.RND_SPIKE: "One-off experiment / spike; meant to explore an idea, not to be maintained.",
        ProductLevel.PROTOTYPE: "Working end-to-end flow or feature; not production-ready; limited tests/infra.",
        ProductLevel.INTERNAL_TOOL: "Usable by the team; deployable; acceptable quality & infra for internal use.",
        ProductLevel.PLATFORM_MODULE: "Architecturally and structurally suitable to become a module in a larger platform.",
        ProductLevel.NEAR_PRODUCT: "Close to production-ready; requires polishing, hardening and product packaging.",
    }
    return descriptions.get(level, "Unknown level")
