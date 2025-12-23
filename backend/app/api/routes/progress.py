"""
Analysis progress WebSocket and REST endpoints.

Real-time progress tracking for repository analysis.
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional, Set
from enum import Enum

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from pydantic import BaseModel

router = APIRouter()
logger = logging.getLogger(__name__)


class AnalysisStage(str, Enum):
    """Analysis pipeline stages."""
    QUEUED = "queued"
    FETCHING = "fetching"
    COLLECTING = "collecting"
    SCORING = "scoring"
    STORING = "storing"
    REPORTING = "reporting"
    COMPLETED = "completed"
    FAILED = "failed"


class CollectorProgress(BaseModel):
    """Progress for individual collector."""
    name: str
    status: str  # pending, running, completed, failed
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metrics_collected: int = 0


class AnalysisProgress(BaseModel):
    """Full analysis progress state."""
    analysis_id: str
    stage: AnalysisStage
    stage_progress: float  # 0-100 for current stage
    overall_progress: float  # 0-100 total
    current_step: str
    collectors: Dict[str, CollectorProgress] = {}
    collectors_completed: int = 0
    collectors_total: int = 0
    started_at: Optional[datetime] = None
    estimated_remaining_seconds: Optional[int] = None
    error: Optional[str] = None


# Global progress store (in production, use Redis)
_progress_store: Dict[str, AnalysisProgress] = {}
_websocket_connections: Dict[str, Set[WebSocket]] = {}


# Stage weights for overall progress calculation
STAGE_WEIGHTS = {
    AnalysisStage.QUEUED: 0,
    AnalysisStage.FETCHING: 10,
    AnalysisStage.COLLECTING: 60,  # Most time spent here
    AnalysisStage.SCORING: 15,
    AnalysisStage.STORING: 10,
    AnalysisStage.REPORTING: 5,
    AnalysisStage.COMPLETED: 0,
}


def calculate_overall_progress(stage: AnalysisStage, stage_progress: float) -> float:
    """Calculate overall progress based on stage and stage progress."""
    stages = list(AnalysisStage)
    current_idx = stages.index(stage)

    # Sum completed stages
    completed_weight = sum(
        STAGE_WEIGHTS.get(stages[i], 0)
        for i in range(current_idx)
    )

    # Add current stage progress
    current_weight = STAGE_WEIGHTS.get(stage, 0)
    current_contribution = (stage_progress / 100) * current_weight

    return min(100, completed_weight + current_contribution)


class ProgressManager:
    """Manages analysis progress state."""

    def __init__(self):
        self._lock = asyncio.Lock()

    async def init_progress(self, analysis_id: str, collectors: list[str]) -> AnalysisProgress:
        """Initialize progress for new analysis."""
        async with self._lock:
            progress = AnalysisProgress(
                analysis_id=analysis_id,
                stage=AnalysisStage.QUEUED,
                stage_progress=0,
                overall_progress=0,
                current_step="Initializing...",
                collectors={
                    name: CollectorProgress(name=name, status="pending")
                    for name in collectors
                },
                collectors_total=len(collectors),
                started_at=datetime.utcnow(),
            )
            _progress_store[analysis_id] = progress
            await self._broadcast(analysis_id, progress)
            return progress

    async def update_stage(
        self,
        analysis_id: str,
        stage: AnalysisStage,
        current_step: str,
        stage_progress: float = 0,
    ) -> Optional[AnalysisProgress]:
        """Update analysis stage."""
        async with self._lock:
            progress = _progress_store.get(analysis_id)
            if not progress:
                return None

            progress.stage = stage
            progress.current_step = current_step
            progress.stage_progress = stage_progress
            progress.overall_progress = calculate_overall_progress(stage, stage_progress)

            # Estimate remaining time based on elapsed and progress
            if progress.started_at and progress.overall_progress > 5:
                elapsed = (datetime.utcnow() - progress.started_at).total_seconds()
                estimated_total = elapsed / (progress.overall_progress / 100)
                progress.estimated_remaining_seconds = int(estimated_total - elapsed)

            await self._broadcast(analysis_id, progress)
            return progress

    async def update_collector(
        self,
        analysis_id: str,
        collector_name: str,
        status: str,
        metrics_collected: int = 0,
    ) -> Optional[AnalysisProgress]:
        """Update collector progress."""
        async with self._lock:
            progress = _progress_store.get(analysis_id)
            if not progress:
                return None

            if collector_name in progress.collectors:
                collector = progress.collectors[collector_name]
                collector.status = status
                collector.metrics_collected = metrics_collected

                if status == "running" and not collector.started_at:
                    collector.started_at = datetime.utcnow()
                elif status in ("completed", "failed"):
                    collector.completed_at = datetime.utcnow()

                # Update counts
                progress.collectors_completed = sum(
                    1 for c in progress.collectors.values()
                    if c.status in ("completed", "failed")
                )

                # Update stage progress
                if progress.collectors_total > 0:
                    progress.stage_progress = (
                        progress.collectors_completed / progress.collectors_total * 100
                    )
                    progress.overall_progress = calculate_overall_progress(
                        progress.stage, progress.stage_progress
                    )

            await self._broadcast(analysis_id, progress)
            return progress

    async def set_error(self, analysis_id: str, error: str) -> Optional[AnalysisProgress]:
        """Set error state."""
        async with self._lock:
            progress = _progress_store.get(analysis_id)
            if not progress:
                return None

            progress.stage = AnalysisStage.FAILED
            progress.error = error
            progress.current_step = f"Failed: {error}"

            await self._broadcast(analysis_id, progress)
            return progress

    async def complete(self, analysis_id: str) -> Optional[AnalysisProgress]:
        """Mark analysis as completed."""
        async with self._lock:
            progress = _progress_store.get(analysis_id)
            if not progress:
                return None

            progress.stage = AnalysisStage.COMPLETED
            progress.stage_progress = 100
            progress.overall_progress = 100
            progress.current_step = "Analysis completed"
            progress.estimated_remaining_seconds = 0

            await self._broadcast(analysis_id, progress)
            return progress

    def get_progress(self, analysis_id: str) -> Optional[AnalysisProgress]:
        """Get current progress."""
        return _progress_store.get(analysis_id)

    async def _broadcast(self, analysis_id: str, progress: AnalysisProgress):
        """Broadcast progress to all connected WebSockets."""
        connections = _websocket_connections.get(analysis_id, set())
        if not connections:
            return

        message = progress.model_dump_json()
        dead_connections = set()

        for ws in connections:
            try:
                await ws.send_text(message)
            except Exception:
                dead_connections.add(ws)

        # Clean up dead connections
        for ws in dead_connections:
            connections.discard(ws)


# Global progress manager
progress_manager = ProgressManager()


@router.websocket("/ws/analysis/{analysis_id}/progress")
async def websocket_progress(websocket: WebSocket, analysis_id: str):
    """
    WebSocket endpoint for real-time analysis progress.

    Connect to receive progress updates for a specific analysis.
    """
    await websocket.accept()

    # Register connection
    if analysis_id not in _websocket_connections:
        _websocket_connections[analysis_id] = set()
    _websocket_connections[analysis_id].add(websocket)

    logger.info(f"WebSocket connected for analysis {analysis_id}")

    try:
        # Send current progress immediately
        progress = progress_manager.get_progress(analysis_id)
        if progress:
            await websocket.send_text(progress.model_dump_json())
        else:
            # No progress yet, send initial state
            await websocket.send_json({
                "analysis_id": analysis_id,
                "stage": "queued",
                "stage_progress": 0,
                "overall_progress": 0,
                "current_step": "Waiting to start...",
            })

        # Keep connection alive
        while True:
            try:
                # Wait for client messages (ping/pong)
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                # Send heartbeat
                await websocket.send_text('{"type":"heartbeat"}')

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for analysis {analysis_id}")
    except Exception as e:
        logger.warning(f"WebSocket error for {analysis_id}: {e}")
    finally:
        # Unregister connection
        if analysis_id in _websocket_connections:
            _websocket_connections[analysis_id].discard(websocket)


@router.get("/analysis/{analysis_id}/progress")
async def get_analysis_progress(analysis_id: str):
    """
    Get current analysis progress (REST fallback).

    Use WebSocket for real-time updates.
    """
    progress = progress_manager.get_progress(analysis_id)
    if not progress:
        return {
            "analysis_id": analysis_id,
            "stage": "unknown",
            "overall_progress": 0,
            "current_step": "No progress data available",
        }
    return progress.model_dump()


# Default collectors list
DEFAULT_COLLECTORS = [
    "structure",
    "git",
    "static",
    "ci",
    "security",
    "coverage",
    "dependency",
    "duplication",
    "licenses",
    "dead_code",
    "git_analytics",
    "docker",
    "complexity",
]
