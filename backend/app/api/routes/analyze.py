"""
Analysis API endpoints.
"""
from datetime import datetime
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.models.repository import RepositoryRepo, AnalysisRepo, TaskRepo
from app.services.analysis_runner import run_analysis_task
from app.services.cocomo_estimator import cocomo_estimator, cost_comparator
from app.services.estimation_suite import estimation_suite

router = APIRouter()


# Request/Response Models
class AnalyzeRequest(BaseModel):
    """Request model for analysis."""
    repo_url: str  # Can be URL, local path, or Google Drive folder ID
    branch: Optional[str] = None
    region_mode: str = "EU_UA"  # EU, UA, or EU_UA
    source_type: str = "github"  # github, gitlab, local, gdrive


class AnalyzeResponse(BaseModel):
    """Response model for analysis request."""
    analysis_id: str
    status: str
    message: str


class TaskResponse(BaseModel):
    """Task response model."""
    id: str
    title: str
    description: Optional[str]
    category: str
    priority: str
    status: str
    estimate_hours: Optional[int]
    labels: List[str]


class AnalysisResult(BaseModel):
    """Full analysis result model."""
    analysis_id: str
    status: str
    repo_url: str
    branch: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    error_message: Optional[str] = None
    repo_health: Optional[dict] = None
    tech_debt: Optional[dict] = None
    product_level: Optional[str] = None
    complexity: Optional[str] = None
    cost_estimates: Optional[dict] = None
    historical_estimate: Optional[dict] = None
    tasks: Optional[List[TaskResponse]] = None

    model_config = {
        "from_attributes": True
    }


class AnalysisSummary(BaseModel):
    """Summary model for list view."""
    analysis_id: str
    repo_url: str
    repo_name: Optional[str]
    branch: Optional[str]
    status: str
    product_level: Optional[str]
    complexity: Optional[str]
    created_at: datetime
    finished_at: Optional[datetime]


class AnalysisListResponse(BaseModel):
    """Response for analysis list."""
    analyses: List[AnalysisSummary]
    total: int
    limit: int
    offset: int


@router.post("/analyze", response_model=AnalyzeResponse)
async def start_analysis(
    request: AnalyzeRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Start a new repository analysis.

    The analysis runs in the background. Use GET /api/analysis/{id}
    to check status and retrieve results.
    """
    import os
    from app.adapters.gdrive_adapter import gdrive_adapter, GoogleDriveError

    # Validate local path if source_type is local
    if request.source_type == "local":
        if not os.path.isdir(request.repo_url):
            raise HTTPException(
                status_code=400,
                detail=f"Local path does not exist: {request.repo_url}"
            )

    # Validate Google Drive source
    if request.source_type == "gdrive":
        if not gdrive_adapter.is_configured():
            raise HTTPException(
                status_code=400,
                detail="Google Drive not configured. Set GOOGLE_SERVICE_ACCOUNT_JSON in .env"
            )
        # Validate folder ID exists
        try:
            await gdrive_adapter.get_file_info(request.repo_url)
        except GoogleDriveError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid Google Drive folder: {str(e)}"
            )

    repo_repo = RepositoryRepo(db)
    analysis_repo = AnalysisRepo(db)

    # Determine provider
    if request.source_type == "local":
        provider = "local"
    elif request.source_type == "gdrive":
        provider = "gdrive"
    elif "github.com" in request.repo_url:
        provider = "github"
    elif "gitlab" in request.repo_url:
        provider = "gitlab"
    else:
        provider = "other"

    # Get or create repository
    repository = await repo_repo.get_or_create(
        url=request.repo_url,
        provider=provider,
    )

    # Create analysis run
    analysis_run = await analysis_repo.create(
        repository_id=repository.id,
        branch=request.branch,
        region_mode=request.region_mode,
    )

    await db.commit()

    # Queue background task
    background_tasks.add_task(
        run_analysis_task,
        analysis_id=str(analysis_run.id),
        repo_url=request.repo_url,
        branch=request.branch,
        region_mode=request.region_mode,
        source_type=request.source_type,
    )

    return AnalyzeResponse(
        analysis_id=str(analysis_run.id),
        status="queued",
        message="Analysis started. Poll GET /api/analysis/{id} for results.",
    )


@router.get("/analysis/{analysis_id}", response_model=AnalysisResult)
async def get_analysis(
    analysis_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get analysis results by ID.

    Returns full analysis data if completed, or current status if still running.
    """
    try:
        uuid = UUID(analysis_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid analysis ID format")

    analysis_repo = AnalysisRepo(db)
    analysis = await analysis_repo.get(uuid)

    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    # Build response
    result = AnalysisResult(
        analysis_id=str(analysis.id),
        status=analysis.status.value,
        repo_url=analysis.repository.url,
        branch=analysis.branch,
        created_at=analysis.created_at,
        started_at=analysis.started_at,
        finished_at=analysis.finished_at,
        error_message=analysis.error_message,
    )

    # Add metrics if completed
    if analysis.metrics:
        result.repo_health = analysis.metrics.repo_health
        result.tech_debt = analysis.metrics.tech_debt
        result.product_level = analysis.metrics.product_level
        result.complexity = analysis.metrics.complexity
        result.cost_estimates = analysis.metrics.cost_estimates
        result.historical_estimate = analysis.metrics.historical_estimate

    # Add tasks if available
    if analysis.tasks:
        result.tasks = [
            TaskResponse(
                id=str(task.id),
                title=task.title,
                description=task.description,
                category=task.category.value if task.category else "other",
                priority=task.priority.value if task.priority else "P2",
                status=task.status.value if task.status else "open",
                estimate_hours=task.estimate_hours,
                labels=task.labels or [],
            )
            for task in analysis.tasks
        ]

    return result


@router.get("/analyses", response_model=AnalysisListResponse)
async def list_analyses(
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """
    List all analyses with pagination.
    """
    analysis_repo = AnalysisRepo(db)
    analyses, total = await analysis_repo.list_all(limit=limit, offset=offset)

    summaries = []
    for analysis in analyses:
        summary = AnalysisSummary(
            analysis_id=str(analysis.id),
            repo_url=analysis.repository.url,
            repo_name=analysis.repository.name,
            branch=analysis.branch,
            status=analysis.status.value,
            product_level=analysis.metrics.product_level if analysis.metrics else None,
            complexity=analysis.metrics.complexity if analysis.metrics else None,
            created_at=analysis.created_at,
            finished_at=analysis.finished_at,
        )
        summaries.append(summary)

    return AnalysisListResponse(
        analyses=summaries,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/analysis/{analysis_id}/tasks", response_model=List[TaskResponse])
async def get_analysis_tasks(
    analysis_id: str,
    category: Optional[str] = None,
    priority: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Get tasks for an analysis with optional filtering.
    """
    try:
        uuid = UUID(analysis_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid analysis ID format")

    task_repo = TaskRepo(db)
    tasks = await task_repo.get_by_analysis(uuid)

    # Filter if requested
    if category:
        tasks = [t for t in tasks if t.category and t.category.value == category]
    if priority:
        tasks = [t for t in tasks if t.priority and t.priority.value == priority]

    return [
        TaskResponse(
            id=str(task.id),
            title=task.title,
            description=task.description,
            category=task.category.value if task.category else "other",
            priority=task.priority.value if task.priority else "P2",
            status=task.status.value if task.status else "open",
            estimate_hours=task.estimate_hours,
            labels=task.labels or [],
        )
        for task in tasks
    ]


# Cost Comparison Models
class CustomRates(BaseModel):
    """Custom hourly rates."""
    junior: Optional[float] = None
    middle: Optional[float] = None
    senior: Optional[float] = None


class CostCompareRequest(BaseModel):
    """Request model for cost comparison."""
    loc: int  # Lines of code
    actual_cost: float  # Actual cost paid
    actual_hours: Optional[float] = None  # Actual hours spent
    custom_rates: Optional[CustomRates] = None  # Custom rates for comparison
    tech_debt_score: int = 10  # Tech debt score (0-15)


class QuickEstimateRequest(BaseModel):
    """Request model for quick cost estimate."""
    loc: int
    tech_debt_score: int = 10
    test_coverage: Optional[float] = None
    has_ci: bool = False
    has_documentation: bool = False
    team_experience: str = "nominal"  # low, nominal, high


@router.post("/cost/estimate")
async def quick_cost_estimate(request: QuickEstimateRequest):
    """
    Get a quick cost estimate for a codebase.

    Uses COCOMO II model with modern calibration.
    Returns estimates for multiple regions.
    """
    estimate = cocomo_estimator.estimate(
        loc=request.loc,
        tech_debt_score=request.tech_debt_score,
        test_coverage_percent=request.test_coverage,
        has_ci=request.has_ci,
        has_documentation=request.has_documentation,
        team_experience=request.team_experience,
    )

    result = estimate.to_dict()

    # Add multi-region estimates
    result["regional_estimates"] = {}
    for region, rates in cocomo_estimator.RATES.items():
        cost = estimate.hours_typical * rates["typical"]
        result["regional_estimates"][region] = {
            "cost_typical": round(cost, 2),
            "cost_min": round(estimate.hours_min * rates["min"], 2),
            "cost_max": round(estimate.hours_max * rates["max"], 2),
            "rate": rates["typical"],
            "currency": rates["currency"],
        }

    return result


@router.post("/cost/compare")
async def compare_cost(request: CostCompareRequest):
    """
    Compare actual project cost with COCOMO II estimate.

    Helps answer: "Did we overpay or underpay for this project?"

    Returns:
    - Comparison with multiple regional benchmarks
    - Comparison with custom rates if provided
    - Deviation analysis and verdict
    """
    custom_rates_dict = None
    if request.custom_rates:
        custom_rates_dict = {
            "junior": request.custom_rates.junior or 0,
            "middle": request.custom_rates.middle or 0,
            "senior": request.custom_rates.senior or 0,
        }

    result = cost_comparator.compare_with_custom_rates(
        loc=request.loc,
        actual_cost=request.actual_cost,
        actual_hours=request.actual_hours,
        custom_rates=custom_rates_dict,
        tech_debt_score=request.tech_debt_score,
    )

    return result


@router.get("/cost/rates")
async def get_available_rates():
    """
    Get available regional hourly rates for cost estimation.

    Returns rates for all supported regions with junior/middle/senior breakdown.
    """
    return {
        "rates": cocomo_estimator.RATES,
        "confidence_factor": cocomo_estimator.CONFIDENCE_FACTOR,
        "hours_per_person_month": cocomo_estimator.HOURS_PER_PM,
        "methodology": "COCOMO II (Modern Calibration)",
    }


# =============================================================================
# COMPREHENSIVE ESTIMATION SUITE ENDPOINTS
# =============================================================================

class ComprehensiveEstimateRequest(BaseModel):
    """Request for comprehensive estimation."""
    loc: int  # Lines of code
    complexity: float = 1.5  # 0.5-3.0
    hourly_rate: float = 35  # USD
    include_pert: bool = True
    include_ai_efficiency: bool = True
    enabled_methodologies: Optional[List[str]] = None


@router.post("/estimate/comprehensive")
async def comprehensive_estimate(request: ComprehensiveEstimateRequest):
    """
    Get comprehensive cost estimation using multiple methodologies.

    Includes:
    - 8 industry-standard methodologies (COCOMO, Gartner, IEEE, Microsoft, Google, PMI, SEI, Function Points)
    - PERT 3-point analysis
    - AI Efficiency comparison (Human vs AI-Assisted vs Hybrid)

    Returns estimates from all methodologies with averages and ranges.
    """
    result = estimation_suite.estimate_all(
        loc=request.loc,
        complexity=request.complexity,
        hourly_rate=request.hourly_rate,
        include_pert=request.include_pert,
        include_ai_efficiency=request.include_ai_efficiency,
        enabled_methodologies=request.enabled_methodologies,
    )

    response = result.to_dict()

    # Add multi-region estimates for the average
    response["regional_estimates"] = {}
    for region, rates in cocomo_estimator.RATES.items():
        avg_hours = result.average_hours
        response["regional_estimates"][region] = {
            "cost_typical": round(avg_hours * rates["typical"], 2),
            "cost_min": round(avg_hours * rates["min"], 2),
            "cost_max": round(avg_hours * rates["max"], 2),
            "rate": rates["typical"],
            "currency": rates["currency"],
            "name": rates["name"],
        }

    return response


class PERTRequest(BaseModel):
    """Request for PERT 3-point estimation."""
    optimistic_days: float
    most_likely_days: float
    pessimistic_days: float
    hourly_rate: float = 35


@router.post("/estimate/pert")
async def pert_estimate(request: PERTRequest):
    """
    Calculate PERT 3-point estimation.

    Formula: Expected = (Optimistic + 4×MostLikely + Pessimistic) / 6

    Returns:
    - Expected value
    - Standard deviation
    - Confidence intervals (68%, 95%, 99%)
    - Cost estimates
    """
    return estimation_suite.calculate_pert_custom(
        optimistic_days=request.optimistic_days,
        most_likely_days=request.most_likely_days,
        pessimistic_days=request.pessimistic_days,
        hourly_rate=request.hourly_rate,
    )


class ROIRequest(BaseModel):
    """Request for ROI analysis."""
    investment_cost: float  # Initial cost
    additional_costs: float = 0  # Tools, training, etc.
    maintenance_percent: float = 20  # Annual maintenance as % of investment
    annual_support_savings: float = 0
    annual_training_savings: float = 0
    annual_efficiency_gain: float = 0
    annual_risk_reduction: float = 0


@router.post("/estimate/roi")
async def roi_analysis(request: ROIRequest):
    """
    Calculate ROI for documentation/development investment.

    Returns:
    - Payback period (months)
    - 1-year and 3-year ROI %
    - NPV at 3 years
    - Investment recommendation
    """
    result = estimation_suite.calculate_roi(
        investment_cost=request.investment_cost,
        additional_costs=request.additional_costs,
        maintenance_percent=request.maintenance_percent,
        annual_support_savings=request.annual_support_savings,
        annual_training_savings=request.annual_training_savings,
        annual_efficiency_gain=request.annual_efficiency_gain,
        annual_risk_reduction=request.annual_risk_reduction,
    )
    return result.to_dict()


class AIEfficiencyRequest(BaseModel):
    """Request for AI efficiency comparison."""
    loc: int
    hourly_rate: float = 35
    complexity: float = 1.5


@router.post("/estimate/ai-efficiency")
async def ai_efficiency_comparison(request: AIEfficiencyRequest):
    """
    Compare development approaches: Human vs AI-Assisted vs Hybrid.

    Demonstrates AI value in software development:
    - Pure Human: 25 hrs/KLOC
    - AI-Assisted: 8 hrs/KLOC
    - Hybrid: 6.5 hrs/KLOC

    Returns cost savings and time reduction factors.
    """
    result = estimation_suite.estimate_all(
        loc=request.loc,
        complexity=request.complexity,
        hourly_rate=request.hourly_rate,
        include_pert=False,
        include_ai_efficiency=True,
    )

    if result.ai_efficiency:
        return result.ai_efficiency.to_dict()
    return {"error": "Could not calculate AI efficiency"}


@router.get("/estimate/methodologies")
async def list_methodologies():
    """
    List available estimation methodologies with descriptions.
    """
    return {
        "methodologies": [
            {
                "id": "cocomo",
                "name": "COCOMO II",
                "source": "Boehm et al. (2000)",
                "confidence": "High",
                "description": "Industry-standard parametric model for software cost estimation",
            },
            {
                "id": "gartner",
                "name": "Gartner Standard",
                "source": "Gartner Research 2023",
                "confidence": "High",
                "description": "Enterprise documentation standard (500-800 words/day)",
            },
            {
                "id": "ieee",
                "name": "IEEE 1063",
                "source": "IEEE Standard 1063",
                "confidence": "High",
                "description": "Technical documentation standard (1-2 pages/day)",
            },
            {
                "id": "microsoft",
                "name": "Microsoft Standard",
                "source": "Microsoft Documentation Standards",
                "confidence": "Medium",
                "description": "Tech industry standard (650 words/day)",
            },
            {
                "id": "google",
                "name": "Google Guidelines",
                "source": "Google Technical Writing Guidelines",
                "confidence": "Medium",
                "description": "UX-driven approach (4 hours per page)",
            },
            {
                "id": "pmi",
                "name": "PMI Standard",
                "source": "PMI Project Management Standards",
                "confidence": "Medium",
                "description": "Project management approach (25% of project effort)",
            },
            {
                "id": "sei_slim",
                "name": "SEI SLIM",
                "source": "SEI SLIM Model",
                "confidence": "Medium",
                "description": "For regulated industries (0.30-0.50 factor)",
            },
            {
                "id": "function_points",
                "name": "Function Points",
                "source": "ISO/IEC 20926",
                "confidence": "Medium",
                "description": "Based on functional requirements estimation",
            },
        ],
        "ai_productivity": {
            "pure_human": {"hours_per_kloc": 25, "description": "Traditional development"},
            "ai_assisted": {"hours_per_kloc": 8, "description": "AI generates, human reviews"},
            "hybrid": {"hours_per_kloc": 6.5, "description": "Optimized AI+Human workflow"},
        },
    }
