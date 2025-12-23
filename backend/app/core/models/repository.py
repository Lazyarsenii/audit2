"""
Repository for database operations.
"""
import logging
from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.models.database import (
    Repository,
    AnalysisRun,
    AnalysisStatus,
    Metrics,
    Task,
    TaskCategory,
    TaskPriority,
    TaskStatus,
)

logger = logging.getLogger(__name__)


class RepositoryRepo:
    """Repository operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create(self, url: str, provider: str = "github") -> Repository:
        """Get existing repository or create new one."""
        # Parse owner/name from URL
        owner, name = self._parse_url(url)

        stmt = select(Repository).where(Repository.url == url)
        result = await self.session.execute(stmt)
        repo = result.scalar_one_or_none()

        if repo:
            return repo

        repo = Repository(
            url=url,
            provider=provider,
            owner=owner,
            name=name,
        )
        self.session.add(repo)
        await self.session.flush()
        return repo

    def _parse_url(self, url: str) -> tuple[str, str]:
        """Parse owner and name from URL."""
        url = url.rstrip("/")
        if url.endswith(".git"):
            url = url[:-4]

        parts = url.split("/")
        if len(parts) >= 2:
            return parts[-2], parts[-1]
        return "", parts[-1] if parts else ""


class AnalysisRepo:
    """Analysis run operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        repository_id: UUID,
        branch: Optional[str] = None,
        region_mode: str = "EU_UA",
    ) -> AnalysisRun:
        """Create new analysis run."""
        run = AnalysisRun(
            repository_id=repository_id,
            branch=branch,
            region_mode=region_mode,
            status=AnalysisStatus.queued,
        )
        self.session.add(run)
        await self.session.flush()
        return run

    async def get(self, analysis_id: UUID) -> Optional[AnalysisRun]:
        """Get analysis run by ID."""
        stmt = (
            select(AnalysisRun)
            .options(
                selectinload(AnalysisRun.repository),
                selectinload(AnalysisRun.metrics),
                selectinload(AnalysisRun.tasks),
            )
            .where(AnalysisRun.id == analysis_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(
        self,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[List[AnalysisRun], int]:
        """List all analysis runs with pagination."""
        # Count total efficiently using COUNT(*)
        from sqlalchemy import func
        count_stmt = select(func.count()).select_from(AnalysisRun)
        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar() or 0

        # Get page
        stmt = (
            select(AnalysisRun)
            .options(selectinload(AnalysisRun.repository))
            .order_by(AnalysisRun.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all(), total

    async def update_status(
        self,
        analysis_id: UUID,
        status: AnalysisStatus,
        error_message: Optional[str] = None,
    ) -> None:
        """Update analysis status."""
        values = {"status": status}

        if status == AnalysisStatus.running:
            values["started_at"] = datetime.now(timezone.utc)
        elif status in [AnalysisStatus.completed, AnalysisStatus.failed]:
            values["finished_at"] = datetime.now(timezone.utc)

        if error_message:
            values["error_message"] = error_message

        stmt = (
            update(AnalysisRun)
            .where(AnalysisRun.id == analysis_id)
            .values(**values)
        )
        await self.session.execute(stmt)

    async def save_metrics(
        self,
        analysis_id: UUID,
        repo_health: dict,
        tech_debt: dict,
        product_level: str,
        complexity: str,
        cost_estimates: dict,
        historical_estimate: dict,
        structure_data: dict,
        static_metrics: dict,
        semgrep_findings: list,
    ) -> Metrics:
        """Save analysis metrics."""
        metrics = Metrics(
            analysis_id=analysis_id,
            repo_health=repo_health,
            tech_debt=tech_debt,
            product_level=product_level,
            complexity=complexity,
            cost_estimates=cost_estimates,
            historical_estimate=historical_estimate,
            structure_data=structure_data,
            static_metrics=static_metrics,
            semgrep_findings=semgrep_findings,
        )
        self.session.add(metrics)
        await self.session.flush()
        return metrics


class TaskRepo:
    """Task operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_many(
        self,
        analysis_id: UUID,
        tasks: List[dict],
    ) -> List[Task]:
        """Create multiple tasks."""
        db_tasks = []
        for task_data in tasks:
            task = Task(
                analysis_id=analysis_id,
                title=task_data["title"],
                description=task_data["description"],
                category=TaskCategory(task_data["category"]),
                priority=TaskPriority(task_data["priority"]),
                estimate_hours=task_data["estimate_hours"],
                labels=task_data.get("labels", []),
                status=TaskStatus.open,
            )
            self.session.add(task)
            db_tasks.append(task)

        await self.session.flush()
        return db_tasks

    async def get_by_analysis(self, analysis_id: UUID) -> List[Task]:
        """Get all tasks for an analysis."""
        stmt = (
            select(Task)
            .where(Task.analysis_id == analysis_id)
            .order_by(Task.priority, Task.created_at)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def update_github_issue(
        self,
        task_id: UUID,
        issue_number: int,
        issue_url: str,
    ) -> None:
        """Update task with GitHub issue info."""
        stmt = (
            update(Task)
            .where(Task.id == task_id)
            .values(
                github_issue_number=issue_number,
                github_issue_url=issue_url,
            )
        )
        await self.session.execute(stmt)
