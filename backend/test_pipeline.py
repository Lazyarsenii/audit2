#!/usr/bin/env python3
"""
Test script for the unified analysis pipeline.

Usage:
    python test_pipeline.py /path/to/repo
"""
import asyncio
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.metrics.pipeline import analyze_repo, AnalysisPipeline, PipelineConfig


async def main():
    # Default to AI-Platform-ISO
    repo_path = sys.argv[1] if len(sys.argv) > 1 else "/Users/maksymdemchenko/AI-Platform-ISO-main"

    print(f"\n{'='*70}")
    print(f" REPO AUDITOR — UNIFIED PIPELINE TEST")
    print(f"{'='*70}")
    print(f"\n Repository: {repo_path}")
    print(f" Starting analysis...\n")

    # Run the pipeline
    result = await analyze_repo(
        repo_path=repo_path,
        repo_url=f"file://{repo_path}",
        region_mode="EU_UA",
    )

    # Print full summary
    print(result.summary())

    # Print metrics breakdown
    if result.metrics:
        print(f"\n{'─'*70}")
        print(f" COLLECTED METRICS ({result.metrics_count} total)")
        print(f"{'─'*70}\n")

        # Group by category
        by_category = {}
        for m in result.metrics.metrics:
            cat = m.category.value
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(m)

        for cat, metrics in sorted(by_category.items()):
            print(f" [{cat.upper()}]")
            for m in metrics:
                value_str = str(m.value)
                if isinstance(m.value, bool):
                    value_str = "Yes" if m.value else "No"
                elif isinstance(m.value, float):
                    value_str = f"{m.value:.2f}"
                print(f"   {m.name}: {value_str}")
            print()

    # Print tasks
    if result.scoring_result and result.scoring_result.tasks:
        print(f"\n{'─'*70}")
        print(f" IMPROVEMENT TASKS ({len(result.scoring_result.tasks)})")
        print(f"{'─'*70}\n")

        for i, task in enumerate(result.scoring_result.tasks[:10], 1):
            priority = task.priority.value if hasattr(task.priority, 'value') else task.priority
            category = task.category.value if hasattr(task.category, 'value') else task.category
            print(f" {i}. [{priority}] {task.title}")
            print(f"    Category: {category}")
            if hasattr(task, 'estimate_hours') and task.estimate_hours:
                print(f"    Estimate: {task.estimate_hours}h")
            print()

    # Print report paths
    if result.report_files:
        print(f"\n{'─'*70}")
        print(f" GENERATED REPORTS")
        print(f"{'─'*70}\n")
        for path in result.report_files:
            print(f"   - {path}")

    # Print any errors
    if result.errors:
        print(f"\n{'─'*70}")
        print(f" ERRORS")
        print(f"{'─'*70}\n")
        for err in result.errors:
            print(f"   [ERROR] {err}")

    print(f"\n{'='*70}")
    print(f" Analysis complete in {result.duration_seconds:.1f}s")
    print(f"{'='*70}\n")

    return result


if __name__ == "__main__":
    result = asyncio.run(main())
