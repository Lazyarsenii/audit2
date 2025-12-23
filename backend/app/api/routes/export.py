"""
Export endpoints for PDF, Excel, and Markdown reports.
"""
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.models.repository import AnalysisRepo
from app.services.export_service import export_service

router = APIRouter()


async def _get_analysis_data(analysis_id: str, db: AsyncSession) -> dict:
    """
    Fetch analysis and convert to export-ready dict format.
    """
    try:
        uuid = UUID(analysis_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid analysis ID format")

    analysis_repo = AnalysisRepo(db)
    analysis = await analysis_repo.get(uuid)

    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    if analysis.status.value != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Analysis not completed. Current status: {analysis.status.value}"
        )

    if not analysis.metrics:
        raise HTTPException(status_code=400, detail="No metrics available for this analysis")

    metrics = analysis.metrics

    # Build export-ready data dict
    data = {
        "analysis_id": str(analysis.id),
        "repo_url": analysis.repository.url if analysis.repository else "N/A",
        "branch": analysis.branch,
        "repo_health": metrics.repo_health or {},
        "tech_debt": metrics.tech_debt or {},
        "product_level": metrics.product_level,
        "complexity": metrics.complexity,
        "cost_estimate": metrics.cost_estimates or {},
        "tasks": [
            {
                "priority": task.priority.value if task.priority else "P2",
                "category": task.category.value if task.category else "refactoring",
                "title": task.title,
                "description": task.description or "",
                "estimate_hours": task.estimate_hours or 0,
            }
            for task in (analysis.tasks or [])
        ],
    }

    # Get repo name for filename
    repo_name = "repo"
    if analysis.repository and analysis.repository.url:
        url = analysis.repository.url
        if "/" in url:
            repo_name = url.rstrip("/").split("/")[-1].replace(".git", "")

    return data, repo_name


@router.get("/analysis/{analysis_id}/export/excel")
async def export_excel(
    analysis_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Export analysis results to Excel format.

    Returns an Excel file with multiple sheets:
    - Summary: Key metrics overview
    - Metrics: Detailed metrics
    - Tasks: Improvement backlog
    - Security: Security findings
    - Cost Estimates: COCOMO II estimates
    """
    data, repo_name = await _get_analysis_data(analysis_id, db)

    try:
        result = export_service.export_to_excel(data, repo_name)
    except RuntimeError as e:
        raise HTTPException(status_code=501, detail=str(e))

    return Response(
        content=result.content,
        media_type=result.content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{result.filename}"'
        }
    )


@router.get("/analysis/{analysis_id}/export/pdf")
async def export_pdf(
    analysis_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Export analysis results to PDF format.

    Returns a styled PDF report with:
    - Executive summary
    - Repo Health scores
    - Tech Debt analysis
    - Cost estimation
    - Top improvement tasks
    """
    data, repo_name = await _get_analysis_data(analysis_id, db)

    try:
        result = export_service.export_to_pdf(data, repo_name)
    except RuntimeError as e:
        raise HTTPException(status_code=501, detail=str(e))

    return Response(
        content=result.content,
        media_type=result.content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{result.filename}"'
        }
    )


@router.get("/analysis/{analysis_id}/export/markdown")
async def export_markdown(
    analysis_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Export analysis results to Markdown format.

    Returns a Markdown file suitable for REPO_AUDIT.md.
    """
    data, repo_name = await _get_analysis_data(analysis_id, db)

    try:
        result = export_service.export_to_markdown(data, repo_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return Response(
        content=result.content,
        media_type=result.content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{result.filename}"'
        }
    )


@router.get("/analysis/{analysis_id}/export/word")
async def export_word(
    analysis_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Export analysis results to Word/DOCX format.

    Returns a Word document with:
    - Executive summary
    - Repo Health scores
    - Tech Debt analysis
    - Cost estimation
    - Top improvement tasks
    """
    data, repo_name = await _get_analysis_data(analysis_id, db)

    try:
        result = export_service.export_to_word(data, repo_name)
    except RuntimeError as e:
        raise HTTPException(status_code=501, detail=str(e))

    return Response(
        content=result.content,
        media_type=result.content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{result.filename}"'
        }
    )


@router.get("/export/formats")
async def list_export_formats():
    """
    List available export formats and their status.
    """
    return {
        "formats": [
            {
                "id": "excel",
                "name": "Excel",
                "extension": ".xlsx",
                "available": export_service._excel_available,
                "description": "Multi-sheet spreadsheet with detailed metrics"
            },
            {
                "id": "pdf",
                "name": "PDF",
                "extension": ".pdf",
                "available": export_service._pdf_available,
                "description": "Styled report document"
            },
            {
                "id": "word",
                "name": "Word",
                "extension": ".docx",
                "available": export_service._word_available,
                "description": "Editable Word document with tables and formatting"
            },
            {
                "id": "markdown",
                "name": "Markdown",
                "extension": ".md",
                "available": True,
                "description": "Plain text report for repositories"
            },
        ]
    }
