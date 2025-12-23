"""
Complexity classification module.

Classifies repository complexity as: S / M / L / XL
"""
from enum import Enum
from typing import Dict, Any

from .repo_health import RepoHealthScore
from .tech_debt import TechDebtScore


class Complexity(str, Enum):
    SMALL = "S"
    MEDIUM = "M"
    LARGE = "L"
    XLARGE = "XL"


# Default thresholds (can be overridden via config)
COMPLEXITY_THRESHOLDS = {
    "S": {"max_loc": 8000, "max_files": 50},
    "M": {"max_loc": 40000, "max_files": 200},
    "L": {"max_loc": 120000, "max_files": 500},
    "XL": {"min_loc": 120001},
}


def calculate_complexity(
    static_metrics: Dict[str, Any],
    repo_health: RepoHealthScore,
    tech_debt: TechDebtScore,
) -> Complexity:
    """
    Calculate complexity level based on size and quality metrics.

    Args:
        static_metrics: Output from StaticAnalyzer containing:
            - total_loc: int
            - files_count: int
            - external_deps_count: int
        repo_health: RepoHealthScore instance
        tech_debt: TechDebtScore instance

    Returns:
        Complexity enum value (S/M/L/XL)
    """
    loc = static_metrics.get("total_loc", 0)
    files = static_metrics.get("files_count", 0)
    deps = static_metrics.get("external_deps_count", 0)

    # Base complexity from LOC
    if loc <= COMPLEXITY_THRESHOLDS["S"]["max_loc"]:
        base = Complexity.SMALL
    elif loc <= COMPLEXITY_THRESHOLDS["M"]["max_loc"]:
        base = Complexity.MEDIUM
    elif loc <= COMPLEXITY_THRESHOLDS["L"]["max_loc"]:
        base = Complexity.LARGE
    else:
        base = Complexity.XLARGE

    # Adjustment factors
    adjusted = base

    # High tech debt bumps complexity
    if tech_debt.total <= 5:  # Very high debt (out of 15)
        adjusted = _bump_complexity(adjusted)

    # Many integrations/deps bumps complexity
    if deps > 30:
        adjusted = _bump_complexity(adjusted)

    # Many files relative to LOC (scattered codebase)
    if files > 0 and loc / files < 50:  # < 50 LOC per file average
        adjusted = _bump_complexity(adjusted)

    return adjusted


def _bump_complexity(current: Complexity) -> Complexity:
    """Bump complexity one level up."""
    order = [Complexity.SMALL, Complexity.MEDIUM, Complexity.LARGE, Complexity.XLARGE]
    idx = order.index(current)
    if idx < len(order) - 1:
        return order[idx + 1]
    return current


def get_complexity_description(complexity: Complexity) -> str:
    """Get description for a complexity level."""
    descriptions = {
        Complexity.SMALL: "Single service, few dependencies (~5-8k LOC)",
        Complexity.MEDIUM: "Multiple modules, a couple of integrations (~8-40k LOC)",
        Complexity.LARGE: "Multiple services, complex architecture (~40-120k LOC)",
        Complexity.XLARGE: "Platform/monolith with extensive integration (>120k LOC)",
    }
    return descriptions.get(complexity, "Unknown complexity")


def get_base_hours(complexity: Complexity) -> Dict[str, int]:
    """Get base development hours for complexity level."""
    hours = {
        Complexity.SMALL: {"min": 40, "typical": 50, "max": 80},
        Complexity.MEDIUM: {"min": 120, "typical": 175, "max": 250},
        Complexity.LARGE: {"min": 250, "typical": 300, "max": 450},
        Complexity.XLARGE: {"min": 500, "typical": 700, "max": 1200},
    }
    return hours.get(complexity, hours[Complexity.MEDIUM])
