"""
Projects API routes.
"""
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.models.database import (
    Project, ProjectActivity, ProjectStatus, ActivityType, AnalysisRun, AnalysisStatus
)

router = APIRouter(prefix="/projects")


# Pydantic schemas
class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    client_name: Optional[str] = None
    contract_number: Optional[str] = None
    repository_urls: List[str] = []
    budget_hours: Optional[int] = None
    hourly_rate: Optional[int] = None
    currency: str = "USD"
    tags: List[str] = []


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[ProjectStatus] = None
    client_name: Optional[str] = None
    contract_number: Optional[str] = None
    repository_urls: Optional[List[str]] = None
    budget_hours: Optional[int] = None
    hourly_rate: Optional[int] = None
    currency: Optional[str] = None
    tags: Optional[List[str]] = None


class ActivityResponse(BaseModel):
    id: UUID
    activity_type: ActivityType
    title: str
    description: Optional[str]
    details: Optional[dict]
    actor: Optional[str]
    created_at: datetime

    model_config = {
        "from_attributes": True
    }


class ProjectResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    status: ProjectStatus
    client_name: Optional[str]
    contract_number: Optional[str]
    repository_urls: List[str]
    budget_hours: Optional[int]
    hourly_rate: Optional[int]
    currency: str
    tags: List[str]
    created_at: datetime
    updated_at: datetime
    
    # Computed fields
    analysis_count: int = 0
    completed_analysis_count: int = 0
    recent_activities: List[ActivityResponse] = []

    model_config = {
        "from_attributes": True
    }


class ProjectListResponse(BaseModel):
    projects: List[ProjectResponse]
    total: int


class ActivityCreate(BaseModel):
    activity_type: ActivityType
    title: str
    description: Optional[str] = None
    details: Optional[dict] = None
    actor: Optional[str] = None


async def log_activity(
    db: AsyncSession,
    project_id: UUID,
    activity_type: ActivityType,
    title: str,
    description: str = None,
    details: dict = None,
    actor: str = None
):
    """Helper to log project activity."""
    activity = ProjectActivity(
        project_id=project_id,
        activity_type=activity_type,
        title=title,
        description=description,
        details=details,
        actor=actor
    )
    db.add(activity)
    return activity


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    status: Optional[ProjectStatus] = None,
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """List all projects with optional filtering."""
    query = select(Project)
    
    if status:
        query = query.where(Project.status == status)
    
    if search:
        query = query.where(Project.name.ilike(f"%{search}%"))
    
    # Get total count
    count_query = select(func.count(Project.id))
    if status:
        count_query = count_query.where(Project.status == status)
    if search:
        count_query = count_query.where(Project.name.ilike(f"%{search}%"))
    
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Get projects with pagination
    query = query.order_by(desc(Project.updated_at)).offset(skip).limit(limit)
    result = await db.execute(query)
    projects = result.scalars().all()
    
    # Enrich with analysis counts and recent activities
    enriched = []
    for project in projects:
        # Get analysis counts
        analysis_count_query = select(func.count(AnalysisRun.id)).where(
            AnalysisRun.project_id == project.id
        )
        analysis_count = (await db.execute(analysis_count_query)).scalar()
        
        completed_count_query = select(func.count(AnalysisRun.id)).where(
            AnalysisRun.project_id == project.id,
            AnalysisRun.status == AnalysisStatus.completed
        )
        completed_count = (await db.execute(completed_count_query)).scalar()
        
        # Get recent activities
        activities_query = select(ProjectActivity).where(
            ProjectActivity.project_id == project.id
        ).order_by(desc(ProjectActivity.created_at)).limit(5)
        activities_result = await db.execute(activities_query)
        activities = activities_result.scalars().all()
        
        enriched.append(ProjectResponse(
            id=project.id,
            name=project.name,
            description=project.description,
            status=project.status,
            client_name=project.client_name,
            contract_number=project.contract_number,
            repository_urls=project.repository_urls or [],
            budget_hours=project.budget_hours,
            hourly_rate=project.hourly_rate,
            currency=project.currency or "USD",
            tags=project.tags or [],
            created_at=project.created_at,
            updated_at=project.updated_at,
            analysis_count=analysis_count,
            completed_analysis_count=completed_count,
            recent_activities=[ActivityResponse.model_validate(a) for a in activities]
        ))
    
    return ProjectListResponse(projects=enriched, total=total)


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    data: ProjectCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new project."""
    project = Project(
        name=data.name,
        description=data.description,
        client_name=data.client_name,
        contract_number=data.contract_number,
        repository_urls=data.repository_urls,
        budget_hours=data.budget_hours,
        hourly_rate=data.hourly_rate,
        currency=data.currency,
        tags=data.tags
    )
    db.add(project)
    await db.flush()
    
    # Log creation activity
    await log_activity(
        db, project.id, ActivityType.project_created,
        f"Project '{project.name}' created",
        details={"name": project.name}
    )
    
    await db.flush()
    
    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        status=project.status,
        client_name=project.client_name,
        contract_number=project.contract_number,
        repository_urls=project.repository_urls or [],
        budget_hours=project.budget_hours,
        hourly_rate=project.hourly_rate,
        currency=project.currency or "USD",
        tags=project.tags or [],
        created_at=project.created_at,
        updated_at=project.updated_at,
        analysis_count=0,
        completed_analysis_count=0,
        recent_activities=[]
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get project by ID."""
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get counts
    analysis_count = (await db.execute(
        select(func.count(AnalysisRun.id)).where(AnalysisRun.project_id == project_id)
    )).scalar()
    
    completed_count = (await db.execute(
        select(func.count(AnalysisRun.id)).where(
            AnalysisRun.project_id == project_id,
            AnalysisRun.status == AnalysisStatus.completed
        )
    )).scalar()
    
    # Get activities
    activities_result = await db.execute(
        select(ProjectActivity)
        .where(ProjectActivity.project_id == project_id)
        .order_by(desc(ProjectActivity.created_at))
        .limit(10)
    )
    activities = activities_result.scalars().all()
    
    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        status=project.status,
        client_name=project.client_name,
        contract_number=project.contract_number,
        repository_urls=project.repository_urls or [],
        budget_hours=project.budget_hours,
        hourly_rate=project.hourly_rate,
        currency=project.currency or "USD",
        tags=project.tags or [],
        created_at=project.created_at,
        updated_at=project.updated_at,
        analysis_count=analysis_count,
        completed_analysis_count=completed_count,
        recent_activities=[ActivityResponse.model_validate(a) for a in activities]
    )


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    data: ProjectUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update project."""
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    old_status = project.status
    
    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)
    
    project.updated_at = datetime.now(timezone.utc)
    
    # Log status change if applicable
    if data.status and data.status != old_status:
        await log_activity(
            db, project.id, ActivityType.status_changed,
            f"Status changed to {data.status.value}",
            details={"old_status": old_status.value, "new_status": data.status.value}
        )
    else:
        await log_activity(
            db, project.id, ActivityType.project_updated,
            "Project updated",
            details={"updated_fields": list(update_data.keys())}
        )
    
    await db.flush()
    
    # Get updated counts
    analysis_count = (await db.execute(
        select(func.count(AnalysisRun.id)).where(AnalysisRun.project_id == project_id)
    )).scalar()
    
    completed_count = (await db.execute(
        select(func.count(AnalysisRun.id)).where(
            AnalysisRun.project_id == project_id,
            AnalysisRun.status == AnalysisStatus.completed
        )
    )).scalar()
    
    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        status=project.status,
        client_name=project.client_name,
        contract_number=project.contract_number,
        repository_urls=project.repository_urls or [],
        budget_hours=project.budget_hours,
        hourly_rate=project.hourly_rate,
        currency=project.currency or "USD",
        tags=project.tags or [],
        created_at=project.created_at,
        updated_at=project.updated_at,
        analysis_count=analysis_count,
        completed_analysis_count=completed_count,
        recent_activities=[]
    )


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete project (soft delete by archiving)."""
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project.status = ProjectStatus.archived
    project.updated_at = datetime.now(timezone.utc)
    
    await log_activity(
        db, project.id, ActivityType.status_changed,
        "Project archived",
        details={"old_status": project.status.value, "new_status": "archived"}
    )


@router.get("/{project_id}/activities", response_model=List[ActivityResponse])
async def get_project_activities(
    project_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """Get project activity log."""
    # Verify project exists
    project_exists = await db.execute(
        select(Project.id).where(Project.id == project_id)
    )
    if not project_exists.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")
    
    result = await db.execute(
        select(ProjectActivity)
        .where(ProjectActivity.project_id == project_id)
        .order_by(desc(ProjectActivity.created_at))
        .offset(skip)
        .limit(limit)
    )
    activities = result.scalars().all()
    
    return [ActivityResponse.model_validate(a) for a in activities]


@router.post("/{project_id}/activities", response_model=ActivityResponse, status_code=201)
async def add_project_activity(
    project_id: UUID,
    data: ActivityCreate,
    db: AsyncSession = Depends(get_db)
):
    """Add activity to project (e.g., comment)."""
    # Verify project exists
    project_exists = await db.execute(
        select(Project.id).where(Project.id == project_id)
    )
    if not project_exists.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")
    
    activity = await log_activity(
        db, project_id,
        data.activity_type,
        data.title,
        data.description,
        data.details,
        data.actor
    )
    
    await db.flush()
    
    return ActivityResponse.model_validate(activity)


@router.get("/{project_id}/analyses")
async def get_project_analyses(
    project_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get all analyses for a project."""
    # Verify project exists
    project_exists = await db.execute(
        select(Project.id).where(Project.id == project_id)
    )
    if not project_exists.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")
    
    result = await db.execute(
        select(AnalysisRun)
        .where(AnalysisRun.project_id == project_id)
        .options(selectinload(AnalysisRun.repository))
        .order_by(desc(AnalysisRun.created_at))
    )
    analyses = result.scalars().all()
    
    return [
        {
            "id": str(a.id),
            "repository_url": a.repository.url if a.repository else None,
            "status": a.status.value,
            "branch": a.branch,
            "started_at": a.started_at.isoformat() if a.started_at else None,
            "finished_at": a.finished_at.isoformat() if a.finished_at else None,
            "created_at": a.created_at.isoformat()
        }
        for a in analyses
    ]
