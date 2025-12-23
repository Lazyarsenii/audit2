# Repo Auditor — Executive Summary

## What Repo Auditor Does

Repo Auditor is an automated service that:

- inspects a source-code repository,
- evaluates its **health** and **technical debt**,
- determines the **product maturity** and **complexity**,
- estimates **future effort and cost** to bring it to a desired level,
- approximates **past effort and cost** already invested,
- generates a **task backlog** for further development.

It is designed for:

- R&D portfolios,
- internal tools,
- platform modules,
- pre-production codebases.

---

## Key Outputs per Repository

For each repository, Repo Auditor produces:

### 1. Project Description
- What this repo does
- Who it is for
- Technology stack
- Current maturity level (R&D spike → near-product)
- Complexity (S / M / L / XL)

### 2. Repository Health
- Documentation quality
- Repository structure
- Ease of running the project
- Commit history / activity

### 3. Technical Debt
- Architecture quality
- Code quality
- Testing maturity
- Infrastructure (Docker, CI/CD)
- Security & dependencies

### 4. Forward-Looking Estimate
- Hours needed for: analysis, design, development, testing, documentation
- Cost ranges for **EU** and **UA** based on configurable hourly rates

### 5. Historical Effort Estimate
- Approximate hours and person-months already invested
- Rough cost ranges for EU and UA
- Clearly marked as high-uncertainty estimation

### 6. Task Backlog
- Concrete tasks to fix gaps
- Each task has an estimate and priority
- Categories: documentation, tests, refactor, infrastructure, security

---

## How It Works (High Level)

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Repository     │────▶│  Analyzers       │────▶│  Scoring        │
│  (clone)        │     │  - Structure     │     │  - Repo Health  │
└─────────────────┘     │  - Static Code   │     │  - Tech Debt    │
                        │  - Semgrep       │     │  - Product Level│
                        │  - Git History   │     │  - Complexity   │
                        └──────────────────┘     └────────┬────────┘
                                                          │
                        ┌──────────────────┐              │
                        │  Cost Estimator  │◀─────────────┘
                        │  - Forward       │
                        │  - Historical    │
                        └────────┬─────────┘
                                 │
                        ┌────────▼─────────┐
                        │  Task Generator  │
                        └────────┬─────────┘
                                 │
                        ┌────────▼─────────┐
                        │  Report Builder  │
                        │  - Markdown      │
                        │  - CSV           │
                        │  - JSON API      │
                        └──────────────────┘
```

---

## Why This Approach Is Reasonable

### Научное обоснование методологии

**1. Модель качества — ISO/IEC 25010**

Мы опираемся на международный стандарт качества ПО, фокусируясь на двух ключевых характеристиках:
- **Maintainability** (сопровождаемость) — насколько легко модифицировать код
- **Security** (безопасность) — отсутствие уязвимостей

Эти характеристики можно объективно измерить автоматически, в отличие от субъективных метрик типа "usability".

**2. Технический долг — подход SonarQube**

Концепция технического долга (Ward Cunningham, 1992) давно стала индустриальным стандартом:
- Code smells, complexity, duplication → измеримые индикаторы
- Прямая корреляция с затратами на поддержку (исследования Microsoft, Google)

Мы используем упрощённую, но прозрачную модель вместо "чёрного ящика".

**3. Оценка стоимости — COCOMO II**

Parametric Cost Estimation (Barry Boehm, USC) — проверенный метод:
- **Размер** (LOC, complexity) → базовые часы
- **Множители** (tech debt, integrations) → коррекция
- **Региональные ставки** → итоговая стоимость

Формула: `Cost = BaseHours × TechDebtMultiplier × ActivityRatios × HourlyRate`

**4. Статический анализ — Semgrep**

Open-source движок от r2c (приобретён в 2023):
- 2000+ правил для безопасности
- Поддержка 30+ языков
- Используется Netflix, Dropbox, Figma

**5. Конфигурируемость**

Все пороги и ставки вынесены в YAML — можно калибровать под реальные данные организации.

### Почему НЕ другие подходы

| Альтернатива | Проблема |
|--------------|----------|
| Только LOC | Не учитывает качество и сложность |
| Только покрытие тестами | Однобокая метрика, можно "накрутить" |
| Ручная оценка | Субъективно, не масштабируется |
| Полный SonarQube | Избыточно сложно для R&D/прототипов |

### Ограничения метода

- Оценки приблизительные (±30-50%)
- Не заменяет ревью экспертом
- Требует калибровки под организацию
- Historical estimate — грубое приближение

---

## Typical Use Cases

### R&D Portfolio Review
Quickly assess experimental repositories to decide:
- what to promote into core platform
- where to invest in refactoring
- what to archive as reference

### Pre-Investment / Due Diligence
Provide an objective, structured, repeatable snapshot:
- health and risk profile
- technical debt level
- approximate effort already invested
- effort and cost required to reach production

### Internal Architecture Governance
Use regularly to:
- maintain a catalog of internal tools and modules
- monitor quality trends
- prioritize technical debt work

---

## What Repo Auditor Is Not

Repo Auditor is not meant to replace human review.

It is a **systematic first pass** that normalizes and structures information about repositories, making expert reviews faster and more informed.

---

## Integration Options

| Interface | Description |
|-----------|-------------|
| **REST API** | `POST /api/analyze`, `GET /api/analysis/{id}` |
| **GitHub App** | `/audit` command in issues, auto-commit `REPO_AUDIT.md` |
| **MCP Tool** | `repo_auditor` tool for AI agents |
| **Web UI** | Dashboard for browsing analyses |
