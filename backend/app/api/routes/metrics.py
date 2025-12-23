"""
Metrics API endpoints.

Provides access to raw metrics data following Datadog-style patterns.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.metrics.storage import metrics_store

router = APIRouter()


class MetricResponse(BaseModel):
    """Individual metric response."""
    name: str
    value: Any
    type: str
    source: str
    category: str
    labels: Dict[str, str]
    timestamp: datetime
    unit: Optional[str] = None
    description: Optional[str] = None


class MetricSetResponse(BaseModel):
    """Full metric set response."""
    analysis_id: str
    repo_url: str
    branch: Optional[str]
    collected_at: datetime
    metrics_count: int
    metrics: List[MetricResponse]
    metadata: Dict[str, Any]


class AnalysisSummaryResponse(BaseModel):
    """Analysis summary for listing."""
    analysis_id: str
    repo_url: str
    branch: Optional[str]
    collected_at: datetime
    metrics_count: int


class MetricsListResponse(BaseModel):
    """Response for metrics list endpoint."""
    analyses: List[AnalysisSummaryResponse]
    total: int
    limit: int
    offset: int


@router.get("/metrics", response_model=MetricsListResponse)
async def list_metrics(
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
):
    """
    List all collected metric sets.

    Returns summaries of all analysis runs stored in the metrics system.
    """
    analyses = await metrics_store.list(limit=limit, offset=offset)

    summaries = [
        AnalysisSummaryResponse(
            analysis_id=a["analysis_id"],
            repo_url=a["repo_url"],
            branch=a.get("branch"),
            collected_at=datetime.fromisoformat(a["collected_at"]),
            metrics_count=a["metrics_count"],
        )
        for a in analyses
    ]

    return MetricsListResponse(
        analyses=summaries,
        total=len(summaries),
        limit=limit,
        offset=offset,
    )


@router.get("/metrics/{analysis_id}", response_model=MetricSetResponse)
async def get_metrics(analysis_id: str):
    """
    Get full metrics for an analysis.

    Returns all collected metrics for the specified analysis ID.
    """
    metric_set = await metrics_store.get(analysis_id)

    if not metric_set:
        raise HTTPException(status_code=404, detail="Metrics not found")

    return MetricSetResponse(
        analysis_id=metric_set.analysis_id,
        repo_url=metric_set.repo_url,
        branch=metric_set.branch,
        collected_at=metric_set.collected_at,
        metrics_count=len(metric_set.metrics),
        metrics=[
            MetricResponse(
                name=m.name,
                value=m.value,
                type=m.metric_type.value,
                source=m.source.value,
                category=m.category.value,
                labels={l.key: l.value for l in m.labels},
                timestamp=m.timestamp,
                unit=m.unit,
                description=m.description,
            )
            for m in metric_set.metrics
        ],
        metadata=metric_set.metadata,
    )


@router.get("/metrics/{analysis_id}/category/{category}")
async def get_metrics_by_category(
    analysis_id: str,
    category: str,
):
    """
    Get metrics filtered by category.

    Categories: documentation, structure, runability, history,
                architecture, code_quality, testing, infrastructure, security
    """
    metric_set = await metrics_store.get(analysis_id)

    if not metric_set:
        raise HTTPException(status_code=404, detail="Metrics not found")

    filtered = [
        MetricResponse(
            name=m.name,
            value=m.value,
            type=m.metric_type.value,
            source=m.source.value,
            category=m.category.value,
            labels={l.key: l.value for l in m.labels},
            timestamp=m.timestamp,
            unit=m.unit,
            description=m.description,
        )
        for m in metric_set.metrics
        if m.category.value == category
    ]

    return {
        "analysis_id": analysis_id,
        "category": category,
        "metrics": filtered,
        "count": len(filtered),
    }


@router.get("/metrics/query/{metric_name}")
async def query_metric(
    metric_name: str,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = Query(default=100, le=1000),
):
    """
    Query a specific metric across all analyses.

    Useful for trending and historical comparisons.
    Example: GET /api/metrics/query/repo.health.total?start_time=2024-01-01
    """
    metrics = await metrics_store.query(
        metric_name=metric_name,
        start_time=start_time,
        end_time=end_time,
    )

    return {
        "metric_name": metric_name,
        "results": [
            {
                "value": m.value,
                "timestamp": m.timestamp.isoformat(),
                "labels": {l.key: l.value for l in m.labels},
            }
            for m in metrics[:limit]
        ],
        "count": len(metrics[:limit]),
    }
