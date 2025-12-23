"""
Comprehensive Estimation Suite.

Includes:
- Multiple industry methodologies (Gartner, IEEE, Microsoft, Google, PMI, SEI SLIM, COCOMO)
- PERT 3-point analysis
- ROI Analysis
- AI Efficiency comparison (Human vs AI-Assisted vs Hybrid)

For research: demonstrates AI value in software development.
"""
import math
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from enum import Enum

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class MethodologyResult:
    """Result from a single estimation methodology."""
    id: str
    name: str
    days: float
    hours: float
    cost: float
    confidence: str  # High, Medium, Low
    formula: str
    source: str
    description: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "days": round(self.days, 1),
            "hours": round(self.hours, 1),
            "cost": round(self.cost, 2),
            "confidence": self.confidence,
            "formula": self.formula,
            "source": self.source,
            "description": self.description,
        }


@dataclass
class PERTResult:
    """PERT 3-point estimation result."""
    optimistic: float
    most_likely: float
    pessimistic: float
    expected: float
    standard_deviation: float
    variance: float
    confidence_68: tuple  # 1 std dev
    confidence_95: tuple  # 2 std dev
    confidence_99: tuple  # 3 std dev

    def to_dict(self) -> Dict[str, Any]:
        return {
            "inputs": {
                "optimistic": round(self.optimistic, 1),
                "most_likely": round(self.most_likely, 1),
                "pessimistic": round(self.pessimistic, 1),
            },
            "expected": round(self.expected, 1),
            "standard_deviation": round(self.standard_deviation, 2),
            "variance": round(self.variance, 2),
            "confidence_intervals": {
                "68%": {"min": round(self.confidence_68[0], 1), "max": round(self.confidence_68[1], 1)},
                "95%": {"min": round(self.confidence_95[0], 1), "max": round(self.confidence_95[1], 1)},
                "99%": {"min": round(self.confidence_99[0], 1), "max": round(self.confidence_99[1], 1)},
            },
        }


@dataclass
class ROIResult:
    """ROI Analysis result."""
    total_investment: float
    annual_maintenance: float
    annual_benefits: float
    net_annual_benefits: float
    roi_percent_1yr: float
    roi_percent_3yr: float
    payback_months: float
    npv_3yr: float
    recommendation: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "investment": {
                "total": round(self.total_investment, 2),
                "annual_maintenance": round(self.annual_maintenance, 2),
            },
            "benefits": {
                "annual": round(self.annual_benefits, 2),
                "net_annual": round(self.net_annual_benefits, 2),
            },
            "metrics": {
                "roi_1yr_percent": round(self.roi_percent_1yr, 1),
                "roi_3yr_percent": round(self.roi_percent_3yr, 1),
                "payback_months": round(self.payback_months, 1),
                "npv_3yr": round(self.npv_3yr, 2),
            },
            "recommendation": self.recommendation,
        }


@dataclass
class AIEfficiencyResult:
    """Comparison of Human vs AI-Assisted vs Hybrid approaches."""
    pure_human: Dict[str, float]
    ai_assisted: Dict[str, float]
    hybrid: Dict[str, float]
    savings_ai_vs_human: float
    savings_hybrid_vs_human: float
    savings_percent_ai: float
    savings_percent_hybrid: float
    time_reduction_factor: float
    recommendation: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "approaches": {
                "pure_human": self.pure_human,
                "ai_assisted": self.ai_assisted,
                "hybrid": self.hybrid,
            },
            "savings": {
                "ai_vs_human_dollars": round(self.savings_ai_vs_human, 2),
                "hybrid_vs_human_dollars": round(self.savings_hybrid_vs_human, 2),
                "ai_vs_human_percent": round(self.savings_percent_ai, 1),
                "hybrid_vs_human_percent": round(self.savings_percent_hybrid, 1),
            },
            "efficiency": {
                "time_reduction_factor": round(self.time_reduction_factor, 2),
            },
            "recommendation": self.recommendation,
        }


@dataclass
class ComprehensiveEstimate:
    """Complete estimation with all methodologies."""
    # Input data
    loc: int
    words: int
    pages: int
    complexity: float
    hourly_rate: float

    # Results
    methodologies: List[MethodologyResult]
    pert: Optional[PERTResult]
    ai_efficiency: Optional[AIEfficiencyResult]

    # Aggregates
    average_hours: float
    average_cost: float
    min_cost: float
    max_cost: float
    confidence_overall: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "input": {
                "loc": self.loc,
                "words": self.words,
                "pages": self.pages,
                "complexity": round(self.complexity, 2),
                "hourly_rate": self.hourly_rate,
            },
            "methodologies": [m.to_dict() for m in self.methodologies],
            "pert": self.pert.to_dict() if self.pert else None,
            "ai_efficiency": self.ai_efficiency.to_dict() if self.ai_efficiency else None,
            "summary": {
                "average_hours": round(self.average_hours, 1),
                "average_cost": round(self.average_cost, 2),
                "cost_range": {
                    "min": round(self.min_cost, 2),
                    "max": round(self.max_cost, 2),
                },
                "confidence": self.confidence_overall,
                "methodologies_count": len(self.methodologies),
            },
        }


# =============================================================================
# ESTIMATION SUITE
# =============================================================================

class EstimationSuite:
    """
    Comprehensive estimation with multiple methodologies.

    Methodologies:
    - COCOMO II: Industry standard for software cost estimation
    - Gartner: Enterprise documentation standard (words/650)
    - IEEE 1063: Technical documentation (pages/1.5)
    - Microsoft: Tech industry standard (words/650)
    - Google: UX-driven (pages × 4 hours)
    - PMI: Project management (pages × 0.25)
    - SEI SLIM: Regulated industries (180 × 0.4)
    """

    # LOC to words/pages conversion
    WORDS_PER_LOC = 10  # Approximate: 10 words per line of code
    WORDS_PER_PAGE = 300  # Standard page

    # Productivity rates (hours per 1000 LOC)
    PRODUCTIVITY = {
        "pure_human": 25,      # Traditional: 25 hrs / 1000 LOC
        "ai_assisted": 8,      # With AI: 8 hrs / 1000 LOC (review, edit)
        "hybrid": 6.5,         # Optimized: 6.5 hrs / 1000 LOC
    }

    # AI cost models
    AI_COSTS = {
        "subscription_monthly": 20,  # ChatGPT Plus, Claude Pro
        "api_per_1k_tokens": 0.01,   # Average API cost
        "tokens_per_page": 1000,
    }

    def estimate_all(
        self,
        loc: int,
        complexity: float = 1.5,
        hourly_rate: float = 35,
        include_pert: bool = True,
        include_ai_efficiency: bool = True,
        enabled_methodologies: Optional[List[str]] = None,
    ) -> ComprehensiveEstimate:
        """
        Run all estimation methodologies.

        Args:
            loc: Lines of code
            complexity: Complexity factor (0.5 - 3.0)
            hourly_rate: Hourly rate in USD
            include_pert: Include PERT 3-point analysis
            include_ai_efficiency: Include AI efficiency comparison
            enabled_methodologies: List of methodology IDs to use (None = all)

        Returns:
            ComprehensiveEstimate with all results
        """
        # Convert LOC to words and pages
        words = loc * self.WORDS_PER_LOC
        pages = math.ceil(words / self.WORDS_PER_PAGE)

        # Calculate all methodologies
        all_methodologies = self._calculate_methodologies(
            loc, words, pages, complexity, hourly_rate
        )

        # Filter if specific methodologies requested
        if enabled_methodologies:
            methodologies = [m for m in all_methodologies if m.id in enabled_methodologies]
        else:
            methodologies = all_methodologies

        # Calculate PERT if requested
        pert = None
        if include_pert and len(methodologies) >= 3:
            hours_list = [m.hours for m in methodologies]
            pert = self._calculate_pert(
                optimistic=min(hours_list),
                most_likely=sum(hours_list) / len(hours_list),
                pessimistic=max(hours_list),
            )

        # Calculate AI efficiency if requested
        ai_efficiency = None
        if include_ai_efficiency:
            ai_efficiency = self._calculate_ai_efficiency(loc, hourly_rate, complexity)

        # Calculate aggregates
        costs = [m.cost for m in methodologies]
        hours = [m.hours for m in methodologies]

        avg_cost = sum(costs) / len(costs) if costs else 0
        avg_hours = sum(hours) / len(hours) if hours else 0

        # Determine overall confidence
        high_confidence_count = sum(1 for m in methodologies if m.confidence == "High")
        if high_confidence_count / len(methodologies) >= 0.6:
            confidence = "High"
        elif high_confidence_count / len(methodologies) >= 0.3:
            confidence = "Medium"
        else:
            confidence = "Low"

        return ComprehensiveEstimate(
            loc=loc,
            words=words,
            pages=pages,
            complexity=complexity,
            hourly_rate=hourly_rate,
            methodologies=methodologies,
            pert=pert,
            ai_efficiency=ai_efficiency,
            average_hours=avg_hours,
            average_cost=avg_cost,
            min_cost=min(costs) if costs else 0,
            max_cost=max(costs) if costs else 0,
            confidence_overall=confidence,
        )

    def _calculate_methodologies(
        self,
        loc: int,
        words: int,
        pages: int,
        complexity: float,
        hourly_rate: float,
    ) -> List[MethodologyResult]:
        """Calculate all methodology estimates."""
        results = []

        # 1. COCOMO II (Modern Calibration)
        kloc = loc / 1000
        cocomo_effort = 0.5 * (kloc ** 0.85) * complexity
        cocomo_hours = cocomo_effort * 160  # person-months to hours
        results.append(MethodologyResult(
            id="cocomo",
            name="COCOMO II",
            days=cocomo_hours / 8,
            hours=cocomo_hours,
            cost=cocomo_hours * hourly_rate,
            confidence="High",
            formula=f"0.5 × ({kloc:.1f})^0.85 × {complexity} = {cocomo_effort:.1f} PM",
            source="Boehm et al. (2000), Modern calibration",
            description="Industry-standard parametric model for software cost estimation",
        ))

        # 2. Gartner Standard
        gartner_days = (words / 650) * complexity
        gartner_hours = gartner_days * 8
        results.append(MethodologyResult(
            id="gartner",
            name="Gartner Standard",
            days=gartner_days,
            hours=gartner_hours,
            cost=gartner_hours * hourly_rate,
            confidence="High",
            formula=f"{words:,} words ÷ 650 × {complexity} = {gartner_days:.1f} days",
            source="Gartner Research 2023",
            description="Enterprise documentation standard (500-800 words/day)",
        ))

        # 3. IEEE 1063
        ieee_days = (pages / 1.5) * complexity
        ieee_hours = ieee_days * 8
        results.append(MethodologyResult(
            id="ieee",
            name="IEEE 1063",
            days=ieee_days,
            hours=ieee_hours,
            cost=ieee_hours * hourly_rate,
            confidence="High",
            formula=f"{pages} pages ÷ 1.5 × {complexity} = {ieee_days:.1f} days",
            source="IEEE Standard 1063",
            description="Technical documentation standard (1-2 pages/day)",
        ))

        # 4. Microsoft Docs
        ms_days = (words / 650) * complexity
        ms_hours = ms_days * 8
        results.append(MethodologyResult(
            id="microsoft",
            name="Microsoft Standard",
            days=ms_days,
            hours=ms_hours,
            cost=ms_hours * hourly_rate,
            confidence="Medium",
            formula=f"{words:,} words ÷ 650 × {complexity} = {ms_days:.1f} days",
            source="Microsoft Documentation Standards",
            description="Tech industry standard (650 words/day)",
        ))

        # 5. Google Guidelines
        google_hours = (pages * 4) * complexity
        google_days = google_hours / 8
        results.append(MethodologyResult(
            id="google",
            name="Google Guidelines",
            days=google_days,
            hours=google_hours,
            cost=google_hours * hourly_rate,
            confidence="Medium",
            formula=f"{pages} pages × 4 hours × {complexity} = {google_hours:.0f} hours",
            source="Google Technical Writing Guidelines",
            description="UX-driven approach (4 hours per page)",
        ))

        # 6. PMI Standard
        pmi_days = (pages * 0.25) * complexity
        pmi_hours = pmi_days * 8
        results.append(MethodologyResult(
            id="pmi",
            name="PMI Standard",
            days=pmi_days,
            hours=pmi_hours,
            cost=pmi_hours * hourly_rate,
            confidence="Medium",
            formula=f"{pages} pages × 0.25 × {complexity} = {pmi_days:.1f} days",
            source="PMI Project Management Standards",
            description="Project management approach (25% of project effort)",
        ))

        # 7. SEI SLIM (for larger projects)
        if loc >= 10000:
            sei_days = 180 * 0.4 * complexity
            sei_hours = sei_days * 8
            results.append(MethodologyResult(
                id="sei_slim",
                name="SEI SLIM",
                days=sei_days,
                hours=sei_hours,
                cost=sei_hours * hourly_rate,
                confidence="Medium",
                formula=f"180 × 0.4 × {complexity} = {sei_days:.1f} days",
                source="SEI SLIM Model",
                description="For regulated industries (0.30-0.50 factor)",
            ))

        # 8. Function Points approximation
        fp_estimate = loc / 50  # Rough: 50 LOC per function point
        fp_doc = fp_estimate * 0.25  # 25% for documentation
        fp_days = fp_doc * 0.5 * complexity
        fp_hours = fp_days * 8
        results.append(MethodologyResult(
            id="function_points",
            name="Function Points",
            days=fp_days,
            hours=fp_hours,
            cost=fp_hours * hourly_rate,
            confidence="Medium",
            formula=f"({loc} ÷ 50) × 0.25 × 0.5 × {complexity} = {fp_days:.1f} days",
            source="ISO/IEC 20926",
            description="Based on functional requirements estimation",
        ))

        return results

    def _calculate_pert(
        self,
        optimistic: float,
        most_likely: float,
        pessimistic: float,
    ) -> PERTResult:
        """
        Calculate PERT 3-point estimation.

        Formula: Expected = (O + 4×M + P) / 6
        Standard Deviation = (P - O) / 6
        """
        expected = (optimistic + 4 * most_likely + pessimistic) / 6
        std_dev = (pessimistic - optimistic) / 6
        variance = std_dev ** 2

        return PERTResult(
            optimistic=optimistic,
            most_likely=most_likely,
            pessimistic=pessimistic,
            expected=expected,
            standard_deviation=std_dev,
            variance=variance,
            confidence_68=(expected - std_dev, expected + std_dev),
            confidence_95=(expected - 2 * std_dev, expected + 2 * std_dev),
            confidence_99=(expected - 3 * std_dev, expected + 3 * std_dev),
        )

    def calculate_pert_custom(
        self,
        optimistic_days: float,
        most_likely_days: float,
        pessimistic_days: float,
        hourly_rate: float = 35,
    ) -> Dict[str, Any]:
        """
        Calculate PERT from custom inputs.

        Returns dict with hours and cost estimates.
        """
        pert = self._calculate_pert(
            optimistic_days * 8,
            most_likely_days * 8,
            pessimistic_days * 8,
        )

        result = pert.to_dict()

        # Add cost estimates
        result["cost"] = {
            "expected": round(pert.expected * hourly_rate, 2),
            "range_68": {
                "min": round(pert.confidence_68[0] * hourly_rate, 2),
                "max": round(pert.confidence_68[1] * hourly_rate, 2),
            },
            "range_95": {
                "min": round(pert.confidence_95[0] * hourly_rate, 2),
                "max": round(pert.confidence_95[1] * hourly_rate, 2),
            },
        }

        return result

    def _calculate_ai_efficiency(
        self,
        loc: int,
        hourly_rate: float,
        complexity: float,
    ) -> AIEfficiencyResult:
        """
        Calculate AI efficiency comparison.

        Compares:
        - Pure Human: Traditional development
        - AI-Assisted: AI generates, human reviews
        - Hybrid: Optimized AI+Human workflow
        """
        kloc = loc / 1000

        # Calculate hours for each approach
        pure_human_hours = kloc * self.PRODUCTIVITY["pure_human"] * complexity
        ai_assisted_hours = kloc * self.PRODUCTIVITY["ai_assisted"] * complexity
        hybrid_hours = kloc * self.PRODUCTIVITY["hybrid"] * complexity

        # AI costs (subscription model for simplicity)
        project_months = max(1, pure_human_hours / 160)  # Estimate project duration
        ai_subscription_cost = self.AI_COSTS["subscription_monthly"] * project_months * 0.3  # 30% usage

        # API cost alternative
        pages = (loc * self.WORDS_PER_LOC) / self.WORDS_PER_PAGE
        api_cost = (pages * self.AI_COSTS["tokens_per_page"] / 1000) * self.AI_COSTS["api_per_1k_tokens"]

        # Use higher of subscription or API cost
        ai_cost = max(ai_subscription_cost, api_cost)

        # Total costs
        pure_human_cost = pure_human_hours * hourly_rate
        ai_assisted_cost = (ai_assisted_hours * hourly_rate) + ai_cost
        hybrid_cost = (hybrid_hours * hourly_rate) + (ai_cost * 1.2)  # 20% more AI for hybrid

        # Savings
        savings_ai = pure_human_cost - ai_assisted_cost
        savings_hybrid = pure_human_cost - hybrid_cost
        savings_percent_ai = (savings_ai / pure_human_cost) * 100 if pure_human_cost > 0 else 0
        savings_percent_hybrid = (savings_hybrid / pure_human_cost) * 100 if pure_human_cost > 0 else 0

        # Time reduction
        time_reduction = pure_human_hours / ai_assisted_hours if ai_assisted_hours > 0 else 1

        # Recommendation
        if savings_percent_hybrid > 40:
            recommendation = "Highly recommend Hybrid approach - significant savings and quality balance"
        elif savings_percent_ai > 30:
            recommendation = "AI-Assisted approach recommended - good cost-benefit ratio"
        elif savings_percent_ai > 15:
            recommendation = "Consider AI-Assisted for time savings, evaluate quality needs"
        else:
            recommendation = "Marginal AI benefit - evaluate based on timeline requirements"

        return AIEfficiencyResult(
            pure_human={
                "hours": round(pure_human_hours, 1),
                "cost": round(pure_human_cost, 2),
                "ai_cost": 0,
                "total_cost": round(pure_human_cost, 2),
                "days": round(pure_human_hours / 8, 1),
            },
            ai_assisted={
                "hours": round(ai_assisted_hours, 1),
                "cost": round(ai_assisted_hours * hourly_rate, 2),
                "ai_cost": round(ai_cost, 2),
                "total_cost": round(ai_assisted_cost, 2),
                "days": round(ai_assisted_hours / 8, 1),
            },
            hybrid={
                "hours": round(hybrid_hours, 1),
                "cost": round(hybrid_hours * hourly_rate, 2),
                "ai_cost": round(ai_cost * 1.2, 2),
                "total_cost": round(hybrid_cost, 2),
                "days": round(hybrid_hours / 8, 1),
            },
            savings_ai_vs_human=savings_ai,
            savings_hybrid_vs_human=savings_hybrid,
            savings_percent_ai=savings_percent_ai,
            savings_percent_hybrid=savings_percent_hybrid,
            time_reduction_factor=time_reduction,
            recommendation=recommendation,
        )

    def calculate_roi(
        self,
        investment_cost: float,
        additional_costs: float = 0,
        maintenance_percent: float = 20,
        annual_support_savings: float = 0,
        annual_training_savings: float = 0,
        annual_efficiency_gain: float = 0,
        annual_risk_reduction: float = 0,
    ) -> ROIResult:
        """
        Calculate ROI for documentation/development investment.

        Args:
            investment_cost: Initial documentation/development cost
            additional_costs: Tools, training, infrastructure
            maintenance_percent: Annual maintenance as % of investment
            annual_support_savings: Reduced support costs
            annual_training_savings: Reduced training costs
            annual_efficiency_gain: Developer efficiency improvements
            annual_risk_reduction: Risk mitigation value

        Returns:
            ROIResult with payback period, NPV, ROI %
        """
        total_investment = investment_cost + additional_costs
        annual_maintenance = investment_cost * (maintenance_percent / 100)

        annual_benefits = (
            annual_support_savings +
            annual_training_savings +
            annual_efficiency_gain +
            annual_risk_reduction
        )

        net_annual_benefits = annual_benefits - annual_maintenance

        # ROI calculations
        roi_1yr = ((net_annual_benefits - total_investment) / total_investment) * 100 if total_investment > 0 else 0
        roi_3yr = ((net_annual_benefits * 3 - total_investment) / total_investment) * 100 if total_investment > 0 else 0

        # Payback period in months
        payback_months = (total_investment / (net_annual_benefits / 12)) if net_annual_benefits > 0 else float('inf')

        # NPV at 3 years (simple, no discount rate)
        npv_3yr = (net_annual_benefits * 3) - total_investment

        # Recommendation
        if roi_3yr > 100:
            recommendation = "Excellent investment - strong positive ROI expected"
        elif roi_3yr > 50:
            recommendation = "Good investment - solid returns within 3 years"
        elif roi_3yr > 0:
            recommendation = "Marginal investment - positive but consider alternatives"
        else:
            recommendation = "Review investment - benefits may not justify costs"

        return ROIResult(
            total_investment=total_investment,
            annual_maintenance=annual_maintenance,
            annual_benefits=annual_benefits,
            net_annual_benefits=net_annual_benefits,
            roi_percent_1yr=roi_1yr,
            roi_percent_3yr=roi_3yr,
            payback_months=payback_months,
            npv_3yr=npv_3yr,
            recommendation=recommendation,
        )


# Singleton instance
estimation_suite = EstimationSuite()
