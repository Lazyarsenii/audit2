"""
Cost Estimator service.

Calculates forward-looking and historical effort/cost estimates.
"""
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from pathlib import Path

import yaml

from app.core.scoring.complexity import Complexity, get_base_hours
from app.core.scoring.tech_debt import TechDebtScore

logger = logging.getLogger(__name__)


@dataclass
class ActivityBreakdown:
    """Hours breakdown by activity."""
    analysis: float
    design: float
    development: float
    qa: float
    documentation: float

    @property
    def total(self) -> float:
        return self.analysis + self.design + self.development + self.qa + self.documentation

    def to_dict(self) -> Dict[str, float]:
        return {
            "analysis": round(self.analysis, 1),
            "design": round(self.design, 1),
            "development": round(self.development, 1),
            "qa": round(self.qa, 1),
            "documentation": round(self.documentation, 1),
            "total": round(self.total, 1),
        }


@dataclass
class CostRange:
    """Cost range with min/max values."""
    min: float
    max: float
    currency: str
    currency_symbol: str

    @property
    def formatted(self) -> str:
        """Human-readable cost range, rounded to hundreds."""
        return (
            f"{self.currency_symbol}{round(self.min, -2):,.0f} - "
            f"{self.currency_symbol}{round(self.max, -2):,.0f}"
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "min": round(self.min, -2),  # Round to nearest 100
            "max": round(self.max, -2),
            "currency": self.currency,
            "formatted": self.formatted,
        }


@dataclass
class ForwardEstimate:
    """Forward-looking cost estimate."""
    hours_min: ActivityBreakdown
    hours_typical: ActivityBreakdown
    hours_max: ActivityBreakdown
    cost_eu: CostRange
    cost_ua: CostRange
    complexity: str
    tech_debt_multiplier: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hours": {
                "min": self.hours_min.to_dict(),
                "typical": self.hours_typical.to_dict(),
                "max": self.hours_max.to_dict(),
            },
            "cost": {
                "eu": self.cost_eu.to_dict(),
                "ua": self.cost_ua.to_dict(),
            },
            "complexity": self.complexity,
            "tech_debt_multiplier": self.tech_debt_multiplier,
        }


@dataclass
class HistoricalEstimate:
    """Historical effort estimate based on git history."""
    active_days: int
    estimated_hours_min: float
    estimated_hours_max: float
    estimated_person_months_min: float
    estimated_person_months_max: float
    cost_eu: CostRange
    cost_ua: CostRange
    confidence: str  # low, medium, high
    note: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "active_days": self.active_days,
            "hours": {
                "min": round(self.estimated_hours_min, 0),
                "max": round(self.estimated_hours_max, 0),
            },
            "person_months": {
                "min": round(self.estimated_person_months_min, 1),
                "max": round(self.estimated_person_months_max, 1),
            },
            "cost": {
                "eu": self.cost_eu.to_dict(),
                "ua": self.cost_ua.to_dict(),
            },
            "confidence": self.confidence,
            "note": self.note,
        }


class CostEstimator:
    """Service for estimating development costs."""

    # Default activity ratios (as multiplier of DEV hours)
    DEFAULT_RATIOS = {
        "analysis": {"min": 0.15, "typical": 0.25, "max": 0.35},
        "design": {"min": 0.20, "typical": 0.30, "max": 0.40},
        "qa": {"min": 0.15, "typical": 0.25, "max": 0.35},
        "documentation": {"min": 0.05, "typical": 0.10, "max": 0.20},
    }

    # Default regional rates
    DEFAULT_RATES = {
        "eu": {"min": 50, "max": 90, "currency": "EUR", "symbol": "€"},
        "ua": {"min": 30, "max": 55, "currency": "USD", "symbol": "$"},
    }

    # Tech debt multipliers
    TECH_DEBT_MULTIPLIERS = {
        (0, 3): 1.5,    # Very high debt
        (4, 6): 1.3,    # High debt
        (7, 9): 1.15,   # Moderate debt
        (10, 12): 1.05, # Low debt
        (13, 15): 1.0,  # Minimal debt
    }

    # Historical estimation config
    HISTORICAL_CONFIG = {
        "activity_factor_min": 0.5,
        "activity_factor_max": 0.8,
        "hours_per_day_min": 4,
        "hours_per_day_max": 7,
        "hours_per_month": 160,
        "max_effective_authors": 4,
    }

    def __init__(self, config_path: Optional[Path] = None):
        self.ratios = self.DEFAULT_RATIOS.copy()
        self.rates = self.DEFAULT_RATES.copy()

        if config_path and config_path.exists():
            self._load_config(config_path)

    def _load_config(self, path: Path) -> None:
        """Load configuration from YAML."""
        try:
            with open(path) as f:
                config = yaml.safe_load(f)

            if "activity_ratios" in config:
                self.ratios.update(config["activity_ratios"])

            if "regional_rates" in config:
                for region, data in config["regional_rates"].items():
                    if region in self.rates:
                        blended = data.get("blended", {})
                        self.rates[region]["min"] = blended.get("min", self.rates[region]["min"])
                        self.rates[region]["max"] = blended.get("max", self.rates[region]["max"])

        except Exception as e:
            logger.warning(f"Failed to load cost config: {e}")

    def estimate_forward(
        self,
        complexity: Complexity,
        tech_debt: TechDebtScore,
        region_mode: str = "EU_UA",
    ) -> ForwardEstimate:
        """
        Calculate forward-looking cost estimate.

        Args:
            complexity: Project complexity level
            tech_debt: Tech debt scores
            region_mode: "EU", "UA", or "EU_UA"

        Returns:
            ForwardEstimate with hours and costs
        """
        # Get base hours for complexity
        base_hours = get_base_hours(complexity)

        # Get tech debt multiplier
        multiplier = self._get_tech_debt_multiplier(tech_debt.total)

        # Calculate hours for each scenario
        hours_min = self._calculate_hours(base_hours["min"], multiplier, "min")
        hours_typical = self._calculate_hours(base_hours["typical"], multiplier, "typical")
        hours_max = self._calculate_hours(base_hours["max"], multiplier, "max")

        # Calculate costs
        cost_eu = CostRange(
            min=hours_min.total * self.rates["eu"]["min"],
            max=hours_max.total * self.rates["eu"]["max"],
            currency=self.rates["eu"]["currency"],
            currency_symbol=self.rates["eu"]["symbol"],
        )

        cost_ua = CostRange(
            min=hours_min.total * self.rates["ua"]["min"],
            max=hours_max.total * self.rates["ua"]["max"],
            currency=self.rates["ua"]["currency"],
            currency_symbol=self.rates["ua"]["symbol"],
        )

        return ForwardEstimate(
            hours_min=hours_min,
            hours_typical=hours_typical,
            hours_max=hours_max,
            cost_eu=cost_eu,
            cost_ua=cost_ua,
            complexity=complexity.value,
            tech_debt_multiplier=multiplier,
        )

    def estimate_historical(
        self,
        structure_data: Dict[str, Any],
    ) -> HistoricalEstimate:
        """
        Estimate historical effort based on git history.

        Args:
            structure_data: Structure analysis data with git metrics

        Returns:
            HistoricalEstimate with approximated effort
        """
        commits = structure_data.get("commits_total", 0)
        authors = structure_data.get("authors_count", 1)
        recent_commits = structure_data.get("recent_commits", 0)

        # Estimate active days (rough: 1 commit ≈ 0.3-0.5 active days)
        # More sophisticated: could use actual commit dates
        active_days = int(commits * 0.4)

        # Cap effective authors
        effective_authors = min(authors, self.HISTORICAL_CONFIG["max_effective_authors"])

        # Calculate hours range
        cfg = self.HISTORICAL_CONFIG
        hours_min = (
            active_days
            * cfg["activity_factor_min"]
            * cfg["hours_per_day_min"]
            * (1 + (effective_authors - 1) * 0.3)  # Diminishing returns for more authors
        )
        hours_max = (
            active_days
            * cfg["activity_factor_max"]
            * cfg["hours_per_day_max"]
            * (1 + (effective_authors - 1) * 0.5)
        )

        # Person months
        pm_min = hours_min / cfg["hours_per_month"]
        pm_max = hours_max / cfg["hours_per_month"]

        # Costs
        cost_eu = CostRange(
            min=hours_min * self.rates["eu"]["min"],
            max=hours_max * self.rates["eu"]["max"],
            currency=self.rates["eu"]["currency"],
            currency_symbol=self.rates["eu"]["symbol"],
        )

        cost_ua = CostRange(
            min=hours_min * self.rates["ua"]["min"],
            max=hours_max * self.rates["ua"]["max"],
            currency=self.rates["ua"]["currency"],
            currency_symbol=self.rates["ua"]["symbol"],
        )

        # Determine confidence
        if commits < 20:
            confidence = "low"
        elif commits < 100:
            confidence = "medium"
        else:
            confidence = "medium"  # Never "high" for heuristic estimates

        return HistoricalEstimate(
            active_days=active_days,
            estimated_hours_min=hours_min,
            estimated_hours_max=hours_max,
            estimated_person_months_min=pm_min,
            estimated_person_months_max=pm_max,
            cost_eu=cost_eu,
            cost_ua=cost_ua,
            confidence=confidence,
            note="Approximate estimate based on commit history. Not suitable for financial accounting.",
        )

    def _calculate_hours(
        self,
        dev_hours: float,
        multiplier: float,
        scenario: str,
    ) -> ActivityBreakdown:
        """Calculate hours breakdown for a scenario."""
        adjusted_dev = dev_hours * multiplier

        return ActivityBreakdown(
            analysis=adjusted_dev * self.ratios["analysis"][scenario],
            design=adjusted_dev * self.ratios["design"][scenario],
            development=adjusted_dev,
            qa=adjusted_dev * self.ratios["qa"][scenario],
            documentation=adjusted_dev * self.ratios["documentation"][scenario],
        )

    def _get_tech_debt_multiplier(self, debt_total: int) -> float:
        """Get multiplier based on tech debt score."""
        for (low, high), mult in self.TECH_DEBT_MULTIPLIERS.items():
            if low <= debt_total <= high:
                return mult
        return 1.0


# Singleton with default config
cost_estimator = CostEstimator(
    config_path=Path(__file__).parent.parent / "config" / "cost_profile.yaml"
)
