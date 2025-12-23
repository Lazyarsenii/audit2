# Repo Auditor MCP Server

MCP (Model Context Protocol) сервер для интеграции с Claude Code и Claude Desktop.

## Возможности

Сервер предоставляет инструменты для:

- **list_profiles** - Список доступных профилей оценки (EU Standard, UA R&D, US Standard и др.)
- **list_contracts** - Список контрактных требований (GDPR, HIPAA, ISO 27001 и др.)
- **estimate_cost** - Расчет стоимости проекта на основе метрик
- **check_readiness** - Проверка готовности проекта к аудиту
- **check_compliance** - Проверка соответствия контрактным требованиям
- **generate_document** - Генерация документов (акты, инвойсы, отчеты)
- **get_template_variables** - Получение переменных для шаблона
- **calculate_scores** - Расчет скорингов репозитория
- **get_scoring_rubric** - Получение методологии оценки

## Установка

```bash
cd mcp-server
pip install -r requirements.txt
```

## Использование с Claude Desktop

Добавьте в конфигурацию Claude Desktop (`~/.claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "repo-auditor": {
      "command": "python",
      "args": ["/path/to/repo-auditor/mcp-server/server.py"],
      "env": {}
    }
  }
}
```

## Использование с Claude Code

Добавьте в `.claude/settings.json` вашего проекта:

```json
{
  "mcpServers": {
    "repo-auditor": {
      "command": "python",
      "args": ["./mcp-server/server.py"]
    }
  }
}
```

## Примеры использования

### Расчет стоимости проекта

```
Используй tool estimate_cost с параметрами:
- lines_of_code: 50000
- complexity: 2.5
- profile_id: "ua_standard"
```

### Проверка готовности

```
Используй tool check_readiness с параметрами:
- has_readme: true
- has_tests: true
- has_docker: false
- has_cicd: true
- has_dependencies: true
```

### Генерация акта выполненных работ

```
Используй tool generate_document с параметрами:
- template_id: "act_of_work_uk"
- variables: {
    "contractor_name": "ТОВ Девелопер",
    "client_name": "ТОВ Замовник",
    "project_name": "Веб-платформа",
    "total_amount": "150000",
    "currency": "UAH"
  }
```

## Шаблоны документов

- `act_of_work_uk` - Акт виконаних робіт (українською)
- `act_of_work_en` - Act of Work Completion (English)
- `invoice` - Invoice / Рахунок
- `analysis_report` - Repository Analysis Report

## Профили оценки

| ID | Название | Регион | Валюта | Junior | Middle | Senior |
|----|----------|--------|--------|--------|--------|--------|
| eu_standard | EU Standard R&D | EU | EUR | €35 | €55 | €85 |
| ua_standard | Ukraine R&D | UA | USD | $15 | $30 | $50 |
| eu_enterprise | EU Enterprise | EU | EUR | €45 | €70 | €110 |
| us_standard | US Standard | US | USD | $50 | $85 | $130 |
| startup | Startup/MVP | Global | USD | $25 | $45 | $70 |
| poland | Poland R&D | EU | EUR | €30 | €45 | €65 |
| germany | Germany Enterprise | DE | EUR | €55 | €85 | €120 |
| uk_standard | UK Standard | UK | GBP | £45 | £75 | £110 |

## Требования к контрактам

| ID | Название | Compliance |
|----|----------|------------|
| global_fund | Global Fund Round 13 | HIPAA, ISO 22301, GDPR |
| eu_gdpr | EU GDPR | GDPR |
| hipaa | HIPAA Healthcare | HIPAA, HITECH |
| iso27001 | ISO 27001 Security | ISO 27001 |
| pci_dss | PCI DSS | PCI DSS |
