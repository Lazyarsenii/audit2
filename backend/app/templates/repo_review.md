# REPOSITORY REVIEW — {{ repo_name }}

**URL:** {{ repo_url }}
**Branch:** {{ branch | default('main') }}
**Date:** {{ date }}

---

## 1. Product Level (тип результата)

**Классификация:** {{ product_level }}

**Описание:**
```
{{ product_description | default('—') }}
```

**Confidence:** {{ confidence | default('—') }}%

---

## 2. Repo Health (0–3 по каждому показателю)

| Метрика        | Оценка | Комментарий |
| -------------- | ------ | ----------- |
| Documentation  | {{ repo_health.documentation }}/3 | {{ comments.documentation | default('—') }} |
| Structure      | {{ repo_health.structure }}/3 | {{ comments.structure | default('—') }} |
| Runability     | {{ repo_health.runability }}/3 | {{ comments.runability | default('—') }} |
| Commit History | {{ repo_health.commit_history }}/3 | {{ comments.commit_history | default('—') }} |

**Итог Repo Health Score:** {{ repo_health.total }}/12

---

## 3. Tech Debt & Code Quality (0–3 по метрике)

| Метрика       | Оценка | Комментарий |
| ------------- | ------ | ----------- |
| Architecture  | {{ tech_debt.architecture }}/3 | {{ comments.architecture | default('—') }} |
| Code Quality  | {{ tech_debt.code_quality }}/3 | {{ comments.code_quality | default('—') }} |
| Testing       | {{ tech_debt.testing }}/3 | {{ comments.testing | default('—') }} |
| Infra         | {{ tech_debt.infrastructure }}/3 | {{ comments.infrastructure | default('—') }} |
| Security/Deps | {{ tech_debt.security_deps }}/3 | {{ comments.security_deps | default('—') }} |

**Итог Tech Debt Score:** {{ tech_debt.total }}/15

---

## 4. Complexity

**Уровень:** {{ complexity }}

| Level | LOC Range | Описание |
|-------|-----------|----------|
| S | до 8k | Один сервис, мало зависимостей |
| M | 8-40k | Несколько модулей, пара интеграций |
| L | 40-120k | Несколько сервисов, сложная архитектура |
| XL | >120k | Платформа/монолит с обширной интеграцией |

**Текущий LOC:** {{ static_metrics.total_loc | default('—') }}
**Файлов:** {{ static_metrics.files_count | default('—') }}

---

## 5. Общая оценка

| Параметр | Значение |
|----------|----------|
| Product Level | {{ product_level }} |
| Repo Health | {{ repo_health.total }}/12 ({{ health_percent }}%) |
| Tech Debt | {{ tech_debt.total }}/15 ({{ debt_percent }}%) |
| Complexity | {{ complexity }} |

### Вердикт: `{{ verdict }}`

Возможные статусы:
- `Archive / Reference Only` — только как референс
- `Internal Tool` — внутренний инструмент
- `R&D Prototype` — прототип для исследований
- `Platform Module Candidate` — кандидат в модуль платформы
- `Near-Product` — близок к продукту

---

## 6. Оценка стоимости

### Forward-Looking (будущие затраты)

| Активность | Min | Typical | Max |
|------------|-----|---------|-----|
| Analysis | {{ cost.hours.min.analysis }}h | {{ cost.hours.typical.analysis }}h | {{ cost.hours.max.analysis }}h |
| Design | {{ cost.hours.min.design }}h | {{ cost.hours.typical.design }}h | {{ cost.hours.max.design }}h |
| Development | {{ cost.hours.min.development }}h | {{ cost.hours.typical.development }}h | {{ cost.hours.max.development }}h |
| QA | {{ cost.hours.min.qa }}h | {{ cost.hours.typical.qa }}h | {{ cost.hours.max.qa }}h |
| Documentation | {{ cost.hours.min.documentation }}h | {{ cost.hours.typical.documentation }}h | {{ cost.hours.max.documentation }}h |
| **Total** | **{{ cost.hours.min.total }}h** | **{{ cost.hours.typical.total }}h** | **{{ cost.hours.max.total }}h** |

**Стоимость:**
- EU: {{ cost.cost.eu.formatted }}
- UA: {{ cost.cost.ua.formatted }}

**Tech Debt Multiplier:** {{ cost.tech_debt_multiplier }}x

### Historical (уже потрачено, приблизительно)

- Active days: {{ historical.active_days }}
- Estimated hours: {{ historical.hours.min }}—{{ historical.hours.max }}h
- Person-months: {{ historical.person_months.min }}—{{ historical.person_months.max }}
- Confidence: {{ historical.confidence }}

---

## 7. Рекомендации

{% for task in tasks %}
### {{ loop.index }}. {{ task.title }}

**Приоритет:** {{ task.priority }} | **Категория:** {{ task.category }} | **Оценка:** {{ task.estimate_hours }}h

{{ task.description }}

{% endfor %}

---

## 8. Следующие шаги

{% if verdict == 'Archive / Reference Only' %}
- Извлечь полезные наработки и задокументировать
- Архивировать репозиторий
- Использовать как reference при разработке новых модулей
{% elif verdict == 'R&D Prototype' %}
- Документировать выводы и гипотезы
- Оценить целесообразность развития
- При положительном решении — планировать рефакторинг
{% elif verdict == 'Internal Tool' %}
- Добавить базовую документацию
- Настроить CI для стабильности
- Поддерживать для внутреннего использования
{% elif verdict == 'Platform Module Candidate' %}
- Провести рефакторинг архитектуры
- Добавить тесты (target: 60%+ coverage)
- Стандартизировать API/интерфейсы
- Подготовить к интеграции в платформу
{% elif verdict == 'Near-Product' %}
- Финальный polish документации
- Security review
- Performance testing
- Подготовка к production deployment
{% endif %}

---

*Generated by Repo Auditor on {{ date }}*
