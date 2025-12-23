"""
Product Level classification module v2.

Enhanced classification with:
- More signals for accurate classification
- Confidence scores
- Weighted scoring system
- Calibration support
"""
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, List, Tuple

from .repo_health import RepoHealthScore
from .tech_debt import TechDebtScore


class ProductLevel(str, Enum):
    RND_SPIKE = "R&D Spike"
    PROTOTYPE = "Prototype"
    INTERNAL_TOOL = "Internal Tool"
    PLATFORM_MODULE = "Platform Module Candidate"
    NEAR_PRODUCT = "Near-Product"


@dataclass
class ClassificationResult:
    """Classification result with confidence."""
    level: ProductLevel
    confidence: float  # 0.0 - 1.0
    signals: Dict[str, bool]
    scores: Dict[str, float]
    reasoning: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level.value,
            "confidence": round(self.confidence, 2),
            "confidence_label": self._confidence_label(),
            "signals": self.signals,
            "scores": {k: round(v, 2) for k, v in self.scores.items()},
            "reasoning": self.reasoning,
        }

    def _confidence_label(self) -> str:
        if self.confidence >= 0.8:
            return "high"
        elif self.confidence >= 0.6:
            return "medium"
        else:
            return "low"


# Signal weights for each product level
# Higher weight = more important for that level
LEVEL_SIGNALS = {
    ProductLevel.NEAR_PRODUCT: {
        # Required signals (weight 1.0 = must have)
        "has_version_file": 0.8,
        "has_changelog": 0.7,
        "has_api_docs": 0.6,
        "has_ci_cd_deploy": 0.9,
        "test_coverage_high": 0.8,
        "has_monitoring": 0.5,
        "has_error_handling": 0.6,
        "multi_environment": 0.7,
        # Scoring thresholds
        "health_threshold": (10, 12),  # min, max
        "debt_threshold": (12, 15),
    },
    ProductLevel.PLATFORM_MODULE: {
        "has_clear_api": 0.9,
        "has_module_structure": 0.8,
        "low_coupling": 0.7,
        "has_interfaces": 0.6,
        "has_ci": 0.7,
        "test_coverage_medium": 0.6,
        "health_threshold": (8, 12),
        "debt_threshold": (10, 15),
    },
    ProductLevel.INTERNAL_TOOL: {
        "has_dockerfile": 0.8,
        "has_run_instructions": 0.7,
        "has_basic_tests": 0.5,
        "has_ci": 0.6,
        "deployable": 0.7,
        "health_threshold": (6, 12),
        "debt_threshold": (7, 15),
    },
    ProductLevel.PROTOTYPE: {
        "has_readme": 0.6,
        "runs_locally": 0.7,
        "has_any_structure": 0.5,
        "more_than_poc": 0.6,
        "health_threshold": (4, 12),
        "debt_threshold": (4, 15),
    },
    ProductLevel.RND_SPIKE: {
        # Low thresholds - catches everything else
        "health_threshold": (0, 4),
        "debt_threshold": (0, 4),
    },
}


def classify_product_level_v2(
    repo_health: RepoHealthScore,
    tech_debt: TechDebtScore,
    structure_data: Dict[str, Any],
    static_metrics: Dict[str, Any] = None,
) -> ClassificationResult:
    """
    Enhanced product level classification with confidence scores.

    Args:
        repo_health: Repository health scores
        tech_debt: Technical debt scores
        structure_data: Structure analysis data
        static_metrics: Optional static analysis metrics

    Returns:
        ClassificationResult with level, confidence, and reasoning
    """
    static_metrics = static_metrics or {}

    # Extract all signals
    signals = _extract_signals(repo_health, tech_debt, structure_data, static_metrics)

    # Calculate scores for each level
    level_scores: Dict[ProductLevel, Tuple[float, List[str]]] = {}

    for level in ProductLevel:
        score, reasons = _calculate_level_score(
            level, signals, repo_health, tech_debt
        )
        level_scores[level] = (score, reasons)

    # Find best matching level
    best_level = max(level_scores.keys(), key=lambda l: level_scores[l][0])
    best_score, reasons = level_scores[best_level]

    # Calculate confidence based on score margin
    scores_sorted = sorted(level_scores.values(), key=lambda x: x[0], reverse=True)
    if len(scores_sorted) > 1:
        margin = scores_sorted[0][0] - scores_sorted[1][0]
        # Confidence based on margin and absolute score
        confidence = min(1.0, (best_score * 0.7) + (margin * 0.3))
    else:
        confidence = best_score

    return ClassificationResult(
        level=best_level,
        confidence=confidence,
        signals=signals,
        scores={l.value: s for l, (s, _) in level_scores.items()},
        reasoning=reasons,
    )


def _extract_signals(
    health: RepoHealthScore,
    debt: TechDebtScore,
    structure: Dict[str, Any],
    static: Dict[str, Any],
) -> Dict[str, bool]:
    """Extract all classification signals from analysis data."""

    # Get test coverage
    coverage = static.get("test_coverage", 0) or 0

    return {
        # Documentation signals
        "has_readme": structure.get("has_readme", False),
        "has_docs_folder": structure.get("has_docs_folder", False),
        "has_api_docs": structure.get("has_api_docs", False),
        "has_architecture_docs": structure.get("has_architecture_docs", False),
        "has_changelog": structure.get("has_changelog", False),
        "has_version_file": structure.get("has_version_file", False),

        # Structure signals
        "has_any_structure": health.structure >= 1,
        "has_module_structure": health.structure >= 2,
        "has_clear_layers": structure.get("has_clear_layers", False),
        "has_interfaces": structure.get("has_interfaces", False),
        "low_coupling": debt.architecture >= 2,
        "has_clear_api": structure.get("has_api_folder", False) or structure.get("has_api_docs", False),

        # Runability signals
        "has_dockerfile": structure.get("has_dockerfile", False),
        "has_docker_compose": structure.get("has_docker_compose", False),
        "has_run_instructions": structure.get("has_run_instructions", False),
        "runs_locally": health.runability >= 2,
        "deployable": health.runability >= 2 and debt.infrastructure >= 2,
        "multi_environment": structure.get("has_env_files", False),

        # Testing signals
        "has_basic_tests": debt.testing >= 1,
        "test_coverage_medium": coverage >= 40,
        "test_coverage_high": coverage >= 70,

        # Infrastructure signals
        "has_ci": debt.infrastructure >= 1,
        "has_ci_cd_deploy": debt.infrastructure >= 3,
        "has_monitoring": structure.get("has_monitoring_config", False),
        "has_error_handling": static.get("has_error_handling", False),

        # Maturity signals
        "more_than_poc": health.total >= 4 or debt.total >= 4,
        "active_development": structure.get("recent_commits", 0) >= 5,
        "multiple_authors": structure.get("authors_count", 1) >= 2,
    }


def _calculate_level_score(
    level: ProductLevel,
    signals: Dict[str, bool],
    health: RepoHealthScore,
    debt: TechDebtScore,
) -> Tuple[float, List[str]]:
    """Calculate how well the repo matches a product level."""

    level_config = LEVEL_SIGNALS.get(level, {})
    reasons = []
    total_weight = 0.0
    matched_weight = 0.0

    # Check threshold requirements
    health_range = level_config.get("health_threshold", (0, 12))
    debt_range = level_config.get("debt_threshold", (0, 15))

    health_ok = health_range[0] <= health.total <= health_range[1]
    debt_ok = debt_range[0] <= debt.total <= debt_range[1]

    # Base score from thresholds
    if level == ProductLevel.RND_SPIKE:
        # R&D Spike: score higher if scores are LOW
        if health.total <= 4 and debt.total <= 4:
            base_score = 0.9
            reasons.append(f"Low scores (health={health.total}, debt={debt.total}) indicate R&D spike")
        else:
            base_score = 0.1
    else:
        # Other levels: must meet minimum thresholds
        if not health_ok:
            reasons.append(f"Health {health.total} below threshold {health_range[0]}")
            return 0.0, reasons
        if not debt_ok:
            reasons.append(f"Tech debt {debt.total} below threshold {debt_range[0]}")
            return 0.0, reasons

        # Normalize score within range
        health_norm = (health.total - health_range[0]) / max(1, health_range[1] - health_range[0])
        debt_norm = (debt.total - debt_range[0]) / max(1, debt_range[1] - debt_range[0])
        base_score = (health_norm + debt_norm) / 2
        reasons.append(f"Base scores: health={health.total}/{health_range[1]}, debt={debt.total}/{debt_range[1]}")

    # Check signal matches
    for signal_name, weight in level_config.items():
        if signal_name.endswith("_threshold"):
            continue

        if not isinstance(weight, (int, float)):
            continue

        total_weight += weight
        if signals.get(signal_name, False):
            matched_weight += weight
            reasons.append(f"+ {signal_name}")
        elif weight >= 0.7:
            reasons.append(f"- Missing important: {signal_name}")

    # Calculate final score
    if total_weight > 0:
        signal_score = matched_weight / total_weight
        final_score = (base_score * 0.4) + (signal_score * 0.6)
    else:
        final_score = base_score

    return final_score, reasons


# Calibration support
class ProductLevelCalibrator:
    """
    Calibrator for adjusting thresholds based on historical data.

    Usage:
        calibrator = ProductLevelCalibrator()
        calibrator.add_sample(analysis_result, actual_level)
        calibrator.add_sample(...)
        new_thresholds = calibrator.calculate_optimal_thresholds()
    """

    def __init__(self):
        self.samples: List[Tuple[Dict[str, Any], ProductLevel]] = []

    def add_sample(
        self,
        signals: Dict[str, bool],
        health_total: int,
        debt_total: int,
        actual_level: ProductLevel,
    ):
        """Add a calibration sample with known correct level."""
        self.samples.append((
            {
                "signals": signals,
                "health": health_total,
                "debt": debt_total,
            },
            actual_level,
        ))

    def calculate_accuracy(self) -> float:
        """Calculate current classification accuracy."""
        if not self.samples:
            return 0.0

        correct = 0
        for data, actual in self.samples:
            # Would need to reconstruct scores - simplified here
            pass

        return correct / len(self.samples)

    def suggest_threshold_adjustments(self) -> Dict[ProductLevel, Dict[str, Any]]:
        """Analyze samples and suggest threshold adjustments."""
        # Group samples by actual level
        by_level: Dict[ProductLevel, List[Dict]] = {l: [] for l in ProductLevel}

        for data, actual in self.samples:
            by_level[actual].append(data)

        suggestions = {}
        for level, samples in by_level.items():
            if not samples:
                continue

            health_values = [s["health"] for s in samples]
            debt_values = [s["debt"] for s in samples]

            suggestions[level] = {
                "health_threshold": (min(health_values), max(health_values)),
                "debt_threshold": (min(debt_values), max(debt_values)),
                "sample_count": len(samples),
            }

        return suggestions
