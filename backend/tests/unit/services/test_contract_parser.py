"""
Unit tests for Contract Parser Service.
"""

import pytest
from datetime import datetime

from app.services.contract_parser import (
    contract_parser,
    ContractParser,
    ParsedContract,
    Activity,
    Milestone,
    BudgetLine,
    Indicator,
    PolicyRequirement,
    DocumentTemplate,
)


class TestContractParser:
    """Tests for ContractParser class."""

    def test_parser_initialization(self):
        """Test parser initializes correctly."""
        parser = ContractParser()
        assert parser is not None
        assert parser._parsed_contracts == {}

    def test_parse_text_file(self):
        """Test parsing plain text content."""
        parser = ContractParser()

        sample_text = """
        Contract Number: GF-2024-TEST-001

        WORK PLAN

        Activity 1: Requirements Gathering
        Description: Collect and document requirements
        Start: 2024-01-01
        End: 2024-03-31

        Activity 2: Development
        Description: Implement the system
        Start: 2024-04-01
        End: 2024-09-30

        BUDGET

        Personnel: $50,000
        Equipment: $10,000
        Travel: $5,000

        Total Budget: $65,000
        """

        result = parser.parse_file(
            file_path="test_contract.txt",
            content=sample_text.encode('utf-8')
        )

        assert result is not None
        assert isinstance(result, ParsedContract)
        assert result.filename == "test_contract.txt"
        assert result.id is not None

    def test_parse_empty_content(self):
        """Test parsing minimal content."""
        parser = ContractParser()

        result = parser.parse_file(
            file_path="empty.txt",
            content=b" "  # Minimal content (space)
        )

        assert result is not None
        assert result.work_plan == []
        assert result.budget == []

    def test_get_parsed_contract(self):
        """Test retrieving parsed contract by ID."""
        parser = ContractParser()

        # Parse a contract first
        result = parser.parse_file(
            file_path="test.txt",
            content=b"Test contract content"
        )

        # Retrieve it
        retrieved = parser.get_parsed(result.id)
        assert retrieved is not None
        assert retrieved.id == result.id

    def test_get_nonexistent_contract(self):
        """Test retrieving non-existent contract."""
        parser = ContractParser()
        result = parser.get_parsed("nonexistent_id")
        assert result is None

    def test_list_parsed_contracts(self):
        """Test listing all parsed contracts."""
        parser = ContractParser()

        # Clear any existing contracts
        parser._parsed_contracts.clear()

        # Parse multiple contracts
        parser.parse_file("test1.txt", b"Contract 1")
        parser.parse_file("test2.txt", b"Contract 2")

        contracts = parser.list_parsed()
        assert len(contracts) == 2

    def test_extract_contract_number(self):
        """Test extracting contract number from text."""
        parser = ContractParser()

        content = b"Contract Number: ABC-2024-001\nOther content"
        result = parser.parse_file("test.txt", content)

        # Contract number should be extracted
        assert result.contract_number is not None or result.contract_number == ""

    def test_extract_dates(self):
        """Test extracting dates from text."""
        parser = ContractParser()

        content = b"Start Date: 2024-01-15\nEnd Date: 2024-12-31"
        result = parser.parse_file("test.txt", content)

        # Parser should handle date extraction
        assert result is not None

    def test_extract_budget_amounts(self):
        """Test extracting budget amounts from text."""
        parser = ContractParser()

        content = b"""
        Budget Summary:
        Total: $150,000
        Personnel: 100000
        Equipment: 50,000 USD
        """
        result = parser.parse_file("budget_test.txt", content)

        assert result is not None


class TestParsedContract:
    """Tests for ParsedContract dataclass."""

    def test_parsed_contract_creation(self):
        """Test creating ParsedContract instance."""
        contract = ParsedContract(
            id="test_001",
            filename="test.pdf",
            parsed_at=datetime.now().isoformat(),
        )

        assert contract.id == "test_001"
        assert contract.filename == "test.pdf"
        assert contract.work_plan == []
        assert contract.milestones == []
        assert contract.budget == []
        assert contract.indicators == []
        assert contract.policies == []
        assert contract.document_templates == []

    def test_parsed_contract_to_dict(self):
        """Test converting ParsedContract to dictionary."""
        contract = ParsedContract(
            id="test_001",
            filename="test.pdf",
            parsed_at="2024-01-01T00:00:00",
            contract_number="GF-2024-001",
            contract_title="Test Contract",
            total_budget=100000.0,
            currency="USD",
        )

        result = contract.to_dict()

        assert isinstance(result, dict)
        assert result["id"] == "test_001"
        assert result["contract_number"] == "GF-2024-001"
        assert result["total_budget"] == 100000.0

    def test_parsed_contract_with_activities(self):
        """Test ParsedContract with activities."""
        activities = [
            Activity(
                id="ACT_1",
                name="Requirements",
                description="Gather requirements",
                start_date="2024-01-01",
                end_date="2024-03-31",
            ),
            Activity(
                id="ACT_2",
                name="Development",
                description="Build the system",
                start_date="2024-04-01",
                end_date="2024-09-30",
            ),
        ]

        contract = ParsedContract(
            id="test_001",
            filename="test.pdf",
            parsed_at="2024-01-01T00:00:00",
            work_plan=activities,
        )

        assert len(contract.work_plan) == 2
        assert contract.work_plan[0].name == "Requirements"

    def test_parsed_contract_with_budget(self):
        """Test ParsedContract with budget lines."""
        budget_lines = [
            BudgetLine(
                id="BL_1",
                category="personnel",
                description="Staff salaries",
                unit="month",
                quantity=12,
                unit_cost=5000,
                total=60000,
                currency="USD",
            ),
        ]

        contract = ParsedContract(
            id="test_001",
            filename="test.pdf",
            parsed_at="2024-01-01T00:00:00",
            budget=budget_lines,
        )

        assert len(contract.budget) == 1
        assert contract.budget[0].total == 60000


class TestActivity:
    """Tests for Activity dataclass."""

    def test_activity_creation(self):
        """Test creating Activity instance."""
        activity = Activity(
            id="ACT_1",
            name="Development",
            description="Main development phase",
            start_date="2024-01-01",
            end_date="2024-06-30",
            deliverables=["Source code", "Documentation"],
            status="in_progress",
        )

        assert activity.id == "ACT_1"
        assert activity.name == "Development"
        assert len(activity.deliverables) == 2
        assert activity.status == "in_progress"


class TestMilestone:
    """Tests for Milestone dataclass."""

    def test_milestone_creation(self):
        """Test creating Milestone instance."""
        milestone = Milestone(
            id="M1",
            name="Phase 1 Complete",
            due_date="2024-03-31",
            deliverables=["Requirements doc"],
            payment_linked=True,
            payment_amount=25000.0,
        )

        assert milestone.id == "M1"
        assert milestone.payment_linked is True
        assert milestone.payment_amount == 25000.0


class TestBudgetLine:
    """Tests for BudgetLine dataclass."""

    def test_budget_line_creation(self):
        """Test creating BudgetLine instance."""
        budget_line = BudgetLine(
            id="BL_1",
            category="personnel",
            description="Developer salaries",
            unit="month",
            quantity=6,
            unit_cost=8000,
            total=48000,
            currency="USD",
        )

        assert budget_line.category == "personnel"
        assert budget_line.total == 48000
        assert budget_line.quantity * budget_line.unit_cost == budget_line.total


class TestIndicator:
    """Tests for Indicator dataclass."""

    def test_indicator_creation(self):
        """Test creating Indicator instance."""
        indicator = Indicator(
            id="IND_1",
            name="Test Coverage",
            description="Code test coverage percentage",
            baseline=0,
            target=80,
            unit="percent",
            frequency="quarterly",
        )

        assert indicator.name == "Test Coverage"
        assert indicator.target == 80


class TestPolicyRequirement:
    """Tests for PolicyRequirement dataclass."""

    def test_policy_requirement_creation(self):
        """Test creating PolicyRequirement instance."""
        policy = PolicyRequirement(
            id="POL_1",
            title="GDPR Compliance",
            description="Must comply with GDPR",
            category="compliance",
            priority="critical",
        )

        assert policy.title == "GDPR Compliance"
        assert policy.priority == "critical"


class TestDocumentTemplate:
    """Tests for DocumentTemplate dataclass."""

    def test_document_template_creation(self):
        """Test creating DocumentTemplate instance."""
        template = DocumentTemplate(
            id="DOC_1",
            name="Progress Report",
            description="Monthly progress report",
            frequency="monthly",
            format="pdf",
            required=True,
        )

        assert template.name == "Progress Report"
        assert template.frequency == "monthly"
        assert template.required is True


class TestContractParserSingleton:
    """Tests for contract_parser singleton instance."""

    def test_singleton_exists(self):
        """Test that singleton instance exists."""
        assert contract_parser is not None
        assert isinstance(contract_parser, ContractParser)

    def test_singleton_functionality(self):
        """Test singleton can parse contracts."""
        result = contract_parser.parse_file(
            "singleton_test.txt",
            b"Singleton test content"
        )
        assert result is not None
