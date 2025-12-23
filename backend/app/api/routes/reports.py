"""
Report export endpoints.
"""
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import PlainTextResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from enum import Enum

from app.core.database import get_db
from app.core.models.repository import AnalysisRepo
from app.core.scoring.repo_health import RepoHealthScore
from app.core.scoring.tech_debt import TechDebtScore
from app.core.scoring.product_level import ProductLevel
from app.core.scoring.complexity import Complexity
from app.services.cost_estimator import ForwardEstimate, HistoricalEstimate, ActivityBreakdown, CostRange
from app.services.task_generator import GeneratedTask, TaskCategory, TaskPriority
from app.services.report_builder import report_builder, AnalysisReport

router = APIRouter()


class ReportFormat(str, Enum):
    markdown = "markdown"
    csv_tasks = "csv_tasks"
    csv_cost = "csv_cost"
    json = "json"


@router.get("/analysis/{analysis_id}/report")
async def get_report(
    analysis_id: str,
    format: ReportFormat = ReportFormat.markdown,
    db: AsyncSession = Depends(get_db),
):
    """
    Export analysis report in specified format.

    Formats:
    - markdown: Full report as Markdown (suitable for REPO_AUDIT.md)
    - csv_tasks: Task backlog as CSV
    - csv_cost: Cost estimates as CSV
    - json: Raw JSON data
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

    # Reconstruct objects from stored data
    metrics = analysis.metrics

    repo_health = RepoHealthScore(
        documentation=metrics.repo_health.get("documentation", 0),
        structure=metrics.repo_health.get("structure", 0),
        runability=metrics.repo_health.get("runability", 0),
        commit_history=metrics.repo_health.get("commit_history", 0),
    )

    tech_debt = TechDebtScore(
        architecture=metrics.tech_debt.get("architecture", 0),
        code_quality=metrics.tech_debt.get("code_quality", 0),
        testing=metrics.tech_debt.get("testing", 0),
        infrastructure=metrics.tech_debt.get("infrastructure", 0),
        security_deps=metrics.tech_debt.get("security_deps", 0),
    )

    product_level = ProductLevel(metrics.product_level)
    complexity = Complexity(metrics.complexity)

    # Reconstruct forward estimate
    cost_data = metrics.cost_estimates
    forward_estimate = _reconstruct_forward_estimate(cost_data)

    # Reconstruct historical estimate
    hist_data = metrics.historical_estimate
    historical_estimate = _reconstruct_historical_estimate(hist_data)

    # Reconstruct tasks
    tasks = []
    for task in analysis.tasks:
        tasks.append(GeneratedTask(
            title=task.title,
            description=task.description or "",
            category=TaskCategory(task.category.value) if task.category else TaskCategory.REFACTORING,
            priority=TaskPriority(task.priority.value) if task.priority else TaskPriority.P2,
            estimate_hours=task.estimate_hours or 0,
            labels=task.labels or [],
        ))

    # Build report object
    report = AnalysisReport(
        analysis_id=str(analysis.id),
        repo_url=analysis.repository.url,
        branch=analysis.branch,
        analyzed_at=analysis.finished_at or analysis.created_at,
        repo_health=repo_health,
        tech_debt=tech_debt,
        product_level=product_level,
        complexity=complexity,
        forward_estimate=forward_estimate,
        historical_estimate=historical_estimate,
        tasks=tasks,
        structure_data=metrics.structure_data or {},
        static_metrics=metrics.static_metrics or {},
    )

    # Generate report in requested format
    if format == ReportFormat.markdown:
        content = report_builder.build_markdown(report)
        return PlainTextResponse(
            content,
            media_type="text/markdown",
            headers={
                "Content-Disposition": f'attachment; filename="REPO_AUDIT_{analysis_id[:8]}.md"'
            }
        )

    elif format == ReportFormat.csv_tasks:
        content = report_builder.build_csv_tasks(tasks)
        return PlainTextResponse(
            content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="tasks_{analysis_id[:8]}.csv"'
            }
        )

    elif format == ReportFormat.csv_cost:
        content = report_builder.build_csv_cost(forward_estimate, historical_estimate)
        return PlainTextResponse(
            content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="cost_{analysis_id[:8]}.csv"'
            }
        )

    elif format == ReportFormat.json:
        data = report_builder.build_json(report)
        return JSONResponse(content=data)

    raise HTTPException(status_code=400, detail=f"Unknown format: {format}")


def _reconstruct_forward_estimate(data: dict) -> ForwardEstimate:
    """Reconstruct ForwardEstimate from stored dict."""
    hours = data.get("hours", {})

    def make_breakdown(key: str) -> ActivityBreakdown:
        h = hours.get(key, {})
        return ActivityBreakdown(
            analysis=h.get("analysis", 0),
            design=h.get("design", 0),
            development=h.get("development", 0),
            qa=h.get("qa", 0),
            documentation=h.get("documentation", 0),
        )

    cost = data.get("cost", {})
    eu = cost.get("eu", {})
    ua = cost.get("ua", {})

    return ForwardEstimate(
        hours_min=make_breakdown("min"),
        hours_typical=make_breakdown("typical"),
        hours_max=make_breakdown("max"),
        cost_eu=CostRange(
            min=eu.get("min", 0),
            max=eu.get("max", 0),
            currency=eu.get("currency", "EUR"),
            currency_symbol="€",
        ),
        cost_ua=CostRange(
            min=ua.get("min", 0),
            max=ua.get("max", 0),
            currency=ua.get("currency", "USD"),
            currency_symbol="$",
        ),
        complexity=data.get("complexity", "M"),
        tech_debt_multiplier=data.get("tech_debt_multiplier", 1.0),
    )


def _reconstruct_historical_estimate(data: dict) -> HistoricalEstimate:
    """Reconstruct HistoricalEstimate from stored dict."""
    hours = data.get("hours", {})
    pm = data.get("person_months", {})
    cost = data.get("cost", {})
    eu = cost.get("eu", {})
    ua = cost.get("ua", {})

    return HistoricalEstimate(
        active_days=data.get("active_days", 0),
        estimated_hours_min=hours.get("min", 0),
        estimated_hours_max=hours.get("max", 0),
        estimated_person_months_min=pm.get("min", 0),
        estimated_person_months_max=pm.get("max", 0),
        cost_eu=CostRange(
            min=eu.get("min", 0),
            max=eu.get("max", 0),
            currency=eu.get("currency", "EUR"),
            currency_symbol="€",
        ),
        cost_ua=CostRange(
            min=ua.get("min", 0),
            max=ua.get("max", 0),
            currency=ua.get("currency", "USD"),
            currency_symbol="$",
        ),
        confidence=data.get("confidence", "low"),
        note=data.get("note", ""),
    )
