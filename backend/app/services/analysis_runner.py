"""
Main analysis orchestrator service.

Coordinates the full repository analysis pipeline using the unified metrics system.

This module is the bridge between:
- FastAPI routes (legacy API interface)
- Unified metrics pipeline (new Datadog-style architecture)
- Database persistence (SQLAlchemy models)
"""
import logging
from pathlib import Path
from typing import Optional
from uuid import UUID

from app.core.database import get_session
from app.core.models.database import AnalysisStatus
from app.core.models.repository import AnalysisRepo, TaskRepo

from app.analyzers.repo_fetcher import repo_fetcher, RepoFetchError
from app.metrics.pipeline import AnalysisPipeline, PipelineConfig, PipelineResult
from app.services.notification_service import notification_service
from app.api.routes.progress import (
    progress_manager, AnalysisStage, DEFAULT_COLLECTORS
)

logger = logging.getLogger(__name__)


class AnalysisRunner:
    """
    Orchestrates the full analysis pipeline.

    Uses the new unified metrics pipeline internally while maintaining
    backward compatibility with the existing API and database models.
    """

    def __init__(self):
        self._pipeline = None

    async def _send_notifications(
        self,
        analysis_id: str,
        repo_url: str,
        sr,  # ScoringResult
        metrics_dict: dict,
    ) -> None:
        """Send notifications after analysis completes."""
        try:
            # Get security metrics
            critical = metrics_dict.get("repo.security.semgrep_critical", 0)
            high = metrics_dict.get("repo.security.semgrep_high", 0)
            vulns = metrics_dict.get("repo.security.deps_vulnerabilities", 0)
            has_secrets = metrics_dict.get("repo.security.has_secrets", False)

            # Send security alert if critical issues found
            if critical > 0 or (vulns > 5) or has_secrets:
                logger.info(f"[{analysis_id}] Sending security alert notification...")
                await notification_service.notify_security_alert(
                    analysis_id=analysis_id,
                    repo_url=repo_url,
                    critical_count=critical,
                    high_count=high,
                    vulnerabilities=vulns,
                    has_secrets=has_secrets,
                )

            # Send analysis complete notification
            logger.info(f"[{analysis_id}] Sending analysis complete notification...")
            hours_estimate = sr.cocomo_estimate.hours_typical if hasattr(sr, 'cocomo_estimate') else 0
            await notification_service.notify_analysis_complete(
                analysis_id=analysis_id,
                repo_url=repo_url,
                repo_health_total=sr.repo_health.total,
                tech_debt_total=sr.tech_debt.total,
                product_level=sr.product_level.value,
                security_score=sr.tech_debt.security_deps,
                hours_estimate=hours_estimate,
            )

        except Exception as e:
            # Don't fail the analysis if notifications fail
            logger.warning(f"[{analysis_id}] Notification failed: {e}")

    def _get_pipeline(self, region_mode: str = "EU_UA") -> AnalysisPipeline:
        """Get or create pipeline with config."""
        config = PipelineConfig(
            region_mode=region_mode,
            generate_reports=True,
            report_types=["review", "summary"],
            storage_backend="json",
        )
        return AnalysisPipeline(config)

    async def run(
        self,
        analysis_id: str,
        repo_url: str,
        branch: Optional[str] = None,
        region_mode: str = "EU_UA",
        source_type: str = "github",
    ) -> dict:
        """
        Run full repository analysis pipeline.

        Args:
            analysis_id: UUID of the analysis run
            repo_url: Repository URL or local path to analyze
            branch: Branch to analyze (optional)
            region_mode: Cost estimation region mode
            source_type: Source type (github, gitlab, local)

        Returns:
            Complete analysis results dict
        """
        analysis_uuid = UUID(analysis_id)
        local_path: Optional[Path] = None
        should_cleanup = False  # Only cleanup if we cloned

        logger.info(f"Starting analysis {analysis_id} for {repo_url} (source_type={source_type})")

        # Initialize progress tracking
        await progress_manager.init_progress(analysis_id, DEFAULT_COLLECTORS)

        async with get_session() as session:
            analysis_repo = AnalysisRepo(session)
            task_repo = TaskRepo(session)

            try:
                # Update status to running
                await analysis_repo.update_status(analysis_uuid, AnalysisStatus.running)
                await session.commit()

                # 1. Get repository path (clone if remote, use directly if local)
                await progress_manager.update_stage(
                    analysis_id, AnalysisStage.FETCHING,
                    "Fetching repository...", 0
                )

                if source_type == "local":
                    logger.info(f"[{analysis_id}] Using local path: {repo_url}")
                    local_path = Path(repo_url)
                    should_cleanup = False
                elif source_type == "gdrive":
                    logger.info(f"[{analysis_id}] Downloading from Google Drive: {repo_url}")
                    await progress_manager.update_stage(
                        analysis_id, AnalysisStage.FETCHING,
                        "Downloading from Google Drive...", 30
                    )
                    from app.adapters.gdrive_adapter import gdrive_adapter
                    local_path = await gdrive_adapter.download_folder_to_local(repo_url)
                    should_cleanup = True
                    logger.info(f"[{analysis_id}] Downloaded to {local_path}")
                else:
                    logger.info(f"[{analysis_id}] Cloning repository...")
                    await progress_manager.update_stage(
                        analysis_id, AnalysisStage.FETCHING,
                        "Cloning repository...", 30
                    )
                    local_path = await repo_fetcher.fetch(repo_url, branch)
                    should_cleanup = True
                    logger.info(f"[{analysis_id}] Cloned to {local_path}")

                await progress_manager.update_stage(
                    analysis_id, AnalysisStage.FETCHING,
                    "Repository ready", 100
                )

                # 2. Run unified pipeline
                logger.info(f"[{analysis_id}] Running unified analysis pipeline...")
                await progress_manager.update_stage(
                    analysis_id, AnalysisStage.COLLECTING,
                    "Running code analysis...", 0
                )

                pipeline = self._get_pipeline(region_mode)
                result: PipelineResult = await pipeline.run(
                    repo_path=str(local_path),
                    repo_url=repo_url,
                    branch=branch,
                    analysis_id=analysis_id[:8],  # Use short ID for metrics
                )

                if result.status == "failed":
                    await progress_manager.set_error(analysis_id, result.errors[0] if result.errors else "Unknown error")
                    raise Exception(f"Pipeline failed: {', '.join(result.errors)}")

                # Extract scoring result
                sr = result.scoring_result
                logger.info(f"[{analysis_id}] Pipeline complete: {sr.verdict}")
                logger.info(f"[{analysis_id}] Repo Health: {sr.repo_health.total}/12")
                logger.info(f"[{analysis_id}] Tech Debt: {sr.tech_debt.total}/15")
                logger.info(f"[{analysis_id}] Product Level: {sr.product_level.value}")
                logger.info(f"[{analysis_id}] Complexity: {sr.complexity.value}")

                # 3. Save results to DB (for API compatibility)
                logger.info(f"[{analysis_id}] Saving results to database...")
                await progress_manager.update_stage(
                    analysis_id, AnalysisStage.STORING,
                    "Saving results...", 0
                )

                # Get structure and static data from metrics
                structure_data = result.metrics.to_flat_dict() if result.metrics else {}
                static_metrics = result.metrics.to_flat_dict() if result.metrics else {}

                await analysis_repo.save_metrics(
                    analysis_id=analysis_uuid,
                    repo_health=sr.repo_health.to_dict(),
                    tech_debt=sr.tech_debt.to_dict(),
                    product_level=sr.product_level.value,
                    complexity=sr.complexity.value,
                    cost_estimates=sr.forward_estimate.to_dict(),
                    historical_estimate=sr.historical_estimate.to_dict(),
                    structure_data=structure_data,
                    static_metrics=static_metrics,
                    semgrep_findings=[],  # TODO: integrate semgrep from pipeline
                )

                # Save tasks
                task_dicts = [t.to_dict() for t in sr.tasks]
                await task_repo.create_many(analysis_uuid, task_dicts)

                # Update status to completed
                await analysis_repo.update_status(analysis_uuid, AnalysisStatus.completed)
                await session.commit()

                logger.info(f"Analysis {analysis_id} completed successfully")
                logger.info(f"Reports saved to: {', '.join(str(p) for p in result.report_files)}")

                # Mark progress as complete
                await progress_manager.complete(analysis_id)

                # Send notifications
                await self._send_notifications(
                    analysis_id=analysis_id,
                    repo_url=repo_url,
                    sr=sr,
                    metrics_dict=structure_data,
                )

                # Return results
                return {
                    "analysis_id": analysis_id,
                    "status": "completed",
                    "repo_url": repo_url,
                    "branch": branch,
                    "repo_health": sr.repo_health.to_dict(),
                    "tech_debt": sr.tech_debt.to_dict(),
                    "product_level": sr.product_level.value,
                    "complexity": sr.complexity.value,
                    "cost_estimates": sr.forward_estimate.to_dict(),
                    "historical_estimate": sr.historical_estimate.to_dict(),
                    "tasks_count": len(sr.tasks),
                    "metrics_count": result.metrics_count,
                    "reports": list(result.reports.keys()),
                    "duration_seconds": result.duration_seconds,
                }

            except RepoFetchError as e:
                logger.error(f"[{analysis_id}] Failed to clone repository: {e}")
                await progress_manager.set_error(analysis_id, f"Failed to clone repository: {e}")
                await analysis_repo.update_status(
                    analysis_uuid,
                    AnalysisStatus.failed,
                    error_message=f"Failed to clone repository: {e}",
                )
                await session.commit()
                raise

            except Exception as e:
                # Check if it's a Google Drive error
                error_msg = str(e)
                if "GoogleDriveError" in type(e).__name__ or "Google Drive" in error_msg:
                    logger.error(f"[{analysis_id}] Failed to download from Google Drive: {e}")
                    error_msg = f"Failed to download from Google Drive: {e}"
                else:
                    logger.error(f"[{analysis_id}] Analysis failed: {e}", exc_info=True)
                await progress_manager.set_error(analysis_id, error_msg)
                await analysis_repo.update_status(
                    analysis_uuid,
                    AnalysisStatus.failed,
                    error_message=error_msg,
                )
                await session.commit()
                raise

            finally:
                # Cleanup cloned repository (only if we cloned it)
                if local_path and should_cleanup:
                    try:
                        repo_fetcher.cleanup(local_path)
                    except Exception as e:
                        logger.warning(f"[{analysis_id}] Failed to cleanup: {e}")


# Singleton instance
analysis_runner = AnalysisRunner()


# Backward compatibility function
async def run_analysis_task(
    analysis_id: str,
    repo_url: str,
    branch: Optional[str] = None,
    region_mode: str = "EU_UA",
    source_type: str = "github",
) -> None:
    """
    Run analysis task (wrapper for backward compatibility).

    This function is called by FastAPI BackgroundTasks.
    """
    await analysis_runner.run(analysis_id, repo_url, branch, region_mode, source_type)
