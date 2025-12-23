"""
Unified Analysis Pipeline — Datadog-style end-to-end flow.

Architecture:
    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
    │  Repository │───▶│  Collectors │───▶│   Scoring   │───▶│   Storage   │
    │   (clone)   │    │  (metrics)  │    │   Engine    │    │  (persist)  │
    └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
                                                │
                                                ▼
                                         ┌─────────────┐
                                         │   Reports   │
                                         │  (output)   │
                                         └─────────────┘

Pipeline stages:
1. FETCH: Clone/access repository
2. COLLECT: Run all metric collectors
3. SCORE: Apply scoring engine
4. STORE: Persist metrics and results
5. REPORT: Generate output documents
"""
import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

from .schema import MetricSet
from .collectors import metrics_aggregator
from .scoring_engine import scoring_engine, ScoringResult
from .storage import metrics_store, MetricsStore
from ..services.report_builder import report_builder, AnalysisReport

logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    """Pipeline configuration."""
    region_mode: str = "EU_UA"
    generate_reports: bool = True
    report_types: List[str] = field(default_factory=lambda: ["review", "summary"])
    storage_backend: str = "json"
    storage_path: Optional[Path] = None


@dataclass
class PipelineResult:
    """Complete pipeline execution result."""
    analysis_id: str
    repo_url: str
    branch: Optional[str]
    status: str  # "completed", "failed"
    started_at: datetime
    finished_at: datetime
    duration_seconds: float

    # Metrics
    metrics: MetricSet
    metrics_count: int

    # Scores
    scoring_result: Optional[ScoringResult]

    # Reports
    reports: Dict[str, str]  # report_type -> content
    report_files: List[Path]  # saved file paths

    # Errors
    errors: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "analysis_id": self.analysis_id,
            "repo_url": self.repo_url,
            "branch": self.branch,
            "status": self.status,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat(),
            "duration_seconds": round(self.duration_seconds, 2),
            "metrics_count": self.metrics_count,
            "scores": self.scoring_result.to_dict() if self.scoring_result else None,
            "reports_generated": list(self.reports.keys()),
            "errors": self.errors,
        }

    def summary(self) -> str:
        """Generate human-readable summary."""
        if not self.scoring_result:
            return f"Analysis {self.analysis_id} failed: {', '.join(self.errors)}"

        sr = self.scoring_result
        return f"""
════════════════════════════════════════════════════════════════
 REPO AUDITOR — ANALYSIS COMPLETE
════════════════════════════════════════════════════════════════

 Repository:     {self.repo_url}
 Branch:         {self.branch or 'default'}
 Analysis ID:    {self.analysis_id}
 Duration:       {self.duration_seconds:.1f}s

────────────────────────────────────────────────────────────────
 SCORES
────────────────────────────────────────────────────────────────

 Repo Health:    {sr.repo_health.total}/12 ({round(sr.repo_health.total/12*100)}%)
   Documentation:  {sr.repo_health.documentation}/3
   Structure:      {sr.repo_health.structure}/3
   Runability:     {sr.repo_health.runability}/3
   History:        {sr.repo_health.commit_history}/3

 Tech Debt:      {sr.tech_debt.total}/15 ({round(sr.tech_debt.total/15*100)}%)
   Architecture:   {sr.tech_debt.architecture}/3
   Code Quality:   {sr.tech_debt.code_quality}/3
   Testing:        {sr.tech_debt.testing}/3
   Infrastructure: {sr.tech_debt.infrastructure}/3
   Security:       {sr.tech_debt.security_deps}/3

────────────────────────────────────────────────────────────────
 CLASSIFICATION
────────────────────────────────────────────────────────────────

 Product Level:  {sr.product_level.value}
 Complexity:     {sr.complexity.value}
 Verdict:        {sr.verdict}

────────────────────────────────────────────────────────────────
 COST ESTIMATION
────────────────────────────────────────────────────────────────

 Forward (typical):
   Hours:         {sr.forward_estimate.hours_typical.total:.0f}h
   Cost EU:       {sr.forward_estimate.cost_eu.to_dict()['formatted']}
   Cost UA:       {sr.forward_estimate.cost_ua.to_dict()['formatted']}

 Historical:
   Hours:         {sr.historical_estimate.estimated_hours_min:.0f}—{sr.historical_estimate.estimated_hours_max:.0f}h
   Confidence:    {sr.historical_estimate.confidence}

────────────────────────────────────────────────────────────────
 TASKS
────────────────────────────────────────────────────────────────

 Generated:      {len(sr.tasks)} improvement tasks

════════════════════════════════════════════════════════════════
"""


class AnalysisPipeline:
    """
    Unified analysis pipeline.

    Usage:
        pipeline = AnalysisPipeline()
        result = await pipeline.run("/path/to/repo")
        print(result.summary())
    """

    def __init__(self, config: Optional[PipelineConfig] = None):
        self.config = config or PipelineConfig()
        self.store = MetricsStore(
            backend=self.config.storage_backend,
            path=self.config.storage_path,
        )

    async def run(
        self,
        repo_path: str,
        repo_url: Optional[str] = None,
        branch: Optional[str] = None,
        analysis_id: Optional[str] = None,
    ) -> PipelineResult:
        """
        Run the complete analysis pipeline.

        Args:
            repo_path: Path to repository (local)
            repo_url: Original repository URL (for metadata)
            branch: Branch being analyzed
            analysis_id: Optional analysis ID (generated if not provided)

        Returns:
            PipelineResult with all analysis data
        """
        started_at = datetime.now(timezone.utc)
        analysis_id = analysis_id or str(uuid.uuid4())[:8]
        repo_path = Path(repo_path)
        repo_url = repo_url or str(repo_path)

        logger.info(f"[Pipeline] Starting analysis {analysis_id} for {repo_path}")

        errors = []
        metrics = None
        scoring_result = None
        reports = {}
        report_files = []

        try:
            # Stage 1: COLLECT
            logger.info(f"[Pipeline] Stage 1: Collecting metrics...")
            metrics = await metrics_aggregator.collect_all(
                repo_path=repo_path,
                analysis_id=analysis_id,
                repo_url=repo_url,
                branch=branch,
            )
            logger.info(f"[Pipeline] Collected {len(metrics.metrics)} metrics")

            # Stage 2: SCORE
            logger.info(f"[Pipeline] Stage 2: Calculating scores...")
            scoring_result = scoring_engine.calculate_scores(
                metrics=metrics,
                region_mode=self.config.region_mode,
            )
            logger.info(f"[Pipeline] Scoring complete: {scoring_result.verdict}")

            # Stage 3: STORE
            logger.info(f"[Pipeline] Stage 3: Storing results...")
            await self.store.save(metrics)
            logger.info(f"[Pipeline] Metrics stored")

            # Stage 4: REPORT
            if self.config.generate_reports:
                logger.info(f"[Pipeline] Stage 4: Generating reports...")
                reports, report_files = await self._generate_reports(
                    analysis_id=analysis_id,
                    metrics=metrics,
                    scoring_result=scoring_result,
                    repo_url=repo_url,
                    branch=branch,
                )
                logger.info(f"[Pipeline] Generated {len(reports)} reports")

            status = "completed"

        except Exception as e:
            logger.error(f"[Pipeline] Error: {e}", exc_info=True)
            errors.append(str(e))
            status = "failed"

        finished_at = datetime.now(timezone.utc)
        duration = (finished_at - started_at).total_seconds()

        result = PipelineResult(
            analysis_id=analysis_id,
            repo_url=repo_url,
            branch=branch,
            status=status,
            started_at=started_at,
            finished_at=finished_at,
            duration_seconds=duration,
            metrics=metrics,
            metrics_count=len(metrics.metrics) if metrics else 0,
            scoring_result=scoring_result,
            reports=reports,
            report_files=report_files,
            errors=errors,
        )

        logger.info(f"[Pipeline] Analysis {analysis_id} {status} in {duration:.1f}s")
        return result

    async def _generate_reports(
        self,
        analysis_id: str,
        metrics: MetricSet,
        scoring_result: ScoringResult,
        repo_url: str,
        branch: Optional[str],
    ) -> tuple:
        """Generate reports based on config."""
        reports = {}
        report_files = []

        # Build AnalysisReport for report builder
        analysis_report = AnalysisReport(
            analysis_id=analysis_id,
            repo_url=repo_url,
            branch=branch,
            analyzed_at=metrics.collected_at,
            repo_health=scoring_result.repo_health,
            tech_debt=scoring_result.tech_debt,
            product_level=scoring_result.product_level,
            complexity=scoring_result.complexity,
            forward_estimate=scoring_result.forward_estimate,
            historical_estimate=scoring_result.historical_estimate,
            tasks=scoring_result.tasks,
            structure_data=metrics.to_flat_dict(),
            static_metrics=metrics.to_flat_dict(),
        )

        # Generate requested reports
        for report_type in self.config.report_types:
            try:
                if report_type == "review":
                    content = report_builder.build_repo_review(analysis_report)
                elif report_type == "summary":
                    content = report_builder.build_repo_summary(analysis_report)
                elif report_type == "markdown":
                    content = report_builder.build_markdown(analysis_report)
                elif report_type == "json":
                    import json
                    content = json.dumps(report_builder.build_json(analysis_report), indent=2)
                else:
                    continue

                reports[report_type] = content

                # Save to storage
                file_path = await self.store.save_report(analysis_id, report_type, content)
                if file_path:
                    report_files.append(file_path)

            except Exception as e:
                logger.warning(f"Failed to generate {report_type} report: {e}")

        return reports, report_files

    async def run_batch(
        self,
        repos: List[Dict[str, Any]],
        parallel: bool = False,
    ) -> List[PipelineResult]:
        """
        Run analysis on multiple repositories.

        Args:
            repos: List of {"path": ..., "url": ..., "branch": ...}
            parallel: Run in parallel (default: sequential)

        Returns:
            List of PipelineResults
        """
        if parallel:
            tasks = [
                self.run(
                    repo_path=r["path"],
                    repo_url=r.get("url"),
                    branch=r.get("branch"),
                )
                for r in repos
            ]
            return await asyncio.gather(*tasks, return_exceptions=False)
        else:
            results = []
            for r in repos:
                result = await self.run(
                    repo_path=r["path"],
                    repo_url=r.get("url"),
                    branch=r.get("branch"),
                )
                results.append(result)
            return results


# Default pipeline instance
analysis_pipeline = AnalysisPipeline()


# Convenience function
async def analyze_repo(
    repo_path: str,
    repo_url: Optional[str] = None,
    branch: Optional[str] = None,
    region_mode: str = "EU_UA",
) -> PipelineResult:
    """
    Convenience function to analyze a repository.

    Usage:
        result = await analyze_repo("/path/to/repo")
        print(result.summary())
    """
    config = PipelineConfig(region_mode=region_mode)
    pipeline = AnalysisPipeline(config)
    return await pipeline.run(repo_path, repo_url, branch)
