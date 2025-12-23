# ТЕХНИЧЕСКОЕ ЗАДАНИЕ
## Система генерации документов и отслеживания проектов Repo Auditor

**Версия:** 2.0
**Дата:** 2025-12-04
**Статус:** К реализации

---

## 0. НАСТРОЙКА И ЗАПУСК

### 0.1 Требования

```
- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Git
```

### 0.2 Установка Backend

```bash
# Клонирование и переход в директорию
cd /Users/maksymdemchenko/repo-auditor/backend

# Виртуальное окружение
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# или: venv\Scripts\activate  # Windows

# Зависимости
pip install -r requirements.txt

# Переменные окружения (создать .env)
cat > .env << 'EOF'
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/repo_auditor
SECRET_KEY=your-secret-key-here
GITHUB_TOKEN=ghp_your_token_here  # Опционально
DEBUG=true
EOF

# Миграции БД
alembic upgrade head

# Запуск (development)
uvicorn app.main:app --reload --host 0.0.0.0 --port 7777
```

### 0.3 Установка Frontend

```bash
# Переход в директорию UI
cd /Users/maksymdemchenko/repo-auditor/ui

# Зависимости
npm install

# Переменные окружения
cat > .env.local << 'EOF'
NEXT_PUBLIC_API_URL=http://localhost:7777
EOF

# Запуск (development)
npm run dev -- -p 3333
```

### 0.4 Проверка работоспособности

```bash
# Backend health check
curl http://localhost:7777/health
# Ожидаемый ответ: {"status":"ok","service":"repo-auditor"}

# Frontend
open http://localhost:3333

# API documentation
open http://localhost:7777/docs
```

### 0.5 Production Build

```bash
# Backend (с gunicorn)
pip install gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:7777

# Frontend
cd ui
npm run build
npm start -- -p 3333
```

### 0.6 Docker (опционально)

```bash
# Backend
docker build -t repo-auditor-backend ./backend
docker run -p 7777:7777 --env-file .env repo-auditor-backend

# Frontend
docker build -t repo-auditor-ui ./ui
docker run -p 3333:3333 repo-auditor-ui

# Или docker-compose
docker-compose up -d
```

---

## 1. ОБЩЕЕ ОПИСАНИЕ

### 1.1 Назначение системы

Расширение платформы Repo Auditor для:
- Автоматической генерации пакетов документов на основе Product Level
- Отслеживания выполнения рабочих планов (Workplan)
- Контроля бюджетных линий
- Мониторинга индикаторов проекта
- Поддержки мультидонорского финансирования

### 1.2 Целевые пользователи

| Роль | Использование |
|------|---------------|
| R&D Team Lead | Генерация tech-отчётов, оценка стоимости |
| Project Manager | Workplan tracking, budget control |
| Grant Manager | Donor reports, compliance, indicators |
| Technical Writer | Документация, runbooks |

### 1.3 Ключевые модули

```
┌─────────────────────────────────────────────────────────────┐
│                     REPO AUDITOR v2.0                       │
├─────────────────────────────────────────────────────────────┤
│  [Analysis]  [Documents]  [Workplan]  [Budget]  [Donors]    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐    │
│  │   Analyzer   │   │  Doc Matrix  │   │   Workplan   │    │
│  │   Engine     │──>│  Generator   │   │   Tracker    │    │
│  └──────────────┘   └──────────────┘   └──────────────┘    │
│         │                  │                   │            │
│         v                  v                   v            │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐    │
│  │   Scoring    │   │   Template   │   │   Budget     │    │
│  │   Engine     │   │   Engine     │   │   Tracker    │    │
│  └──────────────┘   └──────────────┘   └──────────────┘    │
│         │                  │                   │            │
│         v                  v                   v            │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐    │
│  │  Estimation  │   │   Export     │   │  Indicators  │    │
│  │    Suite     │   │   Service    │   │   Tracker    │    │
│  └──────────────┘   └──────────────┘   └──────────────┘    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. МАТРИЦА ДОКУМЕНТОВ ПО PRODUCT LEVEL

### 2.1 Структура данных

```python
# backend/app/services/document_matrix.py

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional

class ProductLevel(str, Enum):
    RND_SPIKE = "rnd_spike"
    PROTOTYPE = "prototype"
    INTERNAL_TOOL = "internal_tool"
    PLATFORM_MODULE = "platform_module"
    NEAR_PRODUCT = "near_product"

class DocumentType(str, Enum):
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

@dataclass
class DocumentTemplate:
    id: DocumentType
    name: str
    description: str
    generator: str  # Function name to generate
    required_data: List[str]  # Required input data
    output_format: List[str]  # md, pdf, docx, json
    is_required: bool = False
    is_auto_generated: bool = True

@dataclass
class DocumentPackage:
    product_level: ProductLevel
    base_documents: List[DocumentType]
    platform_documents: List[DocumentType]  # If is_platform_module
    donor_documents: List[DocumentType]     # If has_donors
```

### 2.2 Матрица документов

```python
DOCUMENT_MATRIX = {
    ProductLevel.RND_SPIKE: {
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

    ProductLevel.PROTOTYPE: {
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

    ProductLevel.INTERNAL_TOOL: {
        "base": [
            DocumentType.TECH_REPORT,
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

    ProductLevel.PLATFORM_MODULE: {
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

    ProductLevel.NEAR_PRODUCT: {
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
```

---

## 3. WORKPLAN TRACKING

### 3.1 Модель данных

```python
# backend/app/core/models/workplan.py

from sqlalchemy import Column, String, Integer, Float, Date, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum

class ActivityStatus(str, enum.Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DELAYED = "delayed"
    BLOCKED = "blocked"

class Workplan(Base):
    __tablename__ = "workplans"

    id = Column(String, primary_key=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    donor_id = Column(String, ForeignKey("donors.id"), nullable=True)
    name = Column(String, nullable=False)
    version = Column(String, default="1.0")
    start_date = Column(Date)
    end_date = Column(Date)
    total_budget = Column(Float)
    currency = Column(String, default="USD")

    # Relationships
    activities = relationship("WorkplanActivity", back_populates="workplan")
    project = relationship("Project", back_populates="workplans")

class WorkplanActivity(Base):
    __tablename__ = "workplan_activities"

    id = Column(String, primary_key=True)
    workplan_id = Column(String, ForeignKey("workplans.id"), nullable=False)
    wp_id = Column(String, nullable=False)  # e.g., "WP1.2.3"
    title = Column(String, nullable=False)
    description = Column(String)

    # Timing
    planned_start = Column(Date)
    planned_end = Column(Date)
    actual_start = Column(Date)
    actual_end = Column(Date)

    # Effort
    planned_hours = Column(Float)
    actual_hours = Column(Float, default=0)

    # Budget
    budget_line_id = Column(String, ForeignKey("budget_lines.id"))
    planned_cost = Column(Float)
    actual_cost = Column(Float, default=0)

    # Status
    status = Column(Enum(ActivityStatus), default=ActivityStatus.NOT_STARTED)
    progress_percent = Column(Integer, default=0)

    # Linked repositories
    linked_repos = Column(JSON, default=list)  # List of repo analysis IDs

    # Relationships
    workplan = relationship("Workplan", back_populates="activities")
    budget_line = relationship("BudgetLine")
```

### 3.2 API Endpoints

```python
# backend/app/api/routes/workplan.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from pydantic import BaseModel
from datetime import date

router = APIRouter(prefix="/api/workplan", tags=["workplan"])

# === Request/Response Models ===

class ActivityCreate(BaseModel):
    wp_id: str
    title: str
    description: Optional[str]
    planned_start: date
    planned_end: date
    planned_hours: float
    planned_cost: Optional[float]
    budget_line_id: Optional[str]

class ActivityUpdate(BaseModel):
    actual_start: Optional[date]
    actual_end: Optional[date]
    actual_hours: Optional[float]
    actual_cost: Optional[float]
    status: Optional[str]
    progress_percent: Optional[int]
    linked_repos: Optional[List[str]]

class WorkplanCreate(BaseModel):
    project_id: str
    donor_id: Optional[str]
    name: str
    start_date: date
    end_date: date
    total_budget: Optional[float]
    currency: str = "USD"
    activities: List[ActivityCreate]

class WorkplanImport(BaseModel):
    """Import from Excel/CSV"""
    project_id: str
    donor_id: Optional[str]
    file_format: str  # excel, csv
    content_base64: str

# === Endpoints ===

@router.post("/create")
async def create_workplan(data: WorkplanCreate, db: AsyncSession = Depends(get_db)):
    """Create new workplan with activities."""
    pass

@router.post("/import")
async def import_workplan(data: WorkplanImport, db: AsyncSession = Depends(get_db)):
    """Import workplan from Excel/CSV file."""
    pass

@router.get("/{workplan_id}")
async def get_workplan(workplan_id: str, db: AsyncSession = Depends(get_db)):
    """Get workplan with all activities."""
    pass

@router.get("/{workplan_id}/progress")
async def get_workplan_progress(workplan_id: str, db: AsyncSession = Depends(get_db)):
    """Get aggregated progress report."""
    pass

@router.put("/activity/{activity_id}")
async def update_activity(
    activity_id: str,
    data: ActivityUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update activity status and progress."""
    pass

@router.post("/activity/{activity_id}/link-repo")
async def link_repo_to_activity(
    activity_id: str,
    analysis_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Link repository analysis to workplan activity."""
    pass

@router.get("/{workplan_id}/alignment-report")
async def generate_alignment_report(
    workplan_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Generate Workplan Alignment Report document."""
    pass
```

---

## 4. BUDGET TRACKING

### 4.1 Модель данных

```python
# backend/app/core/models/budget.py

class BudgetCategory(str, enum.Enum):
    PERSONNEL = "personnel"
    EQUIPMENT = "equipment"
    TRAVEL = "travel"
    SUBCONTRACTS = "subcontracts"
    OVERHEAD = "overhead"
    OTHER = "other"

class BudgetLine(Base):
    __tablename__ = "budget_lines"

    id = Column(String, primary_key=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    donor_id = Column(String, ForeignKey("donors.id"), nullable=True)

    code = Column(String, nullable=False)  # e.g., "1.1.1"
    name = Column(String, nullable=False)
    category = Column(Enum(BudgetCategory))

    # Amounts
    planned_amount = Column(Float, nullable=False)
    committed_amount = Column(Float, default=0)  # Allocated but not spent
    spent_amount = Column(Float, default=0)
    currency = Column(String, default="USD")

    # Limits
    flexibility_percent = Column(Float, default=10)  # Allowed variance

    # Period
    period_start = Column(Date)
    period_end = Column(Date)

    # Relationships
    transactions = relationship("BudgetTransaction", back_populates="budget_line")

class BudgetTransaction(Base):
    __tablename__ = "budget_transactions"

    id = Column(String, primary_key=True)
    budget_line_id = Column(String, ForeignKey("budget_lines.id"), nullable=False)

    date = Column(Date, nullable=False)
    amount = Column(Float, nullable=False)
    description = Column(String)
    reference = Column(String)  # Invoice/PO number

    # Linked entities
    activity_id = Column(String, ForeignKey("workplan_activities.id"))
    analysis_id = Column(String)  # Repo analysis that generated this cost

    # Relationships
    budget_line = relationship("BudgetLine", back_populates="transactions")
```

### 4.2 API Endpoints

```python
# backend/app/api/routes/budget.py

router = APIRouter(prefix="/api/budget", tags=["budget"])

@router.get("/project/{project_id}/status")
async def get_budget_status(
    project_id: str,
    donor_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get budget status report.

    Returns:
    - Per-line: planned, committed, spent, remaining
    - Aggregates by category
    - Burn rate analysis
    - Variance alerts
    """
    pass

@router.get("/project/{project_id}/forecast")
async def get_budget_forecast(
    project_id: str,
    months_ahead: int = 3,
    db: AsyncSession = Depends(get_db)
):
    """
    Forecast budget consumption.

    Uses:
    - Historical burn rate
    - Planned activities
    - Pending repo analyses costs
    """
    pass

@router.post("/line/{line_id}/transaction")
async def add_transaction(
    line_id: str,
    data: TransactionCreate,
    db: AsyncSession = Depends(get_db)
):
    """Add spending transaction to budget line."""
    pass

@router.post("/analysis/{analysis_id}/allocate")
async def allocate_analysis_cost(
    analysis_id: str,
    allocations: List[AllocationRequest],
    db: AsyncSession = Depends(get_db)
):
    """
    Allocate repository analysis cost to budget lines.

    For multi-donor: split cost across multiple lines.
    """
    pass

@router.get("/project/{project_id}/report")
async def generate_budget_report(
    project_id: str,
    donor_id: Optional[str] = None,
    format: str = "md",
    db: AsyncSession = Depends(get_db)
):
    """Generate Budget Status Report document."""
    pass
```

---

## 5. INDICATORS TRACKING

### 5.1 Модель данных

```python
# backend/app/core/models/indicators.py

class IndicatorType(str, enum.Enum):
    OUTPUT = "output"       # Deliverables
    OUTCOME = "outcome"     # Results
    IMPACT = "impact"       # Long-term effects
    PROCESS = "process"     # Activity metrics

class IndicatorUnit(str, enum.Enum):
    NUMBER = "number"
    PERCENT = "percent"
    HOURS = "hours"
    CURRENCY = "currency"
    BOOLEAN = "boolean"
    SCORE = "score"

class Indicator(Base):
    __tablename__ = "indicators"

    id = Column(String, primary_key=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    donor_id = Column(String, ForeignKey("donors.id"), nullable=True)

    code = Column(String, nullable=False)  # e.g., "IND-1.1"
    name = Column(String, nullable=False)
    description = Column(String)

    indicator_type = Column(Enum(IndicatorType))
    unit = Column(Enum(IndicatorUnit))

    # Targets
    baseline_value = Column(Float, default=0)
    target_value = Column(Float, nullable=False)
    current_value = Column(Float, default=0)

    # Reporting
    reporting_frequency = Column(String)  # monthly, quarterly, annually
    data_source = Column(String)

    # Auto-calculation from repos
    auto_calculate = Column(Boolean, default=False)
    calculation_formula = Column(String)  # e.g., "count(repos where product_level >= 'internal_tool')"

    # Relationships
    measurements = relationship("IndicatorMeasurement", back_populates="indicator")

class IndicatorMeasurement(Base):
    __tablename__ = "indicator_measurements"

    id = Column(String, primary_key=True)
    indicator_id = Column(String, ForeignKey("indicators.id"), nullable=False)

    date = Column(Date, nullable=False)
    value = Column(Float, nullable=False)
    note = Column(String)

    # Source
    source_type = Column(String)  # manual, auto, analysis
    source_id = Column(String)    # Analysis ID if auto

    # Relationships
    indicator = relationship("Indicator", back_populates="measurements")
```

### 5.2 Формулы автоматического расчёта

```python
# backend/app/services/indicator_calculator.py

class IndicatorCalculator:
    """Auto-calculate indicator values from repository analyses."""

    FORMULAS = {
        # Count repos at specific product level
        "count_platform_modules": """
            SELECT COUNT(*) FROM analyses
            WHERE product_level IN ('platform_module', 'near_product')
            AND project_id = :project_id
        """,

        # Average health score
        "avg_repo_health": """
            SELECT AVG(repo_health_total) FROM analyses
            WHERE project_id = :project_id
        """,

        # Total estimated hours
        "total_hours": """
            SELECT SUM(cost_estimate->>'hours_typical') FROM analyses
            WHERE project_id = :project_id
        """,

        # Documentation coverage
        "docs_coverage_percent": """
            SELECT
                COUNT(CASE WHEN has_readme AND has_docs_folder THEN 1 END) * 100.0 / COUNT(*)
            FROM analyses
            WHERE project_id = :project_id
        """,

        # Test coverage (repos with tests)
        "test_coverage_percent": """
            SELECT
                COUNT(CASE WHEN test_files_count > 0 THEN 1 END) * 100.0 / COUNT(*)
            FROM analyses
            WHERE project_id = :project_id
        """,
    }

    async def calculate(self, indicator: Indicator, db: AsyncSession) -> float:
        """Calculate indicator value based on formula."""
        pass

    async def update_all_auto_indicators(self, project_id: str, db: AsyncSession):
        """Recalculate all auto indicators for a project."""
        pass
```

### 5.3 API Endpoints

```python
# backend/app/api/routes/indicators.py

router = APIRouter(prefix="/api/indicators", tags=["indicators"])

@router.get("/project/{project_id}")
async def get_project_indicators(
    project_id: str,
    donor_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get all indicators with current values and progress."""
    pass

@router.post("/project/{project_id}/recalculate")
async def recalculate_indicators(
    project_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Recalculate all auto-indicators from analyses."""
    pass

@router.post("/{indicator_id}/measurement")
async def add_measurement(
    indicator_id: str,
    data: MeasurementCreate,
    db: AsyncSession = Depends(get_db)
):
    """Add manual measurement to indicator."""
    pass

@router.get("/project/{project_id}/report")
async def generate_indicators_report(
    project_id: str,
    donor_id: Optional[str] = None,
    format: str = "md",
    db: AsyncSession = Depends(get_db)
):
    """Generate Indicators Status Report document."""
    pass
```

---

## 6. MULTI-DONOR SUPPORT

### 6.1 Модель данных

```python
# backend/app/core/models/donor.py

class Donor(Base):
    __tablename__ = "donors"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    short_name = Column(String)  # Acronym
    donor_type = Column(String)  # grant, investor, internal, partner

    # Contact
    contact_name = Column(String)
    contact_email = Column(String)

    # Requirements
    reporting_requirements = Column(JSON)  # Templates, frequency, format
    compliance_requirements = Column(JSON)  # GDPR, HIPAA, etc.

    # Relationships
    allocations = relationship("DonorAllocation", back_populates="donor")

class DonorAllocation(Base):
    """Allocation of work/cost to a specific donor."""
    __tablename__ = "donor_allocations"

    id = Column(String, primary_key=True)
    donor_id = Column(String, ForeignKey("donors.id"), nullable=False)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)

    # What is allocated
    entity_type = Column(String)  # analysis, activity, cost
    entity_id = Column(String)

    # Allocation
    percent = Column(Float)  # Percentage of cost allocated to this donor
    amount = Column(Float)   # Fixed amount (if not percent)
    hours = Column(Float)    # Hours allocated

    # Justification
    justification = Column(String)

    # Relationships
    donor = relationship("Donor", back_populates="allocations")
```

### 6.2 Multi-Donor Split Service

```python
# backend/app/services/donor_allocator.py

class DonorAllocator:
    """Allocate costs across multiple donors."""

    async def allocate_analysis(
        self,
        analysis_id: str,
        allocations: List[Dict],  # [{donor_id, percent, justification}]
        db: AsyncSession
    ) -> List[DonorAllocation]:
        """
        Allocate analysis cost across donors.

        Rules:
        - Total must equal 100%
        - Each allocation creates budget transactions
        - Links to workplan activities if specified
        """
        pass

    async def generate_split_report(
        self,
        project_id: str,
        period_start: date,
        period_end: date,
        db: AsyncSession
    ) -> Dict:
        """
        Generate Multi-Donor Split Report.

        Returns per-donor:
        - Total hours
        - Total cost
        - Repos/activities covered
        - Budget line breakdown
        """
        pass

    async def validate_allocations(
        self,
        project_id: str,
        db: AsyncSession
    ) -> List[Dict]:
        """
        Validate that all allocations are consistent.

        Checks:
        - No over-allocation (>100%)
        - No unallocated work
        - Budget line alignment
        """
        pass
```

---

## 7. DOCUMENT GENERATORS

### 7.1 Базовый генератор

```python
# backend/app/services/document_generator.py

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from enum import Enum

class OutputFormat(str, Enum):
    MARKDOWN = "md"
    PDF = "pdf"
    DOCX = "docx"
    JSON = "json"
    HTML = "html"

class BaseDocumentGenerator(ABC):
    """Base class for all document generators."""

    def __init__(self, template_dir: Path):
        self.template_dir = template_dir

    @abstractmethod
    async def generate(
        self,
        data: Dict[str, Any],
        format: OutputFormat = OutputFormat.MARKDOWN
    ) -> bytes:
        """Generate document from data."""
        pass

    def _render_template(self, template_name: str, context: Dict) -> str:
        """Render Jinja2 template."""
        pass

    def _to_pdf(self, markdown: str) -> bytes:
        """Convert markdown to PDF."""
        pass

    def _to_docx(self, markdown: str) -> bytes:
        """Convert markdown to DOCX."""
        pass
```

### 7.2 Специфичные генераторы

```python
# backend/app/services/generators/

# === R&D Summary ===
class RNDSummaryGenerator(BaseDocumentGenerator):
    """
    Generates R&D Summary document.

    Content:
    - Hypothesis tested
    - What was done
    - Key findings
    - Next steps
    """

    async def generate(self, data: Dict) -> bytes:
        context = {
            "repo_name": data["repo_name"],
            "hypothesis": data.get("hypothesis", "—"),
            "work_done": self._extract_work_done(data["analysis"]),
            "findings": self._extract_findings(data["analysis"]),
            "next_steps": data["analysis"]["tasks"][:5],
            "effort": data["analysis"]["cost_estimate"],
        }
        return self._render_template("rnd_summary.md.j2", context)


# === Tech Report ===
class TechReportGenerator(BaseDocumentGenerator):
    """
    Generates Technical Report.

    Content:
    - Executive Summary
    - Architecture Overview
    - Technology Stack
    - Quality Metrics
    - Limitations & Risks
    - Cost Estimate
    """
    pass


# === Operational Runbook ===
class RunbookGenerator(BaseDocumentGenerator):
    """
    Generates Operational Runbook.

    Content:
    - Prerequisites
    - Installation
    - Configuration
    - Deployment
    - Monitoring
    - Troubleshooting
    - Rollback Procedures
    """
    pass


# === Workplan Alignment Report ===
class WorkplanAlignmentGenerator(BaseDocumentGenerator):
    """
    Generates Workplan Alignment Report.

    Content:
    - Workplan Overview
    - Activity-Repository Mapping
    - Progress Summary
    - Timeline Analysis
    - Deviations & Risks
    """
    pass


# === Budget Status Report ===
class BudgetStatusGenerator(BaseDocumentGenerator):
    """
    Generates Budget Status Report.

    Content:
    - Budget Overview
    - Line-by-Line Status
    - Burn Rate Analysis
    - Variance Analysis
    - Forecast
    - Recommendations
    """
    pass


# === Indicators Status Report ===
class IndicatorsStatusGenerator(BaseDocumentGenerator):
    """
    Generates Indicators Status Report.

    Content:
    - Indicators Dashboard
    - Progress Charts
    - Trend Analysis
    - Risk Indicators
    - Recommendations
    """
    pass


# === Multi-Donor Split Report ===
class MultiDonorSplitGenerator(BaseDocumentGenerator):
    """
    Generates Multi-Donor Split Report.

    Content:
    - Allocation Overview
    - Per-Donor Breakdown
    - Cost Distribution
    - Hours Distribution
    - Justification Summary
    """
    pass


# === Full Acceptance Package ===
class AcceptancePackageGenerator(BaseDocumentGenerator):
    """
    Generates Full Acceptance Package for donors.

    Combines:
    - Tech Report
    - Compliance Report
    - Workplan Status
    - Budget Status
    - Indicators Status
    - Sign-off Section
    """
    pass
```

---

## 8. FRONTEND COMPONENTS

### 8.1 Структура UI

```
ui/src/
├── app/
│   ├── workflow/           # Existing workflow
│   ├── documents/          # NEW: Document generation
│   │   ├── page.tsx
│   │   └── [type]/page.tsx
│   ├── workplan/           # NEW: Workplan tracking
│   │   ├── page.tsx
│   │   └── [id]/page.tsx
│   ├── budget/             # NEW: Budget tracking
│   │   ├── page.tsx
│   │   └── [id]/page.tsx
│   ├── indicators/         # NEW: Indicators
│   │   └── page.tsx
│   └── donors/             # NEW: Multi-donor
│       ├── page.tsx
│       └── [id]/page.tsx
├── components/
│   ├── documents/
│   │   ├── DocumentMatrix.tsx
│   │   ├── DocumentPreview.tsx
│   │   ├── DocumentExport.tsx
│   │   └── TemplateSelector.tsx
│   ├── workplan/
│   │   ├── WorkplanGantt.tsx
│   │   ├── ActivityCard.tsx
│   │   ├── ProgressTracker.tsx
│   │   └── RepoLinkModal.tsx
│   ├── budget/
│   │   ├── BudgetTable.tsx
│   │   ├── BurnRateChart.tsx
│   │   ├── AllocationModal.tsx
│   │   └── VarianceAlert.tsx
│   ├── indicators/
│   │   ├── IndicatorCard.tsx
│   │   ├── ProgressGauge.tsx
│   │   └── TrendChart.tsx
│   └── donors/
│       ├── DonorSelector.tsx
│       ├── AllocationSplit.tsx
│       └── DonorReport.tsx
└── lib/
    ├── workplan.ts
    ├── budget.ts
    ├── indicators.ts
    └── donors.ts
```

### 8.2 Ключевые компоненты

```typescript
// ui/src/components/documents/DocumentMatrix.tsx

interface DocumentMatrixProps {
  productLevel: string;
  isPlatformModule: boolean;
  hasDonors: boolean;
  analysisId: string;
  onGenerate: (docType: string) => void;
}

export function DocumentMatrix({
  productLevel,
  isPlatformModule,
  hasDonors,
  analysisId,
  onGenerate,
}: DocumentMatrixProps) {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [generating, setGenerating] = useState<string | null>(null);

  useEffect(() => {
    // Fetch available documents based on product level
    fetchDocumentMatrix(productLevel, isPlatformModule, hasDonors)
      .then(setDocuments);
  }, [productLevel, isPlatformModule, hasDonors]);

  return (
    <div className="space-y-6">
      {/* Base Documents */}
      <DocumentSection
        title="Base Documents"
        documents={documents.filter(d => d.category === 'base')}
        onGenerate={onGenerate}
        generating={generating}
      />

      {/* Platform Documents */}
      {isPlatformModule && (
        <DocumentSection
          title="Platform Module Documents"
          documents={documents.filter(d => d.category === 'platform')}
          onGenerate={onGenerate}
          generating={generating}
        />
      )}

      {/* Donor Documents */}
      {hasDonors && (
        <DocumentSection
          title="Donor Documents"
          documents={documents.filter(d => d.category === 'donor')}
          onGenerate={onGenerate}
          generating={generating}
        />
      )}
    </div>
  );
}
```

```typescript
// ui/src/components/workplan/WorkplanGantt.tsx

interface WorkplanGanttProps {
  workplanId: string;
  onActivityClick: (activityId: string) => void;
}

export function WorkplanGantt({ workplanId, onActivityClick }: WorkplanGanttProps) {
  const [activities, setActivities] = useState<Activity[]>([]);
  const [linkedRepos, setLinkedRepos] = useState<Map<string, string[]>>(new Map());

  return (
    <div className="gantt-container">
      {/* Timeline Header */}
      <GanttHeader startDate={workplan.startDate} endDate={workplan.endDate} />

      {/* Activities */}
      {activities.map(activity => (
        <GanttRow
          key={activity.id}
          activity={activity}
          linkedRepos={linkedRepos.get(activity.id) || []}
          onClick={() => onActivityClick(activity.id)}
        >
          <GanttBar
            plannedStart={activity.plannedStart}
            plannedEnd={activity.plannedEnd}
            actualStart={activity.actualStart}
            actualEnd={activity.actualEnd}
            progress={activity.progressPercent}
            status={activity.status}
          />
        </GanttRow>
      ))}
    </div>
  );
}
```

```typescript
// ui/src/components/budget/BudgetTable.tsx

interface BudgetTableProps {
  projectId: string;
  donorId?: string;
}

export function BudgetTable({ projectId, donorId }: BudgetTableProps) {
  const [lines, setLines] = useState<BudgetLine[]>([]);
  const [totals, setTotals] = useState<BudgetTotals | null>(null);

  return (
    <div className="budget-table">
      <table className="w-full">
        <thead>
          <tr>
            <th>Code</th>
            <th>Description</th>
            <th>Planned</th>
            <th>Committed</th>
            <th>Spent</th>
            <th>Remaining</th>
            <th>Variance</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {lines.map(line => (
            <BudgetRow
              key={line.id}
              line={line}
              showVarianceAlert={Math.abs(line.variance) > line.flexibilityPercent}
            />
          ))}
        </tbody>
        <tfoot>
          <BudgetTotalsRow totals={totals} />
        </tfoot>
      </table>

      {/* Burn Rate Chart */}
      <BurnRateChart projectId={projectId} donorId={donorId} />
    </div>
  );
}
```

```typescript
// ui/src/components/donors/AllocationSplit.tsx

interface AllocationSplitProps {
  analysisId: string;
  totalHours: number;
  totalCost: number;
  donors: Donor[];
  onSave: (allocations: Allocation[]) => void;
}

export function AllocationSplit({
  analysisId,
  totalHours,
  totalCost,
  donors,
  onSave,
}: AllocationSplitProps) {
  const [allocations, setAllocations] = useState<Allocation[]>([]);
  const [errors, setErrors] = useState<string[]>([]);

  const totalPercent = allocations.reduce((sum, a) => sum + a.percent, 0);
  const isValid = totalPercent === 100;

  return (
    <div className="allocation-split">
      <h3>Allocate Cost Across Donors</h3>

      <div className="summary">
        <div>Total Hours: {totalHours}h</div>
        <div>Total Cost: ${totalCost.toLocaleString()}</div>
      </div>

      {donors.map(donor => (
        <AllocationRow
          key={donor.id}
          donor={donor}
          allocation={allocations.find(a => a.donorId === donor.id)}
          totalHours={totalHours}
          totalCost={totalCost}
          onChange={(percent, justification) => {
            updateAllocation(donor.id, percent, justification);
          }}
        />
      ))}

      <div className="totals">
        <div className={totalPercent === 100 ? 'text-green-600' : 'text-red-600'}>
          Total: {totalPercent}%
        </div>
      </div>

      <button
        onClick={() => onSave(allocations)}
        disabled={!isValid}
        className="btn-primary"
      >
        Save Allocations
      </button>
    </div>
  );
}
```

---

## 9. ИНТЕГРАЦИИ

### 9.1 Импорт/Экспорт

```python
# backend/app/services/import_export.py

class ImportExportService:
    """Import/export workplans, budgets from external formats."""

    async def import_workplan_excel(self, file: bytes, project_id: str) -> Workplan:
        """
        Import workplan from Excel.

        Expected columns:
        - WP_ID, Title, Description
        - Planned Start, Planned End
        - Planned Hours, Planned Cost
        - Budget Line
        """
        pass

    async def import_budget_excel(self, file: bytes, project_id: str) -> List[BudgetLine]:
        """
        Import budget from Excel.

        Expected columns:
        - Code, Name, Category
        - Planned Amount
        - Period Start, Period End
        """
        pass

    async def export_to_excel(
        self,
        project_id: str,
        include_workplan: bool = True,
        include_budget: bool = True,
        include_indicators: bool = True
    ) -> bytes:
        """Export project data to Excel workbook."""
        pass

    async def export_donor_package(
        self,
        project_id: str,
        donor_id: str,
        format: str = "zip"
    ) -> bytes:
        """
        Export complete donor package as ZIP.

        Contains:
        - All relevant documents (PDF)
        - Data export (Excel)
        - Summary (JSON)
        """
        pass
```

### 9.2 Webhooks

```python
# backend/app/services/webhooks.py

class WebhookService:
    """Send notifications on key events."""

    EVENTS = [
        "analysis.completed",
        "workplan.activity.completed",
        "budget.threshold.exceeded",
        "indicator.target.reached",
        "document.generated",
    ]

    async def notify(self, event: str, data: Dict):
        """Send webhook notification."""
        pass
```

---

## 10. МИГРАЦИИ БД

```python
# backend/alembic/versions/xxx_add_workplan_budget_indicators.py

"""Add workplan, budget, indicators tables

Revision ID: xxx
"""

def upgrade():
    # Workplan tables
    op.create_table('workplans', ...)
    op.create_table('workplan_activities', ...)

    # Budget tables
    op.create_table('budget_lines', ...)
    op.create_table('budget_transactions', ...)

    # Indicator tables
    op.create_table('indicators', ...)
    op.create_table('indicator_measurements', ...)

    # Donor tables
    op.create_table('donors', ...)
    op.create_table('donor_allocations', ...)

    # Indexes
    op.create_index('idx_activities_wp_id', 'workplan_activities', ['wp_id'])
    op.create_index('idx_budget_project', 'budget_lines', ['project_id'])
    op.create_index('idx_indicators_project', 'indicators', ['project_id'])
```

---

## 11. ПЛАН РЕАЛИЗАЦИИ

### Фаза 1: Матрица документов (1-2 недели)
1. `DocumentMatrix` модель и сервис
2. Базовые генераторы (R&D Summary, Tech Report, Tech Note)
3. UI компонент DocumentMatrix
4. Интеграция в workflow

### Фаза 2: Workplan Tracking (2-3 недели)
1. Модели Workplan, Activity
2. CRUD API
3. Import из Excel
4. Gantt UI компонент
5. Связь с analyses

### Фаза 3: Budget Tracking (1-2 недели)
1. Модели BudgetLine, Transaction
2. API для учёта
3. Burn rate calculations
4. Budget UI таблица и графики

### Фаза 4: Indicators (1 неделя)
1. Модели Indicator, Measurement
2. Auto-calculation formulas
3. Indicators dashboard
4. Интеграция с анализом

### Фаза 5: Multi-Donor (1-2 недели)
1. Модель Donor, Allocation
2. Allocation split UI
3. Per-donor reports
4. Multi-donor split report

### Фаза 6: Полировка (1 неделя)
1. PDF/DOCX export
2. Import/Export Excel
3. Webhooks
4. Тестирование

---

## 12. ACCEPTANCE CRITERIA

### 12.1 Документы
- [ ] Автоматический выбор пакета документов по Product Level
- [ ] Генерация всех типов документов в MD/PDF/DOCX
- [ ] Предпросмотр документов в UI
- [ ] Batch генерация для проекта

### 12.2 Workplan
- [ ] Импорт workplan из Excel
- [ ] Визуализация Gantt
- [ ] Связь активностей с репозиториями
- [ ] Progress tracking
- [ ] Alignment report генерация

### 12.3 Budget
- [ ] CRUD бюджетных линий
- [ ] Учёт транзакций
- [ ] Burn rate анализ
- [ ] Variance alerts
- [ ] Budget status report

### 12.4 Indicators
- [ ] Ручной ввод измерений
- [ ] Авто-расчёт из analyses
- [ ] Progress dashboard
- [ ] Indicators report

### 12.5 Multi-Donor
- [ ] Управление донорами
- [ ] Allocation split UI
- [ ] Per-donor фильтрация
- [ ] Multi-donor split report

---

**Подготовлено:** Repo Auditor Team
**Дата:** 2025-12-04
