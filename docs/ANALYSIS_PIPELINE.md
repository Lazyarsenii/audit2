# Analysis Pipeline Overview

This document describes how the Auditor platform runs repository analysis, how metrics are collected, and how scores and reports are produced.

## End-to-End Flow

1. **Fetch** – obtain repository source (local path or cloned remote) using `RepoFetcher`.
2. **Collect** – run metric collectors for structure, static code properties, dependencies, and history to build a unified `MetricSet`.
3. **Score** – apply the scoring engine to produce repository health, technical debt, product level, and complexity verdicts.
4. **Store** – persist metrics and scores through the configured `MetricsStore` backend (JSON by default).
5. **Report** – render human-readable and machine-readable reports through the report builder (Markdown/JSON outputs).

## Key Components

- **Repository acquisition**: `repo_fetcher.fetch` handles cloning or reusing an existing path and cleans up temporary clones after execution. It raises a `RepoFetchError` when cloning fails.
- **Pipeline orchestrator**: `AnalysisPipeline.run` coordinates metric collection, scoring, storage, and report rendering. The pipeline configuration controls region mode, report types, and storage backend selection.
- **Metric collectors**: the metrics aggregator composes results from individual analyzers (structure, static code stats, dependency counts) into a normalized `MetricSet` instance for downstream scoring.
- **Scoring engine**: calculates the Repo Health (documentation, structure, runability, history), Technical Debt (architecture, code quality, testing, infrastructure, security), product level, and complexity classifications. It also bundles cost estimates and improvement tasks.
- **Report builder**: converts pipeline outputs into review and summary reports while returning paths to the generated files for API responses.
- **Analysis runner**: `AnalysisRunner.run` wraps the pipeline for FastAPI routes and database persistence. It updates analysis status, saves metrics and tasks, and returns a compact summary payload for clients.

## Error Handling

- Repository acquisition failures propagate `RepoFetchError` and mark analyses as failed.
- Any pipeline exception triggers status updates to `failed`, commits the error message, and surfaces the error to the caller while still attempting repository cleanup.

## Outputs

- **Metrics**: normalized fields saved via the metrics store (JSON by default) for reuse in reports and API consumers.
- **Scores**: numerical health and debt scores plus qualitative product level and complexity verdicts.
- **Reports**: review and summary documents saved alongside the metrics; paths are returned in API responses.

## Related Documents

- Scoring rubric and cost estimation rules: [METHODOLOGY.md](./METHODOLOGY.md)
- High-level product documentation: [README.md](./README.md) and [USER_MANUAL.md](./USER_MANUAL.md)
