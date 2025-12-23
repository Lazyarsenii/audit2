"""
Tests for Document Matrix Service.

Tests cover:
- Document package selection by product level
- Template retrieval
- Matrix summary generation
- Document generation for all document types
"""
import pytest
from app.services.document_matrix import (
    DocumentMatrixService,
    DocumentType,
    DocumentCategory,
    DocumentTemplate,
    DocumentPackage,
    DOCUMENT_TEMPLATES,
    DOCUMENT_MATRIX,
    document_matrix_service,
)
from app.core.scoring.product_level import ProductLevel


class TestDocumentMatrixService:
    """Tests for DocumentMatrixService class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = DocumentMatrixService()

    # =========================================================================
    # get_document_package tests
    # =========================================================================

    def test_get_document_package_rnd_spike_base_only(self):
        """Test document package for RND_SPIKE without platform or donors."""
        package = self.service.get_document_package(
            product_level=ProductLevel.RND_SPIKE.value,  # "R&D Spike"
            is_platform_module=False,
            has_donors=False,
        )

        assert package.product_level == ProductLevel.RND_SPIKE.value
        assert package.is_platform_module is False
        assert package.has_donors is False
        assert len(package.base_documents) == 3  # RND_SUMMARY, TECH_NOTE, BACKLOG
        assert len(package.platform_documents) == 0
        assert len(package.donor_documents) == 0
        assert package.total_documents == 3

    def test_get_document_package_rnd_spike_with_donors(self):
        """Test document package for RND_SPIKE with donors."""
        package = self.service.get_document_package(
            product_level=ProductLevel.RND_SPIKE.value,
            is_platform_module=False,
            has_donors=True,
        )

        assert len(package.base_documents) == 3
        assert len(package.platform_documents) == 0
        assert len(package.donor_documents) == 1  # DONOR_ONE_PAGER
        assert package.total_documents == 4

    def test_get_document_package_prototype(self):
        """Test document package for PROTOTYPE level."""
        package = self.service.get_document_package(
            product_level=ProductLevel.PROTOTYPE.value,  # "Prototype"
            is_platform_module=False,
            has_donors=False,
        )

        assert package.product_level == ProductLevel.PROTOTYPE.value
        assert len(package.base_documents) == 4  # TECH_REPORT, COST_ESTIMATE, COST_EFFORT_SUMMARY, TASK_LIST
        assert package.total_documents == 4

    def test_get_document_package_prototype_with_donors(self):
        """Test document package for PROTOTYPE with donors."""
        package = self.service.get_document_package(
            product_level=ProductLevel.PROTOTYPE.value,
            is_platform_module=False,
            has_donors=True,
        )

        assert len(package.donor_documents) == 2  # DONOR_TECH_REPORT, WORKPLAN_ALIGNMENT
        assert package.total_documents == 6

    def test_get_document_package_internal_tool(self):
        """Test document package for INTERNAL_TOOL level."""
        package = self.service.get_document_package(
            product_level=ProductLevel.INTERNAL_TOOL.value,  # "Internal Tool"
            is_platform_module=False,
            has_donors=False,
        )

        assert package.product_level == ProductLevel.INTERNAL_TOOL.value
        assert len(package.base_documents) == 5
        assert len(package.platform_documents) == 0  # Not a platform module
        assert package.total_documents == 5

    def test_get_document_package_internal_tool_as_platform(self):
        """Test document package for INTERNAL_TOOL as platform module."""
        package = self.service.get_document_package(
            product_level=ProductLevel.INTERNAL_TOOL.value,
            is_platform_module=True,
            has_donors=False,
        )

        assert len(package.platform_documents) == 2  # INTEGRATION_MAP, ARCHITECTURE_DOC
        assert package.total_documents == 7

    def test_get_document_package_platform_module(self):
        """Test document package for PLATFORM_MODULE level."""
        package = self.service.get_document_package(
            product_level=ProductLevel.PLATFORM_MODULE.value,  # "Platform Module Candidate"
            is_platform_module=True,
            has_donors=True,
        )

        assert package.product_level == ProductLevel.PLATFORM_MODULE.value
        assert len(package.base_documents) == 4
        assert len(package.platform_documents) == 3  # PLATFORM_CHECKLIST, MIGRATION_PLAN, INTEGRATION_MAP
        assert len(package.donor_documents) == 4

    def test_get_document_package_near_product(self):
        """Test document package for NEAR_PRODUCT level."""
        package = self.service.get_document_package(
            product_level=ProductLevel.NEAR_PRODUCT.value,  # "Near-Product"
            is_platform_module=True,
            has_donors=True,
        )

        assert package.product_level == ProductLevel.NEAR_PRODUCT.value
        assert len(package.base_documents) == 4
        assert len(package.platform_documents) == 2  # SLO_SLA, PLATFORM_ACCEPTANCE
        assert len(package.donor_documents) == 3  # FULL_ACCEPTANCE_PACKAGE, MULTI_DONOR_SPLIT, INDICATORS_STATUS

    def test_get_document_package_unknown_level_defaults_to_prototype(self):
        """Test that unknown product level defaults to prototype."""
        package = self.service.get_document_package(
            product_level="unknown_level",
            is_platform_module=False,
            has_donors=False,
        )

        assert package.product_level == ProductLevel.PROTOTYPE.value
        assert len(package.base_documents) == 4

    def test_get_document_package_calculates_pages(self):
        """Test that total pages are calculated correctly."""
        package = self.service.get_document_package(
            product_level=ProductLevel.RND_SPIKE.value,
            is_platform_module=False,
            has_donors=False,
        )

        expected_pages = sum(d.estimated_pages for d in package.base_documents)
        assert package.total_pages == expected_pages
        assert package.total_pages > 0

    def test_get_document_package_to_dict(self):
        """Test DocumentPackage.to_dict() method."""
        package = self.service.get_document_package(
            product_level=ProductLevel.PROTOTYPE.value,
            is_platform_module=False,
            has_donors=False,
        )

        result = package.to_dict()

        assert "product_level" in result
        assert "base_documents" in result
        assert "platform_documents" in result
        assert "donor_documents" in result
        assert "total_documents" in result
        assert "total_pages" in result
        assert isinstance(result["base_documents"], list)
        assert all("type" in d and "name" in d for d in result["base_documents"])

    # =========================================================================
    # get_all_templates tests
    # =========================================================================

    def test_get_all_templates_returns_all(self):
        """Test that all templates are returned."""
        templates = self.service.get_all_templates()

        assert len(templates) == len(DOCUMENT_TEMPLATES)
        assert len(templates) >= 27  # We defined 27+ document types

    def test_get_all_templates_structure(self):
        """Test that templates have correct structure."""
        templates = self.service.get_all_templates()

        for template in templates:
            assert "type" in template
            assert "name" in template
            assert "description" in template
            assert "category" in template
            assert "estimated_pages" in template
            assert "sections" in template
            assert "is_required" in template
            assert "output_formats" in template

    # =========================================================================
    # get_template tests
    # =========================================================================

    def test_get_template_valid_type(self):
        """Test getting a valid template."""
        template = self.service.get_template("tech_report")

        assert template.doc_type == DocumentType.TECH_REPORT
        assert template.name == "Technical Report"
        assert template.is_required is True

    def test_get_template_invalid_type_raises(self):
        """Test that invalid template type raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            self.service.get_template("invalid_type")

        assert "Unknown document type" in str(exc_info.value)

    def test_get_template_all_types(self):
        """Test that all DocumentType enum values can be retrieved."""
        for doc_type in DocumentType:
            template = self.service.get_template(doc_type.value)
            assert template.doc_type == doc_type

    # =========================================================================
    # get_matrix_summary tests
    # =========================================================================

    def test_get_matrix_summary_structure(self):
        """Test matrix summary has correct structure."""
        summary = self.service.get_matrix_summary()

        # Use actual ProductLevel values
        assert ProductLevel.RND_SPIKE.value in summary
        assert ProductLevel.PROTOTYPE.value in summary
        assert ProductLevel.INTERNAL_TOOL.value in summary
        assert ProductLevel.PLATFORM_MODULE.value in summary
        assert ProductLevel.NEAR_PRODUCT.value in summary

    def test_get_matrix_summary_level_details(self):
        """Test each level in matrix summary has correct details."""
        summary = self.service.get_matrix_summary()

        for level, data in summary.items():
            assert "base" in data
            assert "platform" in data
            assert "donor" in data
            assert "total" in data

            assert "count" in data["base"]
            assert "pages" in data["base"]
            assert "count" in data["total"]
            assert "pages" in data["total"]

    def test_get_matrix_summary_totals_correct(self):
        """Test that totals in matrix summary are calculated correctly."""
        summary = self.service.get_matrix_summary()

        for level, data in summary.items():
            expected_count = data["base"]["count"] + data["platform"]["count"] + data["donor"]["count"]
            expected_pages = data["base"]["pages"] + data["platform"]["pages"] + data["donor"]["pages"]

            assert data["total"]["count"] == expected_count
            assert data["total"]["pages"] == expected_pages

    # =========================================================================
    # generate_document tests
    # =========================================================================

    def test_generate_document_rnd_summary(self):
        """Test generating R&D Summary document."""
        data = {
            "files_total": 100,
            "loc_total": 5000,
            "product_level": "R&D Spike",
            "score_repo_health_total": 6,
            "score_tech_debt_total": 8,
        }
        context = {
            "hypothesis": "Test hypothesis",
            "finding_1": "Finding 1",
        }

        content = self.service.generate_document(
            doc_type=DocumentType.RND_SUMMARY,
            data=data,
            context=context,
            language="uk",
        )

        assert "Резюме R&D" in content
        assert "Test hypothesis" in content
        assert "100" in content  # files_total
        assert "5000" in content  # loc_total
        assert "Finding 1" in content

    def test_generate_document_tech_report(self):
        """Test generating Technical Report document."""
        data = {
            "product_level": "Prototype",
            "score_repo_health_total": 8,
            "score_tech_debt_total": 10,
            "complexity": "M",
            "files_total": 50,
            "loc_total": 3000,
        }
        context = {"project_name": "Test Project"}

        content = self.service.generate_document(
            doc_type=DocumentType.TECH_REPORT,
            data=data,
            context=context,
            language="uk",
        )

        assert "Технічний звіт" in content
        assert "Test Project" in content
        assert "Prototype" in content
        assert "8/12" in content or "8" in content

    def test_generate_document_quality_report(self):
        """Test generating Quality Report document."""
        data = {
            "product_level": "Internal Tool",
            "score_repo_health_total": 9,
            "score_tech_debt_total": 11,
            "complexity": "L",
            "score_documentation": 2,
            "score_structure": 3,
            "score_runability": 2,
            "score_history": 2,
            "score_architecture": 3,
            "score_code_quality": 2,
            "score_testing": 2,
            "score_infrastructure": 2,
            "score_security": 2,
        }
        context = {}

        content = self.service.generate_document(
            doc_type=DocumentType.QUALITY_REPORT,
            data=data,
            context=context,
            language="uk",
        )

        assert "Звіт якості" in content
        assert "Internal Tool" in content

    def test_generate_document_cost_estimate(self):
        """Test generating Cost Estimate document."""
        data = {
            "loc_total": 10000,
            "files_total": 80,
            "complexity": "M",
        }
        context = {}

        content = self.service.generate_document(
            doc_type=DocumentType.COST_ESTIMATE,
            data=data,
            context=context,
            language="uk",
        )

        assert "Оцінка вартості" in content
        assert "COCOMO" in content

    def test_generate_document_task_list(self):
        """Test generating Task List document."""
        data = {}
        context = {
            "tasks": [
                {"title": "Task 1", "priority": "P1", "hours": 8, "description": "Description 1"},
                {"title": "Task 2", "priority": "P2", "hours": 4, "description": "Description 2"},
            ]
        }

        content = self.service.generate_document(
            doc_type=DocumentType.TASK_LIST,
            data=data,
            context=context,
            language="uk",
        )

        assert "Список задач" in content
        assert "Task 1" in content
        assert "Task 2" in content
        assert "P1 Tasks" in content
        assert "P2 Tasks" in content

    def test_generate_document_donor_one_pager(self):
        """Test generating Donor One-Pager document."""
        data = {
            "product_level": "R&D Spike",
            "score_repo_health_total": 5,
            "loc_total": 2000,
        }
        context = {
            "objective": "Research new technology",
            "work_1": "Completed task 1",
        }

        content = self.service.generate_document(
            doc_type=DocumentType.DONOR_ONE_PAGER,
            data=data,
            context=context,
            language="uk",
        )

        assert "One-Pager для донора" in content
        assert "Research new technology" in content
        assert "Completed task 1" in content

    def test_generate_document_workplan_alignment(self):
        """Test generating Workplan Alignment Report document."""
        data = {}
        context = {
            "period": "Q4 2024",
            "total_activities": 5,
            "linked_repos": 3,
            "coverage": 80,
        }

        content = self.service.generate_document(
            doc_type=DocumentType.WORKPLAN_ALIGNMENT,
            data=data,
            context=context,
            language="uk",
        )

        assert "відповідності робочому плану" in content
        assert "Q4 2024" in content
        assert "80" in content

    def test_generate_document_budget_status(self):
        """Test generating Budget Status Report document."""
        data = {}
        context = {
            "total_budget": "50000",
            "spent": "25000",
            "remaining": "25000",
            "burn_rate": "50",
        }

        content = self.service.generate_document(
            doc_type=DocumentType.BUDGET_STATUS,
            data=data,
            context=context,
            language="uk",
        )

        assert "Статус бюджету" in content
        assert "$50000" in content
        assert "50%" in content

    def test_generate_document_indicators_status(self):
        """Test generating Indicators Status Report document."""
        data = {}
        context = {
            "indicator_1_name": "Repos Analyzed",
            "indicator_1_target": "10",
            "indicator_1_actual": "7",
        }

        content = self.service.generate_document(
            doc_type=DocumentType.INDICATORS_STATUS,
            data=data,
            context=context,
            language="uk",
        )

        assert "Статус індикаторів" in content
        assert "Repos Analyzed" in content

    def test_generate_document_default_for_unknown_generator(self):
        """Test that documents without specific generator use default."""
        data = {}
        context = {}

        # ARCHITECTURE_DOC doesn't have a specific generator
        content = self.service.generate_document(
            doc_type=DocumentType.ARCHITECTURE_DOC,
            data=data,
            context=context,
            language="uk",
        )

        assert "Architecture Document" in content
        # Should contain sections from template
        assert "System Overview" in content or "Components" in content

    def test_generate_document_english_language(self):
        """Test generating document in English."""
        data = {"files_total": 50, "loc_total": 2000}
        context = {}

        content = self.service.generate_document(
            doc_type=DocumentType.RND_SUMMARY,
            data=data,
            context=context,
            language="en",
        )

        assert "R&D Summary" in content

    # =========================================================================
    # Edge cases and integration tests
    # =========================================================================

    def test_all_product_levels_have_valid_documents(self):
        """Test that all product levels in matrix have valid document types."""
        for level, categories in DOCUMENT_MATRIX.items():
            for category, doc_types in categories.items():
                for doc_type in doc_types:
                    assert doc_type in DOCUMENT_TEMPLATES, f"Document type {doc_type} not in templates"

    def test_all_document_types_have_templates(self):
        """Test that all DocumentType enum values have templates."""
        for doc_type in DocumentType:
            assert doc_type in DOCUMENT_TEMPLATES, f"No template for {doc_type}"

    def test_singleton_instance_exists(self):
        """Test that singleton instance is available."""
        assert document_matrix_service is not None
        assert isinstance(document_matrix_service, DocumentMatrixService)

    def test_document_template_defaults(self):
        """Test DocumentTemplate has correct defaults."""
        template = DocumentTemplate(
            doc_type=DocumentType.TECH_REPORT,
            name="Test",
            description="Test description",
            category=DocumentCategory.BASE,
        )

        assert template.output_formats == ["md", "pdf"]
        assert template.is_required is False
        assert template.is_auto_generated is True
        assert template.estimated_pages == 1
        assert template.sections == []

    def test_product_level_enum_values_match_matrix(self):
        """Test that ProductLevel enum values match DOCUMENT_MATRIX keys."""
        for level in ProductLevel:
            assert level.value in DOCUMENT_MATRIX, f"ProductLevel {level.value} not in DOCUMENT_MATRIX"
