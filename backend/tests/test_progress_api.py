"""
Tests for Analysis Progress API.

Tests the progress tracking WebSocket and REST endpoints.
"""
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.api.routes.progress import (
    progress_manager,
    ProgressManager,
    AnalysisStage,
    AnalysisProgress,
    CollectorProgress,
    calculate_overall_progress,
    DEFAULT_COLLECTORS,
)


client = TestClient(app)


class TestProgressCalculation:
    """Test progress calculation utilities."""

    def test_calculate_overall_progress_queued(self):
        """Queued stage should be 0%."""
        result = calculate_overall_progress(AnalysisStage.QUEUED, 0)
        assert result == 0

    def test_calculate_overall_progress_fetching(self):
        """Fetching at 50% should give partial progress."""
        result = calculate_overall_progress(AnalysisStage.FETCHING, 50)
        assert 0 < result < 100

    def test_calculate_overall_progress_collecting(self):
        """Collecting stage has most weight (60%)."""
        # At start of collecting
        result_start = calculate_overall_progress(AnalysisStage.COLLECTING, 0)
        # At end of collecting
        result_end = calculate_overall_progress(AnalysisStage.COLLECTING, 100)
        # Should have significant progress
        assert result_start >= 10  # After fetching
        assert result_end >= 70   # Collecting is 60% of work

    def test_calculate_overall_progress_completed(self):
        """Completed should cap at 100%."""
        result = calculate_overall_progress(AnalysisStage.COMPLETED, 100)
        assert result == 100


class TestProgressManager:
    """Test ProgressManager class."""

    @pytest.fixture
    def manager(self):
        """Create fresh progress manager for each test."""
        return ProgressManager()

    @pytest.mark.asyncio
    async def test_init_progress(self, manager):
        """Test initializing progress for new analysis."""
        analysis_id = "test-analysis-123"
        collectors = ["structure", "git", "security"]

        progress = await manager.init_progress(analysis_id, collectors)

        assert progress.analysis_id == analysis_id
        assert progress.stage == AnalysisStage.QUEUED
        assert progress.overall_progress == 0
        assert progress.collectors_total == 3
        assert "structure" in progress.collectors
        assert progress.collectors["structure"].status == "pending"

    @pytest.mark.asyncio
    async def test_update_stage(self, manager):
        """Test updating analysis stage."""
        analysis_id = "test-analysis-456"
        await manager.init_progress(analysis_id, ["collector1"])

        progress = await manager.update_stage(
            analysis_id,
            AnalysisStage.FETCHING,
            "Cloning repository...",
            50
        )

        assert progress.stage == AnalysisStage.FETCHING
        assert progress.current_step == "Cloning repository..."
        assert progress.stage_progress == 50
        assert progress.overall_progress > 0

    @pytest.mark.asyncio
    async def test_update_collector(self, manager):
        """Test updating collector status."""
        analysis_id = "test-analysis-789"
        await manager.init_progress(analysis_id, ["structure", "git"])

        # Start collector
        progress = await manager.update_collector(
            analysis_id, "structure", "running", 0
        )
        assert progress.collectors["structure"].status == "running"
        assert progress.collectors["structure"].started_at is not None

        # Complete collector
        progress = await manager.update_collector(
            analysis_id, "structure", "completed", 5
        )
        assert progress.collectors["structure"].status == "completed"
        assert progress.collectors["structure"].metrics_collected == 5
        assert progress.collectors_completed == 1

    @pytest.mark.asyncio
    async def test_set_error(self, manager):
        """Test setting error state."""
        analysis_id = "test-analysis-error"
        await manager.init_progress(analysis_id, ["collector1"])

        progress = await manager.set_error(analysis_id, "Something went wrong")

        assert progress.stage == AnalysisStage.FAILED
        assert progress.error == "Something went wrong"

    @pytest.mark.asyncio
    async def test_complete(self, manager):
        """Test marking analysis as completed."""
        analysis_id = "test-analysis-complete"
        await manager.init_progress(analysis_id, ["collector1"])

        progress = await manager.complete(analysis_id)

        assert progress.stage == AnalysisStage.COMPLETED
        assert progress.overall_progress == 100
        assert progress.estimated_remaining_seconds == 0

    @pytest.mark.asyncio
    async def test_get_progress_nonexistent(self, manager):
        """Test getting progress for non-existent analysis."""
        result = manager.get_progress("nonexistent-id")
        assert result is None


class TestProgressRestAPI:
    """Test REST API endpoints."""

    def test_get_progress_nonexistent(self):
        """Test getting progress for non-existent analysis returns default."""
        response = client.get(
            "/api/analysis/nonexistent-id/progress",
            headers={"X-API-Key": "repoaudit"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["stage"] == "unknown"
        assert data["overall_progress"] == 0


class TestAnalysisStage:
    """Test AnalysisStage enum."""

    def test_stage_values(self):
        """Test all stages have correct string values."""
        assert AnalysisStage.QUEUED.value == "queued"
        assert AnalysisStage.FETCHING.value == "fetching"
        assert AnalysisStage.COLLECTING.value == "collecting"
        assert AnalysisStage.SCORING.value == "scoring"
        assert AnalysisStage.STORING.value == "storing"
        assert AnalysisStage.REPORTING.value == "reporting"
        assert AnalysisStage.COMPLETED.value == "completed"
        assert AnalysisStage.FAILED.value == "failed"


class TestDefaultCollectors:
    """Test default collectors list."""

    def test_default_collectors_not_empty(self):
        """Default collectors should have entries."""
        assert len(DEFAULT_COLLECTORS) > 0

    def test_default_collectors_has_core(self):
        """Should include core collectors."""
        assert "structure" in DEFAULT_COLLECTORS
        assert "git" in DEFAULT_COLLECTORS
        assert "security" in DEFAULT_COLLECTORS


class TestCollectorProgress:
    """Test CollectorProgress model."""

    def test_collector_progress_defaults(self):
        """Test default values."""
        progress = CollectorProgress(name="test", status="pending")
        assert progress.name == "test"
        assert progress.status == "pending"
        assert progress.started_at is None
        assert progress.completed_at is None
        assert progress.metrics_collected == 0


class TestAnalysisProgressModel:
    """Test AnalysisProgress model."""

    def test_analysis_progress_creation(self):
        """Test creating AnalysisProgress model."""
        progress = AnalysisProgress(
            analysis_id="test-123",
            stage=AnalysisStage.COLLECTING,
            stage_progress=50,
            overall_progress=35,
            current_step="Running security scan...",
            collectors_total=10,
        )
        assert progress.analysis_id == "test-123"
        assert progress.stage == AnalysisStage.COLLECTING
        assert progress.overall_progress == 35
