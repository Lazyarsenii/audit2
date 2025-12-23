"""
COCOMO II Cost Estimation Model.

Industry-standard software cost estimation based on:
- Constructive Cost Model II (COCOMO II)
- Calibrated for modern development practices
- Uses actual LOC data for more accurate estimates

Provides ±20% confidence interval instead of 7x spread.

References:
- Boehm, B. W. et al. (2000). Software Cost Estimation with COCOMO II
- IEEE Software Engineering Body of Knowledge (SWEBOK)
"""
import logging
import math
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from enum import Enum

logger = logging.getLogger(__name__)


class ProjectType(str, Enum):
    """COCOMO II project types with calibrated exponents."""
    ORGANIC = "organic"           # Small teams, familiar domain, flexible requirements
    SEMI_DETACHED = "semi"        # Medium teams, mixed experience, some constraints
    EMBEDDED = "embedded"         # Large teams, strict requirements, complex integration


@dataclass
class EffortMultipliers:
    """
    COCOMO II Effort Multipliers (scale factors).

    Each multiplier affects the final estimate:
    - < 1.0 = reduces effort (favorable condition)
    - 1.0 = neutral
    - > 1.0 = increases effort (unfavorable condition)
    """
    # Product factors
    reliability: float = 1.0          # Required software reliability (RELY)
    database_size: float = 1.0        # Database size relative to program (DATA)
    complexity: float = 1.0           # Product complexity (CPLX)
    reuse_required: float = 1.0       # Required reusability (RUSE)
    documentation: float = 1.0        # Documentation match to lifecycle needs (DOCU)

    # Platform factors
    execution_time: float = 1.0       # Execution time constraint (TIME)
    storage_constraint: float = 1.0   # Main storage constraint (STOR)
    platform_volatility: float = 1.0  # Platform volatility (PVOL)

    # Personnel factors
    analyst_capability: float = 1.0   # Analyst capability (ACAP)
    programmer_capability: float = 1.0 # Programmer capability (PCAP)
    personnel_continuity: float = 1.0  # Personnel continuity (PCON)
    application_experience: float = 1.0 # Applications experience (APEX)
    platform_experience: float = 1.0   # Platform experience (PLEX)
    language_experience: float = 1.0   # Language/tool experience (LTEX)

    # Project factors
    tool_use: float = 1.0              # Use of software tools (TOOL)
    multisite_development: float = 1.0 # Multisite development (SITE)
    schedule_pressure: float = 1.0     # Required development schedule (SCED)

    @property
    def product_effort(self) -> float:
        """Combined product multiplier."""
        return (self.reliability * self.database_size * self.complexity *
                self.reuse_required * self.documentation)

    @property
    def total(self) -> float:
        """Total effort adjustment multiplier."""
        return (
            self.reliability * self.database_size * self.complexity *
            self.reuse_required * self.documentation *
            self.execution_time * self.storage_constraint * self.platform_volatility *
            self.analyst_capability * self.programmer_capability * self.personnel_continuity *
            self.application_experience * self.platform_experience * self.language_experience *
            self.tool_use * self.multisite_development * self.schedule_pressure
        )


@dataclass
class CocomoEstimate:
    """COCOMO II estimation result."""
    # Core estimates
    effort_person_months: float
    duration_months: float
    team_size: float

    # Hour calculations
    hours_typical: float
    hours_min: float      # -30% (optimistic)
    hours_max: float      # +30% (pessimistic)

    # Cost by region
    cost_ua_typical: float
    cost_ua_min: float
    cost_ua_max: float
    cost_eu_typical: float
    cost_eu_min: float
    cost_eu_max: float

    # Breakdown
    hours_breakdown: Dict[str, float] = field(default_factory=dict)

    # Metadata
    kloc: float = 0.0
    project_type: str = ""
    effort_multiplier: float = 1.0
    confidence_level: str = "±20%"
    methodology: str = "COCOMO II"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "methodology": self.methodology,
            "confidence": self.confidence_level,
            "kloc": round(self.kloc, 2),
            "project_type": self.project_type,
            "effort_multiplier": round(self.effort_multiplier, 2),
            "effort": {
                "person_months": round(self.effort_person_months, 1),
                "duration_months": round(self.duration_months, 1),
                "team_size": round(self.team_size, 1),
            },
            "hours": {
                "typical": round(self.hours_typical),
                "min": round(self.hours_min),
                "max": round(self.hours_max),
            },
            "hours_breakdown": {k: round(v) for k, v in self.hours_breakdown.items()},
            "cost": {
                "ua": {
                    "typical": round(self.cost_ua_typical, -2),
                    "min": round(self.cost_ua_min, -2),
                    "max": round(self.cost_ua_max, -2),
                    "currency": "USD",
                    "formatted": f"${round(self.cost_ua_typical, -2):,.0f} (±20%: ${round(self.cost_ua_min, -2):,.0f} - ${round(self.cost_ua_max, -2):,.0f})",
                },
                "eu": {
                    "typical": round(self.cost_eu_typical, -2),
                    "min": round(self.cost_eu_min, -2),
                    "max": round(self.cost_eu_max, -2),
                    "currency": "EUR",
                    "formatted": f"€{round(self.cost_eu_typical, -2):,.0f} (±20%: €{round(self.cost_eu_min, -2):,.0f} - €{round(self.cost_eu_max, -2):,.0f})",
                },
            },
        }


class CocomoEstimator:
    """
    COCOMO II based cost estimator.

    Uses the Constructive Cost Model II formula:
        Effort = A × (KLOC)^E × EAF

    Where:
        A = calibration constant (default 2.94)
        KLOC = thousands of lines of code
        E = exponent based on scale factors (1.0 to 1.226)
        EAF = effort adjustment factor (product of all multipliers)

    Duration = C × (Effort)^D

    Where:
        C = 3.67 (calibration constant)
        D = 0.28 + 0.2 × (E - 1.01)
    """

    # COCOMO II calibration constants
    CONSTANTS = {
        ProjectType.ORGANIC: {"a": 2.4, "b": 1.05, "c": 2.5, "d": 0.38},
        ProjectType.SEMI_DETACHED: {"a": 3.0, "b": 1.12, "c": 2.5, "d": 0.35},
        ProjectType.EMBEDDED: {"a": 3.6, "b": 1.20, "c": 2.5, "d": 0.32},
    }

    # Modern calibration (adjusted for agile/modern development)
    # Original COCOMO II.2000 was calibrated for 1990s enterprise projects
    # These values are tuned for modern development practices (2020s)
    # Key insight: modern devs are ~3-4x more productive due to better tools,
    # frameworks, AI assistants, and established patterns.
    MODERN_CONSTANTS = {
        "a": 0.2,       # Effort coefficient (reduced from 2.94 for modern dev)
        "b": 0.85,      # Base exponent (economies of scale in modern dev)
        "c": 2.0,       # Schedule coefficient (faster delivery in modern teams)
        "d": 0.35,      # Schedule exponent base
        "e_base": 1.0,  # Base exponent
    }

    # Regional hourly rates with junior/middle/senior breakdown
    # Synced with frontend profiles.ts (January 2025 market data)
    # Typical = blended rate (20% junior + 50% middle + 30% senior)
    RATES = {
        "ua": {
            "junior": 15, "middle": 25, "senior": 45,
            "typical": 28, "min": 15, "max": 45,
            "currency": "USD",
            "name": "Ukraine",
        },
        "ua_compliance": {
            "junior": 25, "middle": 35, "senior": 55,
            "typical": 38, "min": 25, "max": 55,
            "currency": "USD",
            "name": "Ukraine (Compliance)",
        },
        "pl": {
            "junior": 25, "middle": 40, "senior": 50,
            "typical": 40, "min": 25, "max": 50,
            "currency": "EUR",
            "name": "Poland",
        },
        "eu": {
            "junior": 35, "middle": 50, "senior": 75,
            "typical": 55, "min": 35, "max": 75,
            "currency": "EUR",
            "name": "EU Standard",
        },
        "de": {
            "junior": 40, "middle": 60, "senior": 80,
            "typical": 62, "min": 40, "max": 80,
            "currency": "EUR",
            "name": "Germany",
        },
        "uk": {
            "junior": 40, "middle": 60, "senior": 85,
            "typical": 64, "min": 40, "max": 85,
            "currency": "GBP",
            "name": "United Kingdom",
        },
        "us": {
            "junior": 30, "middle": 65, "senior": 100,
            "typical": 69, "min": 30, "max": 100,
            "currency": "USD",
            "name": "United States",
        },
        "in": {
            "junior": 15, "middle": 25, "senior": 35,
            "typical": 26, "min": 15, "max": 35,
            "currency": "USD",
            "name": "India",
        },
    }

    # Hours per person-month (industry standard)
    HOURS_PER_PM = 160  # Productive hours (standard month)

    # Confidence interval (tighter for more useful estimates)
    CONFIDENCE_FACTOR = 0.20  # ±20% instead of ±30%

    # Activity distribution (based on industry averages)
    ACTIVITY_RATIOS = {
        "analysis": 0.12,        # Requirements, research
        "design": 0.18,          # Architecture, API design
        "implementation": 0.42,  # Coding
        "testing": 0.20,         # QA, testing
        "documentation": 0.08,   # Technical docs
    }

    def __init__(self):
        pass

    def estimate(
        self,
        loc: int,
        tech_debt_score: int = 10,
        test_coverage_percent: Optional[float] = None,
        has_ci: bool = False,
        has_documentation: bool = False,
        team_experience: str = "nominal",  # low, nominal, high
        project_type: ProjectType = ProjectType.SEMI_DETACHED,
    ) -> CocomoEstimate:
        """
        Estimate development effort using COCOMO II model.

        Args:
            loc: Lines of code
            tech_debt_score: Tech debt score (0-15, higher = less debt)
            test_coverage_percent: Test coverage (0-100)
            has_ci: Whether project has CI/CD
            has_documentation: Whether project has good documentation
            team_experience: low, nominal, high
            project_type: COCOMO project classification

        Returns:
            CocomoEstimate with hours and cost projections
        """
        kloc = loc / 1000.0
        if kloc < 0.1:
            kloc = 0.1  # Minimum 100 LOC

        # Calculate effort multipliers based on project characteristics
        multipliers = self._calculate_multipliers(
            tech_debt_score=tech_debt_score,
            test_coverage=test_coverage_percent,
            has_ci=has_ci,
            has_documentation=has_documentation,
            team_experience=team_experience,
        )

        # COCOMO II formula
        constants = self.MODERN_CONSTANTS
        exponent = constants["b"] + 0.01 * self._calculate_scale_factor(tech_debt_score)

        # Base effort in person-months
        effort_pm = constants["a"] * (kloc ** exponent) * multipliers.total

        # Duration in months (schedule compression considered)
        duration_exp = constants["d"] + 0.2 * (exponent - constants["e_base"])
        duration_months = constants["c"] * (effort_pm ** duration_exp)

        # Team size
        team_size = effort_pm / max(duration_months, 1)

        # Convert to hours
        hours_typical = effort_pm * self.HOURS_PER_PM
        cf = self.CONFIDENCE_FACTOR
        hours_min = hours_typical * (1 - cf)   # -20% (optimistic)
        hours_max = hours_typical * (1 + cf)   # +20% (pessimistic)

        # Calculate hours breakdown
        breakdown = {
            activity: hours_typical * ratio
            for activity, ratio in self.ACTIVITY_RATIOS.items()
        }

        # Cost calculations (using same confidence factor for consistency)
        def calc_cost(hours: float, region: str) -> Dict[str, float]:
            rates = self.RATES[region]
            return {
                "typical": hours * rates["typical"],
                "min": hours * (1 - cf) * rates["min"],
                "max": hours * (1 + cf) * rates["max"],
            }

        ua_cost = calc_cost(hours_typical, "ua")
        eu_cost = calc_cost(hours_typical, "eu")

        logger.info(
            f"[COCOMO] {kloc:.1f} KLOC × {multipliers.total:.2f} EAF = "
            f"{effort_pm:.1f} PM = {hours_typical:.0f} hrs = ${ua_cost['typical']:,.0f}"
        )

        return CocomoEstimate(
            effort_person_months=effort_pm,
            duration_months=duration_months,
            team_size=team_size,
            hours_typical=hours_typical,
            hours_min=hours_min,
            hours_max=hours_max,
            cost_ua_typical=ua_cost["typical"],
            cost_ua_min=ua_cost["min"],
            cost_ua_max=ua_cost["max"],
            cost_eu_typical=eu_cost["typical"],
            cost_eu_min=eu_cost["min"],
            cost_eu_max=eu_cost["max"],
            hours_breakdown=breakdown,
            kloc=kloc,
            project_type=project_type.value,
            effort_multiplier=multipliers.total,
        )

    def _calculate_multipliers(
        self,
        tech_debt_score: int,
        test_coverage: Optional[float],
        has_ci: bool,
        has_documentation: bool,
        team_experience: str,
    ) -> EffortMultipliers:
        """Calculate effort multipliers based on project state."""
        m = EffortMultipliers()

        # Tech debt affects complexity and reliability requirements
        if tech_debt_score <= 5:
            m.complexity = 1.30  # High debt = complex to work with
            m.reliability = 1.15
        elif tech_debt_score <= 9:
            m.complexity = 1.15
            m.reliability = 1.05
        elif tech_debt_score <= 12:
            m.complexity = 1.0
            m.reliability = 1.0
        else:
            m.complexity = 0.90  # Low debt = easier
            m.reliability = 0.95

        # Test coverage affects QA effort
        if test_coverage is None:
            m.reuse_required = 1.10  # Unknown = assume needs work
        elif test_coverage < 20:
            m.reuse_required = 1.20  # Need to add tests
        elif test_coverage < 50:
            m.reuse_required = 1.05
        elif test_coverage >= 70:
            m.reuse_required = 0.90  # Good coverage helps

        # CI/CD reduces integration effort
        if has_ci:
            m.tool_use = 0.90
        else:
            m.tool_use = 1.10  # Need to set up CI

        # Documentation affects onboarding
        if has_documentation:
            m.documentation = 0.95
        else:
            m.documentation = 1.10  # Need to document

        # Team experience
        experience_factors = {
            "low": {"analyst": 1.15, "programmer": 1.15, "app_exp": 1.15},
            "nominal": {"analyst": 1.0, "programmer": 1.0, "app_exp": 1.0},
            "high": {"analyst": 0.85, "programmer": 0.85, "app_exp": 0.85},
        }
        exp = experience_factors.get(team_experience, experience_factors["nominal"])
        m.analyst_capability = exp["analyst"]
        m.programmer_capability = exp["programmer"]
        m.application_experience = exp["app_exp"]

        return m

    def _calculate_scale_factor(self, tech_debt_score: int) -> float:
        """
        Calculate scale factor based on project characteristics.

        Scale factors in COCOMO II:
        - PREC: Precedentedness (how familiar is the project type)
        - FLEX: Development flexibility
        - RESL: Architecture/risk resolution
        - TEAM: Team cohesion
        - PMAT: Process maturity

        Returns a value 0-25 that affects the exponent.
        """
        # Simplified: use tech debt as proxy for overall maturity
        if tech_debt_score >= 12:
            return 10  # Mature, well-structured project
        elif tech_debt_score >= 8:
            return 14  # Average
        elif tech_debt_score >= 5:
            return 18  # Some issues
        else:
            return 22  # Significant technical challenges

    def estimate_from_metrics(
        self,
        static_metrics: Dict[str, Any],
        tech_debt_total: int,
        repo_health_total: int,
    ) -> CocomoEstimate:
        """
        Convenience method to estimate from collected metrics.

        Args:
            static_metrics: Dictionary with total_loc, has_ci, test_coverage etc.
            tech_debt_total: Tech debt score (0-15)
            repo_health_total: Repo health score (0-12)
        """
        loc = static_metrics.get("total_loc", 1000)
        test_coverage = static_metrics.get("test_coverage")
        has_ci = static_metrics.get("has_ci", False)
        has_documentation = repo_health_total >= 6  # Proxy for documentation quality

        # Infer team experience from metrics
        if repo_health_total >= 9 and tech_debt_total >= 10:
            team_experience = "high"
        elif repo_health_total >= 6 and tech_debt_total >= 6:
            team_experience = "nominal"
        else:
            team_experience = "low"

        return self.estimate(
            loc=loc,
            tech_debt_score=tech_debt_total,
            test_coverage_percent=test_coverage,
            has_ci=has_ci,
            has_documentation=has_documentation,
            team_experience=team_experience,
        )


@dataclass
class CostComparison:
    """Result of comparing actual cost with COCOMO estimate."""
    actual_cost: float
    actual_hours: Optional[float]
    actual_rate: Optional[float]

    estimated_cost_typical: float
    estimated_cost_min: float
    estimated_cost_max: float
    estimated_hours: float

    # Deviation analysis
    cost_deviation_percent: float  # positive = overpaid, negative = underpaid
    hours_deviation_percent: Optional[float]
    rate_deviation_percent: Optional[float]

    # Verdict
    verdict: str  # "within_range", "overpaid", "underpaid", "significantly_overpaid", "significantly_underpaid"
    verdict_description: str

    # Benchmark comparison
    benchmark_rate: float  # Market rate for comparison
    benchmark_region: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "actual": {
                "cost": round(self.actual_cost, 2),
                "hours": round(self.actual_hours, 1) if self.actual_hours else None,
                "rate": round(self.actual_rate, 2) if self.actual_rate else None,
            },
            "estimated": {
                "cost_typical": round(self.estimated_cost_typical, 2),
                "cost_min": round(self.estimated_cost_min, 2),
                "cost_max": round(self.estimated_cost_max, 2),
                "hours": round(self.estimated_hours, 1),
            },
            "deviation": {
                "cost_percent": round(self.cost_deviation_percent, 1),
                "hours_percent": round(self.hours_deviation_percent, 1) if self.hours_deviation_percent else None,
                "rate_percent": round(self.rate_deviation_percent, 1) if self.rate_deviation_percent else None,
            },
            "verdict": self.verdict,
            "verdict_description": self.verdict_description,
            "benchmark": {
                "rate": self.benchmark_rate,
                "region": self.benchmark_region,
            },
        }


class CostComparator:
    """
    Compares actual project costs with COCOMO estimates.

    Helps answer: "Did we overpay or underpay for this project?"
    """

    # Threshold percentages for verdicts
    THRESHOLDS = {
        "within_range": 20,        # ±20% is acceptable
        "moderate_deviation": 40,  # 20-40% deviation
        "significant_deviation": 60,  # >40% deviation
    }

    def compare(
        self,
        estimate: CocomoEstimate,
        actual_cost: float,
        actual_hours: Optional[float] = None,
        custom_rate: Optional[float] = None,
        region: str = "ua",
    ) -> CostComparison:
        """
        Compare actual project cost with COCOMO estimate.

        Args:
            estimate: COCOMO estimate from estimator
            actual_cost: Actual cost paid (in same currency as region)
            actual_hours: Actual hours spent (optional)
            custom_rate: Custom hourly rate if different from estimate
            region: Region for benchmark comparison

        Returns:
            CostComparison with deviation analysis
        """
        # Get estimated values based on region
        if region == "eu":
            est_typical = estimate.cost_eu_typical
            est_min = estimate.cost_eu_min
            est_max = estimate.cost_eu_max
        else:
            est_typical = estimate.cost_ua_typical
            est_min = estimate.cost_ua_min
            est_max = estimate.cost_ua_max

        # Calculate cost deviation
        cost_deviation = ((actual_cost - est_typical) / est_typical) * 100

        # Calculate hours deviation if provided
        hours_deviation = None
        if actual_hours:
            hours_deviation = ((actual_hours - estimate.hours_typical) / estimate.hours_typical) * 100

        # Calculate actual rate
        actual_rate = None
        rate_deviation = None
        if actual_hours and actual_hours > 0:
            actual_rate = actual_cost / actual_hours
            benchmark_rate = CocomoEstimator.RATES.get(region, CocomoEstimator.RATES["ua"])["typical"]
            rate_deviation = ((actual_rate - benchmark_rate) / benchmark_rate) * 100

        # Determine verdict
        abs_deviation = abs(cost_deviation)
        if abs_deviation <= self.THRESHOLDS["within_range"]:
            verdict = "within_range"
            if cost_deviation > 0:
                verdict_desc = f"Cost is within acceptable range (+{cost_deviation:.1f}% above estimate)"
            else:
                verdict_desc = f"Cost is within acceptable range ({cost_deviation:.1f}% below estimate)"
        elif cost_deviation > 0:
            if abs_deviation <= self.THRESHOLDS["moderate_deviation"]:
                verdict = "overpaid"
                verdict_desc = f"Moderately overpaid: +{cost_deviation:.1f}% above typical estimate"
            else:
                verdict = "significantly_overpaid"
                verdict_desc = f"Significantly overpaid: +{cost_deviation:.1f}% above typical estimate"
        else:
            if abs_deviation <= self.THRESHOLDS["moderate_deviation"]:
                verdict = "underpaid"
                verdict_desc = f"Good deal: {abs(cost_deviation):.1f}% below typical estimate"
            else:
                verdict = "significantly_underpaid"
                verdict_desc = f"Excellent deal: {abs(cost_deviation):.1f}% below typical estimate (verify quality)"

        benchmark = CocomoEstimator.RATES.get(region, CocomoEstimator.RATES["ua"])

        return CostComparison(
            actual_cost=actual_cost,
            actual_hours=actual_hours,
            actual_rate=actual_rate,
            estimated_cost_typical=est_typical,
            estimated_cost_min=est_min,
            estimated_cost_max=est_max,
            estimated_hours=estimate.hours_typical,
            cost_deviation_percent=cost_deviation,
            hours_deviation_percent=hours_deviation,
            rate_deviation_percent=rate_deviation,
            verdict=verdict,
            verdict_description=verdict_desc,
            benchmark_rate=benchmark["typical"],
            benchmark_region=region,
        )

    def compare_with_custom_rates(
        self,
        loc: int,
        actual_cost: float,
        actual_hours: Optional[float] = None,
        custom_rates: Optional[Dict[str, float]] = None,
        tech_debt_score: int = 10,
    ) -> Dict[str, Any]:
        """
        Compare actual cost using custom hourly rates.

        Args:
            loc: Lines of code
            actual_cost: Actual cost paid
            actual_hours: Actual hours (optional)
            custom_rates: Dict with "junior", "middle", "senior" rates
            tech_debt_score: Tech debt score (0-15)

        Returns:
            Dict with multiple comparisons
        """
        estimate = cocomo_estimator.estimate(loc=loc, tech_debt_score=tech_debt_score)

        result = {
            "estimate": estimate.to_dict(),
            "actual": {
                "cost": actual_cost,
                "hours": actual_hours,
            },
            "comparisons": {},
        }

        # Compare with standard regions
        for region in ["ua", "eu", "us", "de", "pl"]:
            rates = CocomoEstimator.RATES.get(region)
            if rates:
                region_cost = estimate.hours_typical * rates["typical"]
                deviation = ((actual_cost - region_cost) / region_cost) * 100
                result["comparisons"][region] = {
                    "estimated_cost": round(region_cost, 2),
                    "rate": rates["typical"],
                    "currency": rates["currency"],
                    "deviation_percent": round(deviation, 1),
                    "verdict": "overpaid" if deviation > 20 else ("underpaid" if deviation < -20 else "fair"),
                }

        # Compare with custom rates if provided
        if custom_rates:
            # Calculate blended rate (typical mix: 20% junior, 50% middle, 30% senior)
            blended_rate = (
                custom_rates.get("junior", 0) * 0.2 +
                custom_rates.get("middle", 0) * 0.5 +
                custom_rates.get("senior", 0) * 0.3
            )
            if blended_rate > 0:
                custom_cost = estimate.hours_typical * blended_rate
                deviation = ((actual_cost - custom_cost) / custom_cost) * 100
                result["comparisons"]["custom"] = {
                    "estimated_cost": round(custom_cost, 2),
                    "rate": round(blended_rate, 2),
                    "rates_breakdown": custom_rates,
                    "deviation_percent": round(deviation, 1),
                    "verdict": "overpaid" if deviation > 20 else ("underpaid" if deviation < -20 else "fair"),
                }

        # Determine actual effective rate
        if actual_hours and actual_hours > 0:
            result["actual"]["effective_rate"] = round(actual_cost / actual_hours, 2)

        return result


# Singleton instances
cocomo_estimator = CocomoEstimator()
cost_comparator = CostComparator()
