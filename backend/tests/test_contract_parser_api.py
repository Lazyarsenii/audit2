"""
API tests for Contract Parser endpoints.
"""

import pytest
from unittest.mock import patch, MagicMock
import io

from app.services.contract_parser import ParsedContract, contract_parser


class TestContractParserAPI:
    """Tests for Contract Parser API endpoints."""

    def setup_method(self):
        """Clear parsed contracts before each test."""
        contract_parser._parsed_contracts.clear()

    def test_get_capabilities(self, client):
        """Test GET /api/contract-parser/capabilities."""
        response = client.get("/api/contract-parser/capabilities")

        assert response.status_code == 200
        data = response.json()

        assert "supported_formats" in data
        assert ".pdf" in data["supported_formats"]
        assert ".docx" in data["supported_formats"]
        assert ".txt" in data["supported_formats"]

        assert "extraction_capabilities" in data
        assert len(data["extraction_capabilities"]) > 0

        assert "comparison_features" in data
        assert "parser_status" in data

    def test_list_parsed_contracts_empty(self, client):
        """Test GET /api/contract-parser/parsed with no contracts."""
        response = client.get("/api/contract-parser/parsed")

        assert response.status_code == 200
        data = response.json()

        assert "contracts" in data
        assert "total" in data
        assert data["total"] == 0

    def test_create_demo_contract(self, client):
        """Test POST /api/contract-parser/demo."""
        response = client.post("/api/contract-parser/demo")

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == "demo_contract_001"
        assert data["contract_title"] == "Demo Grant Contract"
        assert data["total_budget"] == 150000.0
        assert "work_plan" in data
        assert "budget" in data
        assert "indicators" in data
        assert "milestones" in data
        assert "policies" in data
        assert "document_templates" in data

    def test_create_demo_contract_custom_params(self, client):
        """Test POST /api/contract-parser/demo with custom parameters."""
        response = client.post(
            "/api/contract-parser/demo",
            json={
                "contract_name": "Custom Contract",
                "total_budget": 200000.0,
                "currency": "EUR",
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert data["contract_title"] == "Custom Contract"
        assert data["total_budget"] == 200000.0
        assert data["currency"] == "EUR"

    def test_get_parsed_contract(self, client):
        """Test GET /api/contract-parser/parsed/{contract_id}."""
        # First create a demo contract
        client.post("/api/contract-parser/demo")

        # Then get it
        response = client.get("/api/contract-parser/parsed/demo_contract_001")

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == "demo_contract_001"

    def test_get_parsed_contract_not_found(self, client):
        """Test GET /api/contract-parser/parsed/{contract_id} with non-existent ID."""
        response = client.get("/api/contract-parser/parsed/nonexistent_id")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_list_parsed_contracts_after_demo(self, client):
        """Test GET /api/contract-parser/parsed after creating demo."""
        # Create demo contract
        client.post("/api/contract-parser/demo")

        # List contracts
        response = client.get("/api/contract-parser/parsed")

        assert response.status_code == 200
        data = response.json()

        assert data["total"] >= 1

    def test_upload_contract_txt(self, client):
        """Test POST /api/contract-parser/upload with text file."""
        content = b"Contract Number: TEST-001\nTotal Budget: $100,000"

        response = client.post(
            "/api/contract-parser/upload",
            files={"file": ("test_contract.txt", content, "text/plain")},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "success"
        assert data["filename"] == "test_contract.txt"
        assert "contract_id" in data

    def test_upload_contract_with_name(self, client):
        """Test POST /api/contract-parser/upload with custom name."""
        content = b"Contract content"

        response = client.post(
            "/api/contract-parser/upload",
            files={"file": ("test.txt", content, "text/plain")},
            data={"contract_name": "My Custom Contract"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["summary"]["contract_title"] == "My Custom Contract"

    def test_upload_contract_unsupported_format(self, client):
        """Test POST /api/contract-parser/upload with unsupported format."""
        content = b"Some content"

        response = client.post(
            "/api/contract-parser/upload",
            files={"file": ("test.xyz", content, "application/octet-stream")},
        )

        assert response.status_code == 400
        assert "unsupported" in response.json()["detail"].lower()

    def test_compare_demo_contract(self, client):
        """Test POST /api/contract-parser/compare-demo."""
        response = client.post("/api/contract-parser/compare-demo")

        assert response.status_code == 200
        data = response.json()

        assert "contract_id" in data
        assert "overall_status" in data
        assert "overall_score" in data
        assert "work_plan" in data
        assert "budget" in data
        assert "indicators" in data
        assert "recommendations" in data
        assert "risks" in data

    def test_compare_contract(self, client):
        """Test POST /api/contract-parser/compare."""
        # First create demo contract
        client.post("/api/contract-parser/demo")

        # Then compare
        response = client.post(
            "/api/contract-parser/compare",
            json={
                "contract_id": "demo_contract_001",
                "analysis_data": {
                    "repo_health": {
                        "documentation": 2,
                        "structure": 2,
                        "runability": 2,
                        "history": 2,
                        "total": 8,
                    },
                    "tech_debt": {
                        "architecture": 2,
                        "code_quality": 2,
                        "testing": 2,
                        "infrastructure": 2,
                        "security": 2,
                        "total": 10,
                    },
                    "cost": {
                        "cost_estimate": 120000,
                    },
                },
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert data["contract_id"] == "demo_contract_001"
        assert "overall_status" in data

    def test_compare_contract_not_found(self, client):
        """Test POST /api/contract-parser/compare with non-existent contract."""
        response = client.post(
            "/api/contract-parser/compare",
            json={
                "contract_id": "nonexistent",
                "analysis_data": {},
            }
        )

        assert response.status_code == 404

    def test_compare_with_progress(self, client):
        """Test POST /api/contract-parser/compare with project progress."""
        # Create demo contract
        client.post("/api/contract-parser/demo")

        # Compare with progress
        response = client.post(
            "/api/contract-parser/compare",
            json={
                "contract_id": "demo_contract_001",
                "analysis_data": {
                    "cost": {"cost_estimate": 100000},
                },
                "project_progress": {
                    "ACT_1": {"status": "completed", "completion": 100},
                    "ACT_2": {"status": "completed", "completion": 100},
                    "ACT_3": {"status": "in_progress", "completion": 50},
                },
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Check work plan reflects progress
        work_plan = data["work_plan"]
        assert work_plan["total"] > 0


class TestContractParserWorkPlanExtraction:
    """Tests for work plan extraction in demo contract."""

    def test_demo_work_plan_structure(self, client):
        """Test demo contract work plan structure."""
        response = client.post("/api/contract-parser/demo")
        data = response.json()

        work_plan = data["work_plan"]
        assert len(work_plan) == 5

        # Check first activity
        act1 = work_plan[0]
        assert act1["id"] == "ACT_1"
        assert act1["name"] == "Requirements Analysis"
        assert act1["status"] == "completed"
        assert "deliverables" in act1

    def test_demo_milestones_structure(self, client):
        """Test demo contract milestones structure."""
        response = client.post("/api/contract-parser/demo")
        data = response.json()

        milestones = data["milestones"]
        assert len(milestones) == 4

        # Check first milestone
        m1 = milestones[0]
        assert m1["id"] == "M1"
        assert m1["payment_linked"] is True
        assert m1["payment_amount"] > 0


class TestContractParserBudgetExtraction:
    """Tests for budget extraction in demo contract."""

    def test_demo_budget_structure(self, client):
        """Test demo contract budget structure."""
        response = client.post("/api/contract-parser/demo")
        data = response.json()

        budget = data["budget"]
        assert len(budget) == 6

        # Check personnel budget line
        personnel = next((b for b in budget if b["category"] == "personnel"), None)
        assert personnel is not None
        assert personnel["total"] == 72000

    def test_demo_budget_total(self, client):
        """Test demo contract budget total calculation."""
        response = client.post("/api/contract-parser/demo")
        data = response.json()

        budget = data["budget"]
        total = sum(line["total"] for line in budget)

        assert total == 150000  # Default total budget


class TestContractParserIndicators:
    """Tests for indicator extraction in demo contract."""

    def test_demo_indicators_structure(self, client):
        """Test demo contract indicators structure."""
        response = client.post("/api/contract-parser/demo")
        data = response.json()

        indicators = data["indicators"]
        assert len(indicators) == 4

        # Check first indicator
        ind1 = indicators[0]
        assert "id" in ind1
        assert "name" in ind1
        assert "baseline" in ind1
        assert "target" in ind1
        assert "unit" in ind1


class TestContractParserPolicies:
    """Tests for policy extraction in demo contract."""

    def test_demo_policies_structure(self, client):
        """Test demo contract policies structure."""
        response = client.post("/api/contract-parser/demo")
        data = response.json()

        policies = data["policies"]
        assert len(policies) == 4

        # Check policy priorities
        critical_policies = [p for p in policies if p["priority"] == "critical"]
        assert len(critical_policies) >= 2


class TestContractParserDocumentTemplates:
    """Tests for document template extraction in demo contract."""

    def test_demo_templates_structure(self, client):
        """Test demo contract document templates structure."""
        response = client.post("/api/contract-parser/demo")
        data = response.json()

        templates = data["document_templates"]
        assert len(templates) == 4

        # Check template frequencies
        frequencies = [t["frequency"] for t in templates]
        assert "monthly" in frequencies
        assert "quarterly" in frequencies
