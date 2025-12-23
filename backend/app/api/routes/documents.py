"""
Document Generation API endpoints.

Generates professional documents in multiple formats:
- PDF (for auditors)
- Excel (for accountants)
- Word (for editing)

Also provides Document Matrix functionality for automatic
document package selection based on product level.
"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from enum import Enum

from app.metrics.storage import metrics_store
from app.services.document_generator import (
    document_generator,
    DocumentFormat,
    DocumentConfig,
)
from app.services.document_matrix import (
    document_matrix_service,
    DocumentType,
    DOCUMENT_MATRIX,
)

router = APIRouter()


class FormatEnum(str, Enum):
    pdf = "pdf"
    xlsx = "xlsx"
    docx = "docx"
    md = "md"
    json = "json"
    csv = "csv"


class GenerateRequest(BaseModel):
    """Request for document generation."""
    analysis_id: str
    format: FormatEnum = FormatEnum.pdf
    language: str = "en"
    include_metrics: bool = True
    include_recommendations: bool = True
    include_cost_breakdown: bool = True
    company_name: Optional[str] = None


@router.post("/documents/generate")
async def generate_document(request: GenerateRequest):
    """
    Generate document from analysis results.

    Supported formats:
    - pdf: Professional PDF report
    - xlsx: Excel workbook with multiple sheets
    - docx: Word document
    - md: Markdown
    - json: Raw JSON data
    - csv: CSV for spreadsheets
    """
    # Get analysis data
    metrics = await metrics_store.get(request.analysis_id)
    if not metrics:
        raise HTTPException(status_code=404, detail="Analysis not found")

    # Build data dict from metrics
    data = metrics.to_flat_dict()

    # Add scoring data if available
    # This would need to be stored separately or recalculated

    # Configure document
    config = DocumentConfig(
        format=DocumentFormat(request.format.value),
        language=request.language,
        include_metrics=request.include_metrics,
        include_recommendations=request.include_recommendations,
        include_cost_breakdown=request.include_cost_breakdown,
        company_name=request.company_name or "",
    )

    # Generate document
    try:
        content = document_generator.generate(data, DocumentFormat(request.format.value), config)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Document generation failed: {e}")

    # Set content type and filename
    content_types = {
        "pdf": "application/pdf",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "md": "text/markdown",
        "json": "application/json",
        "csv": "text/csv",
    }

    extensions = {
        "pdf": "pdf",
        "xlsx": "xlsx",
        "docx": "docx",
        "md": "md",
        "json": "json",
        "csv": "csv",
    }

    content_type = content_types.get(request.format.value, "application/octet-stream")
    ext = extensions.get(request.format.value, "bin")
    filename = f"audit-report-{request.analysis_id}.{ext}"

    return Response(
        content=content,
        media_type=content_type,
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@router.get("/documents/formats")
async def list_formats():
    """List available document formats."""
    return {
        "formats": [
            {
                "id": "pdf",
                "name": "PDF Report",
                "description": "Professional PDF for auditors and stakeholders",
                "extension": ".pdf",
                "requires": ["reportlab"],
            },
            {
                "id": "xlsx",
                "name": "Excel Workbook",
                "description": "Multi-sheet Excel for accountants and data analysis",
                "extension": ".xlsx",
                "requires": ["openpyxl"],
            },
            {
                "id": "docx",
                "name": "Word Document",
                "description": "Editable Word document for contracts and proposals",
                "extension": ".docx",
                "requires": ["python-docx"],
            },
            {
                "id": "md",
                "name": "Markdown",
                "description": "Developer-friendly markdown report",
                "extension": ".md",
                "requires": [],
            },
            {
                "id": "json",
                "name": "JSON Data",
                "description": "Raw JSON for integrations and APIs",
                "extension": ".json",
                "requires": [],
            },
            {
                "id": "csv",
                "name": "CSV Spreadsheet",
                "description": "Simple CSV for any spreadsheet application",
                "extension": ".csv",
                "requires": [],
            },
        ]
    }


# ============================================================================
# Document Matrix API Endpoints
# ============================================================================

class DocumentPackageRequest(BaseModel):
    """Request for document package based on product level."""
    product_level: str
    is_platform_module: bool = False
    has_donors: bool = False


class GenerateTypedDocumentRequest(BaseModel):
    """Request for generating a specific document type."""
    analysis_id: str
    document_type: str
    format: FormatEnum = FormatEnum.md
    language: str = "uk"
    context: Optional[Dict[str, Any]] = None


@router.get("/documents/matrix/summary")
async def get_matrix_summary():
    """
    Get complete Document Matrix summary.

    Returns all product levels with their document packages.
    """
    return document_matrix_service.get_matrix_summary()


@router.get("/documents/matrix/{product_level}")
async def get_matrix_for_level(product_level: str):
    """
    Get document matrix for specific product level.

    Product levels:
    - rnd_spike: R&D Spike (experimental)
    - prototype: Working prototype
    - internal_tool: Internal tool/service
    - platform_module: Platform module candidate
    - near_product: Near-production ready
    """
    if product_level not in DOCUMENT_MATRIX:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown product level: {product_level}. "
                   f"Valid levels: {list(DOCUMENT_MATRIX.keys())}"
        )

    return {
        "product_level": product_level,
        "documents": DOCUMENT_MATRIX[product_level],
        "counts": {
            cat: len(docs)
            for cat, docs in DOCUMENT_MATRIX[product_level].items()
        }
    }


@router.get("/documents/templates")
async def list_templates():
    """
    List all available document templates.

    Returns template metadata for all document types.
    """
    return {
        "templates": document_matrix_service.get_all_templates(),
        "total": len(document_matrix_service.get_all_templates()),
    }


@router.get("/documents/template/{doc_type}")
async def get_template(doc_type: str):
    """
    Get specific document template.

    Returns full template with structure and required fields.
    """
    try:
        template = document_matrix_service.get_template(doc_type)
        return template.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/documents/package")
async def get_document_package(request: DocumentPackageRequest):
    """
    Get document package for given parameters.

    Automatically selects appropriate documents based on:
    - Product level (rnd_spike → near_product)
    - Platform module status
    - Donor involvement

    Returns list of required documents with templates.
    """
    package = document_matrix_service.get_document_package(
        product_level=request.product_level,
        is_platform_module=request.is_platform_module,
        has_donors=request.has_donors,
    )
    return package.to_dict()


@router.post("/documents/generate-typed")
async def generate_typed_document(request: GenerateTypedDocumentRequest):
    """
    Generate specific document type from analysis.

    Supports all document types from the matrix:
    - rnd_summary: R&D Summary
    - tech_note: Technical Note
    - tech_report: Technical Report
    - architecture_doc: Architecture Documentation
    - operational_runbook: Operational Runbook
    - etc.
    """
    # Validate document type
    try:
        doc_type = DocumentType(request.document_type)
    except ValueError:
        valid_types = [dt.value for dt in DocumentType]
        raise HTTPException(
            status_code=400,
            detail=f"Invalid document type: {request.document_type}. "
                   f"Valid types: {valid_types}"
        )

    # Get analysis data
    metrics = await metrics_store.get(request.analysis_id)
    if not metrics:
        raise HTTPException(status_code=404, detail="Analysis not found")

    # Get template
    try:
        template = document_matrix_service.get_template(request.document_type)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Build document content
    data = metrics.to_flat_dict()
    context = request.context or {}

    # Generate document based on type
    content = document_matrix_service.generate_document(
        doc_type=doc_type,
        data=data,
        context=context,
        language=request.language,
    )

    # Set content type based on format
    content_types = {
        "pdf": "application/pdf",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "md": "text/markdown; charset=utf-8",
        "json": "application/json",
        "csv": "text/csv",
    }

    content_type = content_types.get(request.format.value, "text/plain")
    filename = f"{request.document_type}-{request.analysis_id}.{request.format.value}"

    return Response(
        content=content.encode('utf-8') if isinstance(content, str) else content,
        media_type=content_type,
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@router.get("/documents/types")
async def list_document_types():
    """
    List all available document types with descriptions.
    """
    return {
        "types": [
            {
                "id": dt.value,
                "name": dt.value.replace("_", " ").title(),
                "category": _get_document_category(dt),
            }
            for dt in DocumentType
        ]
    }


def _get_document_category(doc_type: DocumentType) -> str:
    """Get category for document type."""
    base_docs = {
        DocumentType.RND_SUMMARY, DocumentType.TECH_NOTE, DocumentType.BACKLOG,
        DocumentType.TECH_REPORT, DocumentType.COST_ESTIMATE, DocumentType.COST_EFFORT_SUMMARY,
        DocumentType.ARCHITECTURE_DOC, DocumentType.OPERATIONAL_RUNBOOK,
        DocumentType.SECURITY_SUMMARY, DocumentType.QUALITY_REPORT, DocumentType.TECH_DEBT_REPORT,
        DocumentType.TASK_LIST, DocumentType.ROADMAP, DocumentType.INTERNAL_ACCEPTANCE,
        DocumentType.RELEASE_NOTES,
    }
    platform_docs = {
        DocumentType.INTEGRATION_MAP, DocumentType.SLO_SLA, DocumentType.PLATFORM_CHECKLIST,
        DocumentType.MIGRATION_PLAN, DocumentType.PLATFORM_ACCEPTANCE,
    }
    donor_docs = {
        DocumentType.DONOR_ONE_PAGER, DocumentType.DONOR_TECH_REPORT,
        DocumentType.WORKPLAN_ALIGNMENT, DocumentType.BUDGET_STATUS,
        DocumentType.INDICATORS_STATUS, DocumentType.MULTI_DONOR_SPLIT,
        DocumentType.FULL_ACCEPTANCE_PACKAGE, DocumentType.FORECAST_VS_BUDGET,
    }

    if doc_type in base_docs:
        return "base"
    elif doc_type in platform_docs:
        return "platform"
    elif doc_type in donor_docs:
        return "donor"
    return "other"


# ============================================================================
# Catch-all document download (must be last to avoid route conflicts)
# ============================================================================

@router.get("/documents/{analysis_id}/{format}")
async def download_document(
    analysis_id: str,
    format: FormatEnum,
    language: str = Query(default="en"),
):
    """
    Quick download endpoint for documents.

    Example: GET /api/documents/abc123/pdf

    NOTE: This route must be defined LAST to avoid capturing
    /documents/matrix/summary and similar specific routes.
    """
    request = GenerateRequest(
        analysis_id=analysis_id,
        format=format,
        language=language,
    )
    return await generate_document(request)
