# Repository Summary — {{ repo_name }}

## Статус: {{ verdict }}

## Что сделано:

{{ product_description | default('Проведена разработка и исследование архитектурного прототипа.') }}

## Ключевые метрики:

| Метрика | Значение |
|---------|----------|
| Product Level | {{ product_level }} |
| Repo Health | {{ repo_health.total }}/12 |
| Tech Debt | {{ tech_debt.total }}/15 |
| Complexity | {{ complexity }} |
| Estimated Hours | {{ cost.hours.typical.total }}h |

## Выводы:

{% if verdict == 'Platform Module Candidate' or verdict == 'Near-Product' %}
Прототип подтвердил техническую реализуемость. Закрыты архитектурные и интеграционные риски. Полученные наработки рекомендованы для переноса в системный модуль платформы.
{% elif verdict == 'Internal Tool' %}
Реализован рабочий внутренний инструмент. Пригоден для использования командой. Не требует значительных доработок для текущих задач.
{% elif verdict == 'R&D Prototype' %}
Прототип выполнил задачу исследования. Получены ценные выводы для дальнейшей разработки. Рекомендуется как reference.
{% else %}
R&D spike закрыл поставленную гипотезу. Результаты задокументированы для использования в будущих проектах.
{% endif %}

## Следующие шаги:

{% if verdict == 'Platform Module Candidate' %}
- Стандартизация и перенос логики в платформу
- Рефакторинг архитектуры
- Добавление тестов
- Подготовка к интеграции в ядро
{% elif verdict == 'Near-Product' %}
- Финальная доработка документации
- Security hardening
- Performance optimization
- Deployment preparation
{% elif verdict == 'Internal Tool' %}
- Поддержка текущего функционала
- Документирование для команды
- Опциональное улучшение по запросу
{% else %}
- Архивирование после извлечения полезного опыта
- Документирование выводов
- Использование как reference
{% endif %}

---

*{{ date }}*
