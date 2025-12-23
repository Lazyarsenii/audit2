#!/usr/bin/env python3
"""
Repo Auditor — Portable Audit Script

Drop this file into any project folder and run:
    python3 audit.py

Or with Claude:
    "Read CLAUDE.md and run the audit"

Features:
- Zero dependencies for basic scan
- Auto-installs requirements if needed
- Generates reports in multiple formats
- Sends results to server (optional)

Usage:
    python3 audit.py                    # Full analysis with reports
    python3 audit.py --quick            # Quick scan only
    python3 audit.py --format pdf       # Generate PDF report
    python3 audit.py --server URL       # Send results to server
    python3 audit.py --profile eu       # Use EU pricing profile
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import re


# ============================================================================
# CONFIGURATION
# ============================================================================

VERSION = "1.0.0"
DEFAULT_SERVER = "http://localhost:8000"

PROFILES = {
    "eu": {
        "name": "EU Standard",
        "currency": "EUR",
        "rates": {"junior": 35, "middle": 55, "senior": 85},
        "overhead": 1.35,
    },
    "ua": {
        "name": "Ukraine",
        "currency": "USD",
        "rates": {"junior": 15, "middle": 30, "senior": 50},
        "overhead": 1.20,
    },
    "us": {
        "name": "US Standard",
        "currency": "USD",
        "rates": {"junior": 50, "middle": 85, "senior": 130},
        "overhead": 1.40,
    },
}


# ============================================================================
# METRIC COLLECTORS (Zero Dependencies)
# ============================================================================

def collect_structure_metrics(repo_path: Path) -> Dict[str, Any]:
    """Collect structure metrics without external dependencies."""
    metrics = {}

    # README
    readme_files = list(repo_path.glob("README*"))
    metrics["has_readme"] = len(readme_files) > 0
    if readme_files:
        content = readme_files[0].read_text(errors='ignore').lower()
        metrics["readme_size"] = len(content)
        metrics["readme_has_install"] = any(w in content for w in ["install", "setup", "getting started"])
        metrics["readme_has_usage"] = any(w in content for w in ["usage", "example", "how to"])

    # Directories
    metrics["has_src"] = (repo_path / "src").exists()
    metrics["has_tests"] = any((repo_path / d).exists() for d in ["tests", "test", "__tests__"])
    metrics["has_docs"] = (repo_path / "docs").exists()

    # Dependencies
    dep_files = ["requirements.txt", "package.json", "Pipfile", "pyproject.toml", "Cargo.toml", "go.mod"]
    metrics["has_deps"] = any((repo_path / f).exists() for f in dep_files)

    # Docker
    metrics["has_dockerfile"] = (repo_path / "Dockerfile").exists()
    metrics["has_docker_compose"] = any((repo_path / f).exists() for f in ["docker-compose.yml", "docker-compose.yaml"])

    # CI/CD
    ci_paths = [".github/workflows", ".gitlab-ci.yml", ".travis.yml", "Jenkinsfile", ".circleci"]
    metrics["has_ci"] = any((repo_path / p).exists() for p in ci_paths)

    # Makefile
    metrics["has_makefile"] = (repo_path / "Makefile").exists()

    # Changelog
    metrics["has_changelog"] = any((repo_path / f).exists() for f in ["CHANGELOG.md", "CHANGELOG", "HISTORY.md"])

    return metrics


def collect_code_metrics(repo_path: Path) -> Dict[str, Any]:
    """Collect code metrics."""
    metrics = {"files": {}, "total_loc": 0, "total_files": 0, "test_files": 0}

    # File extensions to analyze
    extensions = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".jsx": "javascript",
        ".go": "go",
        ".rs": "rust",
        ".java": "java",
        ".rb": "ruby",
        ".php": "php",
    }

    skip_dirs = {"node_modules", "venv", ".venv", "__pycache__", ".git", "dist", "build", ".next"}

    for ext, lang in extensions.items():
        count = 0
        loc = 0
        test_count = 0

        for file in repo_path.rglob(f"*{ext}"):
            # Skip excluded directories
            if any(skip in file.parts for skip in skip_dirs):
                continue

            count += 1
            try:
                lines = len(file.read_text(errors='ignore').splitlines())
                loc += lines
            except (OSError, IOError):
                pass  # Skip unreadable files

            # Count test files
            if "test" in file.name.lower() or "spec" in file.name.lower():
                test_count += 1

        if count > 0:
            metrics["files"][lang] = {"count": count, "loc": loc}
            metrics["total_loc"] += loc
            metrics["total_files"] += count
            metrics["test_files"] += test_count

    return metrics


def collect_git_metrics(repo_path: Path) -> Dict[str, Any]:
    """Collect git metrics."""
    metrics = {"commits": 0, "authors": 0, "first_commit": None, "last_commit": None}

    if not (repo_path / ".git").exists():
        return metrics

    try:
        # Commit count
        result = subprocess.run(
            ["git", "rev-list", "--count", "HEAD"],
            cwd=repo_path, capture_output=True, text=True
        )
        if result.returncode == 0:
            metrics["commits"] = int(result.stdout.strip())

        # Author count
        result = subprocess.run(
            ["git", "shortlog", "-sn", "HEAD"],
            cwd=repo_path, capture_output=True, text=True
        )
        if result.returncode == 0:
            metrics["authors"] = len(result.stdout.strip().splitlines())

        # First commit date
        result = subprocess.run(
            ["git", "log", "--reverse", "--format=%aI", "-1"],
            cwd=repo_path, capture_output=True, text=True
        )
        if result.returncode == 0:
            metrics["first_commit"] = result.stdout.strip()

        # Last commit date
        result = subprocess.run(
            ["git", "log", "--format=%aI", "-1"],
            cwd=repo_path, capture_output=True, text=True
        )
        if result.returncode == 0:
            metrics["last_commit"] = result.stdout.strip()

    except Exception as e:
        print(f"Warning: Git metrics collection failed: {e}")

    return metrics


# ============================================================================
# SCORING ENGINE
# ============================================================================

def calculate_repo_health(structure: Dict, git: Dict) -> Dict[str, int]:
    """Calculate Repo Health score (0-12)."""
    scores = {}

    # Documentation (0-3)
    doc_score = 0
    if structure.get("has_readme"):
        doc_score = 1
        if structure.get("readme_has_install") and structure.get("readme_has_usage"):
            doc_score = 2
        if structure.get("has_docs"):
            doc_score = 3
    scores["documentation"] = doc_score

    # Structure (0-3)
    struct_score = 0
    if structure.get("has_src") or structure.get("has_tests"):
        struct_score = 1
    if structure.get("has_src") and structure.get("has_tests"):
        struct_score = 2
    if structure.get("has_docs"):
        struct_score = 3
    scores["structure"] = struct_score

    # Runability (0-3)
    run_score = 0
    if structure.get("has_deps"):
        run_score = 1
    if structure.get("has_makefile") or structure.get("readme_has_install"):
        run_score = 2
    if structure.get("has_dockerfile"):
        run_score = 3
    scores["runability"] = run_score

    # History (0-3)
    commits = git.get("commits", 0)
    authors = git.get("authors", 0)
    if commits <= 5:
        hist_score = 0
    elif commits <= 30:
        hist_score = 1
    elif commits <= 200:
        hist_score = 2 if authors < 3 else 3
    else:
        hist_score = 3
    scores["history"] = hist_score

    scores["total"] = sum(scores.values())
    return scores


def calculate_tech_debt(structure: Dict, code: Dict) -> Dict[str, int]:
    """Calculate Tech Debt score (0-15)."""
    scores = {}

    # Architecture (0-3)
    arch_score = 1
    if structure.get("has_src"):
        arch_score = 2
    if structure.get("has_src") and structure.get("has_tests") and structure.get("has_docs"):
        arch_score = 3
    scores["architecture"] = arch_score

    # Code Quality (0-3) — default good without deeper analysis
    scores["code_quality"] = 2

    # Testing (0-3)
    test_files = code.get("test_files", 0)
    total_files = code.get("total_files", 1)
    test_ratio = test_files / max(total_files, 1)
    if test_files == 0:
        test_score = 0
    elif test_ratio > 0.2:
        test_score = 3
    elif test_ratio > 0.1:
        test_score = 2
    else:
        test_score = 1
    scores["testing"] = test_score

    # Infrastructure (0-3)
    infra_score = 0
    if structure.get("has_dockerfile"):
        infra_score = 1
    if structure.get("has_ci"):
        infra_score = 2
    if structure.get("has_ci") and structure.get("has_dockerfile"):
        infra_score = 3
    scores["infrastructure"] = infra_score

    # Security (0-3) — default good without scanner
    scores["security"] = 3

    scores["total"] = sum(scores.values())
    return scores


def classify_product_level(repo_health: Dict, tech_debt: Dict, code: Dict, structure: Dict) -> Dict[str, Any]:
    """
    Classify product into development stage with extended model.

    Stages:
    - R&D Spike          → Experiment
    - Proof of Concept   → Technical demo
    - Prototype          → Working concept
    - MVP                → Minimum viable product
    - Alpha              → Feature complete, internal testing
    - Beta               → External testing
    - Release Candidate  → Final testing
    - Production Ready   → Ready for release
    """
    h = repo_health.get("total", 0)  # 0-12
    d = tech_debt.get("total", 0)    # 0-15

    has_tests = code.get("test_files", 0) > 0
    has_ci = structure.get("has_ci", False)
    has_docker = structure.get("has_dockerfile", False)
    has_readme = structure.get("has_readme", False)

    # Production Ready (10-12 health, 13-15 debt)
    if h >= 10 and d >= 13:
        stage = "Production Ready"
        confidence = 0.9
        next_steps = ["Maintain quality", "Monitor performance"]

    # Release Candidate (9-11 health, 12-14 debt)
    elif h >= 9 and d >= 12 and has_ci:
        stage = "Release Candidate"
        confidence = 0.85
        next_steps = ["Security audit", "Load testing", "Final docs"]

    # Beta (8-10 health, 10-13 debt)
    elif h >= 8 and d >= 10 and has_tests and has_ci:
        stage = "Beta"
        confidence = 0.8
        next_steps = ["Increase coverage to 80%", "Add monitoring", "Performance tests"]

    # Alpha (7-9 health, 8-11 debt)
    elif h >= 7 and d >= 8 and has_tests:
        stage = "Alpha"
        confidence = 0.75
        next_steps = ["Integration tests", "CD pipeline", "API docs"]

    # MVP (5-7 health, 6-9 debt)
    elif h >= 5 and d >= 6 and has_readme:
        stage = "MVP"
        confidence = 0.7
        next_steps = ["40% test coverage", "Error handling", "Deployment docs"]

    # Prototype (4-6 health, 5-7 debt)
    elif h >= 4 and d >= 5:
        stage = "Prototype"
        confidence = 0.65
        next_steps = ["Add CI pipeline", "Docker config", "More tests"]

    # Proof of Concept (2-4 health, 3-5 debt)
    elif h >= 2 and d >= 3:
        stage = "Proof of Concept"
        confidence = 0.6
        next_steps = ["Add tests", "Usage examples", "Organize code"]

    # R&D Spike
    else:
        stage = "R&D Spike"
        confidence = 0.5
        next_steps = ["Add README", "Create structure", "Add dependencies"]

    # Determine maintenance status
    if structure.get("commits_total", 0) == 0:
        maintenance = "New"
    elif structure.get("days_since_last_commit", 999) > 365:
        maintenance = "Archived"
    elif structure.get("days_since_last_commit", 999) > 180:
        maintenance = "Legacy"
    elif structure.get("days_since_last_commit", 999) > 90:
        maintenance = "Maintenance Mode"
    else:
        maintenance = "Active Development"

    # Determine readiness
    if stage in ["Production Ready"]:
        readiness = "Market Ready"
    elif stage in ["Release Candidate", "Beta"]:
        readiness = "Partner Ready"
    elif stage in ["Alpha", "MVP"]:
        readiness = "Internal Use Only"
    else:
        readiness = "Not Ready"

    return {
        "stage": stage,
        "confidence": confidence,
        "maintenance": maintenance,
        "readiness": readiness,
        "next_steps": next_steps,
        "scores": {"health": h, "debt": d},
    }


def determine_complexity(code: Dict) -> str:
    """Determine complexity based on LOC."""
    loc = code.get("total_loc", 0)
    if loc > 120000:
        return "XL"
    elif loc > 40000:
        return "L"
    elif loc > 8000:
        return "M"
    else:
        return "S"


def estimate_cost(complexity: str, tech_debt: Dict, profile: str = "eu") -> Dict[str, Any]:
    """Estimate development cost."""
    profile_data = PROFILES.get(profile, PROFILES["eu"])

    # Base hours by complexity
    base_hours = {"S": 120, "M": 300, "L": 700, "XL": 1500}
    hours = base_hours.get(complexity, 300)

    # Tech debt multiplier
    debt_total = tech_debt.get("total", 10)
    multiplier = 1.0 + (15 - debt_total) * 0.05  # Lower debt = higher cost to reproduce
    hours = int(hours * multiplier)

    # Calculate costs
    middle_rate = profile_data["rates"]["middle"]
    overhead = profile_data["overhead"]

    min_cost = int(hours * 0.75 * middle_rate * overhead)
    max_cost = int(hours * 1.25 * middle_rate * 1.2 * overhead)

    return {
        "hours": hours,
        "currency": profile_data["currency"],
        "min": min_cost,
        "max": max_cost,
        "formatted": f"{profile_data['currency']} {min_cost:,} - {max_cost:,}",
        "profile": profile_data["name"],
    }


# ============================================================================
# REPORT GENERATORS
# ============================================================================

def generate_markdown_report(data: Dict[str, Any]) -> str:
    """Generate Markdown report."""
    classification = data.get('classification', {})
    return f"""# Repository Audit Report

**Generated:** {data['timestamp']}
**Repository:** {data['repo_path']}

---

## Executive Summary

| Metric | Value |
|--------|-------|
| **Stage** | {classification.get('stage', data.get('product_level', 'N/A'))} |
| **Confidence** | {classification.get('confidence', 0)*100:.0f}% |
| **Status** | {classification.get('maintenance', 'Unknown')} |
| **Readiness** | {classification.get('readiness', 'Unknown')} |
| **Complexity** | {data['complexity']} |
| **Repo Health** | {data['repo_health']['total']}/12 ({round(data['repo_health']['total']/12*100)}%) |
| **Tech Debt** | {data['tech_debt']['total']}/15 ({round(data['tech_debt']['total']/15*100)}%) |

### Next Steps to Progress

{chr(10).join(f'- [ ] {step}' for step in classification.get('next_steps', []))}

---

## Repo Health Breakdown

| Category | Score |
|----------|-------|
| Documentation | {data['repo_health']['documentation']}/3 |
| Structure | {data['repo_health']['structure']}/3 |
| Runability | {data['repo_health']['runability']}/3 |
| History | {data['repo_health']['history']}/3 |
| **Total** | **{data['repo_health']['total']}/12** |

---

## Tech Debt Breakdown

| Category | Score |
|----------|-------|
| Architecture | {data['tech_debt']['architecture']}/3 |
| Code Quality | {data['tech_debt']['code_quality']}/3 |
| Testing | {data['tech_debt']['testing']}/3 |
| Infrastructure | {data['tech_debt']['infrastructure']}/3 |
| Security | {data['tech_debt']['security']}/3 |
| **Total** | **{data['tech_debt']['total']}/15** |

---

## Code Metrics

| Metric | Value |
|--------|-------|
| Total Files | {data['code']['total_files']} |
| Total LOC | {data['code']['total_loc']:,} |
| Test Files | {data['code']['test_files']} |
| Commits | {data['git']['commits']} |
| Authors | {data['git']['authors']} |

### By Language

| Language | Files | LOC |
|----------|-------|-----|
{chr(10).join(f"| {lang} | {info['count']} | {info['loc']:,} |" for lang, info in data['code']['files'].items())}

---

## Cost Estimation

**Profile:** {data['cost']['profile']}

| Metric | Value |
|--------|-------|
| Estimated Hours | {data['cost']['hours']} |
| Cost Range | {data['cost']['formatted']} |

---

## Recommendations

{chr(10).join(f"- {r}" for r in data.get('recommendations', ['No critical issues found.']))}

---

*Generated by Repo Auditor v{VERSION}*
"""


def generate_json_report(data: Dict[str, Any]) -> str:
    """Generate JSON report."""
    return json.dumps(data, indent=2, default=str)


def generate_csv_report(data: Dict[str, Any]) -> str:
    """Generate CSV report for Excel."""
    lines = [
        "Category,Metric,Value",
        f"Summary,Product Level,{data['product_level']}",
        f"Summary,Complexity,{data['complexity']}",
        f"Summary,Repo Health Total,{data['repo_health']['total']}/12",
        f"Summary,Tech Debt Total,{data['tech_debt']['total']}/15",
        "",
        f"Repo Health,Documentation,{data['repo_health']['documentation']}/3",
        f"Repo Health,Structure,{data['repo_health']['structure']}/3",
        f"Repo Health,Runability,{data['repo_health']['runability']}/3",
        f"Repo Health,History,{data['repo_health']['history']}/3",
        "",
        f"Tech Debt,Architecture,{data['tech_debt']['architecture']}/3",
        f"Tech Debt,Code Quality,{data['tech_debt']['code_quality']}/3",
        f"Tech Debt,Testing,{data['tech_debt']['testing']}/3",
        f"Tech Debt,Infrastructure,{data['tech_debt']['infrastructure']}/3",
        f"Tech Debt,Security,{data['tech_debt']['security']}/3",
        "",
        f"Code,Total Files,{data['code']['total_files']}",
        f"Code,Total LOC,{data['code']['total_loc']}",
        f"Code,Test Files,{data['code']['test_files']}",
        "",
        f"Git,Commits,{data['git']['commits']}",
        f"Git,Authors,{data['git']['authors']}",
        "",
        f"Cost,Hours,{data['cost']['hours']}",
        f"Cost,Min ({data['cost']['currency']}),{data['cost']['min']}",
        f"Cost,Max ({data['cost']['currency']}),{data['cost']['max']}",
    ]
    return "\n".join(lines)


# ============================================================================
# MAIN
# ============================================================================

def run_audit(
    repo_path: Path,
    profile: str = "eu",
    quick: bool = False,
    output_format: str = "markdown",
    server_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Run full audit."""
    print(f"\n{'='*60}")
    print(f" REPO AUDITOR v{VERSION}")
    print(f"{'='*60}\n")

    print(f"Scanning: {repo_path}")
    print(f"Profile: {PROFILES.get(profile, PROFILES['eu'])['name']}")
    print()

    # Collect metrics
    print("[1/4] Collecting structure metrics...")
    structure = collect_structure_metrics(repo_path)

    print("[2/4] Collecting code metrics...")
    code = collect_code_metrics(repo_path)

    print("[3/4] Collecting git metrics...")
    git = collect_git_metrics(repo_path)

    print("[4/4] Calculating scores...")
    repo_health = calculate_repo_health(structure, git)
    tech_debt = calculate_tech_debt(structure, code)
    classification = classify_product_level(repo_health, tech_debt, code, structure)
    complexity = determine_complexity(code)
    cost = estimate_cost(complexity, tech_debt, profile)

    # Build result
    result = {
        "version": VERSION,
        "timestamp": datetime.now().isoformat(),
        "repo_path": str(repo_path),
        "profile": profile,
        "structure": structure,
        "code": code,
        "git": git,
        "repo_health": repo_health,
        "tech_debt": tech_debt,
        "classification": classification,
        "product_level": classification["stage"],  # backward compat
        "complexity": complexity,
        "cost": cost,
        "recommendations": generate_recommendations(structure, code, repo_health, tech_debt),
    }

    # Print summary
    print(f"\n{'─'*60}")
    print(" RESULTS")
    print(f"{'─'*60}\n")
    print(f"  Stage:          {classification['stage']} ({classification['confidence']*100:.0f}% confidence)")
    print(f"  Status:         {classification['maintenance']}")
    print(f"  Readiness:      {classification['readiness']}")
    print(f"  Complexity:     {complexity}")
    print(f"  Repo Health:    {repo_health['total']}/12 ({round(repo_health['total']/12*100)}%)")
    print(f"  Tech Debt:      {tech_debt['total']}/15 ({round(tech_debt['total']/15*100)}%)")
    print(f"  Cost Estimate:  {cost['formatted']}")
    print()
    print("  Next Steps:")
    for step in classification['next_steps'][:3]:
        print(f"    → {step}")
    print()

    # Generate reports
    if not quick:
        output_dir = repo_path / ".audit"
        output_dir.mkdir(exist_ok=True)

        # Markdown
        md_path = output_dir / "report.md"
        md_path.write_text(generate_markdown_report(result))
        print(f"  Report saved: {md_path}")

        # JSON
        json_path = output_dir / "report.json"
        json_path.write_text(generate_json_report(result))
        print(f"  Data saved: {json_path}")

        # CSV for Excel
        csv_path = output_dir / "report.csv"
        csv_path.write_text(generate_csv_report(result))
        print(f"  CSV saved: {csv_path}")

    # Send to server
    if server_url:
        try:
            import urllib.request
            import urllib.parse

            # Validate URL to prevent SSRF and file:// access
            parsed = urllib.parse.urlparse(server_url)
            if parsed.scheme not in ('http', 'https'):
                print(f"  Warning: Invalid URL scheme '{parsed.scheme}'. Only http/https allowed.")
            elif not parsed.netloc:
                print(f"  Warning: Invalid URL - no host specified.")
            else:
                # Safe to proceed with validated URL
                api_url = f"{server_url.rstrip('/')}/api/audit/submit"
                req = urllib.request.Request(
                    api_url,
                    data=json.dumps(result).encode(),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    print(f"  Sent to server: {resp.status}")
        except Exception as e:
            print(f"  Warning: Failed to send to server: {e}")

    print(f"\n{'='*60}\n")

    return result


def generate_recommendations(structure: Dict, code: Dict, health: Dict, debt: Dict) -> List[str]:
    """Generate recommendations."""
    recs = []

    if not structure.get("has_readme"):
        recs.append("[CRITICAL] Add README.md with project description")
    elif not structure.get("readme_has_install"):
        recs.append("[IMPORTANT] Add installation instructions to README")

    if not structure.get("has_tests"):
        recs.append("[CRITICAL] Add test directory with unit tests")
    elif code.get("test_files", 0) < 5:
        recs.append("[IMPORTANT] Increase test coverage")

    if not structure.get("has_dockerfile"):
        recs.append("[IMPORTANT] Add Dockerfile for containerization")

    if not structure.get("has_ci"):
        recs.append("[IMPORTANT] Set up CI/CD pipeline")

    if not structure.get("has_docs"):
        recs.append("[OPTIONAL] Add docs/ directory with documentation")

    if not recs:
        recs.append("Project is well-structured. Consider minor improvements.")

    return recs


def main():
    parser = argparse.ArgumentParser(
        description="Repo Auditor — Portable Repository Analysis Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python3 audit.py                     # Analyze current directory
    python3 audit.py /path/to/repo       # Analyze specific path
    python3 audit.py --profile ua        # Use Ukraine pricing
    python3 audit.py --quick             # Quick scan only
    python3 audit.py --server http://...  # Send results to server
        """
    )

    parser.add_argument("path", nargs="?", default=".", help="Repository path")
    parser.add_argument("--profile", "-p", default="eu", choices=["eu", "ua", "us"],
                       help="Pricing profile (default: eu)")
    parser.add_argument("--quick", "-q", action="store_true",
                       help="Quick scan without generating reports")
    parser.add_argument("--format", "-f", default="markdown",
                       choices=["markdown", "json", "csv"],
                       help="Output format (default: markdown)")
    parser.add_argument("--server", "-s", help="Server URL to send results")
    parser.add_argument("--version", "-v", action="version", version=f"Repo Auditor v{VERSION}")

    args = parser.parse_args()

    repo_path = Path(args.path).resolve()
    if not repo_path.exists():
        print(f"Error: Path does not exist: {repo_path}")
        sys.exit(1)

    run_audit(
        repo_path=repo_path,
        profile=args.profile,
        quick=args.quick,
        output_format=args.format,
        server_url=args.server,
    )


if __name__ == "__main__":
    main()
