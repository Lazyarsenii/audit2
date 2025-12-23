"""
Unit tests for Contract Comparison Service.
"""

import pytest
from datetime import datetime

from app.services.contract_comparison import (
    comparison_service,
    ContractComparisonService,
    ComparisonReport,
    ComparisonStatus,
    ActivityComparison,
    BudgetComparison,
    IndicatorComparison,
)
from app.services.contract_parser import (
    ParsedContract,
    Activity,
    BudgetLine,
    Indicator,
)


class TestComparisonStatus:
    """Tests for ComparisonStatus enum."""

    def test_status_values(self):
        """Test all status values exist."""
        assert ComparisonStatus.ON_TRACK.value == "on_track"
        assert ComparisonStatus.AT_RISK.value == "at_risk"
        assert ComparisonStatus.BEHIND.value == "behind"
        assert ComparisonStatus.OVER_BUDGET.value == "over_budget"
        assert ComparisonStatus.UNDER_BUDGET.value == "under_budget"
        assert ComparisonStatus.NOT_APPLICABLE.value == "not_applicable"


class TestActivityComparison:
    """Tests for ActivityComparison dataclass."""

    def test_activity_comparison_creation(self):
        """Test creating ActivityComparison instance."""
        comparison = ActivityComparison(
            activity_id="ACT_1",
            activity_name="Development",
            planned_status="in_progress",
            actual_status="completed",
            status=ComparisonStatus.ON_TRACK,
            notes="Completed ahead of schedule",
            completion_percent=100.0,
        )

        assert comparison.activity_id == "ACT_1"
        assert comparison.completion_percent == 100.0
        assert comparison.status == ComparisonStatus.ON_TRACK


class TestBudgetComparison:
    """Tests for BudgetComparison dataclass."""

    def test_budget_comparison_creation(self):
        """Test creating BudgetComparison instance."""
        comparison = BudgetComparison(
            category="personnel",
            planned_amount=100000.0,
            estimated_amount=95000.0,
            variance=-5000.0,
            variance_percent=-5.0,
            status=ComparisonStatus.ON_TRACK,
        )

        assert comparison.category == "personnel"
        assert comparison.variance == -5000.0
        assert comparison.status == ComparisonStatus.ON_TRACK


class TestIndicatorComparison:
    """Tests for IndicatorComparison dataclass."""

    def test_indicator_comparison_creation(self):
        """Test creating IndicatorComparison instance."""
        comparison = IndicatorComparison(
            indicator_id="IND_1",
            indicator_name="Test Coverage",
            target_value=80.0,
            actual_value=75.0,
            unit="percent",
            achievement_percent=93.75,
            status=ComparisonStatus.ON_TRACK,
        )

        assert comparison.indicator_name == "Test Coverage"
        assert comparison.achievement_percent == 93.75


class TestComparisonReport:
    """Tests for ComparisonReport dataclass."""

    def test_comparison_report_creation(self):
        """Test creating ComparisonReport instance."""
        report = ComparisonReport(
            contract_id="test_001",
            analysis_id="analysis_001",
            compared_at="2024-01-01T00:00:00",
            overall_status=ComparisonStatus.ON_TRACK,
            overall_score=85.0,
            work_plan_status=ComparisonStatus.ON_TRACK,
            activities_total=5,
            activities_on_track=4,
            activities_at_risk=1,
            activities_behind=0,
            budget_status=ComparisonStatus.ON_TRACK,
            total_planned_budget=150000.0,
            total_estimated_cost=145000.0,
            budget_variance=-5000.0,
            budget_variance_percent=-3.33,
            indicators_status=ComparisonStatus.ON_TRACK,
            indicators_total=4,
            indicators_met=3,
            indicators_at_risk=1,
            indicators_not_met=0,
        )

        assert report.contract_id == "test_001"
        assert report.overall_score == 85.0
        assert report.activities_total == 5

    def test_comparison_report_to_dict(self):
        """Test converting ComparisonReport to dictionary."""
        report = ComparisonReport(
            contract_id="test_001",
            analysis_id="analysis_001",
            compared_at="2024-01-01T00:00:00",
            overall_status=ComparisonStatus.ON_TRACK,
            overall_score=85.0,
            work_plan_status=ComparisonStatus.ON_TRACK,
            activities_total=5,
            activities_on_track=4,
            activities_at_risk=1,
            activities_behind=0,
            budget_status=ComparisonStatus.ON_TRACK,
            total_planned_budget=150000.0,
            total_estimated_cost=145000.0,
            budget_variance=-5000.0,
            budget_variance_percent=-3.33,
            indicators_status=ComparisonStatus.ON_TRACK,
            indicators_total=4,
            indicators_met=3,
            indicators_at_risk=1,
            indicators_not_met=0,
        )

        result = report.to_dict()

        assert isinstance(result, dict)
        assert result["contract_id"] == "test_001"
        assert result["overall_status"] == "on_track"
        assert "work_plan" in result
        assert "budget" in result
        assert "indicators" in result


class TestContractComparisonService:
    """Tests for ContractComparisonService class."""

    @pytest.fixture
    def service(self):
        """Create comparison service instance."""
        return ContractComparisonService()

    @pytest.fixture
    def sample_contract(self):
        """Create sample parsed contract."""
        return ParsedContract(
            id="test_contract_001",
            filename="test.pdf",
            parsed_at=datetime.now().isoformat(),
            contract_number="GF-2024-001",
            contract_title="Test Contract",
            total_budget=150000.0,
            currency="USD",
            work_plan=[
                Activity(
                    id="ACT_1",
                    name="Requirements",
                    description="Gather requirements",
                    start_date="2024-01-01",
                    end_date="2024-02-28",
                    status="completed",
                ),
                Activity(
                    id="ACT_2",
                    name="Development",
                    description="Build the system",
                    start_date="2024-03-01",
                    end_date="2024-09-30",
                    status="in_progress",
                ),
            ],
            budget=[
                BudgetLine(
                    id="BL_1",
                    category="personnel",
                    description="Staff salaries",
                    unit="month",
                    quantity=12,
                    unit_cost=6000,
                    total=72000,
                    currency="USD",
                ),
                BudgetLine(
                    id="BL_2",
                    category="equipment",
                    description="Infrastructure",
                    unit="unit",
                    quantity=1,
                    unit_cost=30000,
                    total=30000,
                    currency="USD",
                ),
            ],
            indicators=[
                Indicator(
                    id="IND_1",
                    name="Documentation Score",
                    description="Code documentation quality",
                    baseline=1,
                    target=3,
                    unit="level",
                    frequency="quarterly",
                ),
                Indicator(
                    id="IND_2",
                    name="Test Coverage",
                    description="Test coverage",
                    baseline=0,
                    target=2,
                    unit="level",
                    frequency="quarterly",
                ),
            ],
        )

    @pytest.fixture
    def sample_analysis(self):
        """Create sample analysis data."""
        return {
            "analysis_id": "analysis_001",
            "repo_health": {
                "documentation": 2,
                "structure": 2,
                "runability": 1,
                "history": 2,
                "total": 7,
            },
            "tech_debt": {
                "architecture": 2,
                "code_quality": 2,
                "testing": 1,
                "infrastructure": 1,
                "security": 2,
                "total": 8,
            },
            "cost": {
                "hours_typical_total": 2400,
                "hourly_rate": 50,
                "cost_estimate": 120000,
            },
        }

    def test_service_initialization(self, service):
        """Test service initializes correctly."""
        assert service is not None
        assert hasattr(service, 'METRIC_MAPPING')
        assert hasattr(service, 'COST_CATEGORY_MAPPING')

    def test_compare_basic(self, service, sample_contract, sample_analysis):
        """Test basic comparison."""
        report = service.compare(
            contract=sample_contract,
            analysis_data=sample_analysis,
        )

        assert report is not None
        assert isinstance(report, ComparisonReport)
        assert report.contract_id == sample_contract.id

    def test_compare_with_progress(self, service, sample_contract, sample_analysis):
        """Test comparison with project progress data."""
        progress = {
            "ACT_1": {"status": "completed", "completion": 100},
            "ACT_2": {"status": "in_progress", "completion": 60},
        }

        report = service.compare(
            contract=sample_contract,
            analysis_data=sample_analysis,
            project_progress=progress,
        )

        assert report is not None
        assert report.activities_total == 2

    def test_compare_work_plan(self, service, sample_contract, sample_analysis):
        """Test work plan comparison."""
        report = service.compare(
            contract=sample_contract,
            analysis_data=sample_analysis,
        )

        assert report.activities_total == 2
        assert len(report.activity_comparisons) == 2

    def test_compare_budget(self, service, sample_contract, sample_analysis):
        """Test budget comparison."""
        report = service.compare(
            contract=sample_contract,
            analysis_data=sample_analysis,
        )

        assert report.total_planned_budget == 102000.0  # 72000 + 30000
        assert report.total_estimated_cost == sample_analysis["cost"]["cost_estimate"]
        assert len(report.budget_comparisons) > 0

    def test_compare_indicators(self, service, sample_contract, sample_analysis):
        """Test indicator comparison."""
        report = service.compare(
            contract=sample_contract,
            analysis_data=sample_analysis,
        )

        assert report.indicators_total == 2
        assert len(report.indicator_comparisons) == 2

    def test_overall_score_calculation(self, service, sample_contract, sample_analysis):
        """Test overall score is calculated."""
        report = service.compare(
            contract=sample_contract,
            analysis_data=sample_analysis,
        )

        assert report.overall_score >= 0
        assert report.overall_score <= 100

    def test_recommendations_generated(self, service, sample_contract, sample_analysis):
        """Test recommendations are generated."""
        report = service.compare(
            contract=sample_contract,
            analysis_data=sample_analysis,
        )

        # Recommendations should be generated based on comparison
        assert isinstance(report.recommendations, list)
        assert isinstance(report.risks, list)

    def test_compare_empty_contract(self, service, sample_analysis):
        """Test comparison with empty contract."""
        empty_contract = ParsedContract(
            id="empty_001",
            filename="empty.pdf",
            parsed_at=datetime.now().isoformat(),
        )

        report = service.compare(
            contract=empty_contract,
            analysis_data=sample_analysis,
        )

        assert report is not None
        assert report.activities_total == 0
        assert report.indicators_total == 0

    def test_compare_empty_analysis(self, service, sample_contract):
        """Test comparison with empty analysis data."""
        report = service.compare(
            contract=sample_contract,
            analysis_data={},
        )

        assert report is not None

    def test_budget_status_over_budget(self, service):
        """Test budget status when over budget."""
        contract = ParsedContract(
            id="test_001",
            filename="test.pdf",
            parsed_at=datetime.now().isoformat(),
            budget=[
                BudgetLine(
                    id="BL_1",
                    category="personnel",
                    description="Staff",
                    unit="month",
                    quantity=1,
                    unit_cost=50000,
                    total=50000,
                    currency="USD",
                ),
            ],
        )

        analysis = {
            "cost": {
                "cost_estimate": 100000,  # 100% over budget
            }
        }

        report = service.compare(contract=contract, analysis_data=analysis)
        assert report.budget_status == ComparisonStatus.OVER_BUDGET

    def test_budget_status_under_budget(self, service):
        """Test budget status when under budget."""
        contract = ParsedContract(
            id="test_001",
            filename="test.pdf",
            parsed_at=datetime.now().isoformat(),
            budget=[
                BudgetLine(
                    id="BL_1",
                    category="personnel",
                    description="Staff",
                    unit="month",
                    quantity=1,
                    unit_cost=100000,
                    total=100000,
                    currency="USD",
                ),
            ],
        )

        analysis = {
            "cost": {
                "cost_estimate": 50000,  # 50% under budget
            }
        }

        report = service.compare(contract=contract, analysis_data=analysis)
        assert report.budget_status == ComparisonStatus.UNDER_BUDGET


class TestComparisonServiceSingleton:
    """Tests for comparison_service singleton."""

    def test_singleton_exists(self):
        """Test singleton instance exists."""
        assert comparison_service is not None
        assert isinstance(comparison_service, ContractComparisonService)

    def test_singleton_has_mappings(self):
        """Test singleton has metric mappings."""
        assert hasattr(comparison_service, 'METRIC_MAPPING')
        assert hasattr(comparison_service, 'COST_CATEGORY_MAPPING')
        assert len(comparison_service.METRIC_MAPPING) > 0
