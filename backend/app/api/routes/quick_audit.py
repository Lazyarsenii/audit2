"""
Quick Audit API - Simple one-click repository audit with document export.

Usage:
  POST /api/quick-audit
  {
    "repo_url": "https://github.com/user/repo",
    "gdrive_folder_id": "optional_folder_id"
  }

Returns ZIP with all documentation or uploads to Google Drive.
"""
import io
import zipfile
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import tempfile
import shutil

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.analyzers.static_analyzer import static_analyzer
from app.analyzers.git_analyzer import git_analyzer
from app.services.document_generator import DocumentGenerator, DocumentConfig, DocumentFormat
from app.adapters.gdrive_adapter import gdrive_adapter, GoogleDriveError
from app.core.scoring.tech_debt import calculate_tech_debt
from app.core.scoring.repo_health import calculate_repo_health
from app.services.cocomo_estimator import cocomo_estimator
from app.services.work_report_generator import work_report_generator, WorkReportConfig

logger = logging.getLogger(__name__)
router = APIRouter()


class QuickAuditRequest(BaseModel):
    """Request for quick audit."""
    repo_url: str = Field(..., description="Public GitHub/GitLab repository URL")
    gdrive_folder_id: Optional[str] = Field(None, description="Google Drive folder ID for upload (optional)")
    include_pdf: bool = Field(True, description="Generate PDF report")
    include_excel: bool = Field(True, description="Generate Excel with metrics")
    include_markdown: bool = Field(True, description="Generate Markdown summary")
    # Work report options
    include_work_report: bool = Field(False, description="Generate work report with task breakdown")
    report_start_date: Optional[str] = Field(None, description="Work report start date (YYYY-MM-DD)")
    report_end_date: Optional[str] = Field(None, description="Work report end date (YYYY-MM-DD)")
    consultant_name: str = Field("Developer", description="Consultant name for work report")
    organization_name: str = Field("Organization", description="Organization name for work report")


class QuickAuditResponse(BaseModel):
    """Response from quick audit."""
    success: bool
    repo_name: str
    analysis_summary: dict
    documents: list
    gdrive_folder_url: Optional[str] = None
    download_available: bool = False
    message: str


async def clone_repo(repo_url: str) -> Path:
    """Clone repository to temp directory."""
    import subprocess

    temp_dir = Path(tempfile.mkdtemp(prefix="quick_audit_"))
    repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
    clone_path = temp_dir / repo_name

    try:
        result = subprocess.run(
            ["git", "clone", "--depth", "1", repo_url, str(clone_path)],
            capture_output=True,
            text=True,
            timeout=120
        )
        if result.returncode != 0:
            raise HTTPException(400, f"Failed to clone: {result.stderr}")
        return clone_path
    except subprocess.TimeoutExpired:
        raise HTTPException(408, "Clone timeout - repository too large")
    except Exception as e:
        raise HTTPException(400, f"Clone failed: {str(e)}")


async def analyze_repo(repo_path: Path) -> dict:
    """Run full analysis on repository."""

    # Static analysis
    static_metrics = await static_analyzer.analyze(repo_path)

    # Git analysis
    git_metrics = await git_analyzer.analyze(repo_path)

    # Combine metrics for repo health scoring
    combined_metrics = {**static_metrics, **git_metrics}

    # Calculate scores (using correct signatures)
    repo_health_result = calculate_repo_health(combined_metrics)
    tech_debt_result = calculate_tech_debt(static_metrics, [])  # Empty semgrep findings

    # Convert to dict for JSON serialization
    repo_health = repo_health_result.to_dict()
    tech_debt = tech_debt_result.to_dict()

    # Cost estimation
    loc = static_metrics.get("total_loc", 0)
    estimate = cocomo_estimator.estimate(
        loc=loc,
        tech_debt_score=tech_debt.get("total", 10),
    )

    return {
        "repo_name": repo_path.name,
        "static_metrics": static_metrics,
        "git_metrics": git_metrics,
        "repo_health": repo_health,
        "tech_debt": tech_debt,
        "cost_estimate": estimate.to_dict() if hasattr(estimate, "to_dict") else {},
        "analyzed_at": datetime.utcnow().isoformat(),
    }


def generate_documents(analysis: dict, config: QuickAuditRequest) -> list:
    """Generate all requested documents."""
    documents = []
    generator = DocumentGenerator()
    repo_name = analysis["repo_name"]

    # Markdown summary (always generated)
    md_content = generate_markdown_summary(analysis)
    documents.append({
        "name": f"{repo_name}_summary.md",
        "type": "md",
        "content": md_content.encode("utf-8"),
    })

    # JSON data
    import json
    json_content = json.dumps(analysis, indent=2, default=str)
    documents.append({
        "name": f"{repo_name}_data.json",
        "type": "json",
        "content": json_content.encode("utf-8"),
    })

    # PDF report
    if config.include_pdf:
        try:
            pdf_config = DocumentConfig(format=DocumentFormat.PDF)
            pdf_bytes = generator.generate_pdf(analysis, pdf_config)
            if pdf_bytes:
                documents.append({
                    "name": f"{repo_name}_report.pdf",
                    "type": "pdf",
                    "content": pdf_bytes,
                })
        except Exception as e:
            logger.warning(f"PDF generation failed: {e}")

    # Excel metrics
    if config.include_excel:
        try:
            xlsx_config = DocumentConfig(format=DocumentFormat.EXCEL)
            xlsx_bytes = generator.generate_excel(analysis, xlsx_config)
            if xlsx_bytes:
                documents.append({
                    "name": f"{repo_name}_metrics.xlsx",
                    "type": "xlsx",
                    "content": xlsx_bytes,
                })
        except Exception as e:
            logger.warning(f"Excel generation failed: {e}")

    # Work report with task breakdown
    if config.include_work_report:
        try:
            # Parse dates or use defaults (current month)
            if config.report_start_date:
                start_date = datetime.strptime(config.report_start_date, "%Y-%m-%d")
            else:
                today = datetime.now()
                start_date = today.replace(day=1)
            
            if config.report_end_date:
                end_date = datetime.strptime(config.report_end_date, "%Y-%m-%d")
            else:
                # End of current month
                next_month = start_date.replace(day=28) + timedelta(days=4)
                end_date = next_month - timedelta(days=next_month.day)
            
            # Get total hours from COCOMO estimate and divide by 10
            cost_data = analysis.get("cost_estimate", {})
            hours_data = cost_data.get("hours", {})
            total_hours = hours_data.get("typical", 100) if isinstance(hours_data, dict) else 100
            work_hours = total_hours / 10  # Divide by 10 as requested
            
            report_config = WorkReportConfig(
                start_date=start_date,
                end_date=end_date,
                consultant_name=config.consultant_name,
                organization=config.organization_name,
                project_name=repo_name,
            )
            
            # Generate tasks
            tasks = work_report_generator.generate_tasks_from_analysis(
                analysis, work_hours, report_config
            )
            
            # Generate PDF work report
            work_report_pdf = work_report_generator.generate_pdf_report(
                tasks, report_config, analysis
            )
            
            if work_report_pdf:
                documents.append({
                    "name": f"{repo_name}_work_report.pdf",
                    "type": "pdf",
                    "content": work_report_pdf,
                })
                logger.info(f"Work report generated: {work_hours:.0f} hours distributed across {len(tasks)} tasks")
                
        except Exception as e:
            logger.warning(f"Work report generation failed: {e}")

    return documents


def generate_markdown_summary(analysis: dict) -> str:
    """Generate markdown summary of analysis."""
    repo_name = analysis.get("repo_name", "Repository")
    static = analysis.get("static_metrics", {})
    git = analysis.get("git_metrics", {})
    health = analysis.get("repo_health", {})
    debt = analysis.get("tech_debt", {})
    cost = analysis.get("cost_estimate", {})

    # Get hours from cost estimate
    hours_data = cost.get("hours", {})
    hours_typical = hours_data.get("typical", 0) if isinstance(hours_data, dict) else 0

    md = f"""# Repository Audit: {repo_name}

**Generated:** {analysis.get("analyzed_at", datetime.utcnow().isoformat())}

---

## Summary

| Metric | Value |
|--------|-------|
| Total LOC | {static.get("total_loc", 0):,} |
| Files | {static.get("files_count", 0)} |
| Languages | {", ".join(static.get("languages", {}).keys()) or "N/A"} |
| Commits | {git.get("total_commits", 0)} |
| Contributors | {git.get("authors_count", 0)} |

---

## Health Score: {health.get("total", 0)}/12

| Category | Score |
|----------|-------|
| Documentation | {health.get("documentation", 0)}/3 |
| Testing | {health.get("testing", 0)}/3 |
| CI/CD | {health.get("ci_cd", 0)}/3 |
| Code Quality | {health.get("code_quality", 0)}/3 |

---

## Technical Debt Score: {debt.get("total", 0)}/15

| Category | Score |
|----------|-------|
| Complexity | {debt.get("complexity", 0)}/5 |
| Duplication | {debt.get("duplication", 0)}/5 |
| Dependencies | {debt.get("dependencies", 0)}/5 |

---

## Cost Estimation

| Region | Estimate |
|--------|----------|
| Hours (typical) | {hours_typical:,.0f}h |

---

## Languages Breakdown

"""
    for lang, data in static.get("languages", {}).items():
        loc = data.get("loc", 0) if isinstance(data, dict) else data
        md += f"- **{lang}**: {loc:,} LOC\n"

    md += """
---

## Recommendations

"""
    if static.get("cyclomatic_complexity_avg", 0) > 10:
        md += "- Consider refactoring complex functions (avg complexity > 10)\n"
    if static.get("duplication_percent", 0) > 10:
        md += "- Reduce code duplication (currently {:.1f}%)\n".format(static.get("duplication_percent", 0))
    if not git.get("has_readme", False):
        md += "- Add README.md documentation\n"
    if health.get("testing", 0) < 2:
        md += "- Improve test coverage\n"
    if health.get("ci_cd", 0) < 2:
        md += "- Set up CI/CD pipeline\n"

    md += """
---

*Generated by Repo Auditor*
"""
    return md


def create_zip(documents: list, repo_name: str) -> bytes:
    """Create ZIP file with all documents."""
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for doc in documents:
            zf.writestr(doc["name"], doc["content"])

    zip_buffer.seek(0)
    return zip_buffer.getvalue()


@router.post("/quick-audit")
async def quick_audit(request: QuickAuditRequest):
    """
    Quick one-click repository audit.

    1. Clones the repository
    2. Analyzes code metrics, health, tech debt
    3. Generates documentation (PDF, Excel, Markdown)
    4. Returns ZIP or uploads to Google Drive
    """
    repo_path = None

    try:
        # Clone
        logger.info(f"Quick audit starting for: {request.repo_url}")
        repo_path = await clone_repo(request.repo_url)
        repo_name = repo_path.name

        # Analyze
        logger.info(f"Analyzing {repo_name}...")
        analysis = await analyze_repo(repo_path)

        # Generate documents
        logger.info("Generating documents...")
        documents = generate_documents(analysis, request)

        # Upload to Google Drive if folder ID provided
        gdrive_url = None
        if request.gdrive_folder_id and gdrive_adapter.is_configured():
            try:
                logger.info(f"Uploading to Google Drive folder: {request.gdrive_folder_id}")
                result = await gdrive_adapter.upload_multiple_documents(
                    documents=documents,
                    folder_id=request.gdrive_folder_id,
                    folder_name=f"{repo_name}_audit_{datetime.now().strftime('%Y%m%d_%H%M')}",
                )
                if result.get("folder"):
                    gdrive_url = result["folder"].get("webViewLink")
                logger.info(f"Uploaded {result.get('success_count', 0)} documents to Drive")
            except GoogleDriveError as e:
                logger.warning(f"Google Drive upload failed: {e}")

        # Create summary
        summary = {
            "total_loc": analysis["static_metrics"].get("total_loc", 0),
            "files_count": analysis["static_metrics"].get("files_count", 0),
            "languages": list(analysis["static_metrics"].get("languages", {}).keys()),
            "repo_health_score": analysis["repo_health"].get("total", 0),
            "tech_debt_score": analysis["tech_debt"].get("total", 0),
            "complexity_avg": analysis["static_metrics"].get("cyclomatic_complexity_avg", 0),
            "duplication_percent": analysis["static_metrics"].get("duplication_percent", 0),
        }

        return QuickAuditResponse(
            success=True,
            repo_name=repo_name,
            analysis_summary=summary,
            documents=[{"name": d["name"], "type": d["type"]} for d in documents],
            gdrive_folder_url=gdrive_url,
            download_available=True,
            message="Audit completed successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Quick audit failed: {e}")
        raise HTTPException(500, f"Audit failed: {str(e)}")
    finally:
        # Cleanup
        if repo_path and repo_path.parent.exists():
            shutil.rmtree(repo_path.parent, ignore_errors=True)


@router.post("/quick-audit/download")
async def quick_audit_download(request: QuickAuditRequest):
    """
    Quick audit with direct ZIP download.

    Returns a ZIP file with all generated documentation.
    """
    repo_path = None

    try:
        # Clone
        repo_path = await clone_repo(request.repo_url)
        repo_name = repo_path.name

        # Analyze
        analysis = await analyze_repo(repo_path)

        # Generate documents
        documents = generate_documents(analysis, request)

        # Create ZIP
        zip_content = create_zip(documents, repo_name)

        # Return as downloadable file
        return StreamingResponse(
            io.BytesIO(zip_content),
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename={repo_name}_audit.zip"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Quick audit download failed: {e}")
        raise HTTPException(500, f"Audit failed: {str(e)}")
    finally:
        if repo_path and repo_path.parent.exists():
            shutil.rmtree(repo_path.parent, ignore_errors=True)
