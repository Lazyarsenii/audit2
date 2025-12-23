"""
Tests for Document Matrix API endpoints.

Tests cover:
- GET /api/documents/matrix/summary
- GET /api/documents/matrix/{product_level}
- GET /api/documents/templates
- GET /api/documents/template/{doc_type}
- POST /api/documents/package
- GET /api/documents/types
"""
import pytest

from app.core.scoring.product_level import ProductLevel


# Product level values for testing
RND_SPIKE = ProductLevel.RND_SPIKE.value  # "R&D Spike"
PROTOTYPE = ProductLevel.PROTOTYPE.value  # "Prototype"
INTERNAL_TOOL = ProductLevel.INTERNAL_TOOL.value  # "Internal Tool"
PLATFORM_MODULE = ProductLevel.PLATFORM_MODULE.value  # "Platform Module Candidate"
NEAR_PRODUCT = ProductLevel.NEAR_PRODUCT.value  # "Near-Product"


class TestDocumentMatrixAPI:
    """Tests for Document Matrix API endpoints."""

    # =========================================================================
    # GET /api/documents/matrix/summary tests
    # =========================================================================

    def test_get_matrix_summary(self, client):
        """Test getting document matrix summary."""
        response = client.get("/api/documents/matrix/summary")

        assert response.status_code == 200
        data = response.json()

        # Check all product levels are present (using display names)
        assert RND_SPIKE in data
        assert PROTOTYPE in data
        assert INTERNAL_TOOL in data
        assert PLATFORM_MODULE in data
        assert NEAR_PRODUCT in data

    def test_get_matrix_summary_structure(self, client):
        """Test matrix summary has correct structure."""
        response = client.get("/api/documents/matrix/summary")
        data = response.json()

        for level, details in data.items():
            assert "base" in details
            assert "platform" in details
            assert "donor" in details
            assert "total" in details

            assert "count" in details["base"]
            assert "pages" in details["base"]
            assert "count" in details["total"]
            assert "pages" in details["total"]

    # =========================================================================
    # GET /api/documents/matrix/{product_level} tests
    # =========================================================================

    def test_get_matrix_for_level_rnd_spike(self, client):
        """Test getting matrix for RND_SPIKE level."""
        response = client.get(f"/api/documents/matrix/{RND_SPIKE}")

        assert response.status_code == 200
        data = response.json()

        assert data["product_level"] == RND_SPIKE
        assert "documents" in data
        assert "counts" in data
        assert "base" in data["documents"]
        assert "platform" in data["documents"]
        assert "donor" in data["documents"]

    def test_get_matrix_for_level_prototype(self, client):
        """Test getting matrix for PROTOTYPE level."""
        response = client.get(f"/api/documents/matrix/{PROTOTYPE}")

        assert response.status_code == 200
        data = response.json()

        assert data["product_level"] == PROTOTYPE

    def test_get_matrix_for_level_internal_tool(self, client):
        """Test getting matrix for INTERNAL_TOOL level."""
        response = client.get(f"/api/documents/matrix/{INTERNAL_TOOL}")

        assert response.status_code == 200
        data = response.json()

        assert data["product_level"] == INTERNAL_TOOL

    def test_get_matrix_for_level_platform_module(self, client):
        """Test getting matrix for PLATFORM_MODULE level."""
        response = client.get(f"/api/documents/matrix/{PLATFORM_MODULE}")

        assert response.status_code == 200
        data = response.json()

        assert data["product_level"] == PLATFORM_MODULE

    def test_get_matrix_for_level_near_product(self, client):
        """Test getting matrix for NEAR_PRODUCT level."""
        response = client.get(f"/api/documents/matrix/{NEAR_PRODUCT}")

        assert response.status_code == 200
        data = response.json()

        assert data["product_level"] == NEAR_PRODUCT

    def test_get_matrix_for_invalid_level(self, client):
        """Test getting matrix for invalid level returns 404."""
        response = client.get("/api/documents/matrix/invalid_level")

        assert response.status_code == 404
        assert "Unknown product level" in response.json()["detail"]

    # =========================================================================
    # GET /api/documents/templates tests
    # =========================================================================

    def test_list_templates(self, client):
        """Test listing all document templates."""
        response = client.get("/api/documents/templates")

        assert response.status_code == 200
        data = response.json()

        assert "templates" in data
        assert "total" in data
        assert len(data["templates"]) > 0
        assert data["total"] == len(data["templates"])
        assert data["total"] >= 27  # We have 27+ document types

    def test_list_templates_structure(self, client):
        """Test template list structure."""
        response = client.get("/api/documents/templates")
        data = response.json()

        for template in data["templates"]:
            assert "type" in template
            assert "name" in template
            assert "description" in template
            assert "category" in template
            assert "estimated_pages" in template
            assert "sections" in template
            assert "is_required" in template
            assert "output_formats" in template

    # =========================================================================
    # GET /api/documents/template/{doc_type} tests
    # =========================================================================

    def test_get_template_tech_report(self, client):
        """Test getting tech_report template."""
        response = client.get("/api/documents/template/tech_report")

        assert response.status_code == 200
        data = response.json()

        assert data["type"] == "tech_report"
        assert data["name"] == "Technical Report"
        assert data["is_required"] is True
        assert "sections" in data

    def test_get_template_rnd_summary(self, client):
        """Test getting rnd_summary template."""
        response = client.get("/api/documents/template/rnd_summary")

        assert response.status_code == 200
        data = response.json()

        assert data["type"] == "rnd_summary"
        assert data["name"] == "R&D Summary"

    def test_get_template_quality_report(self, client):
        """Test getting quality_report template."""
        response = client.get("/api/documents/template/quality_report")

        assert response.status_code == 200
        data = response.json()

        assert data["type"] == "quality_report"
        assert data["is_required"] is True

    def test_get_template_invalid_type(self, client):
        """Test getting invalid template type returns 404."""
        response = client.get("/api/documents/template/invalid_type")

        assert response.status_code == 404

    # =========================================================================
    # POST /api/documents/package tests
    # =========================================================================

    def test_get_document_package_base_only(self, client):
        """Test getting document package with base docs only."""
        response = client.post(
            "/api/documents/package",
            json={
                "product_level": PROTOTYPE,
                "is_platform_module": False,
                "has_donors": False,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["product_level"] == PROTOTYPE
        assert data["is_platform_module"] is False
        assert data["has_donors"] is False
        assert len(data["base_documents"]) > 0
        assert len(data["platform_documents"]) == 0
        assert len(data["donor_documents"]) == 0

    def test_get_document_package_with_platform(self, client):
        """Test getting document package as platform module."""
        response = client.post(
            "/api/documents/package",
            json={
                "product_level": INTERNAL_TOOL,
                "is_platform_module": True,
                "has_donors": False,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["is_platform_module"] is True
        assert len(data["platform_documents"]) > 0

    def test_get_document_package_with_donors(self, client):
        """Test getting document package with donors."""
        response = client.post(
            "/api/documents/package",
            json={
                "product_level": PROTOTYPE,
                "is_platform_module": False,
                "has_donors": True,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["has_donors"] is True
        assert len(data["donor_documents"]) > 0

    def test_get_document_package_full(self, client):
        """Test getting full document package."""
        response = client.post(
            "/api/documents/package",
            json={
                "product_level": PLATFORM_MODULE,
                "is_platform_module": True,
                "has_donors": True,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["base_documents"]) > 0
        assert len(data["platform_documents"]) > 0
        assert len(data["donor_documents"]) > 0
        assert data["total_documents"] > 0
        assert data["total_pages"] > 0

    def test_get_document_package_totals(self, client):
        """Test that totals are calculated correctly."""
        response = client.post(
            "/api/documents/package",
            json={
                "product_level": PROTOTYPE,
                "is_platform_module": False,
                "has_donors": True,
            },
        )

        assert response.status_code == 200
        data = response.json()

        expected_count = len(data["base_documents"]) + len(data["platform_documents"]) + len(data["donor_documents"])
        assert data["total_documents"] == expected_count

        expected_pages = sum(d["estimated_pages"] for d in data["base_documents"])
        expected_pages += sum(d["estimated_pages"] for d in data["platform_documents"])
        expected_pages += sum(d["estimated_pages"] for d in data["donor_documents"])
        assert data["total_pages"] == expected_pages

    # =========================================================================
    # GET /api/documents/types tests
    # =========================================================================

    def test_list_document_types(self, client):
        """Test listing document types."""
        response = client.get("/api/documents/types")

        assert response.status_code == 200
        data = response.json()

        assert "types" in data
        assert len(data["types"]) > 0

    def test_list_document_types_structure(self, client):
        """Test document types list structure."""
        response = client.get("/api/documents/types")
        data = response.json()

        for doc_type in data["types"]:
            assert "id" in doc_type
            assert "name" in doc_type
            assert "category" in doc_type
            assert doc_type["category"] in ["base", "platform", "donor", "other"]

    # =========================================================================
    # GET /api/documents/formats tests
    # =========================================================================

    def test_list_formats(self, client):
        """Test listing available document formats."""
        response = client.get("/api/documents/formats")

        assert response.status_code == 200
        data = response.json()

        assert "formats" in data
        assert len(data["formats"]) >= 6  # pdf, xlsx, docx, md, json, csv

        format_ids = [f["id"] for f in data["formats"]]
        assert "pdf" in format_ids
        assert "md" in format_ids
        assert "json" in format_ids

    # =========================================================================
    # All product levels have valid responses
    # =========================================================================

    @pytest.mark.parametrize("level", [
        RND_SPIKE,
        PROTOTYPE,
        INTERNAL_TOOL,
        PLATFORM_MODULE,
        NEAR_PRODUCT,
    ])
    def test_all_levels_return_valid_package(self, client, level):
        """Test that all product levels return valid document packages."""
        response = client.post(
            "/api/documents/package",
            json={
                "product_level": level,
                "is_platform_module": True,
                "has_donors": True,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["product_level"] == level
        assert "base_documents" in data
        assert "platform_documents" in data
        assert "donor_documents" in data
        assert data["total_documents"] > 0
