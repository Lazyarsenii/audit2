"""
Contract Comparison Service.

Compares parsed contract data with repository analysis results:
- Work Plan vs. Actual Progress
- Budget vs. Cost Estimates
- Indicators vs. Metrics
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime

from app.services.contract_parser import ParsedContract, Activity, BudgetLine, Indicator


class ComparisonStatus(str, Enum):
    ON_TRACK = "on_track"
    AT_RISK = "at_risk"
    BEHIND = "behind"
    OVER_BUDGET = "over_budget"
    UNDER_BUDGET = "under_budget"
    NOT_APPLICABLE = "not_applicable"


@dataclass
class ActivityComparison:
    """Comparison of planned activity vs actual."""
    activity_id: str
    activity_name: str
    planned_status: str
    actual_status: str
    status: ComparisonStatus
    notes: str = ""
    completion_percent: float = 0.0


@dataclass
class BudgetComparison:
    """Comparison of budget line vs actual cost."""
    category: str
    planned_amount: float
    estimated_amount: float
    variance: float
    variance_percent: float
    status: ComparisonStatus
    notes: str = ""


@dataclass
class IndicatorComparison:
    """Comparison of KPI target vs actual."""
    indicator_id: str
    indicator_name: str
    target_value: Optional[float]
    actual_value: Optional[float]
    unit: str
    achievement_percent: Optional[float]
    status: ComparisonStatus
    notes: str = ""


@dataclass
class ComparisonReport:
    """Full comparison report."""
    contract_id: str
    analysis_id: Optional[str]
    compared_at: str

    # Summary
    overall_status: ComparisonStatus
    overall_score: float  # 0-100

    # Work plan comparison
    work_plan_status: ComparisonStatus
    activities_total: int
    activities_on_track: int
    activities_at_risk: int
    activities_behind: int

    # Budget comparison
    budget_status: ComparisonStatus
    total_planned_budget: float
    total_estimated_cost: float
    budget_variance: float
    budget_variance_percent: float

    # Indicators comparison
    indicators_status: ComparisonStatus
    indicators_total: int
    indicators_met: int
    indicators_at_risk: int
    indicators_not_met: int

    # Lists with defaults (must come after fields without defaults)
    activity_comparisons: List[ActivityComparison] = field(default_factory=list)
    budget_comparisons: List[BudgetComparison] = field(default_factory=list)
    indicator_comparisons: List[IndicatorComparison] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "contract_id": self.contract_id,
            "analysis_id": self.analysis_id,
            "compared_at": self.compared_at,
            "overall_status": self.overall_status.value,
            "overall_score": self.overall_score,
            "work_plan": {
                "status": self.work_plan_status.value,
                "total": self.activities_total,
                "on_track": self.activities_on_track,
                "at_risk": self.activities_at_risk,
                "behind": self.activities_behind,
                "details": [asdict(a) for a in self.activity_comparisons],
            },
            "budget": {
                "status": self.budget_status.value,
                "planned": self.total_planned_budget,
                "estimated": self.total_estimated_cost,
                "variance": self.budget_variance,
                "variance_percent": self.budget_variance_percent,
                "details": [asdict(b) for b in self.budget_comparisons],
            },
            "indicators": {
                "status": self.indicators_status.value,
                "total": self.indicators_total,
                "met": self.indicators_met,
                "at_risk": self.indicators_at_risk,
                "not_met": self.indicators_not_met,
                "details": [asdict(i) for i in self.indicator_comparisons],
            },
            "recommendations": self.recommendations,
            "risks": self.risks,
        }


class ContractComparisonService:
    """
    Compares contract requirements with analysis results.
    """

    # Mapping from analysis metrics to indicator types
    METRIC_MAPPING = {
        "documentation": ["documentation", "docs", "readme"],
        "code_quality": ["quality", "code", "maintainability"],
        "testing": ["test", "coverage", "testing"],
        "security": ["security", "vulnerability", "secure"],
        "architecture": ["architecture", "structure", "design"],
    }

    # Budget category mapping from analysis
    COST_CATEGORY_MAPPING = {
        "personnel": ["development", "coding", "implementation"],
        "consultants": ["review", "audit", "analysis"],
        "equipment": ["infrastructure", "deployment", "hosting"],
        "training": ["documentation", "onboarding"],
        "overhead": ["management", "coordination"],
    }

    def compare(
        self,
        contract: ParsedContract,
        analysis_data: Dict[str, Any],
        project_progress: Optional[Dict[str, Any]] = None,
    ) -> ComparisonReport:
        """
        Compare contract with analysis results.

        Args:
            contract: Parsed contract data
            analysis_data: Analysis results dictionary with keys like:
                - repo_health: {documentation, structure, runability, history, total}
                - tech_debt: {architecture, code_quality, testing, infrastructure, security, total}
                - cost: {hours_min, hours_typical, hours_max, cost_estimate}
                - Product Level info
            project_progress: Optional progress data for activities

        Returns:
            ComparisonReport with detailed comparisons
        """
        report = ComparisonReport(
            contract_id=contract.id,
            analysis_id=analysis_data.get("analysis_id"),
            compared_at=datetime.now().isoformat(),
            overall_status=ComparisonStatus.ON_TRACK,
            overall_score=0.0,
            work_plan_status=ComparisonStatus.NOT_APPLICABLE,
            activities_total=0,
            activities_on_track=0,
            activities_at_risk=0,
            activities_behind=0,
            budget_status=ComparisonStatus.NOT_APPLICABLE,
            total_planned_budget=0.0,
            total_estimated_cost=0.0,
            budget_variance=0.0,
            budget_variance_percent=0.0,
            indicators_status=ComparisonStatus.NOT_APPLICABLE,
            indicators_total=0,
            indicators_met=0,
            indicators_at_risk=0,
            indicators_not_met=0,
        )

        # Compare work plan
        self._compare_work_plan(report, contract, project_progress or {})

        # Compare budget
        self._compare_budget(report, contract, analysis_data)

        # Compare indicators
        self._compare_indicators(report, contract, analysis_data)

        # Calculate overall status and score
        self._calculate_overall(report)

        # Generate recommendations
        self._generate_recommendations(report, contract, analysis_data)

        return report

    def _compare_work_plan(
        self,
        report: ComparisonReport,
        contract: ParsedContract,
        progress: Dict[str, Any],
    ):
        """Compare work plan activities."""
        if not contract.work_plan:
            return

        report.activities_total = len(contract.work_plan)

        for activity in contract.work_plan:
            # Get actual status from progress data
            actual_status = progress.get(activity.id, {}).get("status", "planned")
            completion = progress.get(activity.id, {}).get("completion", 0)

            # Determine comparison status
            if actual_status == "completed" or completion >= 100:
                status = ComparisonStatus.ON_TRACK
                report.activities_on_track += 1
            elif actual_status == "in_progress" or 30 <= completion < 100:
                status = ComparisonStatus.ON_TRACK
                report.activities_on_track += 1
            elif actual_status == "delayed":
                status = ComparisonStatus.BEHIND
                report.activities_behind += 1
            elif completion < 30 and activity.status == "in_progress":
                status = ComparisonStatus.AT_RISK
                report.activities_at_risk += 1
            else:
                status = ComparisonStatus.ON_TRACK
                report.activities_on_track += 1

            report.activity_comparisons.append(ActivityComparison(
                activity_id=activity.id,
                activity_name=activity.name,
                planned_status=activity.status,
                actual_status=actual_status,
                status=status,
                completion_percent=completion,
            ))

        # Determine work plan status
        if report.activities_total > 0:
            on_track_ratio = report.activities_on_track / report.activities_total
            if on_track_ratio >= 0.8:
                report.work_plan_status = ComparisonStatus.ON_TRACK
            elif on_track_ratio >= 0.5:
                report.work_plan_status = ComparisonStatus.AT_RISK
            else:
                report.work_plan_status = ComparisonStatus.BEHIND

    def _compare_budget(
        self,
        report: ComparisonReport,
        contract: ParsedContract,
        analysis_data: Dict[str, Any],
    ):
        """Compare budget with cost estimates."""
        if not contract.budget:
            return

        # Get cost estimate from analysis
        cost_data = analysis_data.get("cost", {})
        estimated_hours = cost_data.get("hours_typical_total", cost_data.get("hours_typical", 0))
        hourly_rate = cost_data.get("hourly_rate", 50)  # Default rate
        estimated_total = cost_data.get("cost_estimate", estimated_hours * hourly_rate)

        # Sum planned budget
        planned_total = sum(line.total for line in contract.budget)
        report.total_planned_budget = planned_total
        report.total_estimated_cost = estimated_total

        if planned_total > 0:
            report.budget_variance = estimated_total - planned_total
            report.budget_variance_percent = (report.budget_variance / planned_total) * 100
        else:
            report.budget_variance = 0
            report.budget_variance_percent = 0

        # Group budget by category for comparison
        category_budgets: Dict[str, float] = {}
        for line in contract.budget:
            cat = line.category
            category_budgets[cat] = category_budgets.get(cat, 0) + line.total

        # Estimate costs by category from analysis breakdown
        activity_breakdown = analysis_data.get("activity_breakdown", {})

        for category, planned in category_budgets.items():
            # Try to find matching estimated costs
            estimated = 0
            for cost_cat, keywords in self.COST_CATEGORY_MAPPING.items():
                if category == cost_cat or any(kw in category.lower() for kw in keywords):
                    # Get from activity breakdown
                    for act_name, act_hours in activity_breakdown.items():
                        if any(kw in act_name.lower() for kw in keywords):
                            estimated += act_hours * hourly_rate

            # If no match, proportionally allocate
            if estimated == 0 and estimated_total > 0 and planned_total > 0:
                estimated = estimated_total * (planned / planned_total)

            variance = estimated - planned
            variance_pct = (variance / planned * 100) if planned > 0 else 0

            if variance_pct > 20:
                status = ComparisonStatus.OVER_BUDGET
            elif variance_pct < -20:
                status = ComparisonStatus.UNDER_BUDGET
            elif abs(variance_pct) <= 10:
                status = ComparisonStatus.ON_TRACK
            else:
                status = ComparisonStatus.AT_RISK

            report.budget_comparisons.append(BudgetComparison(
                category=category,
                planned_amount=planned,
                estimated_amount=estimated,
                variance=variance,
                variance_percent=variance_pct,
                status=status,
            ))

        # Determine overall budget status
        if report.budget_variance_percent > 15:
            report.budget_status = ComparisonStatus.OVER_BUDGET
        elif report.budget_variance_percent < -15:
            report.budget_status = ComparisonStatus.UNDER_BUDGET
        elif abs(report.budget_variance_percent) <= 10:
            report.budget_status = ComparisonStatus.ON_TRACK
        else:
            report.budget_status = ComparisonStatus.AT_RISK

    def _compare_indicators(
        self,
        report: ComparisonReport,
        contract: ParsedContract,
        analysis_data: Dict[str, Any],
    ):
        """Compare indicators with analysis metrics."""
        if not contract.indicators:
            return

        report.indicators_total = len(contract.indicators)

        # Get metrics from analysis
        repo_health = analysis_data.get("repo_health", {})
        tech_debt = analysis_data.get("tech_debt", {})

        for indicator in contract.indicators:
            # Try to match indicator to analysis metric
            actual_value = None
            for metric_name, keywords in self.METRIC_MAPPING.items():
                if any(kw in indicator.name.lower() for kw in keywords):
                    # Check repo_health first, then tech_debt
                    if metric_name in repo_health:
                        actual_value = repo_health[metric_name]
                    elif metric_name in tech_debt:
                        actual_value = tech_debt[metric_name]
                    break

            # Calculate achievement
            achievement = None
            if actual_value is not None and indicator.target:
                achievement = (actual_value / indicator.target) * 100

            # Determine status
            if achievement is not None:
                if achievement >= 90:
                    status = ComparisonStatus.ON_TRACK
                    report.indicators_met += 1
                elif achievement >= 60:
                    status = ComparisonStatus.AT_RISK
                    report.indicators_at_risk += 1
                else:
                    status = ComparisonStatus.BEHIND
                    report.indicators_not_met += 1
            else:
                status = ComparisonStatus.NOT_APPLICABLE

            report.indicator_comparisons.append(IndicatorComparison(
                indicator_id=indicator.id,
                indicator_name=indicator.name,
                target_value=indicator.target,
                actual_value=actual_value,
                unit=indicator.unit,
                achievement_percent=achievement,
                status=status,
            ))

        # Determine overall indicator status
        if report.indicators_total > 0:
            met_ratio = report.indicators_met / report.indicators_total
            if met_ratio >= 0.8:
                report.indicators_status = ComparisonStatus.ON_TRACK
            elif met_ratio >= 0.5:
                report.indicators_status = ComparisonStatus.AT_RISK
            else:
                report.indicators_status = ComparisonStatus.BEHIND

    def _calculate_overall(self, report: ComparisonReport):
        """Calculate overall status and score."""
        scores = []
        weights = []

        # Work plan score
        if report.activities_total > 0:
            wp_score = (report.activities_on_track / report.activities_total) * 100
            scores.append(wp_score)
            weights.append(0.35)

        # Budget score
        if report.total_planned_budget > 0:
            # Score based on variance (lower is better)
            budget_score = max(0, 100 - abs(report.budget_variance_percent))
            scores.append(budget_score)
            weights.append(0.40)

        # Indicator score
        if report.indicators_total > 0:
            ind_score = (report.indicators_met / report.indicators_total) * 100
            scores.append(ind_score)
            weights.append(0.25)

        # Calculate weighted average
        if scores and weights:
            total_weight = sum(weights)
            report.overall_score = sum(s * w for s, w in zip(scores, weights)) / total_weight
        else:
            report.overall_score = 50.0  # Default if no data

        # Determine overall status
        if report.overall_score >= 80:
            report.overall_status = ComparisonStatus.ON_TRACK
        elif report.overall_score >= 60:
            report.overall_status = ComparisonStatus.AT_RISK
        else:
            report.overall_status = ComparisonStatus.BEHIND

    def _generate_recommendations(
        self,
        report: ComparisonReport,
        contract: ParsedContract,
        analysis_data: Dict[str, Any],
    ):
        """Generate recommendations and identify risks."""

        # Budget recommendations
        if report.budget_status == ComparisonStatus.OVER_BUDGET:
            report.risks.append(
                f"Budget risk: Estimated cost exceeds plan by {report.budget_variance_percent:.1f}%"
            )
            report.recommendations.append(
                "Review scope and prioritize features to reduce estimated effort"
            )

            # Find over-budget categories
            for bc in report.budget_comparisons:
                if bc.status == ComparisonStatus.OVER_BUDGET:
                    report.recommendations.append(
                        f"Review '{bc.category}' costs - {bc.variance_percent:.1f}% over budget"
                    )

        # Work plan recommendations
        if report.work_plan_status == ComparisonStatus.BEHIND:
            report.risks.append(
                f"Schedule risk: {report.activities_behind} activities behind schedule"
            )
            report.recommendations.append(
                "Accelerate delayed activities or revise timeline"
            )

        if report.work_plan_status == ComparisonStatus.AT_RISK:
            report.recommendations.append(
                "Monitor at-risk activities closely and allocate additional resources if needed"
            )

        # Indicator recommendations
        if report.indicators_status == ComparisonStatus.BEHIND:
            report.risks.append(
                f"Performance risk: {report.indicators_not_met} indicators not meeting targets"
            )

            # Add specific indicator recommendations
            for ic in report.indicator_comparisons:
                if ic.status == ComparisonStatus.BEHIND:
                    report.recommendations.append(
                        f"Improve '{ic.indicator_name}' - currently at {ic.achievement_percent:.0f}% of target"
                    )

        # Technical quality recommendations based on analysis
        tech_debt = analysis_data.get("tech_debt", {})
        if tech_debt.get("testing", 0) < 2:
            report.recommendations.append(
                "Increase test coverage to meet quality requirements"
            )
        if tech_debt.get("security", 0) < 2:
            report.recommendations.append(
                "Address security vulnerabilities before delivery"
            )
        if tech_debt.get("documentation", 0) < 2:
            report.recommendations.append(
                "Improve documentation to meet contract requirements"
            )


# Singleton instance
comparison_service = ContractComparisonService()
