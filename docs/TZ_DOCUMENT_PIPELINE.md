# Техническое задание: Полный пайплайн работы с документами

**Версия:** 1.0
**Дата:** 2025-12-06
**Статус:** Draft

---

## 1. Общее описание

### 1.1 Цель проекта

Создание полноценной системы управления документами для Repo Auditor, включающей:
- Загрузку и хранение контрактов, политик, шаблонов
- Интеллектуальное извлечение данных (LLM + паттерны)
- Связывание документов с анализами репозиториев
- Генерацию отчётов на основе извлечённых данных
- Множественные варианты хранения и экспорта

### 1.2 Текущее состояние

| Компонент | Статус | Проблема |
|-----------|--------|----------|
| Contract Parser | Частично | Только regex, данные в памяти |
| Document Storage | Отсутствует | Нет персистентного хранения |
| LLM Extraction | Отсутствует | Только паттерны |
| Contract↔Analysis Link | Отсутствует | Нет связи в БД |
| Multi-storage | Частично | Только Google Drive |
| Report Generation | Частично | PDF/Word неполные |

### 1.3 Ожидаемый результат

Полнофункциональная система, где:
1. Пользователь загружает контракт/политику
2. Система извлекает структурированные данные
3. Данные сохраняются в БД и связываются с анализом
4. При генерации отчётов используются данные из контрактов
5. Документы можно сохранять в разные хранилища

---

## 2. Функциональные требования

### 2.1 Модуль загрузки документов (Upload Module)

#### 2.1.1 Поддерживаемые источники

| Источник | Описание | Приоритет |
|----------|----------|-----------|
| Local Upload | Загрузка с компьютера пользователя | P0 |
| Google Drive | Выбор из Google Drive | P0 |
| Direct Paste | Вставка текста напрямую | P1 |
| URL Import | Загрузка по ссылке | P2 |
| Email Import | Парсинг вложений из email | P3 |

#### 2.1.2 Поддерживаемые форматы

| Формат | Расширения | Библиотека |
|--------|------------|------------|
| PDF | .pdf | PyPDF2, pdfplumber |
| Word | .docx, .doc | python-docx |
| Text | .txt, .md | built-in |
| Excel | .xlsx, .xls | openpyxl |
| Images | .png, .jpg | pytesseract (OCR) |
| Scans | .pdf (scanned) | pytesseract + pdf2image |

#### 2.1.3 API Endpoints

```
POST /api/documents/upload
  - multipart/form-data
  - Параметры: file, document_type, analysis_id (optional)
  - Возвращает: document_id, extracted_preview

POST /api/documents/upload-from-drive
  - JSON: { drive_file_id, document_type, analysis_id }

POST /api/documents/upload-text
  - JSON: { content, document_type, title, analysis_id }

POST /api/documents/upload-url
  - JSON: { url, document_type, analysis_id }
```

---

### 2.2 Модуль хранения (Storage Module)

#### 2.2.1 Структура базы данных

```sql
-- Основная таблица документов
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Метаданные
    title VARCHAR(500) NOT NULL,
    document_type VARCHAR(50) NOT NULL, -- contract, policy, template, report
    file_name VARCHAR(255),
    mime_type VARCHAR(100),
    file_size INTEGER,

    -- Контент
    original_content BYTEA,           -- Оригинальный файл
    extracted_text TEXT,              -- Извлечённый текст

    -- Связи
    analysis_id UUID REFERENCES analyses(id),
    parent_document_id UUID REFERENCES documents(id), -- Для версий

    -- Статус обработки
    processing_status VARCHAR(20) DEFAULT 'pending',
    processing_error TEXT,

    -- Метаданные извлечения
    extraction_confidence FLOAT,
    extraction_method VARCHAR(50),    -- regex, llm, hybrid

    -- Временные метки
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP,

    -- Soft delete
    deleted_at TIMESTAMP
);

-- Извлечённые данные из контрактов
CREATE TABLE contract_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,

    -- Основные поля контракта
    contract_number VARCHAR(100),
    contract_title VARCHAR(500),
    contract_date DATE,
    start_date DATE,
    end_date DATE,
    total_amount DECIMAL(15, 2),
    currency VARCHAR(10),

    -- Стороны
    client_name VARCHAR(255),
    client_address TEXT,
    contractor_name VARCHAR(255),
    contractor_address TEXT,

    -- JSON данные
    work_plan JSONB,          -- [{phase, description, duration, deliverables}]
    budget_breakdown JSONB,   -- [{category, amount, description}]
    milestones JSONB,         -- [{name, date, deliverable, payment}]
    indicators JSONB,         -- [{name, target, measurement}]

    -- Извлечённые политики
    policies JSONB,           -- [{type, requirement, source_text}]

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Извлечённые паттерны для обучения
CREATE TABLE extraction_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    pattern_type VARCHAR(50),     -- date, amount, activity, deliverable
    pattern_regex TEXT,
    pattern_examples JSONB,       -- Примеры успешных извлечений
    confidence_score FLOAT,
    usage_count INTEGER DEFAULT 0,

    created_at TIMESTAMP DEFAULT NOW(),
    last_used_at TIMESTAMP
);

-- История версий документов
CREATE TABLE document_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id),
    version_number INTEGER,
    changes_summary TEXT,
    previous_content BYTEA,
    created_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(255)
);

-- Связь документов с анализами (many-to-many)
CREATE TABLE document_analysis_links (
    document_id UUID REFERENCES documents(id),
    analysis_id UUID REFERENCES analyses(id),
    link_type VARCHAR(50),        -- source_contract, reference, generated
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (document_id, analysis_id)
);

-- Индексы
CREATE INDEX idx_documents_type ON documents(document_type);
CREATE INDEX idx_documents_analysis ON documents(analysis_id);
CREATE INDEX idx_documents_status ON documents(processing_status);
CREATE INDEX idx_contract_data_dates ON contract_data(start_date, end_date);
```

#### 2.2.2 Модели SQLAlchemy

```python
# app/core/models/document.py

class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID, primary_key=True, default=uuid4)
    title = Column(String(500), nullable=False)
    document_type = Column(String(50), nullable=False)  # contract, policy, template
    file_name = Column(String(255))
    mime_type = Column(String(100))
    file_size = Column(Integer)

    original_content = Column(LargeBinary)
    extracted_text = Column(Text)

    analysis_id = Column(UUID, ForeignKey("analyses.id"))
    parent_document_id = Column(UUID, ForeignKey("documents.id"))

    processing_status = Column(String(20), default="pending")
    processing_error = Column(Text)
    extraction_confidence = Column(Float)
    extraction_method = Column(String(50))

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    processed_at = Column(DateTime)
    deleted_at = Column(DateTime)

    # Relationships
    analysis = relationship("Analysis", back_populates="documents")
    contract_data = relationship("ContractData", back_populates="document", uselist=False)
    versions = relationship("DocumentVersion", back_populates="document")


class ContractData(Base):
    __tablename__ = "contract_data"

    id = Column(UUID, primary_key=True, default=uuid4)
    document_id = Column(UUID, ForeignKey("documents.id", ondelete="CASCADE"))

    contract_number = Column(String(100))
    contract_title = Column(String(500))
    contract_date = Column(Date)
    start_date = Column(Date)
    end_date = Column(Date)
    total_amount = Column(Numeric(15, 2))
    currency = Column(String(10))

    client_name = Column(String(255))
    contractor_name = Column(String(255))

    work_plan = Column(JSONB)
    budget_breakdown = Column(JSONB)
    milestones = Column(JSONB)
    indicators = Column(JSONB)
    policies = Column(JSONB)

    document = relationship("Document", back_populates="contract_data")
```

#### 2.2.3 Варианты хранения файлов

| Хранилище | Использование | Конфигурация |
|-----------|---------------|--------------|
| PostgreSQL BYTEA | Малые файлы (<10MB) | По умолчанию |
| Local Filesystem | Средние файлы | STORAGE_PATH |
| S3/MinIO | Большие файлы, продакшн | S3_* настройки |
| Google Drive | Интеграция с пользователем | GOOGLE_* настройки |

```python
# app/services/file_storage.py

class FileStorageService:
    """Абстракция над разными хранилищами файлов."""

    def __init__(self):
        self.backend = self._get_backend()

    def _get_backend(self) -> StorageBackend:
        storage_type = settings.FILE_STORAGE_TYPE  # db, local, s3, gdrive

        if storage_type == "db":
            return DatabaseStorage()
        elif storage_type == "local":
            return LocalFileStorage(settings.STORAGE_PATH)
        elif storage_type == "s3":
            return S3Storage(
                bucket=settings.S3_BUCKET,
                access_key=settings.S3_ACCESS_KEY,
                secret_key=settings.S3_SECRET_KEY,
            )
        elif storage_type == "gdrive":
            return GoogleDriveStorage()

    async def store(self, content: bytes, filename: str, metadata: dict) -> str:
        """Сохранить файл, вернуть storage_key."""
        return await self.backend.store(content, filename, metadata)

    async def retrieve(self, storage_key: str) -> bytes:
        """Получить файл по ключу."""
        return await self.backend.retrieve(storage_key)

    async def delete(self, storage_key: str) -> bool:
        """Удалить файл."""
        return await self.backend.delete(storage_key)
```

---

### 2.3 Модуль извлечения данных (Extraction Module)

#### 2.3.1 Архитектура извлечения

```
┌─────────────────────────────────────────────────────────────┐
│                    EXTRACTION PIPELINE                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐              │
│  │  OCR     │───▶│  Text    │───▶│  Clean   │              │
│  │ (images) │    │ Extract  │    │  & Norm  │              │
│  └──────────┘    └──────────┘    └──────────┘              │
│                                       │                      │
│                                       ▼                      │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              HYBRID EXTRACTION ENGINE                   │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │ │
│  │  │   Regex     │  │    LLM      │  │  Template   │    │ │
│  │  │  Patterns   │  │  Analysis   │  │  Matching   │    │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘    │ │
│  │         │                │                │            │ │
│  │         └────────────────┼────────────────┘            │ │
│  │                          ▼                             │ │
│  │              ┌─────────────────────┐                   │ │
│  │              │   Result Merger     │                   │ │
│  │              │  + Confidence Score │                   │ │
│  │              └─────────────────────┘                   │ │
│  └────────────────────────────────────────────────────────┘ │
│                          │                                   │
│                          ▼                                   │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              VALIDATION & ENRICHMENT                    │ │
│  │  - Schema validation                                    │ │
│  │  - Cross-reference check                                │ │
│  │  - Missing field detection                              │ │
│  └────────────────────────────────────────────────────────┘ │
│                          │                                   │
│                          ▼                                   │
│               ┌──────────────────────┐                      │
│               │   Structured Data    │                      │
│               │   (ContractData)     │                      │
│               └──────────────────────┘                      │
└─────────────────────────────────────────────────────────────┘
```

#### 2.3.2 LLM Extraction Service

```python
# app/services/llm_extraction.py

from typing import Optional, Dict, Any, List
from pydantic import BaseModel

class ExtractionResult(BaseModel):
    """Результат извлечения данных."""
    field_name: str
    value: Any
    confidence: float  # 0.0 - 1.0
    source_text: str   # Откуда извлечено
    method: str        # regex, llm, template


class ContractExtractionSchema(BaseModel):
    """Схема для извлечения данных контракта."""
    contract_number: Optional[str]
    contract_title: Optional[str]
    contract_date: Optional[str]
    parties: List[Dict[str, str]]
    total_amount: Optional[float]
    currency: Optional[str]
    work_plan: List[Dict[str, Any]]
    budget: List[Dict[str, Any]]
    milestones: List[Dict[str, Any]]
    indicators: List[Dict[str, Any]]
    policies: List[Dict[str, Any]]


class LLMExtractionService:
    """Сервис извлечения данных с помощью LLM."""

    EXTRACTION_PROMPT = """
    Analyze the following document and extract structured data.

    Document type: {document_type}

    Extract the following information:
    1. Contract details (number, title, date, parties, amount)
    2. Work plan (phases, activities, deliverables, timelines)
    3. Budget breakdown (categories, amounts, descriptions)
    4. Milestones (name, date, deliverable, payment amount)
    5. KPIs/Indicators (name, target value, measurement method)
    6. Policy requirements (type, requirement text)

    Return as JSON matching this schema:
    {schema}

    Document text:
    ---
    {text}
    ---

    Important:
    - Extract exact values from the text
    - Include source quotes for verification
    - Mark uncertain extractions with lower confidence
    - Use null for missing fields, don't make up data
    """

    def __init__(self):
        self.llm_client = LLMClient()
        self.regex_extractor = RegexExtractor()

    async def extract(
        self,
        text: str,
        document_type: str,
        use_llm: bool = True,
        use_regex: bool = True,
    ) -> Dict[str, ExtractionResult]:
        """
        Гибридное извлечение данных.

        1. Сначала regex для точных паттернов (даты, суммы)
        2. Затем LLM для семантического анализа
        3. Объединение результатов с приоритетом по confidence
        """
        results = {}

        # Regex extraction (fast, high confidence for matches)
        if use_regex:
            regex_results = await self.regex_extractor.extract(text)
            for field, result in regex_results.items():
                result.method = "regex"
                results[field] = result

        # LLM extraction (slower, better for complex structures)
        if use_llm:
            llm_results = await self._llm_extract(text, document_type)
            for field, result in llm_results.items():
                result.method = "llm"
                # Merge: prefer higher confidence
                if field not in results or result.confidence > results[field].confidence:
                    results[field] = result

        return results

    async def _llm_extract(
        self,
        text: str,
        document_type: str
    ) -> Dict[str, ExtractionResult]:
        """Извлечение через LLM."""
        prompt = self.EXTRACTION_PROMPT.format(
            document_type=document_type,
            schema=ContractExtractionSchema.schema_json(),
            text=text[:15000],  # Limit context
        )

        response = await self.llm_client.query(
            prompt=prompt,
            task_type="extraction",
            response_format="json",
        )

        return self._parse_llm_response(response)
```

#### 2.3.3 Regex Patterns Database

```python
# app/services/regex_patterns.py

EXTRACTION_PATTERNS = {
    # Даты
    "date_dmy": r"\b(\d{1,2})[./-](\d{1,2})[./-](\d{4})\b",
    "date_mdy": r"\b(\d{1,2})[./-](\d{1,2})[./-](\d{4})\b",
    "date_iso": r"\b(\d{4})-(\d{2})-(\d{2})\b",
    "date_text_en": r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b",
    "date_text_uk": r"\b\d{1,2}\s+(січня|лютого|березня|квітня|травня|червня|липня|серпня|вересня|жовтня|листопада|грудня)\s+\d{4}\b",

    # Суммы
    "amount_usd": r"\$\s*[\d,]+(?:\.\d{2})?",
    "amount_eur": r"€\s*[\d,]+(?:\.\d{2})?",
    "amount_uah": r"(?:₴|грн\.?|UAH)\s*[\d\s,]+(?:\.\d{2})?",
    "amount_generic": r"\b[\d,]+(?:\.\d{2})?\s*(?:USD|EUR|UAH|грн|dollars?|euros?)\b",

    # Номер контракта
    "contract_number": r"(?:Contract|Договір|Контракт)\s*(?:No\.?|№|#)\s*([A-Za-z0-9\-/]+)",

    # Сроки
    "duration_days": r"(\d+)\s*(?:days?|днів|дня|день)",
    "duration_weeks": r"(\d+)\s*(?:weeks?|тижнів|тижні|тиждень)",
    "duration_months": r"(\d+)\s*(?:months?|місяців|місяці|місяць)",

    # Этапы/фазы
    "phase_pattern": r"(?:Phase|Етап|Фаза)\s*(\d+)[:\s]*([^\n]+)",
    "milestone_pattern": r"(?:Milestone|Веха|Етап)\s*(\d+)[:\s]*([^\n]+)",

    # Deliverables
    "deliverable_pattern": r"(?:Deliverable|Результат|Продукт)\s*(\d+)?[:\s]*([^\n]+)",

    # Budget categories
    "budget_line": r"(?:\d+\.?\s*)?([A-Za-zА-Яа-яІіЇїЄє\s]+)[:\s]+(?:\$|€|₴|грн)?\s*([\d,]+(?:\.\d{2})?)",
}


class RegexExtractor:
    """Извлечение данных на основе regex паттернов."""

    def __init__(self):
        self.patterns = EXTRACTION_PATTERNS
        self.compiled = {k: re.compile(v, re.IGNORECASE | re.MULTILINE)
                        for k, v in self.patterns.items()}

    async def extract(self, text: str) -> Dict[str, ExtractionResult]:
        results = {}

        # Extract dates
        dates = self._extract_dates(text)
        if dates:
            results["dates"] = ExtractionResult(
                field_name="dates",
                value=dates,
                confidence=0.9,
                source_text=str(dates),
                method="regex"
            )

        # Extract amounts
        amounts = self._extract_amounts(text)
        if amounts:
            results["amounts"] = ExtractionResult(
                field_name="amounts",
                value=amounts,
                confidence=0.95,
                source_text=str(amounts),
                method="regex"
            )

        # ... more extractors

        return results
```

#### 2.3.4 Pattern Learning

```python
# app/services/pattern_learning.py

class PatternLearningService:
    """
    Сервис обучения на основе подтверждённых извлечений.
    Анализирует успешные извлечения и создаёт новые паттерны.
    """

    async def learn_from_confirmation(
        self,
        document_id: str,
        field: str,
        extracted_value: Any,
        confirmed_value: Any,
        source_text: str,
    ):
        """
        Обучение на основе подтверждения пользователем.

        Если extracted == confirmed: усиливаем паттерн
        Если extracted != confirmed: создаём новый паттерн
        """
        if extracted_value == confirmed_value:
            await self._reinforce_pattern(field, source_text)
        else:
            await self._create_new_pattern(field, confirmed_value, source_text)

    async def _create_new_pattern(
        self,
        field: str,
        value: Any,
        source_text: str
    ):
        """Создание нового паттерна на основе примера."""
        # Используем LLM для генерации regex
        prompt = f"""
        Create a regex pattern to extract "{value}" from text like:
        "{source_text}"

        Return only the regex pattern, nothing else.
        """

        pattern = await self.llm_client.query(prompt, task_type="pattern_generation")

        # Validate pattern
        if re.search(pattern, source_text):
            await self.pattern_repo.create(
                pattern_type=field,
                pattern_regex=pattern,
                pattern_examples=[{"source": source_text, "value": value}],
                confidence_score=0.5,  # Start low, increase with usage
            )
```

---

### 2.4 Модуль связывания документов с анализами (Linking Module)

#### 2.4.1 Типы связей

| Тип связи | Описание | Пример |
|-----------|----------|--------|
| source_contract | Исходный контракт для анализа | Договор → Анализ репо |
| reference | Справочный документ | Политика → Анализ |
| generated | Сгенерированный отчёт | Анализ → PDF отчёт |
| comparison | Документ сравнения | Контракт + Анализ → Сравнение |

#### 2.4.2 API для связывания

```python
# app/api/routes/document_links.py

@router.post("/documents/{document_id}/link")
async def link_document_to_analysis(
    document_id: UUID,
    request: LinkRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Связать документ с анализом.

    Request:
    {
        "analysis_id": "uuid",
        "link_type": "source_contract" | "reference" | "generated"
    }
    """
    pass


@router.get("/analysis/{analysis_id}/documents")
async def get_analysis_documents(
    analysis_id: UUID,
    link_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Получить все документы, связанные с анализом."""
    pass


@router.get("/documents/{document_id}/analyses")
async def get_document_analyses(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Получить все анализы, связанные с документом."""
    pass
```

#### 2.4.3 Автоматическое связывание

```python
# app/services/auto_linker.py

class AutoLinkerService:
    """
    Автоматическое определение связей между документами и анализами.
    """

    async def suggest_links(
        self,
        document_id: UUID
    ) -> List[SuggestedLink]:
        """
        Предложить связи на основе:
        1. Совпадения названий проектов
        2. Совпадения дат
        3. Совпадения репозиториев (если указан URL)
        4. Текстового сходства
        """
        document = await self.doc_repo.get(document_id)
        contract_data = document.contract_data

        suggestions = []

        # По названию проекта
        if contract_data and contract_data.contract_title:
            analyses = await self.analysis_repo.search_by_name(
                contract_data.contract_title
            )
            for analysis in analyses:
                suggestions.append(SuggestedLink(
                    analysis_id=analysis.id,
                    confidence=0.8,
                    reason="Project name match",
                ))

        # По датам (анализ в период контракта)
        if contract_data and contract_data.start_date:
            analyses = await self.analysis_repo.find_in_date_range(
                start=contract_data.start_date,
                end=contract_data.end_date,
            )
            for analysis in analyses:
                suggestions.append(SuggestedLink(
                    analysis_id=analysis.id,
                    confidence=0.6,
                    reason="Date range match",
                ))

        return suggestions
```

---

### 2.5 Модуль генерации документов (Generation Module)

#### 2.5.1 Типы генерируемых документов

| Категория | Документы | Форматы |
|-----------|-----------|---------|
| Аудит | Tech Report, Quality Report, Security Report | PDF, Word, MD |
| Финансы | Cost Estimate, Budget Status, Act of Work | PDF, Excel |
| Донорские | Donor One-Pager, Progress Report, Indicators | PDF, Word |
| Сравнение | Contract Compliance, Variance Report | PDF, Excel |

#### 2.5.2 Шаблонизация с данными из контрактов

```python
# app/services/document_generator_v2.py

class EnhancedDocumentGenerator:
    """
    Генератор документов с поддержкой данных из контрактов.
    """

    async def generate(
        self,
        document_type: str,
        analysis_id: UUID,
        format: str,
        include_contract_data: bool = True,
    ) -> bytes:
        """
        Генерация документа с автоматическим включением данных контракта.
        """
        # Получаем анализ
        analysis = await self.analysis_repo.get(analysis_id)

        # Получаем связанные контракты
        contracts = []
        if include_contract_data:
            linked_docs = await self.link_repo.get_by_analysis(
                analysis_id,
                link_type="source_contract"
            )
            for doc in linked_docs:
                if doc.contract_data:
                    contracts.append(doc.contract_data)

        # Собираем данные
        data = {
            "analysis": analysis.to_dict(),
            "metrics": analysis.metrics.to_dict() if analysis.metrics else {},
            "contracts": [c.to_dict() for c in contracts],
            "comparison": await self._generate_comparison(analysis, contracts),
        }

        # Генерируем по типу
        if document_type == "compliance_report":
            return await self._generate_compliance_report(data, format)
        elif document_type == "progress_report":
            return await self._generate_progress_report(data, format)
        # ... etc

    async def _generate_comparison(
        self,
        analysis: Analysis,
        contracts: List[ContractData],
    ) -> Dict:
        """Сравнение плана (контракт) с фактом (анализ)."""
        if not contracts:
            return {}

        contract = contracts[0]  # Primary contract

        return {
            "budget": {
                "planned": contract.total_amount,
                "estimated": analysis.metrics.cost_estimates.get("typical"),
                "variance": self._calc_variance(
                    contract.total_amount,
                    analysis.metrics.cost_estimates.get("typical")
                ),
            },
            "timeline": {
                "planned_days": (contract.end_date - contract.start_date).days,
                "estimated_hours": analysis.metrics.cost_estimates.get("hours_typical"),
            },
            "deliverables": self._compare_deliverables(
                contract.work_plan,
                analysis.tasks,
            ),
            "indicators": self._compare_indicators(
                contract.indicators,
                analysis.metrics,
            ),
        }
```

#### 2.5.3 Template Engine

```python
# app/services/template_engine.py

class TemplateEngine:
    """
    Движок шаблонов с поддержкой:
    - Jinja2 для текстовых шаблонов
    - DOCX templates для Word
    - HTML templates для PDF
    """

    def __init__(self):
        self.jinja_env = Environment(
            loader=FileSystemLoader("templates"),
            autoescape=True,
        )
        self.docx_templates = Path("templates/docx")
        self.html_templates = Path("templates/html")

    async def render_markdown(
        self,
        template_name: str,
        data: Dict
    ) -> str:
        template = self.jinja_env.get_template(f"{template_name}.md.j2")
        return template.render(**data)

    async def render_docx(
        self,
        template_name: str,
        data: Dict,
    ) -> bytes:
        """Render DOCX from template."""
        from docxtpl import DocxTemplate

        template_path = self.docx_templates / f"{template_name}.docx"
        doc = DocxTemplate(template_path)
        doc.render(data)

        buffer = io.BytesIO()
        doc.save(buffer)
        return buffer.getvalue()

    async def render_pdf(
        self,
        template_name: str,
        data: Dict,
    ) -> bytes:
        """Render PDF from HTML template."""
        template = self.jinja_env.get_template(f"{template_name}.html.j2")
        html = template.render(**data)

        from weasyprint import HTML
        return HTML(string=html).write_pdf()
```

---

### 2.6 Модуль экспорта и распространения (Export Module)

#### 2.6.1 Варианты экспорта

| Destination | Метод | Конфигурация |
|-------------|-------|--------------|
| Local Download | HTTP Response | - |
| Google Drive | API | GOOGLE_* |
| Email | SMTP | SMTP_* |
| Webhook | HTTP POST | WEBHOOK_URL |
| S3 Bucket | AWS SDK | S3_* |
| Slack | Webhook | SLACK_WEBHOOK |

#### 2.6.2 Export API

```python
# app/api/routes/export_v2.py

@router.post("/documents/{document_id}/export")
async def export_document(
    document_id: UUID,
    request: ExportRequest,
):
    """
    Универсальный экспорт документа.

    Request:
    {
        "destination": "download" | "gdrive" | "email" | "s3" | "slack",
        "format": "pdf" | "docx" | "xlsx" | "md",
        "options": {
            // Для gdrive
            "folder_id": "...",

            // Для email
            "recipients": ["email@example.com"],
            "subject": "...",

            // Для s3
            "bucket": "...",
            "key": "...",

            // Для slack
            "channel": "#reports",
            "message": "..."
        }
    }
    """
    pass


@router.post("/analysis/{analysis_id}/export-package")
async def export_document_package(
    analysis_id: UUID,
    request: PackageExportRequest,
):
    """
    Экспорт пакета документов для анализа.

    Request:
    {
        "document_types": ["tech_report", "cost_estimate", "task_list"],
        "format": "pdf",
        "destination": "gdrive",
        "create_folder": true,
        "folder_name": "Audit Report {date}"
    }
    """
    pass
```

#### 2.6.3 Scheduled Export

```python
# app/services/scheduled_export.py

class ScheduledExportService:
    """
    Планировщик автоматического экспорта.
    """

    async def schedule_export(
        self,
        analysis_id: UUID,
        schedule: str,  # cron expression
        export_config: ExportConfig,
    ):
        """
        Настроить регулярный экспорт.

        Например: еженедельный отчёт прогресса донору.
        """
        pass

    async def run_scheduled_exports(self):
        """Запуск по расписанию (вызывается из cron/celery)."""
        pass
```

---

## 3. Нефункциональные требования

### 3.1 Производительность

| Метрика | Требование |
|---------|------------|
| Загрузка файла <10MB | < 3 сек |
| Извлечение (regex) | < 1 сек |
| Извлечение (LLM) | < 30 сек |
| Генерация PDF | < 5 сек |
| Генерация Excel | < 3 сек |

### 3.2 Масштабируемость

- Поддержка до 10,000 документов на организацию
- Параллельная обработка до 10 документов
- Очередь задач для тяжёлых операций (Celery/RQ)

### 3.3 Безопасность

- Шифрование файлов at rest (AES-256)
- RBAC для доступа к документам
- Audit log всех операций
- Автоматическое удаление через N дней (configurable)

### 3.4 Интеграции

| Система | Тип интеграции | Статус |
|---------|----------------|--------|
| Google Drive | OAuth 2.0 + API | Есть |
| LLM (Claude/GPT) | API | Частично |
| PostgreSQL | Direct | Есть |
| S3/MinIO | AWS SDK | Планируется |
| Email (SMTP) | Direct | Частично |
| Slack | Webhook | Планируется |

---

## 4. UI/UX требования

### 4.1 Страница загрузки документов

```
┌─────────────────────────────────────────────────────────────┐
│  Upload Document                                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐│
│  │                                                          ││
│  │     📁 Drop files here or click to browse               ││
│  │                                                          ││
│  │     Supported: PDF, DOCX, XLSX, TXT                     ││
│  │                                                          ││
│  └─────────────────────────────────────────────────────────┘│
│                                                              │
│  ─── OR ───                                                  │
│                                                              │
│  [📁 Google Drive]  [📋 Paste Text]  [🔗 From URL]          │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│  Document Type:  [Contract ▼]                                │
│                                                              │
│  Link to Analysis: [Select or create new... ▼]              │
│                                                              │
│  [Upload & Process]                                          │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 Страница просмотра извлечённых данных

```
┌─────────────────────────────────────────────────────────────┐
│  Contract: Project Alpha Agreement                           │
│  Status: ✅ Processed  |  Confidence: 87%                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  [Overview] [Work Plan] [Budget] [Indicators] [Raw Text]    │
│                                                              │
│  ┌───────────────────────┬─────────────────────────────────┐│
│  │ Field                 │ Extracted Value          [Edit] ││
│  ├───────────────────────┼─────────────────────────────────┤│
│  │ Contract Number       │ PA-2024-001              ✅     ││
│  │ Contract Date         │ January 15, 2024         ✅     ││
│  │ Total Amount          │ $150,000 USD             ✅     ││
│  │ Start Date            │ February 1, 2024         ✅     ││
│  │ End Date              │ December 31, 2024        ⚠️     ││
│  │ Client                │ ACME Foundation          ✅     ││
│  └───────────────────────┴─────────────────────────────────┘│
│                                                              │
│  ⚠️ Low confidence fields need review                        │
│                                                              │
│  [Confirm All]  [Link to Analysis]  [Generate Reports]       │
└─────────────────────────────────────────────────────────────┘
```

### 4.3 Страница сравнения контракт vs анализ

```
┌─────────────────────────────────────────────────────────────┐
│  Contract vs Analysis Comparison                             │
├─────────────────────────────────────────────────────────────┤
│  Contract: PA-2024-001  ↔  Analysis: repo-xyz               │
│                                                              │
│  Overall Status: ⚠️ AT RISK                                  │
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ Budget Comparison                                        ││
│  │ ┌────────────────────────────────────────────┐          ││
│  │ │ Planned:   ████████████████████ $150,000   │          ││
│  │ │ Estimated: ██████████████████████ $165,000 │          ││
│  │ │                                 +10% ⚠️     │          ││
│  │ └────────────────────────────────────────────┘          ││
│  └─────────────────────────────────────────────────────────┘│
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ Deliverables Progress                                    ││
│  │ ☑ Phase 1: Requirements Analysis     ✅ Complete         ││
│  │ ☑ Phase 2: Development               🔄 In Progress      ││
│  │ ☐ Phase 3: Testing                   ⏳ Pending          ││
│  │ ☐ Phase 4: Deployment                ⏳ Pending          ││
│  └─────────────────────────────────────────────────────────┘│
│                                                              │
│  [Download Report]  [Send to Stakeholders]  [Schedule Update]│
└─────────────────────────────────────────────────────────────┘
```

---

## 5. План реализации

### Фаза 1: Базовая инфраструктура (2 недели)

| Задача | Приоритет | Оценка |
|--------|-----------|--------|
| Миграции БД (documents, contract_data) | P0 | 4h |
| SQLAlchemy модели | P0 | 4h |
| File Storage Service (абстракция) | P0 | 8h |
| Document Repository | P0 | 4h |
| Upload API endpoints | P0 | 8h |
| Unit tests | P0 | 8h |

### Фаза 2: Извлечение данных (2 недели)

| Задача | Приоритет | Оценка |
|--------|-----------|--------|
| Улучшенный Regex Extractor | P0 | 8h |
| LLM Extraction Service | P0 | 16h |
| Hybrid Extraction Pipeline | P0 | 8h |
| Confidence Scoring | P1 | 4h |
| Pattern Learning Service | P2 | 8h |
| Integration tests | P0 | 8h |

### Фаза 3: Связывание и сравнение (1 неделя)

| Задача | Приоритет | Оценка |
|--------|-----------|--------|
| Document-Analysis linking API | P0 | 4h |
| Auto-linker suggestions | P1 | 8h |
| Enhanced comparison service | P0 | 8h |
| Comparison reports | P0 | 8h |

### Фаза 4: Генерация документов (2 недели)

| Задача | Приоритет | Оценка |
|--------|-----------|--------|
| Template engine setup | P0 | 8h |
| DOCX templates | P0 | 16h |
| PDF templates (WeasyPrint) | P0 | 16h |
| Excel templates | P1 | 8h |
| Contract-aware generation | P0 | 8h |

### Фаза 5: UI и интеграции (2 недели)

| Задача | Приоритет | Оценка |
|--------|-----------|--------|
| Upload page UI | P0 | 8h |
| Extracted data review UI | P0 | 12h |
| Comparison dashboard | P0 | 12h |
| Multi-export destinations | P1 | 8h |
| Slack/Email integration | P2 | 8h |

### Фаза 6: Полировка и тесты (1 неделя)

| Задача | Приоритет | Оценка |
|--------|-----------|--------|
| E2E tests | P0 | 16h |
| Performance optimization | P1 | 8h |
| Documentation | P0 | 8h |
| Bug fixes | P0 | 8h |

---

## 6. Риски и митигация

| Риск | Вероятность | Влияние | Митигация |
|------|-------------|---------|-----------|
| LLM extraction неточен | Высокая | Среднее | Hybrid approach + manual review |
| Большие файлы тормозят | Средняя | Среднее | Async processing + progress |
| Разные форматы контрактов | Высокая | Высокое | Configurable patterns + learning |
| Интеграция с GDrive ломается | Низкая | Высокое | Fallback to local storage |

---

## 7. Метрики успеха

| Метрика | Target |
|---------|--------|
| Extraction accuracy | > 85% |
| Processing time (avg) | < 10 sec |
| User confirmation rate | > 90% |
| Documents processed/day | > 100 |
| Report generation errors | < 1% |

---

## 8. Приложения

### A. Структура директорий

```
backend/
├── app/
│   ├── api/routes/
│   │   ├── documents.py      # Существующий
│   │   ├── document_upload.py # Новый
│   │   ├── document_links.py  # Новый
│   │   └── export_v2.py       # Новый
│   ├── core/models/
│   │   └── document.py        # Новый
│   ├── services/
│   │   ├── contract_parser.py # Существующий (расширить)
│   │   ├── llm_extraction.py  # Новый
│   │   ├── file_storage.py    # Новый
│   │   ├── pattern_learning.py # Новый
│   │   ├── auto_linker.py     # Новый
│   │   └── template_engine.py  # Новый
│   └── repositories/
│       └── document_repo.py    # Новый
├── templates/
│   ├── docx/                   # Word шаблоны
│   ├── html/                   # HTML для PDF
│   └── md/                     # Markdown шаблоны
└── migrations/
    └── versions/
        └── xxx_add_documents.py # Новый
```

### B. Environment Variables

```env
# File Storage
FILE_STORAGE_TYPE=db  # db, local, s3, gdrive
STORAGE_PATH=/var/data/documents
MAX_FILE_SIZE_MB=50

# S3 (optional)
S3_BUCKET=repo-auditor-docs
S3_ACCESS_KEY=xxx
S3_SECRET_KEY=xxx
S3_ENDPOINT=https://s3.amazonaws.com

# LLM Extraction
LLM_EXTRACTION_ENABLED=true
LLM_EXTRACTION_PROVIDER=anthropic  # anthropic, openai
LLM_EXTRACTION_MODEL=claude-3-haiku

# Export
EXPORT_TEMP_DIR=/tmp/exports
EXPORT_RETENTION_DAYS=7
```

---

**Конец документа**
