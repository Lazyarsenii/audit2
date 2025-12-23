"""
API routes for contract parsing and comparison.

Endpoints:
- POST /api/contract-parser/upload - Upload and parse contract document
- GET /api/contract-parser/parsed - List parsed contracts
- GET /api/contract-parser/parsed/{contract_id} - Get parsed contract details
- POST /api/contract-parser/compare - Compare contract with analysis
- GET /api/contract-parser/demo - Get demo parsed contract
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

from app.services.contract_parser import contract_parser, ParsedContract
from app.services.contract_comparison import comparison_service


router = APIRouter(prefix="/contract-parser", tags=["contract-parser"])


# -------------------------------------------------------------------------
# Request/Response Models
# -------------------------------------------------------------------------

class CompareRequest(BaseModel):
    contract_id: str
    analysis_data: Dict[str, Any]
    project_progress: Optional[Dict[str, Any]] = None


class DemoContractRequest(BaseModel):
    """Request to create demo contract data."""
    contract_name: Optional[str] = "Demo Grant Contract"
    total_budget: Optional[float] = 150000.0
    currency: Optional[str] = "USD"


# -------------------------------------------------------------------------
# Endpoints
# -------------------------------------------------------------------------

@router.post("/upload")
async def upload_contract(
    file: UploadFile = File(...),
    contract_name: Optional[str] = Form(None),
):
    """
    Upload and parse a contract document.

    Supported formats: PDF, DOCX, TXT

    Extracts:
    - Work plan (activities, milestones)
    - Budget (line items)
    - Indicators (KPIs)
    - Policy requirements
    - Document templates
    """
    # Validate file type
    allowed_types = [".pdf", ".docx", ".doc", ".txt"]
    file_ext = "." + file.filename.split(".")[-1].lower() if "." in file.filename else ""

    if file_ext not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file_ext}. Allowed: {', '.join(allowed_types)}"
        )

    # Read file content
    content = await file.read()

    # Parse the contract
    parsed = contract_parser.parse_file(
        file_path=file.filename,
        content=content,
    )

    # Override title if provided
    if contract_name:
        parsed.contract_title = contract_name

    return {
        "status": "success",
        "contract_id": parsed.id,
        "filename": parsed.filename,
        "parsed_at": parsed.parsed_at,
        "summary": {
            "contract_number": parsed.contract_number,
            "contract_title": parsed.contract_title,
            "total_budget": parsed.total_budget,
            "activities_count": len(parsed.work_plan),
            "milestones_count": len(parsed.milestones),
            "budget_lines_count": len(parsed.budget),
            "indicators_count": len(parsed.indicators),
            "policies_count": len(parsed.policies),
            "templates_count": len(parsed.document_templates),
        }
    }


@router.get("/parsed")
async def list_parsed_contracts():
    """List all parsed contracts."""
    contracts = contract_parser.list_parsed()
    return {
        "contracts": contracts,
        "total": len(contracts),
    }


@router.get("/parsed/{contract_id}")
async def get_parsed_contract(contract_id: str):
    """Get full details of a parsed contract."""
    parsed = contract_parser.get_parsed(contract_id)
    if not parsed:
        raise HTTPException(status_code=404, detail=f"Contract '{contract_id}' not found")

    return parsed.to_dict()


@router.post("/compare")
async def compare_contract(request: CompareRequest):
    """
    Compare parsed contract with analysis results.

    Returns comparison of:
    - Work plan activities vs progress
    - Budget vs cost estimates
    - Indicators vs metrics
    """
    # Get parsed contract
    parsed = contract_parser.get_parsed(request.contract_id)
    if not parsed:
        raise HTTPException(status_code=404, detail=f"Contract '{request.contract_id}' not found")

    # Run comparison
    report = comparison_service.compare(
        contract=parsed,
        analysis_data=request.analysis_data,
        project_progress=request.project_progress,
    )

    return report.to_dict()


@router.post("/demo")
async def create_demo_contract(request: DemoContractRequest = None):
    """
    Create a demo parsed contract for testing.

    Returns a pre-populated contract with sample work plan, budget, and indicators.
    """
    if request is None:
        request = DemoContractRequest()

    from datetime import datetime
    from app.services.contract_parser import (
        ParsedContract, Activity, Milestone, BudgetLine,
        Indicator, PolicyRequirement, DocumentTemplate
    )

    demo = ParsedContract(
        id="demo_contract_001",
        filename="demo_grant_agreement.pdf",
        parsed_at=datetime.now().isoformat(),
        contract_number="GF-2024-001",
        contract_title=request.contract_name,
        contractor="Tech Solutions NGO",
        client="Global Fund",
        start_date="2024-01-01",
        end_date="2024-12-31",
        total_budget=request.total_budget,
        currency=request.currency,
        work_plan=[
            Activity(
                id="ACT_1",
                name="Requirements Analysis",
                description="Analyze and document system requirements",
                start_date="2024-01-01",
                end_date="2024-02-28",
                deliverables=["Requirements document", "Use cases"],
                status="completed",
            ),
            Activity(
                id="ACT_2",
                name="System Design",
                description="Design system architecture and database",
                start_date="2024-03-01",
                end_date="2024-04-30",
                deliverables=["Architecture document", "ERD"],
                status="completed",
            ),
            Activity(
                id="ACT_3",
                name="Development",
                description="Implement core functionality",
                start_date="2024-05-01",
                end_date="2024-09-30",
                deliverables=["Working system", "Source code"],
                status="in_progress",
            ),
            Activity(
                id="ACT_4",
                name="Testing & QA",
                description="System testing and quality assurance",
                start_date="2024-10-01",
                end_date="2024-11-15",
                deliverables=["Test reports", "Bug fixes"],
                status="planned",
            ),
            Activity(
                id="ACT_5",
                name="Deployment & Training",
                description="Deploy system and train users",
                start_date="2024-11-16",
                end_date="2024-12-31",
                deliverables=["Deployed system", "Training materials"],
                status="planned",
            ),
        ],
        milestones=[
            Milestone(
                id="M1",
                name="Requirements Complete",
                due_date="2024-02-28",
                deliverables=["Requirements document"],
                payment_linked=True,
                payment_amount=request.total_budget * 0.15,
            ),
            Milestone(
                id="M2",
                name="Design Complete",
                due_date="2024-04-30",
                deliverables=["Architecture document"],
                payment_linked=True,
                payment_amount=request.total_budget * 0.20,
            ),
            Milestone(
                id="M3",
                name="Development Complete",
                due_date="2024-09-30",
                deliverables=["Working system"],
                payment_linked=True,
                payment_amount=request.total_budget * 0.35,
            ),
            Milestone(
                id="M4",
                name="Final Delivery",
                due_date="2024-12-31",
                deliverables=["Deployed system", "Documentation"],
                payment_linked=True,
                payment_amount=request.total_budget * 0.30,
            ),
        ],
        budget=[
            BudgetLine(
                id="BL_1",
                category="personnel",
                description="Development team salaries",
                unit="month",
                quantity=12,
                unit_cost=6000,
                total=72000,
                currency=request.currency,
            ),
            BudgetLine(
                id="BL_2",
                category="consultants",
                description="Technical consultants",
                unit="days",
                quantity=30,
                unit_cost=500,
                total=15000,
                currency=request.currency,
            ),
            BudgetLine(
                id="BL_3",
                category="equipment",
                description="Servers and infrastructure",
                unit="unit",
                quantity=1,
                unit_cost=20000,
                total=20000,
                currency=request.currency,
            ),
            BudgetLine(
                id="BL_4",
                category="training",
                description="Training and workshops",
                unit="event",
                quantity=5,
                unit_cost=3000,
                total=15000,
                currency=request.currency,
            ),
            BudgetLine(
                id="BL_5",
                category="travel",
                description="Travel and transportation",
                unit="trip",
                quantity=10,
                unit_cost=1000,
                total=10000,
                currency=request.currency,
            ),
            BudgetLine(
                id="BL_6",
                category="overhead",
                description="Administrative overhead",
                unit="month",
                quantity=12,
                unit_cost=1500,
                total=18000,
                currency=request.currency,
            ),
        ],
        indicators=[
            Indicator(
                id="IND_1",
                name="Documentation Score",
                description="Repository documentation quality",
                baseline=1,
                target=3,
                unit="level",
                frequency="quarterly",
            ),
            Indicator(
                id="IND_2",
                name="Test Coverage",
                description="Automated test coverage",
                baseline=0,
                target=2,
                unit="level",
                frequency="quarterly",
            ),
            Indicator(
                id="IND_3",
                name="Security Score",
                description="Security assessment score",
                baseline=1,
                target=3,
                unit="level",
                frequency="quarterly",
            ),
            Indicator(
                id="IND_4",
                name="Code Quality",
                description="Code quality metrics",
                baseline=1,
                target=2,
                unit="level",
                frequency="quarterly",
            ),
        ],
        policies=[
            PolicyRequirement(
                id="POL_1",
                title="Monthly Progress Reports",
                description="Submit monthly progress reports by 5th of each month",
                category="reporting",
                priority="high",
            ),
            PolicyRequirement(
                id="POL_2",
                title="Financial Audit",
                description="Annual financial audit required",
                category="financial",
                priority="critical",
            ),
            PolicyRequirement(
                id="POL_3",
                title="Data Protection",
                description="Comply with GDPR requirements",
                category="compliance",
                priority="critical",
            ),
            PolicyRequirement(
                id="POL_4",
                title="Open Source License",
                description="Use approved open source licenses only",
                category="technical",
                priority="high",
            ),
        ],
        document_templates=[
            DocumentTemplate(
                id="DOC_PROGRESS",
                name="Progress Report",
                description="Monthly project progress report",
                frequency="monthly",
                format="pdf",
                required=True,
            ),
            DocumentTemplate(
                id="DOC_FINANCIAL",
                name="Financial Report",
                description="Quarterly financial report",
                frequency="quarterly",
                format="xlsx",
                required=True,
            ),
            DocumentTemplate(
                id="DOC_TECHNICAL",
                name="Technical Report",
                description="Technical documentation",
                frequency="once",
                format="pdf",
                required=True,
            ),
            DocumentTemplate(
                id="DOC_AUDIT",
                name="Audit Report",
                description="Annual audit report",
                frequency="annually",
                format="pdf",
                required=True,
            ),
        ],
    )

    # Cache the demo contract
    contract_parser._parsed_contracts[demo.id] = demo

    return demo.to_dict()


@router.post("/compare-demo")
async def compare_demo_contract(
    analysis_id: Optional[str] = None,
):
    """
    Run comparison using demo contract and sample analysis data.

    Useful for testing the comparison feature without actual uploads.
    """
    # Create demo contract if not exists
    demo_id = "demo_contract_001"
    if demo_id not in contract_parser._parsed_contracts:
        await create_demo_contract()

    parsed = contract_parser.get_parsed(demo_id)

    # Sample analysis data
    sample_analysis = {
        "analysis_id": analysis_id or "demo_analysis",
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
        "activity_breakdown": {
            "development": 1200,
            "review": 200,
            "documentation": 300,
            "testing": 400,
            "deployment": 300,
        },
    }

    # Sample progress data
    sample_progress = {
        "ACT_1": {"status": "completed", "completion": 100},
        "ACT_2": {"status": "completed", "completion": 100},
        "ACT_3": {"status": "in_progress", "completion": 60},
        "ACT_4": {"status": "planned", "completion": 0},
        "ACT_5": {"status": "planned", "completion": 0},
    }

    # Run comparison
    report = comparison_service.compare(
        contract=parsed,
        analysis_data=sample_analysis,
        project_progress=sample_progress,
    )

    return report.to_dict()


@router.get("/capabilities")
async def get_capabilities():
    """
    Get parser capabilities and supported formats.
    """
    return {
        "supported_formats": [".pdf", ".docx", ".doc", ".txt"],
        "extraction_capabilities": [
            {
                "name": "work_plan",
                "description": "Activities, tasks, and their schedules",
                "fields": ["id", "name", "description", "start_date", "end_date", "deliverables"],
            },
            {
                "name": "milestones",
                "description": "Project milestones and payment triggers",
                "fields": ["id", "name", "due_date", "deliverables", "payment_amount"],
            },
            {
                "name": "budget",
                "description": "Budget line items by category",
                "fields": ["category", "description", "quantity", "unit_cost", "total"],
            },
            {
                "name": "indicators",
                "description": "KPIs and performance metrics",
                "fields": ["id", "name", "baseline", "target", "unit", "frequency"],
            },
            {
                "name": "policies",
                "description": "Policy and compliance requirements",
                "fields": ["id", "title", "description", "category", "priority"],
            },
            {
                "name": "document_templates",
                "description": "Required document templates",
                "fields": ["name", "description", "frequency", "format"],
            },
        ],
        "comparison_features": [
            "Work plan vs actual progress",
            "Budget vs cost estimates",
            "Indicators vs analysis metrics",
            "Risk identification",
            "Recommendations generation",
        ],
        "parser_status": {
            "pdf_support": contract_parser.has_pypdf or contract_parser.has_pdfplumber,
            "docx_support": contract_parser.has_docx,
        },
    }
