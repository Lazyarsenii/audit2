"""
Document Matrix Service

Automatically selects and generates document packages based on:
- Product Level (RND_SPIKE, PROTOTYPE, INTERNAL_TOOL, PLATFORM_MODULE, NEAR_PRODUCT)
- Project context (is_platform_module, has_donors)
- Analysis results
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from app.core.scoring.product_level import ProductLevel

logger = logging.getLogger(__name__)


class DocumentType(str, Enum):
    """All available document types."""
    # Technical Documents
    RND_SUMMARY = "rnd_summary"
    TECH_NOTE = "tech_note"
    TECH_REPORT = "tech_report"
    ARCHITECTURE_DOC = "architecture_doc"
    INTEGRATION_MAP = "integration_map"
    OPERATIONAL_RUNBOOK = "operational_runbook"
    SECURITY_SUMMARY = "security_summary"

    # Quality Documents
    QUALITY_REPORT = "quality_report"
    TECH_DEBT_REPORT = "tech_debt_report"
    PLATFORM_CHECKLIST = "platform_checklist"

    # Cost Documents
    COST_ESTIMATE = "cost_estimate"
    COST_EFFORT_SUMMARY = "cost_effort_summary"
    FORECAST_VS_BUDGET = "forecast_vs_budget"

    # Planning Documents
    BACKLOG = "backlog"
    TASK_LIST = "task_list"
    MIGRATION_PLAN = "migration_plan"
    ROADMAP = "roadmap"

    # Acceptance Documents
    INTERNAL_ACCEPTANCE = "internal_acceptance"
    PLATFORM_ACCEPTANCE = "platform_acceptance"
    RELEASE_NOTES = "release_notes"
    SLO_SLA = "slo_sla"

    # Donor Documents
    DONOR_ONE_PAGER = "donor_one_pager"
    DONOR_TECH_REPORT = "donor_tech_report"
    WORKPLAN_ALIGNMENT = "workplan_alignment"
    BUDGET_STATUS = "budget_status"
    INDICATORS_STATUS = "indicators_status"
    MULTI_DONOR_SPLIT = "multi_donor_split"
    FULL_ACCEPTANCE_PACKAGE = "full_acceptance_package"


class DocumentCategory(str, Enum):
    """Document categories."""
    BASE = "base"
    PLATFORM = "platform"
    DONOR = "donor"


@dataclass
class DocumentTemplate:
    """Document template definition."""
    doc_type: DocumentType
    name: str
    description: str
    category: DocumentCategory
    output_formats: List[str] = field(default_factory=lambda: ["md", "pdf"])
    is_required: bool = False
    is_auto_generated: bool = True
    estimated_pages: int = 1
    sections: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert template to dictionary."""
        return {
            "type": self.doc_type.value,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "estimated_pages": self.estimated_pages,
            "sections": self.sections,
            "is_required": self.is_required,
            "output_formats": self.output_formats,
        }


# Document templates registry
DOCUMENT_TEMPLATES: Dict[DocumentType, DocumentTemplate] = {
    # R&D Summary
    DocumentType.RND_SUMMARY: DocumentTemplate(
        doc_type=DocumentType.RND_SUMMARY,
        name="R&D Summary",
        description="Brief summary of R&D spike: hypothesis, work done, findings, next steps",
        category=DocumentCategory.BASE,
        estimated_pages=1,
        sections=["Hypothesis", "Work Done", "Key Findings", "Next Steps"],
    ),

    # Tech Note
    DocumentType.TECH_NOTE: DocumentTemplate(
        doc_type=DocumentType.TECH_NOTE,
        name="Technical Note",
        description="Draft technical note with architecture ideas and stack overview",
        category=DocumentCategory.BASE,
        estimated_pages=2,
        sections=["Overview", "Architecture Idea", "Technology Stack", "Risks"],
    ),

    # Tech Report
    DocumentType.TECH_REPORT: DocumentTemplate(
        doc_type=DocumentType.TECH_REPORT,
        name="Technical Report",
        description="Full technical report with functionality, architecture, limitations",
        category=DocumentCategory.BASE,
        estimated_pages=5,
        sections=["Executive Summary", "Functionality", "Architecture", "Quality Metrics", "Limitations", "Recommendations"],
        is_required=True,
    ),

    # Architecture Doc
    DocumentType.ARCHITECTURE_DOC: DocumentTemplate(
        doc_type=DocumentType.ARCHITECTURE_DOC,
        name="Architecture Document",
        description="Comprehensive architecture documentation with diagrams",
        category=DocumentCategory.BASE,
        estimated_pages=8,
        sections=["System Overview", "Components", "Data Flow", "Integrations", "Security", "Deployment"],
    ),

    # Integration Map
    DocumentType.INTEGRATION_MAP: DocumentTemplate(
        doc_type=DocumentType.INTEGRATION_MAP,
        name="Integration Map",
        description="How module integrates with platform ecosystem (APIs, events, dependencies)",
        category=DocumentCategory.PLATFORM,
        estimated_pages=3,
        sections=["Overview", "API Contracts", "Events", "Dependencies", "Data Flows"],
    ),

    # Operational Runbook
    DocumentType.OPERATIONAL_RUNBOOK: DocumentTemplate(
        doc_type=DocumentType.OPERATIONAL_RUNBOOK,
        name="Operational Runbook",
        description="How to deploy, monitor, troubleshoot, and rollback",
        category=DocumentCategory.BASE,
        estimated_pages=6,
        sections=["Prerequisites", "Installation", "Configuration", "Deployment", "Monitoring", "Troubleshooting", "Rollback"],
    ),

    # Security Summary
    DocumentType.SECURITY_SUMMARY: DocumentTemplate(
        doc_type=DocumentType.SECURITY_SUMMARY,
        name="Security & Compliance Summary",
        description="Security review and compliance status",
        category=DocumentCategory.BASE,
        estimated_pages=3,
        sections=["Security Overview", "Vulnerabilities", "Compliance Status", "Recommendations"],
    ),

    # Quality Report
    DocumentType.QUALITY_REPORT: DocumentTemplate(
        doc_type=DocumentType.QUALITY_REPORT,
        name="Quality Report",
        description="Repo Health, Tech Debt, Product Level analysis",
        category=DocumentCategory.BASE,
        estimated_pages=4,
        sections=["Summary", "Repo Health", "Tech Debt", "Product Level", "Complexity"],
        is_required=True,
    ),

    # Tech Debt Report
    DocumentType.TECH_DEBT_REPORT: DocumentTemplate(
        doc_type=DocumentType.TECH_DEBT_REPORT,
        name="Tech Debt Report",
        description="Detailed technical debt analysis with remediation plan",
        category=DocumentCategory.BASE,
        estimated_pages=4,
        sections=["Overview", "Debt Categories", "Priority Items", "Remediation Plan", "Effort Estimate"],
    ),

    # Platform Checklist
    DocumentType.PLATFORM_CHECKLIST: DocumentTemplate(
        doc_type=DocumentType.PLATFORM_CHECKLIST,
        name="Platform Compatibility Checklist",
        description="Checklist for platform integration readiness",
        category=DocumentCategory.PLATFORM,
        estimated_pages=2,
        sections=["Logging", "Metrics", "Security", "Versioning", "API Standards", "Documentation"],
    ),

    # Cost Estimate
    DocumentType.COST_ESTIMATE: DocumentTemplate(
        doc_type=DocumentType.COST_ESTIMATE,
        name="Cost Estimate",
        description="Forward-looking cost estimation using multiple methodologies",
        category=DocumentCategory.BASE,
        estimated_pages=3,
        sections=["Summary", "Methodology Comparison", "Regional Estimates", "Confidence Intervals"],
        is_required=True,
    ),

    # Cost Effort Summary
    DocumentType.COST_EFFORT_SUMMARY: DocumentTemplate(
        doc_type=DocumentType.COST_EFFORT_SUMMARY,
        name="Cost & Effort Summary",
        description="Historical and forward cost/effort analysis",
        category=DocumentCategory.BASE,
        estimated_pages=3,
        sections=["Historical Effort", "Forward Estimate", "Activity Breakdown", "Regional Costs"],
    ),

    # Backlog
    DocumentType.BACKLOG: DocumentTemplate(
        doc_type=DocumentType.BACKLOG,
        name="Backlog",
        description="Prioritized list of tasks and hypotheses",
        category=DocumentCategory.BASE,
        estimated_pages=2,
        sections=["Priority Tasks", "Improvement Items", "Technical Debt Items", "Future Ideas"],
    ),

    # Task List
    DocumentType.TASK_LIST: DocumentTemplate(
        doc_type=DocumentType.TASK_LIST,
        name="Task List",
        description="Detailed task list with estimates",
        category=DocumentCategory.BASE,
        estimated_pages=3,
        sections=["P1 Tasks", "P2 Tasks", "P3 Tasks", "Summary"],
    ),

    # Migration Plan
    DocumentType.MIGRATION_PLAN: DocumentTemplate(
        doc_type=DocumentType.MIGRATION_PLAN,
        name="Migration/Refactoring Plan",
        description="Plan for migrating module to platform standards",
        category=DocumentCategory.PLATFORM,
        estimated_pages=4,
        sections=["Current State", "Target State", "Migration Steps", "Risks", "Timeline"],
    ),

    # Roadmap
    DocumentType.ROADMAP: DocumentTemplate(
        doc_type=DocumentType.ROADMAP,
        name="Roadmap",
        description="Development roadmap with milestones",
        category=DocumentCategory.BASE,
        estimated_pages=2,
        sections=["Vision", "Milestones", "Dependencies", "Resources"],
    ),

    # Internal Acceptance
    DocumentType.INTERNAL_ACCEPTANCE: DocumentTemplate(
        doc_type=DocumentType.INTERNAL_ACCEPTANCE,
        name="Internal Acceptance Note",
        description="Internal team acceptance document",
        category=DocumentCategory.BASE,
        estimated_pages=1,
        sections=["Deliverables", "Acceptance Criteria", "Sign-off"],
    ),

    # Platform Acceptance
    DocumentType.PLATFORM_ACCEPTANCE: DocumentTemplate(
        doc_type=DocumentType.PLATFORM_ACCEPTANCE,
        name="Platform Acceptance Document",
        description="Platform team acceptance with KPIs",
        category=DocumentCategory.PLATFORM,
        estimated_pages=2,
        sections=["Module Summary", "Ownership", "KPIs", "SLO/SLA", "Sign-off"],
    ),

    # Release Notes
    DocumentType.RELEASE_NOTES: DocumentTemplate(
        doc_type=DocumentType.RELEASE_NOTES,
        name="Release Notes",
        description="Change log and release notes",
        category=DocumentCategory.BASE,
        estimated_pages=1,
        sections=["Version", "Changes", "Breaking Changes", "Known Issues"],
    ),

    # SLO/SLA
    DocumentType.SLO_SLA: DocumentTemplate(
        doc_type=DocumentType.SLO_SLA,
        name="SLO/SLA Document",
        description="Service Level Objectives and Agreements",
        category=DocumentCategory.PLATFORM,
        estimated_pages=2,
        sections=["Availability", "Latency", "Error Rate", "Release Cadence"],
    ),

    # Forecast vs Budget
    DocumentType.FORECAST_VS_BUDGET: DocumentTemplate(
        doc_type=DocumentType.FORECAST_VS_BUDGET,
        name="Forecast vs Budget Report",
        description="Comparison of forecasted vs actual budget",
        category=DocumentCategory.DONOR,
        estimated_pages=3,
        sections=["Summary", "Budget Lines", "Variances", "Recommendations"],
    ),

    # Donor One-Pager
    DocumentType.DONOR_ONE_PAGER: DocumentTemplate(
        doc_type=DocumentType.DONOR_ONE_PAGER,
        name="R&D One-Pager for Donor",
        description="One-page summary for donors about R&D work",
        category=DocumentCategory.DONOR,
        estimated_pages=1,
        sections=["Objective", "Work Done", "Results", "Next Steps"],
    ),

    # Donor Tech Report
    DocumentType.DONOR_TECH_REPORT: DocumentTemplate(
        doc_type=DocumentType.DONOR_TECH_REPORT,
        name="Donor Technical Report",
        description="Adapted technical report for donor audience",
        category=DocumentCategory.DONOR,
        estimated_pages=4,
        sections=["Executive Summary", "Technical Overview", "Outcomes", "Budget Alignment"],
    ),

    # Workplan Alignment
    DocumentType.WORKPLAN_ALIGNMENT: DocumentTemplate(
        doc_type=DocumentType.WORKPLAN_ALIGNMENT,
        name="Workplan Alignment Report",
        description="Maps repository work to workplan activities",
        category=DocumentCategory.DONOR,
        estimated_pages=3,
        sections=["Overview", "Activity Mapping", "Progress Status", "Deviations"],
    ),

    # Budget Status
    DocumentType.BUDGET_STATUS: DocumentTemplate(
        doc_type=DocumentType.BUDGET_STATUS,
        name="Budget Status Report",
        description="Budget consumption and forecast",
        category=DocumentCategory.DONOR,
        estimated_pages=3,
        sections=["Summary", "Line-by-Line Status", "Burn Rate", "Forecast"],
    ),

    # Indicators Status
    DocumentType.INDICATORS_STATUS: DocumentTemplate(
        doc_type=DocumentType.INDICATORS_STATUS,
        name="Indicators Status Report",
        description="Project indicators progress",
        category=DocumentCategory.DONOR,
        estimated_pages=2,
        sections=["Dashboard", "Progress Details", "Trends", "Risks"],
    ),

    # Multi-Donor Split
    DocumentType.MULTI_DONOR_SPLIT: DocumentTemplate(
        doc_type=DocumentType.MULTI_DONOR_SPLIT,
        name="Multi-Donor Split Report",
        description="Cost/effort allocation across donors",
        category=DocumentCategory.DONOR,
        estimated_pages=3,
        sections=["Overview", "Per-Donor Breakdown", "Justification"],
    ),

    # Full Acceptance Package
    DocumentType.FULL_ACCEPTANCE_PACKAGE: DocumentTemplate(
        doc_type=DocumentType.FULL_ACCEPTANCE_PACKAGE,
        name="Full Acceptance Package",
        description="Complete donor acceptance package",
        category=DocumentCategory.DONOR,
        estimated_pages=10,
        sections=["Tech Report", "Compliance", "Workplan Status", "Budget Status", "Indicators", "Sign-off"],
    ),
}


# Document matrix by product level
DOCUMENT_MATRIX: Dict[str, Dict[str, List[DocumentType]]] = {
    ProductLevel.RND_SPIKE.value: {
        "base": [
            DocumentType.RND_SUMMARY,
            DocumentType.TECH_NOTE,
            DocumentType.BACKLOG,
        ],
        "platform": [],
        "donor": [
            DocumentType.DONOR_ONE_PAGER,
        ],
    },

    ProductLevel.PROTOTYPE.value: {
        "base": [
            DocumentType.TECH_REPORT,
            DocumentType.COST_ESTIMATE,
            DocumentType.COST_EFFORT_SUMMARY,
            DocumentType.TASK_LIST,
        ],
        "platform": [],
        "donor": [
            DocumentType.DONOR_TECH_REPORT,
            DocumentType.WORKPLAN_ALIGNMENT,
        ],
    },

    ProductLevel.INTERNAL_TOOL.value: {
        "base": [
            DocumentType.TECH_REPORT,
            DocumentType.QUALITY_REPORT,
            DocumentType.COST_EFFORT_SUMMARY,
            DocumentType.RELEASE_NOTES,
            DocumentType.INTERNAL_ACCEPTANCE,
        ],
        "platform": [
            DocumentType.INTEGRATION_MAP,
            DocumentType.ARCHITECTURE_DOC,
        ],
        "donor": [
            DocumentType.WORKPLAN_ALIGNMENT,
            DocumentType.BUDGET_STATUS,
            DocumentType.INDICATORS_STATUS,
        ],
    },

    ProductLevel.PLATFORM_MODULE.value: {
        "base": [
            DocumentType.ARCHITECTURE_DOC,
            DocumentType.QUALITY_REPORT,
            DocumentType.TECH_DEBT_REPORT,
            DocumentType.ROADMAP,
        ],
        "platform": [
            DocumentType.PLATFORM_CHECKLIST,
            DocumentType.MIGRATION_PLAN,
            DocumentType.INTEGRATION_MAP,
        ],
        "donor": [
            DocumentType.WORKPLAN_ALIGNMENT,
            DocumentType.BUDGET_STATUS,
            DocumentType.INDICATORS_STATUS,
            DocumentType.FORECAST_VS_BUDGET,
        ],
    },

    ProductLevel.NEAR_PRODUCT.value: {
        "base": [
            DocumentType.ARCHITECTURE_DOC,
            DocumentType.OPERATIONAL_RUNBOOK,
            DocumentType.SECURITY_SUMMARY,
            DocumentType.COST_EFFORT_SUMMARY,
        ],
        "platform": [
            DocumentType.SLO_SLA,
            DocumentType.PLATFORM_ACCEPTANCE,
        ],
        "donor": [
            DocumentType.FULL_ACCEPTANCE_PACKAGE,
            DocumentType.MULTI_DONOR_SPLIT,
            DocumentType.INDICATORS_STATUS,
        ],
    },
}


@dataclass
class DocumentPackage:
    """Package of documents for a specific context."""
    product_level: str
    is_platform_module: bool
    has_donors: bool
    base_documents: List[DocumentTemplate]
    platform_documents: List[DocumentTemplate]
    donor_documents: List[DocumentTemplate]
    total_documents: int
    total_pages: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "product_level": self.product_level,
            "is_platform_module": self.is_platform_module,
            "has_donors": self.has_donors,
            "base_documents": [
                {
                    "type": d.doc_type.value,
                    "name": d.name,
                    "description": d.description,
                    "category": d.category.value,
                    "estimated_pages": d.estimated_pages,
                    "sections": d.sections,
                    "is_required": d.is_required,
                    "output_formats": d.output_formats,
                }
                for d in self.base_documents
            ],
            "platform_documents": [
                {
                    "type": d.doc_type.value,
                    "name": d.name,
                    "description": d.description,
                    "category": d.category.value,
                    "estimated_pages": d.estimated_pages,
                    "sections": d.sections,
                    "is_required": d.is_required,
                    "output_formats": d.output_formats,
                }
                for d in self.platform_documents
            ],
            "donor_documents": [
                {
                    "type": d.doc_type.value,
                    "name": d.name,
                    "description": d.description,
                    "category": d.category.value,
                    "estimated_pages": d.estimated_pages,
                    "sections": d.sections,
                    "is_required": d.is_required,
                    "output_formats": d.output_formats,
                }
                for d in self.donor_documents
            ],
            "total_documents": self.total_documents,
            "total_pages": self.total_pages,
        }


class DocumentMatrixService:
    """
    Service for document matrix operations.

    Determines which documents to generate based on:
    - Product Level
    - Whether it's a platform module
    - Whether there are donors involved
    """

    def get_document_package(
        self,
        product_level: str,
        is_platform_module: bool = False,
        has_donors: bool = False,
    ) -> DocumentPackage:
        """
        Get document package for given context.

        Args:
            product_level: Product level (rnd_spike, prototype, etc.)
            is_platform_module: Whether this is intended for platform
            has_donors: Whether there are donors/grants involved

        Returns:
            DocumentPackage with all applicable documents
        """
        # Normalize product level
        if product_level not in DOCUMENT_MATRIX:
            product_level = ProductLevel.PROTOTYPE.value

        matrix = DOCUMENT_MATRIX[product_level]

        # Get base documents (always included)
        base_docs = [
            DOCUMENT_TEMPLATES[doc_type]
            for doc_type in matrix["base"]
            if doc_type in DOCUMENT_TEMPLATES
        ]

        # Get platform documents (if applicable)
        platform_docs = []
        if is_platform_module:
            platform_docs = [
                DOCUMENT_TEMPLATES[doc_type]
                for doc_type in matrix["platform"]
                if doc_type in DOCUMENT_TEMPLATES
            ]

        # Get donor documents (if applicable)
        donor_docs = []
        if has_donors:
            donor_docs = [
                DOCUMENT_TEMPLATES[doc_type]
                for doc_type in matrix["donor"]
                if doc_type in DOCUMENT_TEMPLATES
            ]

        # Calculate totals
        all_docs = base_docs + platform_docs + donor_docs
        total_pages = sum(d.estimated_pages for d in all_docs)

        return DocumentPackage(
            product_level=product_level,
            is_platform_module=is_platform_module,
            has_donors=has_donors,
            base_documents=base_docs,
            platform_documents=platform_docs,
            donor_documents=donor_docs,
            total_documents=len(all_docs),
            total_pages=total_pages,
        )

    def get_all_templates(self) -> List[Dict[str, Any]]:
        """Get all available document templates."""
        return [
            {
                "type": template.doc_type.value,
                "name": template.name,
                "description": template.description,
                "category": template.category.value,
                "estimated_pages": template.estimated_pages,
                "sections": template.sections,
                "is_required": template.is_required,
                "output_formats": template.output_formats,
            }
            for template in DOCUMENT_TEMPLATES.values()
        ]

    def get_template(self, doc_type: str) -> DocumentTemplate:
        """Get specific document template."""
        try:
            return DOCUMENT_TEMPLATES[DocumentType(doc_type)]
        except (ValueError, KeyError):
            raise ValueError(f"Unknown document type: {doc_type}")

    def get_matrix_summary(self) -> Dict[str, Any]:
        """Get summary of document matrix by product level."""
        summary = {}
        for level, docs in DOCUMENT_MATRIX.items():
            base_count = len(docs["base"])
            platform_count = len(docs["platform"])
            donor_count = len(docs["donor"])

            base_pages = sum(
                DOCUMENT_TEMPLATES[d].estimated_pages
                for d in docs["base"]
                if d in DOCUMENT_TEMPLATES
            )
            platform_pages = sum(
                DOCUMENT_TEMPLATES[d].estimated_pages
                for d in docs["platform"]
                if d in DOCUMENT_TEMPLATES
            )
            donor_pages = sum(
                DOCUMENT_TEMPLATES[d].estimated_pages
                for d in docs["donor"]
                if d in DOCUMENT_TEMPLATES
            )

            summary[level] = {
                "base": {"count": base_count, "pages": base_pages},
                "platform": {"count": platform_count, "pages": platform_pages},
                "donor": {"count": donor_count, "pages": donor_pages},
                "total": {
                    "count": base_count + platform_count + donor_count,
                    "pages": base_pages + platform_pages + donor_pages,
                },
            }

        return summary

    def generate_document(
        self,
        doc_type: DocumentType,
        data: Dict[str, Any],
        context: Dict[str, Any],
        language: str = "uk",
    ) -> str:
        """
        Generate document content based on type.

        Args:
            doc_type: Document type to generate
            data: Analysis data from MetricSet
            context: Additional context (project name, dates, etc.)
            language: Output language (uk, en)

        Returns:
            Generated document content in Markdown format
        """
        template = self.get_template(doc_type.value)

        # Common header
        project_name = context.get("project_name", data.get("repo_name", "Unknown Project"))
        date = datetime.now().strftime("%Y-%m-%d")

        generators = {
            DocumentType.RND_SUMMARY: self._generate_rnd_summary,
            DocumentType.TECH_NOTE: self._generate_tech_note,
            DocumentType.TECH_REPORT: self._generate_tech_report,
            DocumentType.QUALITY_REPORT: self._generate_quality_report,
            DocumentType.COST_ESTIMATE: self._generate_cost_estimate,
            DocumentType.TASK_LIST: self._generate_task_list,
            DocumentType.BACKLOG: self._generate_backlog,
            DocumentType.WORKPLAN_ALIGNMENT: self._generate_workplan_alignment,
            DocumentType.BUDGET_STATUS: self._generate_budget_status,
            DocumentType.INDICATORS_STATUS: self._generate_indicators_status,
            DocumentType.DONOR_ONE_PAGER: self._generate_donor_one_pager,
            DocumentType.DONOR_TECH_REPORT: self._generate_donor_tech_report,
        }

        generator = generators.get(doc_type)
        if generator:
            return generator(data, context, language, template, project_name, date)

        # Default: generate sections skeleton
        return self._generate_default(data, context, language, template, project_name, date)

    def _generate_rnd_summary(
        self, data: Dict, context: Dict, lang: str, template: DocumentTemplate, project: str, date: str
    ) -> str:
        """Generate R&D Summary document."""
        title = "Резюме R&D" if lang == "uk" else "R&D Summary"
        return f"""# {title}: {project}

**Дата:** {date}

## Гіпотеза

{context.get('hypothesis', 'Описати гіпотезу, яку перевіряли...')}

## Виконана робота

- Проаналізовано репозиторій: **{data.get('files_total', 'N/A')}** файлів, **{data.get('loc_total', 'N/A')}** рядків коду
- Product Level: **{data.get('product_level', 'prototype')}**
- Repo Health: **{data.get('score_repo_health_total', 'N/A')}/12**
- Tech Debt: **{data.get('score_tech_debt_total', 'N/A')}/15**

## Ключові знахідки

1. {context.get('finding_1', 'Знахідка 1...')}
2. {context.get('finding_2', 'Знахідка 2...')}
3. {context.get('finding_3', 'Знахідка 3...')}

## Наступні кроки

- [ ] {context.get('next_step_1', 'Наступний крок 1...')}
- [ ] {context.get('next_step_2', 'Наступний крок 2...')}
- [ ] {context.get('next_step_3', 'Наступний крок 3...')}

---
*Згенеровано: Repo Auditor*
"""

    def _generate_tech_note(
        self, data: Dict, context: Dict, lang: str, template: DocumentTemplate, project: str, date: str
    ) -> str:
        """Generate Technical Note document."""
        title = "Технічна нотатка" if lang == "uk" else "Technical Note"
        return f"""# {title}: {project}

**Дата:** {date}

## Огляд

{context.get('overview', 'Короткий опис проекту та його призначення...')}

## Архітектурна ідея

{context.get('architecture_idea', 'Опис архітектурного підходу...')}

### Основні компоненти

- **Frontend:** {data.get('frontend_tech', 'N/A')}
- **Backend:** {data.get('backend_tech', 'N/A')}
- **Database:** {data.get('database_tech', 'N/A')}

## Стек технологій

| Категорія | Технологія | Обґрунтування |
|-----------|------------|---------------|
| Мова | {context.get('main_language', 'Python/TypeScript')} | - |
| Framework | {context.get('framework', 'N/A')} | - |
| CI/CD | {data.get('has_ci', False) and 'Наявний' or 'Відсутній'} | - |
| Docker | {data.get('has_dockerfile', False) and 'Наявний' or 'Відсутній'} | - |

## Ризики та обмеження

1. {context.get('risk_1', 'Ризик 1...')}
2. {context.get('risk_2', 'Ризик 2...')}

---
*Згенеровано: Repo Auditor*
"""

    def _generate_tech_report(
        self, data: Dict, context: Dict, lang: str, template: DocumentTemplate, project: str, date: str
    ) -> str:
        """Generate full Technical Report."""
        title = "Технічний звіт" if lang == "uk" else "Technical Report"
        return f"""# {title}: {project}

**Дата:** {date}
**Версія:** 1.0

---

## Executive Summary

Проект **{project}** проаналізовано автоматичною системою аудиту репозиторіїв.

| Метрика | Значення |
|---------|----------|
| Product Level | **{data.get('product_level', 'prototype')}** |
| Repo Health | **{data.get('score_repo_health_total', 'N/A')}/12** |
| Tech Debt | **{data.get('score_tech_debt_total', 'N/A')}/15** |
| Complexity | **{data.get('complexity', 'medium')}** |
| Files | **{data.get('files_total', 'N/A')}** |
| LOC | **{data.get('loc_total', 'N/A')}** |

## Функціональність

{context.get('functionality_description', 'Опис основної функціональності системи...')}

### Реалізовані можливості

- {context.get('feature_1', 'Функція 1')}
- {context.get('feature_2', 'Функція 2')}
- {context.get('feature_3', 'Функція 3')}

## Архітектура

### Структура проекту

```
{data.get('structure_description', 'src/  tests/  docs/')}
```

### Якість структури

- Documentation: **{data.get('score_documentation', 'N/A')}/3**
- Structure: **{data.get('score_structure', 'N/A')}/3**
- Runability: **{data.get('score_runability', 'N/A')}/3**
- History: **{data.get('score_history', 'N/A')}/3**

## Quality Metrics

### Tech Debt Analysis

| Категорія | Оцінка | Опис |
|-----------|--------|------|
| Architecture | **{data.get('score_architecture', 'N/A')}/3** | Структура коду |
| Code Quality | **{data.get('score_code_quality', 'N/A')}/3** | Якість коду |
| Testing | **{data.get('score_testing', 'N/A')}/3** | Тестове покриття |
| Infrastructure | **{data.get('score_infrastructure', 'N/A')}/3** | CI/CD, Docker |
| Security | **{data.get('score_security', 'N/A')}/3** | Безпека |

## Обмеження та ризики

1. {context.get('limitation_1', 'Обмеження 1...')}
2. {context.get('limitation_2', 'Обмеження 2...')}

## Рекомендації

### Пріоритет 1 (Critical)
- {context.get('recommendation_p1', 'Критична рекомендація...')}

### Пріоритет 2 (High)
- {context.get('recommendation_p2', 'Важлива рекомендація...')}

### Пріоритет 3 (Medium)
- {context.get('recommendation_p3', 'Середньої важливості...')}

---
*Згенеровано: Repo Auditor | {date}*
"""

    def _generate_quality_report(
        self, data: Dict, context: Dict, lang: str, template: DocumentTemplate, project: str, date: str
    ) -> str:
        """Generate Quality Report."""
        title = "Звіт якості" if lang == "uk" else "Quality Report"
        return f"""# {title}: {project}

**Дата:** {date}

## Summary

| Метрика | Значення | Статус |
|---------|----------|--------|
| Product Level | {data.get('product_level', 'prototype')} | {'✅' if data.get('product_level') in ['platform_module', 'near_product'] else '⚠️'} |
| Repo Health | {data.get('score_repo_health_total', 'N/A')}/12 | {'✅' if (data.get('score_repo_health_total', 0) or 0) >= 8 else '⚠️'} |
| Tech Debt | {data.get('score_tech_debt_total', 'N/A')}/15 | {'✅' if (data.get('score_tech_debt_total', 0) or 0) >= 10 else '⚠️'} |
| Complexity | {data.get('complexity', 'medium')} | - |

## Repo Health Breakdown

| Категорія | Оцінка | Макс | % |
|-----------|--------|------|---|
| Documentation | {data.get('score_documentation', 0)} | 3 | {int((data.get('score_documentation', 0) or 0) / 3 * 100)}% |
| Structure | {data.get('score_structure', 0)} | 3 | {int((data.get('score_structure', 0) or 0) / 3 * 100)}% |
| Runability | {data.get('score_runability', 0)} | 3 | {int((data.get('score_runability', 0) or 0) / 3 * 100)}% |
| History | {data.get('score_history', 0)} | 3 | {int((data.get('score_history', 0) or 0) / 3 * 100)}% |

## Tech Debt Breakdown

| Категорія | Оцінка | Макс | % |
|-----------|--------|------|---|
| Architecture | {data.get('score_architecture', 0)} | 3 | {int((data.get('score_architecture', 0) or 0) / 3 * 100)}% |
| Code Quality | {data.get('score_code_quality', 0)} | 3 | {int((data.get('score_code_quality', 0) or 0) / 3 * 100)}% |
| Testing | {data.get('score_testing', 0)} | 3 | {int((data.get('score_testing', 0) or 0) / 3 * 100)}% |
| Infrastructure | {data.get('score_infrastructure', 0)} | 3 | {int((data.get('score_infrastructure', 0) or 0) / 3 * 100)}% |
| Security | {data.get('score_security', 0)} | 3 | {int((data.get('score_security', 0) or 0) / 3 * 100)}% |

## Product Level Analysis

**Current Level:** {data.get('product_level', 'prototype')}

### Критерії для наступного рівня

{self._get_next_level_criteria(data.get('product_level', 'prototype'))}

---
*Згенеровано: Repo Auditor*
"""

    def _generate_cost_estimate(
        self, data: Dict, context: Dict, lang: str, template: DocumentTemplate, project: str, date: str
    ) -> str:
        """Generate Cost Estimate document."""
        title = "Оцінка вартості" if lang == "uk" else "Cost Estimate"
        return f"""# {title}: {project}

**Дата:** {date}

## Summary

| Параметр | Значення |
|----------|----------|
| LOC | {data.get('loc_total', 'N/A')} |
| Files | {data.get('files_total', 'N/A')} |
| Complexity | {data.get('complexity', 'medium')} |

## Оцінка за методологіями

### COCOMO II (Primary)

| Метрика | Значення |
|---------|----------|
| Effort (PM) | {data.get('cocomo_effort_pm', 'N/A')} |
| Hours | {data.get('cocomo_hours', 'N/A')} |
| Cost Range | ${data.get('cocomo_cost_min', 'N/A')} - ${data.get('cocomo_cost_max', 'N/A')} |

### Industry Benchmarks

| Методологія | Години | Вартість |
|-------------|--------|----------|
| COCOMO II | {data.get('cocomo_hours', '-')} | ${data.get('cocomo_cost_typical', '-')} |
| Gartner | - | - |
| IEEE | - | - |

## Regional Estimates

| Регіон | Rate/hr | Вартість |
|--------|---------|----------|
| EU | $65-85 | - |
| Ukraine | $30-50 | - |
| US | $100-150 | - |

## ROI Analysis

{context.get('roi_analysis', 'ROI аналіз буде додано...')}

---
*Згенеровано: Repo Auditor*
"""

    def _generate_task_list(
        self, data: Dict, context: Dict, lang: str, template: DocumentTemplate, project: str, date: str
    ) -> str:
        """Generate Task List document."""
        title = "Список задач" if lang == "uk" else "Task List"
        tasks = context.get('tasks', [])

        task_sections = ""
        for priority in ['P1', 'P2', 'P3']:
            priority_tasks = [t for t in tasks if t.get('priority') == priority]
            if priority_tasks:
                task_sections += f"\n### {priority} Tasks\n\n"
                for t in priority_tasks:
                    task_sections += f"- [ ] **{t.get('title', 'Task')}** ({t.get('hours', '?')}h)\n"
                    task_sections += f"  {t.get('description', '')}\n"

        if not task_sections:
            task_sections = """
### P1 Tasks (Critical)

- [ ] **Задача 1** (8h)
  Опис задачі...

### P2 Tasks (High)

- [ ] **Задача 2** (4h)
  Опис задачі...

### P3 Tasks (Medium)

- [ ] **Задача 3** (2h)
  Опис задачі...
"""

        return f"""# {title}: {project}

**Дата:** {date}

## Summary

| Метрика | Значення |
|---------|----------|
| Total Tasks | {len(tasks) if tasks else 'N/A'} |
| Total Hours | {sum(t.get('hours', 0) for t in tasks) if tasks else 'N/A'} |

{task_sections}

---
*Згенеровано: Repo Auditor*
"""

    def _generate_backlog(
        self, data: Dict, context: Dict, lang: str, template: DocumentTemplate, project: str, date: str
    ) -> str:
        """Generate Backlog document."""
        title = "Backlog" if lang == "uk" else "Backlog"
        return f"""# {title}: {project}

**Дата:** {date}

## Priority Tasks

{context.get('priority_tasks', '- [ ] Task 1; - [ ] Task 2; - [ ] Task 3')}

## Improvement Items

{context.get('improvements', '- Покращення 1; - Покращення 2')}

## Technical Debt Items

{context.get('tech_debt_items', '- Технічний борг 1; - Технічний борг 2')}

## Future Ideas

{context.get('future_ideas', '- Ідея 1; - Ідея 2')}

---
*Згенеровано: Repo Auditor*
"""

    def _generate_workplan_alignment(
        self, data: Dict, context: Dict, lang: str, template: DocumentTemplate, project: str, date: str
    ) -> str:
        """Generate Workplan Alignment Report."""
        title = "Звіт відповідності робочому плану" if lang == "uk" else "Workplan Alignment Report"
        return f"""# {title}: {project}

**Дата:** {date}
**Період:** {context.get('period', 'Q1 2025')}

## Overview

| Метрика | Значення |
|---------|----------|
| Total Activities | {context.get('total_activities', 'N/A')} |
| Linked Repos | {context.get('linked_repos', 'N/A')} |
| Coverage | {context.get('coverage', 'N/A')}% |

## Activity Mapping

| WP ID | Activity | Status | Repos | Progress |
|-------|----------|--------|-------|----------|
| {context.get('wp_id_1', 'WP-001')} | {context.get('activity_1', 'Activity 1')} | {context.get('status_1', 'In Progress')} | {context.get('repos_1', '1')} | {context.get('progress_1', '50')}% |
| {context.get('wp_id_2', 'WP-002')} | {context.get('activity_2', 'Activity 2')} | {context.get('status_2', 'Completed')} | {context.get('repos_2', '2')} | {context.get('progress_2', '100')}% |

## Progress Status

### Completed Activities
{context.get('completed_activities', '- Завершена активність 1')}

### In Progress
{context.get('in_progress_activities', '- Поточна активність 1')}

### Deviations
{context.get('deviations', 'Відхилень немає')}

---
*Згенеровано: Repo Auditor*
"""

    def _generate_budget_status(
        self, data: Dict, context: Dict, lang: str, template: DocumentTemplate, project: str, date: str
    ) -> str:
        """Generate Budget Status Report."""
        title = "Статус бюджету" if lang == "uk" else "Budget Status Report"
        return f"""# {title}: {project}

**Дата:** {date}
**Період:** {context.get('period', 'Q1 2025')}

## Summary

| Метрика | Значення |
|---------|----------|
| Total Budget | ${context.get('total_budget', 'N/A')} |
| Spent | ${context.get('spent', 'N/A')} |
| Remaining | ${context.get('remaining', 'N/A')} |
| Burn Rate | {context.get('burn_rate', 'N/A')}% |

## Line-by-Line Status

| Budget Line | Allocated | Spent | Remaining | % Used |
|-------------|-----------|-------|-----------|--------|
| {context.get('line_1', 'Personnel')} | ${context.get('line_1_allocated', '0')} | ${context.get('line_1_spent', '0')} | ${context.get('line_1_remaining', '0')} | {context.get('line_1_percent', '0')}% |
| {context.get('line_2', 'Equipment')} | ${context.get('line_2_allocated', '0')} | ${context.get('line_2_spent', '0')} | ${context.get('line_2_remaining', '0')} | {context.get('line_2_percent', '0')}% |

## Burn Rate Analysis

{context.get('burn_rate_analysis', 'Аналіз витрат за період...')}

## Forecast

{context.get('forecast', 'Прогноз витрат до кінця періоду...')}

---
*Згенеровано: Repo Auditor*
"""

    def _generate_indicators_status(
        self, data: Dict, context: Dict, lang: str, template: DocumentTemplate, project: str, date: str
    ) -> str:
        """Generate Indicators Status Report."""
        title = "Статус індикаторів" if lang == "uk" else "Indicators Status Report"
        return f"""# {title}: {project}

**Дата:** {date}

## Dashboard

| Індикатор | Target | Actual | Progress | Status |
|-----------|--------|--------|----------|--------|
| {context.get('indicator_1_name', 'Repos Analyzed')} | {context.get('indicator_1_target', '10')} | {context.get('indicator_1_actual', '0')} | {context.get('indicator_1_progress', '0')}% | {context.get('indicator_1_status', '🔴')} |
| {context.get('indicator_2_name', 'Avg Quality')} | {context.get('indicator_2_target', '8')} | {context.get('indicator_2_actual', '0')} | {context.get('indicator_2_progress', '0')}% | {context.get('indicator_2_status', '🔴')} |

## Progress Details

### {context.get('indicator_1_name', 'Indicator 1')}

{context.get('indicator_1_details', 'Деталі прогресу...')}

### {context.get('indicator_2_name', 'Indicator 2')}

{context.get('indicator_2_details', 'Деталі прогресу...')}

## Trends

{context.get('trends', 'Аналіз трендів...')}

## Risks

{context.get('risks', 'Ризики для досягнення цілей...')}

---
*Згенеровано: Repo Auditor*
"""

    def _generate_donor_one_pager(
        self, data: Dict, context: Dict, lang: str, template: DocumentTemplate, project: str, date: str
    ) -> str:
        """Generate Donor One-Pager."""
        title = "R&D One-Pager для донора" if lang == "uk" else "R&D One-Pager for Donor"
        return f"""# {title}

**Проект:** {project}
**Дата:** {date}

---

## 🎯 Objective

{context.get('objective', 'Мета R&D роботи...')}

## 🔧 Work Done

- {context.get('work_1', 'Виконана робота 1')}
- {context.get('work_2', 'Виконана робота 2')}
- {context.get('work_3', 'Виконана робота 3')}

## 📊 Results

| Метрика | Значення |
|---------|----------|
| Product Level | {data.get('product_level', 'N/A')} |
| Quality Score | {data.get('score_repo_health_total', 'N/A')}/12 |
| LOC | {data.get('loc_total', 'N/A')} |

## ➡️ Next Steps

1. {context.get('next_1', 'Наступний крок 1')}
2. {context.get('next_2', 'Наступний крок 2')}

---
*Repo Auditor | {date}*
"""

    def _generate_donor_tech_report(
        self, data: Dict, context: Dict, lang: str, template: DocumentTemplate, project: str, date: str
    ) -> str:
        """Generate Donor Technical Report."""
        title = "Технічний звіт для донора" if lang == "uk" else "Donor Technical Report"
        return f"""# {title}: {project}

**Дата:** {date}
**Грант:** {context.get('grant_name', 'N/A')}

---

## Executive Summary

{context.get('executive_summary', 'Короткий опис технічних результатів...')}

## Technical Overview

### Project Metrics

| Метрика | Значення |
|---------|----------|
| Product Level | {data.get('product_level', 'N/A')} |
| Repo Health | {data.get('score_repo_health_total', 'N/A')}/12 |
| Tech Debt | {data.get('score_tech_debt_total', 'N/A')}/15 |
| Files | {data.get('files_total', 'N/A')} |
| LOC | {data.get('loc_total', 'N/A')} |

### Technologies Used

{context.get('technologies', '- Technology 1; - Technology 2')}

## Outcomes

### Achieved Results

{context.get('achieved_results', '1. Результат 1; 2. Результат 2')}

### Impact

{context.get('impact', 'Опис впливу на проект/організацію...')}

## Budget Alignment

| Category | Allocated | Used | Remaining |
|----------|-----------|------|-----------|
| Development | ${context.get('dev_allocated', '0')} | ${context.get('dev_used', '0')} | ${context.get('dev_remaining', '0')} |
| Infrastructure | ${context.get('infra_allocated', '0')} | ${context.get('infra_used', '0')} | ${context.get('infra_remaining', '0')} |

---
*Згенеровано: Repo Auditor*
"""

    def _generate_default(
        self, data: Dict, context: Dict, lang: str, template: DocumentTemplate, project: str, date: str
    ) -> str:
        """Generate default document with template sections."""
        sections_content = "\n\n".join([
            f"## {section}\n\n{context.get(section.lower().replace(' ', '_'), f'Content for {section}...')}"
            for section in template.sections
        ])

        return f"""# {template.name}: {project}

**Дата:** {date}
**Тип документа:** {template.doc_type.value}

---

{sections_content}

---
*Згенеровано: Repo Auditor*
"""

    def _get_next_level_criteria(self, current_level: str) -> str:
        """Get criteria for reaching next product level."""
        criteria = {
            "rnd_spike": """
Для переходу на **PROTOTYPE**:
- [ ] Repo Health >= 4/12
- [ ] Наявна базова документація
- [ ] Проект запускається локально""",
            "prototype": """
Для переходу на **INTERNAL_TOOL**:
- [ ] Repo Health >= 6/12
- [ ] Tech Debt >= 6/15
- [ ] Наявні тести
- [ ] CI/CD налаштований""",
            "internal_tool": """
Для переходу на **PLATFORM_MODULE**:
- [ ] Repo Health >= 8/12
- [ ] Tech Debt >= 10/15
- [ ] Документація API
- [ ] Інтеграційні специфікації""",
            "platform_module": """
Для переходу на **NEAR_PRODUCT**:
- [ ] Repo Health >= 10/12
- [ ] Tech Debt >= 12/15
- [ ] SLO/SLA визначені
- [ ] Security audit пройдено""",
            "near_product": """
**Максимальний рівень досягнуто!**
- Підтримка поточного рівня якості
- Регулярний моніторинг метрик""",
        }
        return criteria.get(current_level, "Критерії не визначені")


# Singleton instance
document_matrix_service = DocumentMatrixService()
