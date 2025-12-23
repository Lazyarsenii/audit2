"""Functional API coverage for core services and document scripts."""


def test_health_endpoint(client):
    """Service health endpoint should respond with OK status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "repo-auditor"


def test_readiness_check_returns_assessment(client):
    """Readiness service should score the project and include check breakdown."""
    payload = {
        "repo_health": {"documentation": 2, "structure": 2, "runability": 2, "history": 2},
        "tech_debt": {"architecture": 2, "code_quality": 2, "testing": 1, "infrastructure": 1, "security_deps": 1},
        "product_level": "internal_tool",
        "complexity": "medium",
        "structure_data": {"has_readme": True, "has_docs_folder": True, "has_run_instructions": True},
        "static_metrics": {"total_loc": 1200, "files_count": 40, "has_ci": True},
    }

    response = client.post("/api/readiness/check", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert 0 <= data["readiness_score"] <= 100
    assert data["passed_checks"] + data["failed_checks"] == len(data["checks"])
    assert data["readiness_level"] in {"not_ready", "needs_work", "almost_ready", "ready", "exemplary"}
    assert data["recommendations"] == [] or isinstance(data["recommendations"], list)


def test_comprehensive_estimate_suite(client):
    """Comprehensive estimation suite should return multi-methodology output."""
    response = client.post(
        "/api/estimate/comprehensive",
        json={
            "loc": 5000,
            "complexity": 1.3,
            "hourly_rate": 45,
            "include_pert": True,
            "include_ai_efficiency": True,
        },
    )

    assert response.status_code == 200
    data = response.json()

    assert "methodologies" in data and len(data["methodologies"]) >= 1
    assert "summary" in data and data["summary"]["average_hours"] > 0
    assert "regional_estimates" in data and len(data["regional_estimates"]) > 0
    assert data["pert"] is None or "expected" in data["pert"]
    assert data["ai_efficiency"] is None or "savings" in data["ai_efficiency"]


def test_financial_document_generation(client):
    """Financial document endpoints should emit downloadable content."""
    base_party = {
        "name": "Test LLC",
        "address": "Main street 1",
        "country": "Ukraine",
    }
    payload = {
        "act_number": "001",
        "work_period_start": "2024-01-01",
        "work_period_end": "2024-01-31",
        "work_description": "Audit services",
        "deliverables": ["Report", "Findings"],
        "project_name": "Audit",
        "contractor": base_party,
        "client": base_party,
        "items": [
            {"description": "Repository review", "quantity": 5, "unit_price": 120},
        ],
    }

    response = client.post("/api/financial/act", json=payload)
    assert response.status_code == 200
    assert "act_001" in response.headers.get("content-disposition", "")
    assert "Audit services" in response.text

    invoice_response = client.post(
        "/api/financial/invoice",
        json={
            "invoice_number": "INV-1",
            "due_date": "2024-02-15",
            "contractor": base_party,
            "client": base_party,
            "items": payload["items"],
        },
    )
    assert invoice_response.status_code == 200
    assert "invoice_INV-1" in invoice_response.headers.get("content-disposition", "")
    assert "Test LLC" in invoice_response.text

    contract_response = client.post(
        "/api/financial/contract",
        json={
            "contract_number": "C-1",
            "contractor": base_party,
            "client": base_party,
            "project_name": "Audit",
            "scope_of_work": "Full review",
            "deliverables": ["Report"],
            "start_date": "2024-01-01",
            "end_date": "2024-03-01",
            "total_price": 1000,
        },
    )
    assert contract_response.status_code == 200
    assert contract_response.json()["contract_number"] == "C-1"
    assert contract_response.json()["note"]
