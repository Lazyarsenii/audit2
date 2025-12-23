"""
API routes for Unified Audit workflow.

Этапы:
1. Выбор проекта + Проверка готовности
2. Анализ состояния (тип, качество, зрелость, тех.долг, IP)
3. Проверка соответствия (ТЗ, контракт, политики) - TODO
4. Оценка стоимости - TODO
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.services.project_readiness import (
    project_readiness_checker,
    ComplianceDocument,
    AnalysisType,
)
from app.services.state_analyzer import state_analyzer


router = APIRouter(prefix="/unified-audit", tags=["unified-audit"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class ReadinessCheckRequest(BaseModel):
    """Запрос на проверку готовности проекта"""
    repo_path: str
    repo_url: Optional[str] = ""
    compliance_documents: Optional[List[Dict[str, Any]]] = None


class StateAnalysisRequest(BaseModel):
    """Запрос на анализ состояния"""
    repo_path: str
    analysis_id: Optional[str] = None
    # Предсобранные метрики (опционально)
    metrics: Optional[Dict[str, Any]] = None


class UploadComplianceDocRequest(BaseModel):
    """Информация о загруженном compliance документе"""
    doc_type: str  # "tz" | "contract" | "policy"
    filename: str
    requirements_count: int = 0


# =============================================================================
# ЭТАП 1: ПРОВЕРКА ГОТОВНОСТИ
# =============================================================================

@router.post("/check-readiness")
async def check_project_readiness(request: ReadinessCheckRequest):
    """
    Этап 1: Проверка готовности проекта к аудиту.

    Проверяет:
    - Наличие исходного кода
    - Наличие документации
    - Наличие тестов
    - Наличие инфраструктуры (Docker, CI)
    - Загруженные ТЗ/контракт

    Returns:
        - readiness_score (0-100%)
        - ready_for_audit (bool)
        - artifacts (список с наличием)
        - available_analyses (какие анализы доступны)
        - recommendations (что добавить)
    """
    # Конвертируем compliance документы
    compliance_docs = []
    if request.compliance_documents:
        for doc in request.compliance_documents:
            compliance_docs.append(ComplianceDocument(
                doc_id=doc.get("doc_id", ""),
                doc_type=doc.get("doc_type", ""),
                filename=doc.get("filename", ""),
                uploaded_at=datetime.fromisoformat(doc["uploaded_at"]) if "uploaded_at" in doc else datetime.now(),
                parsed=doc.get("parsed", False),
                requirements_count=doc.get("requirements_count", 0),
            ))

    result = await project_readiness_checker.check_readiness(
        repo_path=request.repo_path,
        repo_url=request.repo_url,
        compliance_documents=compliance_docs,
    )

    return result.to_dict()


@router.post("/check-readiness-demo")
async def check_readiness_demo():
    """
    Демо проверки готовности с тестовым репозиторием.
    """
    import tempfile
    import os

    # Создаём временный "репозиторий" для демо
    with tempfile.TemporaryDirectory() as temp_dir:
        # Создаём структуру
        os.makedirs(os.path.join(temp_dir, "src"))
        os.makedirs(os.path.join(temp_dir, "tests"))
        os.makedirs(os.path.join(temp_dir, "docs"))
        os.makedirs(os.path.join(temp_dir, ".git"))

        # Создаём файлы
        with open(os.path.join(temp_dir, "README.md"), "w") as f:
            f.write("# Demo Project\n\nThis is a demo project for testing.")

        with open(os.path.join(temp_dir, "requirements.txt"), "w") as f:
            f.write("fastapi>=0.100.0\npydantic>=2.0.0\n")

        with open(os.path.join(temp_dir, "src", "main.py"), "w") as f:
            f.write("def main():\n    print('Hello')\n")

        with open(os.path.join(temp_dir, "tests", "test_main.py"), "w") as f:
            f.write("def test_main():\n    assert True\n")

        # Демо compliance документ
        demo_docs = [
            ComplianceDocument(
                doc_id="demo_tz_001",
                doc_type="tz",
                filename="technical_specification.pdf",
                uploaded_at=datetime.now(),
                parsed=True,
                requirements_count=15,
            ),
        ]

        result = await project_readiness_checker.check_readiness(
            repo_path=temp_dir,
            repo_url="https://github.com/demo/project",
            compliance_documents=demo_docs,
        )

        return result.to_dict()


@router.get("/required-artifacts")
async def get_required_artifacts(analysis_types: Optional[str] = None):
    """
    Получить список артефактов, необходимых для анализа.

    Args:
        analysis_types: Типы анализов через запятую (state,quality,ip,compliance,cost)
    """
    if analysis_types:
        types = [AnalysisType(t.strip()) for t in analysis_types.split(",")]
    else:
        types = list(AnalysisType)

    artifacts = project_readiness_checker.get_required_artifacts_for_analysis(types)

    return {
        "analysis_types": [t.value for t in types],
        "artifacts": [
            {
                "artifact_id": a.artifact_id,
                "name": a.name,
                "name_ru": a.name_ru,
                "category": a.category.value,
                "required": a.required,
                "patterns": a.patterns,
                "for_analyses": [at.value for at in a.for_analyses],
                "description": a.description,
            }
            for a in artifacts
        ],
        "total": len(artifacts),
        "required_count": sum(1 for a in artifacts if a.required),
    }


# =============================================================================
# ЭТАП 2: АНАЛИЗ СОСТОЯНИЯ
# =============================================================================

@router.post("/analyze-state")
async def analyze_project_state(request: StateAnalysisRequest):
    """
    Этап 2: Полный анализ состояния проекта.

    Включает:
    - Определение типа проекта (R&D/Prototype/Internal/Platform/Product)
    - Анализ качества (code quality, tests, docs)
    - Анализ зрелости (repo health 0-12)
    - Анализ технического долга (0-15)
    - IP анализ (уникальность, лицензии, авторство)

    Returns:
        - project_type: тип и уровень проекта
        - quality: оценка качества
        - maturity: зрелость (repo health)
        - tech_debt: технический долг
        - ip: IP анализ
        - overall_score: общая оценка
        - metrics_for_compliance: метрики для следующего этапа
        - metrics_for_cost: метрики для оценки стоимости
    """
    result = await state_analyzer.analyze(
        repo_path=request.repo_path,
        collected_metrics=request.metrics,
        analysis_id=request.analysis_id,
    )

    return result.to_dict()


@router.post("/analyze-state-demo")
async def analyze_state_demo():
    """
    Демо анализа состояния с тестовыми данными.
    """
    import tempfile
    import os

    with tempfile.TemporaryDirectory() as temp_dir:
        # Создаём более полную структуру для демо
        os.makedirs(os.path.join(temp_dir, "src", "services"))
        os.makedirs(os.path.join(temp_dir, "src", "api"))
        os.makedirs(os.path.join(temp_dir, "tests", "unit"))
        os.makedirs(os.path.join(temp_dir, "docs", "api"))
        os.makedirs(os.path.join(temp_dir, ".git"))
        os.makedirs(os.path.join(temp_dir, ".github", "workflows"))

        # README
        with open(os.path.join(temp_dir, "README.md"), "w") as f:
            f.write("""# Demo Project

## Overview
This is a demo project for testing the unified audit system.

## Installation
```bash
pip install -r requirements.txt
```

## Usage
```python
from src.main import run
run()
```

## Testing
```bash
pytest tests/
```
""")

        # Requirements
        with open(os.path.join(temp_dir, "requirements.txt"), "w") as f:
            f.write("fastapi>=0.100.0\npydantic>=2.0.0\nuvicorn>=0.20.0\npytest>=7.0.0\n")

        # Source files
        with open(os.path.join(temp_dir, "src", "__init__.py"), "w") as f:
            f.write("")

        with open(os.path.join(temp_dir, "src", "main.py"), "w") as f:
            f.write("""
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"status": "ok"}

@app.get("/health")
def health():
    return {"healthy": True}
""")

        with open(os.path.join(temp_dir, "src", "services", "__init__.py"), "w") as f:
            f.write("")

        with open(os.path.join(temp_dir, "src", "services", "analyzer.py"), "w") as f:
            f.write("""
class Analyzer:
    def __init__(self):
        self.data = {}

    def analyze(self, input_data):
        result = self._process(input_data)
        return result

    def _process(self, data):
        return {"processed": True, "data": data}
""")

        # Tests
        with open(os.path.join(temp_dir, "tests", "__init__.py"), "w") as f:
            f.write("")

        with open(os.path.join(temp_dir, "tests", "unit", "test_analyzer.py"), "w") as f:
            f.write("""
import pytest
from src.services.analyzer import Analyzer

def test_analyzer_init():
    a = Analyzer()
    assert a.data == {}

def test_analyzer_analyze():
    a = Analyzer()
    result = a.analyze({"test": 1})
    assert result["processed"] is True
""")

        # Dockerfile
        with open(os.path.join(temp_dir, "Dockerfile"), "w") as f:
            f.write("""FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0"]
""")

        # CI
        with open(os.path.join(temp_dir, ".github", "workflows", "ci.yml"), "w") as f:
            f.write("""name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
      - run: pip install -r requirements.txt
      - run: pytest tests/
""")

        # API docs
        with open(os.path.join(temp_dir, "docs", "api", "openapi.yaml"), "w") as f:
            f.write("openapi: 3.0.0\ninfo:\n  title: Demo API\n  version: 1.0.0\n")

        # CHANGELOG
        with open(os.path.join(temp_dir, "CHANGELOG.md"), "w") as f:
            f.write("# Changelog\n\n## 1.0.0\n- Initial release\n")

        result = await state_analyzer.analyze(
            repo_path=temp_dir,
            analysis_id="demo_state_001",
        )

        return result.to_dict()


@router.get("/product-levels")
async def get_product_levels():
    """
    Получить описание уровней зрелости продукта.
    """
    from app.services.state_analyzer import PRODUCT_LEVEL_INDICATORS, ProductLevel

    return {
        "levels": [
            {
                "level": level.value,
                "score": config["score"],
                "name_ru": config["name_ru"],
                "description": config["description"],
                "required_artifacts": config.get("required", []),
                "optional_artifacts": config.get("optional", []),
            }
            for level, config in PRODUCT_LEVEL_INDICATORS.items()
        ]
    }


# =============================================================================
# ПОЛНЫЙ WORKFLOW (этапы 1-2)
# =============================================================================

@router.post("/run-stages-1-2")
async def run_stages_one_and_two(request: ReadinessCheckRequest):
    """
    Запустить Этапы 1 и 2 последовательно.

    Этап 1: Проверка готовности
    Этап 2: Анализ состояния (если готов)

    Returns:
        - stage1: результат проверки готовности
        - stage2: результат анализа состояния (если ready_for_audit=True)
        - can_proceed: можно ли продолжать к этапу 3
    """
    # Этап 1
    compliance_docs = []
    if request.compliance_documents:
        for doc in request.compliance_documents:
            compliance_docs.append(ComplianceDocument(
                doc_id=doc.get("doc_id", ""),
                doc_type=doc.get("doc_type", ""),
                filename=doc.get("filename", ""),
                uploaded_at=datetime.fromisoformat(doc["uploaded_at"]) if "uploaded_at" in doc else datetime.now(),
                parsed=doc.get("parsed", False),
                requirements_count=doc.get("requirements_count", 0),
            ))

    readiness = await project_readiness_checker.check_readiness(
        repo_path=request.repo_path,
        repo_url=request.repo_url,
        compliance_documents=compliance_docs,
    )

    result = {
        "stage1_readiness": readiness.to_dict(),
        "stage2_state": None,
        "can_proceed_to_compliance": False,
        "can_proceed_to_cost": False,
    }

    # Этап 2 (если готов)
    if readiness.ready_for_audit:
        state = await state_analyzer.analyze(
            repo_path=request.repo_path,
        )
        result["stage2_state"] = state.to_dict()
        result["can_proceed_to_compliance"] = readiness.has_tz or readiness.has_contract
        result["can_proceed_to_cost"] = True

    return result


# =============================================================================
# CAPABILITIES
# =============================================================================

@router.get("/capabilities")
async def get_capabilities():
    """
    Получить информацию о возможностях Unified Audit.
    """
    return {
        "stages": [
            {
                "stage": 1,
                "name": "Проверка готовности",
                "name_en": "Readiness Check",
                "endpoint": "/unified-audit/check-readiness",
                "description": "Проверка наличия необходимых артефактов для аудита",
            },
            {
                "stage": 2,
                "name": "Анализ состояния",
                "name_en": "State Analysis",
                "endpoint": "/unified-audit/analyze-state",
                "description": "Анализ типа, качества, зрелости, тех.долга, IP",
            },
            {
                "stage": 3,
                "name": "Проверка соответствия",
                "name_en": "Compliance Check",
                "endpoint": "/unified-audit/check-compliance",
                "description": "Проверка соответствия ТЗ, контракту, политикам",
                "status": "coming_soon",
            },
            {
                "stage": 4,
                "name": "Оценка стоимости",
                "name_en": "Cost Estimation",
                "endpoint": "/unified-audit/estimate-cost",
                "description": "Оценка трудозатрат и стоимости",
                "status": "coming_soon",
            },
        ],
        "analysis_types": [
            {"type": at.value, "name_ru": {
                "state": "Анализ состояния",
                "quality": "Анализ качества",
                "ip": "IP анализ",
                "compliance": "Проверка соответствия",
                "cost": "Оценка стоимости",
                "security": "Анализ безопасности",
            }.get(at.value, at.value)}
            for at in AnalysisType
        ],
        "supported_sources": ["local_path", "github", "gitlab"],
        "supported_compliance_docs": ["tz", "contract", "policy"],
    }
