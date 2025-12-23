"""
Report Builder service.

Generates reports in various formats: Markdown, CSV, JSON.
Supports templates for:
- Individual repo reviews
- Partner reports (batch)
- Acts of completed work
"""
import csv
import io
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from app.core.scoring.repo_health import RepoHealthScore
from app.core.scoring.tech_debt import TechDebtScore
from app.core.scoring.product_level import ProductLevel, get_product_level_description
from app.core.scoring.complexity import Complexity, get_complexity_description
from app.services.cost_estimator import ForwardEstimate, HistoricalEstimate
from app.services.task_generator import GeneratedTask

logger = logging.getLogger(__name__)

# Template directory
TEMPLATE_DIR = Path(__file__).parent.parent / "templates"


@dataclass
class AnalysisReport:
    """Complete analysis report data."""
    analysis_id: str
    repo_url: str
    branch: Optional[str]
    analyzed_at: datetime
    repo_health: RepoHealthScore
    tech_debt: TechDebtScore
    product_level: ProductLevel
    complexity: Complexity
    forward_estimate: ForwardEstimate
    historical_estimate: HistoricalEstimate
    tasks: List[GeneratedTask]
    structure_data: Dict[str, Any]
    static_metrics: Dict[str, Any]


class ReportBuilder:
    """Builds reports in various formats."""

    def __init__(self):
        pass

    def build_markdown(self, report: AnalysisReport) -> str:
        """
        Build comprehensive Markdown report.

        Args:
            report: Complete analysis data

        Returns:
            Markdown string
        """
        lines = []

        # Header
        lines.append("# Repository Audit Report")
        lines.append("")
        lines.append(f"**Repository:** {report.repo_url}")
        lines.append(f"**Branch:** {report.branch or 'default'}")
        lines.append(f"**Analyzed:** {report.analyzed_at.strftime('%Y-%m-%d %H:%M UTC')}")
        lines.append(f"**Analysis ID:** `{report.analysis_id}`")
        lines.append("")

        # Executive Summary
        lines.append("## Executive Summary")
        lines.append("")
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        lines.append(f"| **Product Level** | {report.product_level.value} |")
        lines.append(f"| **Complexity** | {report.complexity.value} ({get_complexity_description(report.complexity)}) |")
        lines.append(f"| **Repo Health** | {report.repo_health.total}/12 |")
        lines.append(f"| **Tech Debt** | {report.tech_debt.total}/15 |")
        lines.append("")

        # Cost Summary
        fwd = report.forward_estimate
        lines.append("### Cost Estimate (Forward-Looking)")
        lines.append("")
        lines.append(f"| Region | Cost Range |")
        lines.append(f"|--------|------------|")
        lines.append(f"| **EU** | {fwd.cost_eu.to_dict()['formatted']} |")
        lines.append(f"| **UA** | {fwd.cost_ua.to_dict()['formatted']} |")
        lines.append("")
        lines.append(f"*Typical hours: {fwd.hours_typical.total:.0f}h (Tech debt multiplier: {fwd.tech_debt_multiplier}x)*")
        lines.append("")

        # Repo Health Details
        lines.append("## Repository Health")
        lines.append("")
        lines.append(self._health_table(report.repo_health))
        lines.append("")

        # Tech Debt Details
        lines.append("## Technical Debt")
        lines.append("")
        lines.append(self._tech_debt_table(report.tech_debt))
        lines.append("")

        # Hours Breakdown
        lines.append("## Effort Breakdown")
        lines.append("")
        lines.append("### Forward Estimate (Typical)")
        lines.append("")
        lines.append("| Activity | Hours |")
        lines.append("|----------|-------|")
        typical = fwd.hours_typical
        lines.append(f"| Analysis | {typical.analysis:.0f}h |")
        lines.append(f"| Design | {typical.design:.0f}h |")
        lines.append(f"| Development | {typical.development:.0f}h |")
        lines.append(f"| QA/Testing | {typical.qa:.0f}h |")
        lines.append(f"| Documentation | {typical.documentation:.0f}h |")
        lines.append(f"| **Total** | **{typical.total:.0f}h** |")
        lines.append("")

        # Historical Estimate
        hist = report.historical_estimate
        lines.append("### Historical Estimate")
        lines.append("")
        lines.append(f"Based on commit history analysis:")
        lines.append("")
        lines.append(f"- **Active days:** ~{hist.active_days}")
        lines.append(f"- **Estimated hours:** {hist.estimated_hours_min:.0f} - {hist.estimated_hours_max:.0f}h")
        lines.append(f"- **Person-months:** {hist.estimated_person_months_min:.1f} - {hist.estimated_person_months_max:.1f}")
        lines.append(f"- **Confidence:** {hist.confidence}")
        lines.append("")
        lines.append(f"> Note: {hist.note}")
        lines.append("")

        # Tasks
        if report.tasks:
            lines.append("## Improvement Tasks")
            lines.append("")
            lines.append(f"Total tasks: {len(report.tasks)}")
            lines.append("")

            # Group by priority
            for priority in ["P1", "P2", "P3"]:
                priority_tasks = [t for t in report.tasks if t.priority.value == priority]
                if priority_tasks:
                    priority_label = {"P1": "Critical", "P2": "Important", "P3": "Nice to Have"}[priority]
                    lines.append(f"### {priority} - {priority_label}")
                    lines.append("")
                    for task in priority_tasks:
                        lines.append(f"#### {task.title}")
                        lines.append("")
                        lines.append(f"**Category:** {task.category.value} | **Estimate:** {task.estimate_hours}h")
                        lines.append("")
                        lines.append(task.description)
                        lines.append("")
                        if task.labels:
                            lines.append(f"*Labels: {', '.join(task.labels)}*")
                            lines.append("")

        # Project Stats
        lines.append("## Project Statistics")
        lines.append("")
        static = report.static_metrics
        struct = report.structure_data
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        lines.append(f"| Total LOC | {static.get('total_loc', 'N/A'):,} |")
        lines.append(f"| Files | {static.get('files_count', 'N/A')} |")
        lines.append(f"| Test Files | {static.get('test_files_count', 'N/A')} |")
        lines.append(f"| Total Commits | {struct.get('commits_total', 'N/A')} |")
        lines.append(f"| Contributors | {struct.get('authors_count', 'N/A')} |")
        lines.append(f"| Recent Commits (90d) | {struct.get('recent_commits', 'N/A')} |")
        lines.append("")

        # Languages
        if static.get("languages"):
            lines.append("### Languages")
            lines.append("")
            lines.append("| Language | Files | LOC |")
            lines.append("|----------|-------|-----|")
            for lang, data in static["languages"].items():
                lines.append(f"| {lang} | {data['files']} | {data['loc']:,} |")
            lines.append("")

        # Footer
        lines.append("---")
        lines.append("")
        lines.append("*Generated by [Repo Auditor](https://github.com/your-org/repo-auditor)*")

        return "\n".join(lines)

    def build_csv_tasks(self, tasks: List[GeneratedTask]) -> str:
        """
        Build CSV export of tasks.

        Args:
            tasks: List of generated tasks

        Returns:
            CSV string
        """
        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow([
            "title",
            "category",
            "priority",
            "estimate_hours",
            "description",
            "labels",
        ])

        # Data
        for task in tasks:
            writer.writerow([
                task.title,
                task.category.value,
                task.priority.value,
                task.estimate_hours,
                task.description.replace("\n", " "),
                ";".join(task.labels),
            ])

        return output.getvalue()

    def build_csv_cost(self, forward: ForwardEstimate, historical: HistoricalEstimate) -> str:
        """
        Build CSV export of cost estimates.

        Args:
            forward: Forward-looking estimate
            historical: Historical estimate

        Returns:
            CSV string
        """
        output = io.StringIO()
        writer = csv.writer(output)

        # Forward estimate
        writer.writerow(["Forward-Looking Estimate"])
        writer.writerow([
            "activity",
            "hours_min",
            "hours_typical",
            "hours_max",
        ])

        activities = ["analysis", "design", "development", "qa", "documentation"]
        for act in activities:
            writer.writerow([
                act,
                getattr(forward.hours_min, act),
                getattr(forward.hours_typical, act),
                getattr(forward.hours_max, act),
            ])

        writer.writerow([
            "TOTAL",
            forward.hours_min.total,
            forward.hours_typical.total,
            forward.hours_max.total,
        ])

        writer.writerow([])
        writer.writerow(["Cost Ranges"])
        writer.writerow(["region", "currency", "min", "max"])
        writer.writerow(["EU", forward.cost_eu.currency, forward.cost_eu.min, forward.cost_eu.max])
        writer.writerow(["UA", forward.cost_ua.currency, forward.cost_ua.min, forward.cost_ua.max])

        writer.writerow([])
        writer.writerow(["Historical Estimate"])
        writer.writerow(["metric", "min", "max"])
        writer.writerow(["hours", historical.estimated_hours_min, historical.estimated_hours_max])
        writer.writerow(["person_months", historical.estimated_person_months_min, historical.estimated_person_months_max])
        writer.writerow(["cost_eu", historical.cost_eu.min, historical.cost_eu.max])
        writer.writerow(["cost_ua", historical.cost_ua.min, historical.cost_ua.max])

        return output.getvalue()

    def build_json(self, report: AnalysisReport) -> Dict[str, Any]:
        """
        Build JSON representation of full report.

        Args:
            report: Complete analysis data

        Returns:
            Dictionary for JSON serialization
        """
        return {
            "analysis_id": report.analysis_id,
            "repo_url": report.repo_url,
            "branch": report.branch,
            "analyzed_at": report.analyzed_at.isoformat(),
            "summary": {
                "product_level": report.product_level.value,
                "product_level_description": get_product_level_description(report.product_level),
                "complexity": report.complexity.value,
                "complexity_description": get_complexity_description(report.complexity),
            },
            "repo_health": report.repo_health.to_dict(),
            "tech_debt": report.tech_debt.to_dict(),
            "forward_estimate": report.forward_estimate.to_dict(),
            "historical_estimate": report.historical_estimate.to_dict(),
            "tasks": [t.to_dict() for t in report.tasks],
            "statistics": {
                "total_loc": report.static_metrics.get("total_loc"),
                "files_count": report.static_metrics.get("files_count"),
                "test_files_count": report.static_metrics.get("test_files_count"),
                "languages": report.static_metrics.get("languages", {}),
                "commits_total": report.structure_data.get("commits_total"),
                "authors_count": report.structure_data.get("authors_count"),
            },
        }

    def _health_table(self, health: RepoHealthScore) -> str:
        """Generate health score table."""
        def score_bar(score: int, max_score: int = 3) -> str:
            filled = "█" * score
            empty = "░" * (max_score - score)
            return f"{filled}{empty} {score}/{max_score}"

        lines = [
            "| Dimension | Score | Status |",
            "|-----------|-------|--------|",
            f"| Documentation | {score_bar(health.documentation)} | {self._score_status(health.documentation)} |",
            f"| Structure | {score_bar(health.structure)} | {self._score_status(health.structure)} |",
            f"| Runability | {score_bar(health.runability)} | {self._score_status(health.runability)} |",
            f"| Commit History | {score_bar(health.commit_history)} | {self._score_status(health.commit_history)} |",
            f"| **Total** | **{health.total}/12** | |",
        ]
        return "\n".join(lines)

    def _tech_debt_table(self, debt: TechDebtScore) -> str:
        """Generate tech debt score table."""
        def score_bar(score: int, max_score: int = 3) -> str:
            filled = "█" * score
            empty = "░" * (max_score - score)
            return f"{filled}{empty} {score}/{max_score}"

        lines = [
            "| Dimension | Score | Status |",
            "|-----------|-------|--------|",
            f"| Architecture | {score_bar(debt.architecture)} | {self._score_status(debt.architecture)} |",
            f"| Code Quality | {score_bar(debt.code_quality)} | {self._score_status(debt.code_quality)} |",
            f"| Testing | {score_bar(debt.testing)} | {self._score_status(debt.testing)} |",
            f"| Infrastructure | {score_bar(debt.infrastructure)} | {self._score_status(debt.infrastructure)} |",
            f"| Security & Deps | {score_bar(debt.security_deps)} | {self._score_status(debt.security_deps)} |",
            f"| **Total** | **{debt.total}/15** | |",
        ]
        return "\n".join(lines)

    def _score_status(self, score: int) -> str:
        """Convert score to status indicator."""
        if score == 0:
            return "[CRITICAL]"
        elif score == 1:
            return "[NEEDS WORK]"
        elif score == 2:
            return "[ACCEPTABLE]"
        else:
            return "[GOOD]"


    def determine_verdict(self, report: AnalysisReport) -> str:
        """
        Determine the verdict/status for a repository.

        Returns one of:
        - Archive / Reference Only
        - R&D Prototype
        - Internal Tool
        - Platform Module Candidate
        - Near-Product
        """
        health = report.repo_health.total
        debt = report.tech_debt.total
        level = report.product_level

        if level == ProductLevel.NEAR_PRODUCT:
            return "Near-Product"
        elif level == ProductLevel.PLATFORM_MODULE:
            return "Platform Module Candidate"
        elif level == ProductLevel.INTERNAL_TOOL:
            return "Internal Tool"
        elif level == ProductLevel.PROTOTYPE:
            if health >= 6 or debt >= 6:
                return "R&D Prototype"
            return "Archive / Reference Only"
        else:  # RND_SPIKE
            return "Archive / Reference Only"

    def build_repo_review(self, report: AnalysisReport, comments: Optional[Dict[str, str]] = None) -> str:
        """
        Build detailed repository review document.

        Args:
            report: Complete analysis data
            comments: Optional comments for each metric

        Returns:
            Markdown string using repo_review template
        """
        comments = comments or {}
        verdict = self.determine_verdict(report)

        lines = []
        lines.append(f"# REPOSITORY REVIEW — {self._extract_repo_name(report.repo_url)}")
        lines.append("")
        lines.append(f"**URL:** {report.repo_url}")
        lines.append(f"**Branch:** {report.branch or 'main'}")
        lines.append(f"**Date:** {report.analyzed_at.strftime('%Y-%m-%d')}")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Product Level
        lines.append("## 1. Product Level (тип результата)")
        lines.append("")
        lines.append(f"**Классификация:** {report.product_level.value}")
        lines.append("")
        lines.append(f"**Описание:** {get_product_level_description(report.product_level)}")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Repo Health
        lines.append("## 2. Repo Health (0–3 по каждому показателю)")
        lines.append("")
        lines.append("| Метрика        | Оценка | Комментарий |")
        lines.append("| -------------- | ------ | ----------- |")
        lines.append(f"| Documentation  | {report.repo_health.documentation}/3 | {comments.get('documentation', '—')} |")
        lines.append(f"| Structure      | {report.repo_health.structure}/3 | {comments.get('structure', '—')} |")
        lines.append(f"| Runability     | {report.repo_health.runability}/3 | {comments.get('runability', '—')} |")
        lines.append(f"| Commit History | {report.repo_health.commit_history}/3 | {comments.get('commit_history', '—')} |")
        lines.append("")
        lines.append(f"**Итог Repo Health Score:** {report.repo_health.total}/12")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Tech Debt
        lines.append("## 3. Tech Debt & Code Quality (0–3 по метрике)")
        lines.append("")
        lines.append("| Метрика       | Оценка | Комментарий |")
        lines.append("| ------------- | ------ | ----------- |")
        lines.append(f"| Architecture  | {report.tech_debt.architecture}/3 | {comments.get('architecture', '—')} |")
        lines.append(f"| Code Quality  | {report.tech_debt.code_quality}/3 | {comments.get('code_quality', '—')} |")
        lines.append(f"| Testing       | {report.tech_debt.testing}/3 | {comments.get('testing', '—')} |")
        lines.append(f"| Infra         | {report.tech_debt.infrastructure}/3 | {comments.get('infrastructure', '—')} |")
        lines.append(f"| Security/Deps | {report.tech_debt.security_deps}/3 | {comments.get('security_deps', '—')} |")
        lines.append("")
        lines.append(f"**Итог Tech Debt Score:** {report.tech_debt.total}/15")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Summary
        health_pct = round(report.repo_health.total / 12 * 100)
        debt_pct = round(report.tech_debt.total / 15 * 100)

        lines.append("## 4. Общая оценка")
        lines.append("")
        lines.append("| Параметр | Значение |")
        lines.append("|----------|----------|")
        lines.append(f"| Product Level | {report.product_level.value} |")
        lines.append(f"| Repo Health | {report.repo_health.total}/12 ({health_pct}%) |")
        lines.append(f"| Tech Debt | {report.tech_debt.total}/15 ({debt_pct}%) |")
        lines.append(f"| Complexity | {report.complexity.value} |")
        lines.append("")
        lines.append(f"### Вердикт: `{verdict}`")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Cost
        fwd = report.forward_estimate
        lines.append("## 5. Оценка стоимости")
        lines.append("")
        lines.append("### Forward-Looking")
        lines.append("")
        lines.append("| Активность | Typical |")
        lines.append("|------------|---------|")
        lines.append(f"| Analysis | {fwd.hours_typical.analysis:.0f}h |")
        lines.append(f"| Design | {fwd.hours_typical.design:.0f}h |")
        lines.append(f"| Development | {fwd.hours_typical.development:.0f}h |")
        lines.append(f"| QA | {fwd.hours_typical.qa:.0f}h |")
        lines.append(f"| Documentation | {fwd.hours_typical.documentation:.0f}h |")
        lines.append(f"| **Total** | **{fwd.hours_typical.total:.0f}h** |")
        lines.append("")
        lines.append(f"**EU:** {fwd.cost_eu.to_dict()['formatted']}")
        lines.append(f"**UA:** {fwd.cost_ua.to_dict()['formatted']}")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Tasks
        lines.append("## 6. Рекомендации")
        lines.append("")
        for i, task in enumerate(report.tasks[:5], 1):
            lines.append(f"### {i}. {task.title}")
            lines.append("")
            lines.append(f"**Приоритет:** {task.priority.value} | **Категория:** {task.category.value} | **Оценка:** {task.estimate_hours}h")
            lines.append("")
            lines.append(task.description)
            lines.append("")

        lines.append("---")
        lines.append("")
        lines.append(f"*Generated by Repo Auditor — {report.analyzed_at.strftime('%Y-%m-%d')}*")

        return "\n".join(lines)

    def build_repo_summary(self, report: AnalysisReport) -> str:
        """
        Build short summary for a repository (for acts/reports).
        """
        verdict = self.determine_verdict(report)
        repo_name = self._extract_repo_name(report.repo_url)

        lines = []
        lines.append(f"## Repository Summary — {repo_name}")
        lines.append("")
        lines.append(f"**Статус:** {verdict}")
        lines.append("")
        lines.append("### Ключевые метрики:")
        lines.append("")
        lines.append("| Метрика | Значение |")
        lines.append("|---------|----------|")
        lines.append(f"| Product Level | {report.product_level.value} |")
        lines.append(f"| Repo Health | {report.repo_health.total}/12 |")
        lines.append(f"| Tech Debt | {report.tech_debt.total}/15 |")
        lines.append(f"| Complexity | {report.complexity.value} |")
        lines.append(f"| Est. Hours | {report.forward_estimate.hours_typical.total:.0f}h |")
        lines.append("")

        return "\n".join(lines)

    def build_partner_report(
        self,
        reports: List[AnalysisReport],
        author: str = "—",
        period: str = "—",
    ) -> str:
        """
        Build comprehensive partner report for multiple repositories.

        Args:
            reports: List of analysis reports
            author: Report author name
            period: Reporting period

        Returns:
            Markdown string
        """
        # Calculate stats
        stats = {
            "platform_module": 0,
            "near_product": 0,
            "internal_tool": 0,
            "prototype": 0,
            "rnd_spike": 0,
        }

        total_hours = 0
        total_health = 0
        total_debt = 0

        for r in reports:
            verdict = self.determine_verdict(r)
            if verdict == "Platform Module Candidate":
                stats["platform_module"] += 1
            elif verdict == "Near-Product":
                stats["near_product"] += 1
            elif verdict == "Internal Tool":
                stats["internal_tool"] += 1
            elif verdict == "R&D Prototype":
                stats["prototype"] += 1
            else:
                stats["rnd_spike"] += 1

            total_hours += r.forward_estimate.hours_typical.total
            total_health += r.repo_health.total
            total_debt += r.tech_debt.total

        n = len(reports) or 1
        avg_health = round(total_health / n, 1)
        avg_debt = round(total_debt / n, 1)

        lines = []
        lines.append("# R&D RESULTS REPORT")
        lines.append("")
        lines.append("## Этап: Exploratory Architecture & Prototyping")
        lines.append("")
        lines.append(f"**Подготовил:** {author}")
        lines.append(f"**Период:** {period}")
        lines.append(f"**Дата отчёта:** {datetime.now().strftime('%Y-%m-%d')}")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Overview
        lines.append("## 1. Общее описание этапа")
        lines.append("")
        lines.append("В рамках исследовательского этапа была проведена разработка и тестирование прототипов для будущей экосистемы/платформы. Целью этапа было проверить технические гипотезы, протестировать архитектурные решения, провести интеграционные эксперименты и подготовить основу для последующей продуктовой фазы.")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Stats
        lines.append("## 2. Сводка по репозиториям")
        lines.append("")
        lines.append("### Общая статистика")
        lines.append("")
        lines.append("| Метрика | Значение |")
        lines.append("|---------|----------|")
        lines.append(f"| Всего репозиториев | {len(reports)} |")
        lines.append(f"| Platform Module Candidates | {stats['platform_module']} |")
        lines.append(f"| Near-Product | {stats['near_product']} |")
        lines.append(f"| Internal Tools | {stats['internal_tool']} |")
        lines.append(f"| R&D Prototypes | {stats['prototype']} |")
        lines.append(f"| R&D Spikes | {stats['rnd_spike']} |")
        lines.append("")
        lines.append("### Средние показатели")
        lines.append("")
        lines.append("| Метрика | Среднее |")
        lines.append("|---------|---------|")
        lines.append(f"| Repo Health | {avg_health}/12 ({round(avg_health/12*100)}%) |")
        lines.append(f"| Tech Debt | {avg_debt}/15 ({round(avg_debt/15*100)}%) |")
        lines.append(f"| Total Hours | {total_hours:.0f}h |")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Per-repo details
        lines.append("## 3. Результаты по репозиториям")
        lines.append("")

        for i, r in enumerate(reports, 1):
            repo_name = self._extract_repo_name(r.repo_url)
            verdict = self.determine_verdict(r)

            lines.append(f"### {i}. {repo_name}")
            lines.append("")
            lines.append("| Параметр | Значение |")
            lines.append("|----------|----------|")
            lines.append(f"| **Статус** | {verdict} |")
            lines.append(f"| **Product Level** | {r.product_level.value} |")
            lines.append(f"| **Repo Health** | {r.repo_health.total}/12 |")
            lines.append(f"| **Tech Debt** | {r.tech_debt.total}/15 |")
            lines.append(f"| **Complexity** | {r.complexity.value} |")
            lines.append(f"| **Est. Hours** | {r.forward_estimate.hours_typical.total:.0f}h |")
            lines.append("")
            lines.append("---")
            lines.append("")

        # Conclusions
        lines.append("## 4. Общие выводы")
        lines.append("")
        lines.append(f"- Проведено **{len(reports)}** прототипов и архитектурных экспериментов")
        lines.append("- Сняты критические технические риски")
        lines.append(f"- Определены **{stats['platform_module'] + stats['near_product']}** ключевых модулей для платформы")
        lines.append("- Сформирована база знаний и технических наработок")
        lines.append("- Подготовлен фундамент для продуктовой фазы")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Recommendations
        lines.append("## 5. Рекомендации на следующую фазу")
        lines.append("")
        lines.append("1. **Стандартизация кода** — вынос выбранных модулей в продуктовую структуру")
        lines.append("2. **Style Guide** — создание единого стандарта и архитектурных слоёв")
        lines.append("3. **Рефакторинг** — избранных модулей с высоким потенциалом")
        lines.append("4. **Онбординг** — использование прототипов как reference")
        lines.append("5. **Backlog** — формирование для сборки платформы")
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append(f"*Отчёт сгенерирован Repo Auditor — {datetime.now().strftime('%Y-%m-%d')}*")

        return "\n".join(lines)

    def build_act_of_work(
        self,
        reports: List[AnalysisReport],
        executor: str = "—",
        client: str = "—",
        period: str = "—",
        project_name: str = "R&D Development of Platform Ecosystem",
    ) -> str:
        """
        Build Act of Completed Work document.
        """
        # Calculate totals
        total_hours = sum(r.forward_estimate.hours_typical.total for r in reports)

        stats = {"platform_module": 0, "near_product": 0, "internal_tool": 0, "prototype": 0, "rnd_spike": 0}
        for r in reports:
            verdict = self.determine_verdict(r)
            if verdict == "Platform Module Candidate":
                stats["platform_module"] += 1
            elif verdict == "Near-Product":
                stats["near_product"] += 1
            elif verdict == "Internal Tool":
                stats["internal_tool"] += 1
            elif verdict == "R&D Prototype":
                stats["prototype"] += 1
            else:
                stats["rnd_spike"] += 1

        # Calculate cost totals
        total_eu_min = sum(r.forward_estimate.cost_eu.min for r in reports)
        total_eu_max = sum(r.forward_estimate.cost_eu.max for r in reports)
        total_ua_min = sum(r.forward_estimate.cost_ua.min for r in reports)
        total_ua_max = sum(r.forward_estimate.cost_ua.max for r in reports)

        lines = []
        lines.append("# ACT OF COMPLETED WORK")
        lines.append("")
        lines.append("## R&D Stage: Exploratory Architecture & Prototyping")
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append(f"**Исполнитель:** {executor}")
        lines.append(f"**Заказчик:** {client}")
        lines.append(f"**Период:** {period}")
        lines.append(f"**Проект:** {project_name}")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Description
        lines.append("## 1. Описание выполненных работ")
        lines.append("")
        lines.append("Проведены исследовательские и архитектурные работы по проекту. Разработаны и протестированы набор прототипов, технических модулей и интеграционных решений.")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Artifacts
        lines.append("## 2. Перечень артефактов")
        lines.append("")
        lines.append(f"### Репозитории ({len(reports)} шт.)")
        lines.append("")
        lines.append("| # | Название | Статус | Тип |")
        lines.append("|---|----------|--------|-----|")
        for i, r in enumerate(reports, 1):
            repo_name = self._extract_repo_name(r.repo_url)
            verdict = self.determine_verdict(r)
            lines.append(f"| {i} | {repo_name} | {verdict} | {r.product_level.value} |")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Classification
        lines.append("## 3. Результаты классификации")
        lines.append("")
        lines.append("| Категория | Количество |")
        lines.append("|-----------|------------|")
        lines.append(f"| Platform Module Candidates | {stats['platform_module']} |")
        lines.append(f"| Near-Product | {stats['near_product']} |")
        lines.append(f"| Internal Tools | {stats['internal_tool']} |")
        lines.append(f"| R&D Prototypes | {stats['prototype']} |")
        lines.append(f"| R&D Spikes | {stats['rnd_spike']} |")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Hours
        lines.append("## 4. Потраченные часы")
        lines.append("")
        lines.append("| Репозиторий | Часы |")
        lines.append("|-------------|------|")
        for r in reports:
            repo_name = self._extract_repo_name(r.repo_url)
            lines.append(f"| {repo_name} | {r.forward_estimate.hours_typical.total:.0f}h |")
        lines.append(f"| **ИТОГО** | **{total_hours:.0f}h** |")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Cost
        lines.append("## 5. Стоимость работ")
        lines.append("")
        lines.append("| Регион | Диапазон |")
        lines.append("|--------|----------|")
        lines.append(f"| EU | €{total_eu_min:,.0f} — €{total_eu_max:,.0f} |")
        lines.append(f"| UA | ${total_ua_min:,.0f} — ${total_ua_max:,.0f} |")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Confirmation
        lines.append("## 6. Подтверждение")
        lines.append("")
        lines.append("Работы выполнены в полном объёме.")
        lines.append("")
        lines.append("**Исполнитель:** ___________________________ / " + executor + " /")
        lines.append("")
        lines.append(f"**Дата:** {datetime.now().strftime('%Y-%m-%d')}")
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append(f"*Документ сформирован: {datetime.now().strftime('%Y-%m-%d')}*")

        return "\n".join(lines)

    def _extract_repo_name(self, url: str) -> str:
        """Extract repository name from URL."""
        try:
            return url.rstrip("/").split("/")[-1].replace(".git", "")
        except (AttributeError, IndexError):
            return "unknown"


# Singleton instance
report_builder = ReportBuilder()
