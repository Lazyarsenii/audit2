"""
Work Report Generator Service.

Generates work reports with task breakdown based on code analysis.
Uses LLM to generate realistic development tasks from repository analysis.
"""
import io
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


@dataclass
class WorkTask:
    """A work task with hours allocation."""
    date: str
    activity: str
    result: str
    hours: float


@dataclass
class WorkReportConfig:
    """Configuration for work report generation."""
    start_date: datetime
    end_date: datetime
    consultant_name: str = "Developer"
    organization: str = "Organization"
    project_name: str = "Project"
    total_days: int = 20  # Working days in period


class WorkReportGenerator:
    """
    Generates work reports with task breakdown.

    Takes COCOMO estimate, divides by 10, and distributes
    across realistic development tasks.
    """

    def __init__(self):
        self.llm_provider = None
        self._init_llm()

    def _init_llm(self):
        """Initialize LLM provider."""
        try:
            from app.llm.router import llm_router
            self.llm_provider = llm_router
        except Exception as e:
            logger.warning(f"LLM not available: {e}")

    def generate_tasks_from_analysis(
        self,
        analysis: Dict[str, Any],
        total_hours: float,
        config: WorkReportConfig
    ) -> List[WorkTask]:
        """
        Generate work tasks based on code analysis.

        Args:
            analysis: Repository analysis results
            total_hours: Total hours to distribute (COCOMO / 10)
            config: Report configuration

        Returns:
            List of WorkTask objects
        """
        # Extract key metrics for task generation
        static_metrics = analysis.get("static_metrics", {})
        languages = static_metrics.get("languages", {})
        total_loc = static_metrics.get("total_loc", 0)
        files_count = static_metrics.get("files_count", 0)

        repo_health = analysis.get("repo_health", {})
        tech_debt = analysis.get("tech_debt", {})

        # Generate tasks using LLM or fallback to template
        if self.llm_provider:
            try:
                tasks = self._generate_tasks_with_llm(
                    analysis, total_hours, config
                )
                if tasks:
                    return tasks
            except Exception as e:
                logger.warning(f"LLM task generation failed: {e}")

        # Fallback to template-based generation
        return self._generate_template_tasks(
            analysis, total_hours, config
        )

    def _generate_tasks_with_llm(
        self,
        analysis: Dict[str, Any],
        total_hours: float,
        config: WorkReportConfig
    ) -> List[WorkTask]:
        """Generate tasks using LLM."""
        static_metrics = analysis.get("static_metrics", {})
        languages = list(static_metrics.get("languages", {}).keys())

        prompt = f"""Based on this code repository analysis, generate a work report with development tasks.

Repository: {analysis.get('repo_name', 'Unknown')}
Languages: {', '.join(languages[:5])}
Total LOC: {static_metrics.get('total_loc', 0):,}
Files: {static_metrics.get('files_count', 0)}
Repo Health Score: {analysis.get('repo_health', {}).get('total', 0)}/12
Tech Debt Score: {analysis.get('tech_debt', {}).get('total', 0)}/15

Period: {config.start_date.strftime('%d.%m.%Y')} - {config.end_date.strftime('%d.%m.%Y')}
Total hours to distribute: {total_hours:.0f} hours

Generate 5-8 realistic development tasks that would be performed on this codebase.
Each task should have:
1. Activity description (what was done)
2. Result (deliverable/outcome)
3. Hours (distribute the {total_hours:.0f} hours across tasks)

Format each task as:
TASK:
Activity: [description]
Result: [outcome]
Hours: [number]

Make tasks specific to the codebase type and languages used."""

        try:
            response = self.llm_provider.generate(prompt, max_tokens=2000)
            return self._parse_llm_tasks(response, config)
        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            return []

    def _parse_llm_tasks(
        self,
        llm_response: str,
        config: WorkReportConfig
    ) -> List[WorkTask]:
        """Parse LLM response into WorkTask objects."""
        tasks = []
        current_task = {}

        for line in llm_response.split('\n'):
            line = line.strip()
            if line.startswith('Activity:'):
                if current_task.get('activity'):
                    tasks.append(current_task)
                current_task = {'activity': line[9:].strip()}
            elif line.startswith('Result:'):
                current_task['result'] = line[7:].strip()
            elif line.startswith('Hours:'):
                try:
                    hours_str = line[6:].strip().replace('hours', '').replace('hour', '').strip()
                    current_task['hours'] = float(hours_str)
                except:
                    current_task['hours'] = 8

        if current_task.get('activity'):
            tasks.append(current_task)

        # Distribute dates across the period
        work_days = self._get_work_days(config.start_date, config.end_date)

        result = []
        for i, task in enumerate(tasks):
            date_idx = min(i * len(work_days) // len(tasks), len(work_days) - 1)
            date = work_days[date_idx] if work_days else config.start_date

            result.append(WorkTask(
                date=date.strftime('%d.%m.%Y'),
                activity=task.get('activity', 'Development work'),
                result=task.get('result', 'Completed'),
                hours=task.get('hours', 8)
            ))

        return result

    def _generate_template_tasks(
        self,
        analysis: Dict[str, Any],
        total_hours: float,
        config: WorkReportConfig
    ) -> List[WorkTask]:
        """Generate tasks using templates based on analysis."""
        static_metrics = analysis.get("static_metrics", {})
        languages = list(static_metrics.get("languages", {}).keys())[:3]
        repo_name = analysis.get("repo_name", "Repository")

        # Template tasks based on typical development activities
        task_templates = [
            {
                "activity": f"Code review and architecture analysis of {repo_name} codebase",
                "result": f"Completed comprehensive code review. Identified {static_metrics.get('files_count', 0)} files across {len(languages)} languages. Documented architecture patterns and dependencies.",
                "hours_pct": 0.15
            },
            {
                "activity": f"Static code analysis and quality assessment using automated tools",
                "result": f"Generated quality metrics report. Code health score: {analysis.get('repo_health', {}).get('total', 0)}/12. Identified areas for improvement.",
                "hours_pct": 0.12
            },
            {
                "activity": f"Technical debt assessment and documentation",
                "result": f"Documented technical debt score: {analysis.get('tech_debt', {}).get('total', 0)}/15. Created prioritized list of refactoring tasks.",
                "hours_pct": 0.13
            },
            {
                "activity": f"Development of new features and functionality for {', '.join(languages)} components",
                "result": "Implemented new features according to specifications. Updated relevant documentation and tests.",
                "hours_pct": 0.25
            },
            {
                "activity": "Bug fixes and code optimization based on analysis findings",
                "result": "Fixed identified issues and optimized performance-critical code paths. Improved code maintainability.",
                "hours_pct": 0.15
            },
            {
                "activity": "Testing, quality assurance, and documentation updates",
                "result": "Executed test suites, documented test results. Updated technical documentation to reflect changes.",
                "hours_pct": 0.12
            },
            {
                "activity": "Project coordination, meetings, and progress reporting",
                "result": "Participated in team meetings, provided progress updates. Prepared status reports and documentation.",
                "hours_pct": 0.08
            }
        ]

        # Get work days in period
        work_days = self._get_work_days(config.start_date, config.end_date)

        tasks = []
        for i, template in enumerate(task_templates):
            hours = round(total_hours * template["hours_pct"], 1)
            if hours < 1:
                hours = 1

            # Assign date from work days
            date_idx = min(i * len(work_days) // len(task_templates), len(work_days) - 1)
            date = work_days[date_idx] if work_days else config.start_date

            tasks.append(WorkTask(
                date=date.strftime('%d.%m.%Y'),
                activity=template["activity"],
                result=template["result"],
                hours=hours
            ))

        return tasks

    def _get_work_days(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[datetime]:
        """Get list of work days (Mon-Fri) in period."""
        work_days = []
        current = start_date
        while current <= end_date:
            if current.weekday() < 5:  # Monday = 0, Friday = 4
                work_days.append(current)
            current += timedelta(days=1)
        return work_days

    def generate_pdf_report(
        self,
        tasks: List[WorkTask],
        config: WorkReportConfig,
        analysis: Dict[str, Any]
    ) -> bytes:
        """Generate PDF work report."""
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import cm
            from reportlab.platypus import (
                SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
                PageBreak
            )
            from reportlab.lib.enums import TA_CENTER, TA_LEFT
        except ImportError:
            logger.error("reportlab not installed")
            return self._generate_text_report(tasks, config, analysis)

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=1.5*cm,
            leftMargin=1.5*cm,
            topMargin=2*cm,
            bottomMargin=2*cm,
        )

        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(
            name='Title2',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=20,
            alignment=TA_CENTER,
        ))
        styles.add(ParagraphStyle(
            name='Subtitle',
            parent=styles['Normal'],
            fontSize=11,
            textColor=colors.grey,
            alignment=TA_CENTER,
        ))
        styles.add(ParagraphStyle(
            name='CellText',
            parent=styles['Normal'],
            fontSize=9,
            leading=12,
        ))

        elements = []

        # Title
        elements.append(Paragraph("Report on the work done", styles['Title2']))
        elements.append(Paragraph(
            f"Consultant: {config.consultant_name}",
            styles['Subtitle']
        ))
        elements.append(Paragraph(
            f"Organization: {config.organization}",
            styles['Subtitle']
        ))
        elements.append(Paragraph(
            f"Period: {config.start_date.strftime('%d.%m.%Y')} - {config.end_date.strftime('%d.%m.%Y')}",
            styles['Subtitle']
        ))

        total_hours = sum(t.hours for t in tasks)
        elements.append(Paragraph(
            f"Total hours: {total_hours:.0f}",
            styles['Subtitle']
        ))
        elements.append(Spacer(1, 20))

        # Project info
        repo_name = analysis.get("repo_name", "Repository")
        elements.append(Paragraph(
            f"Project: {repo_name}",
            styles['Heading2']
        ))
        elements.append(Spacer(1, 10))

        # Tasks table
        table_data = [["Date", "Activities implemented", "Result", "Time"]]

        for task in tasks:
            table_data.append([
                task.date,
                Paragraph(task.activity, styles['CellText']),
                Paragraph(task.result, styles['CellText']),
                f"{task.hours:.0f} hours"
            ])

        # Add total row
        table_data.append([
            "TOTAL",
            "",
            "",
            f"{total_hours:.0f} hours"
        ])

        col_widths = [2.2*cm, 6*cm, 6*cm, 2*cm]
        table = Table(table_data, colWidths=col_widths, repeatRows=1)

        table.setStyle(TableStyle([
            # Header
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),

            # Body
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),
            ('ALIGN', (3, 1), (3, -1), 'CENTER'),

            # Total row
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f0f0f0')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),

            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f8f8f8')]),

            # Padding
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ]))

        elements.append(table)
        elements.append(Spacer(1, 30))

        # Signature section
        elements.append(Paragraph(
            f"Date: {config.end_date.strftime('%d.%m.%Y')}",
            styles['Normal']
        ))
        elements.append(Spacer(1, 20))
        elements.append(Paragraph(
            f"Signature: _____________________     Name: {config.consultant_name}",
            styles['Normal']
        ))

        # Footer
        elements.append(Spacer(1, 30))
        elements.append(Paragraph(
            "Generated by Repo Auditor",
            styles['Subtitle']
        ))

        doc.build(elements)
        return buffer.getvalue()

    def _generate_text_report(
        self,
        tasks: List[WorkTask],
        config: WorkReportConfig,
        analysis: Dict[str, Any]
    ) -> bytes:
        """Fallback text report if PDF generation fails."""
        lines = [
            "REPORT ON THE WORK DONE",
            "=" * 50,
            f"Consultant: {config.consultant_name}",
            f"Organization: {config.organization}",
            f"Period: {config.start_date.strftime('%d.%m.%Y')} - {config.end_date.strftime('%d.%m.%Y')}",
            f"Project: {analysis.get('repo_name', 'Repository')}",
            "",
            "TASKS:",
            "-" * 50,
        ]

        total_hours = 0
        for task in tasks:
            lines.append(f"\nDate: {task.date}")
            lines.append(f"Activity: {task.activity}")
            lines.append(f"Result: {task.result}")
            lines.append(f"Hours: {task.hours}")
            total_hours += task.hours

        lines.append("")
        lines.append("-" * 50)
        lines.append(f"TOTAL HOURS: {total_hours:.0f}")
        lines.append("")
        lines.append(f"Date: {config.end_date.strftime('%d.%m.%Y')}")
        lines.append(f"Signature: _____________________")
        lines.append(f"Name: {config.consultant_name}")

        return "\n".join(lines).encode('utf-8')


# Singleton
work_report_generator = WorkReportGenerator()
