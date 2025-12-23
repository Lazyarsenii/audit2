"""
Metrics module — Datadog-style metrics collection and processing.

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

Components:
- schema: Unified metric format (Metric, MetricSet, MetricNames)
- collectors: Data collection agents (Structure, Git, Static, CI)
- storage: Metric persistence (JSON, SQLite backends)
- scoring_engine: Scoring logic (Repo Health, Tech Debt, Classification)
- pipeline: End-to-end analysis orchestration
"""
from .schema import (
    Metric,
    MetricSet,
    MetricType,
    MetricSource,
    MetricCategory,
    MetricLabel,
    MetricNames,
)
from .pipeline import (
    AnalysisPipeline,
    PipelineConfig,
    PipelineResult,
    analyze_repo,
)
from .storage import MetricsStore, metrics_store
from .scoring_engine import ScoringEngine, ScoringResult, scoring_engine

__all__ = [
    # Schema
    "Metric",
    "MetricSet",
    "MetricType",
    "MetricSource",
    "MetricCategory",
    "MetricLabel",
    "MetricNames",
    # Pipeline
    "AnalysisPipeline",
    "PipelineConfig",
    "PipelineResult",
    "analyze_repo",
    # Storage
    "MetricsStore",
    "metrics_store",
    # Scoring
    "ScoringEngine",
    "ScoringResult",
    "scoring_engine",
]
