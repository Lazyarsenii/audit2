# Налаштування для Організації

## 🌐 Варіант 1: Використання через API (Рекомендовано)

Всі члени організації можуть використовувати розгорнутий API без додаткових налаштувань.

### Work Report через API

```bash
curl -X POST "https://audit2-production.up.railway.app/api/work-report" \
  -H "Content-Type: application/json" \
  -d '{
    "repo_url": "https://github.com/user/repo",
    "start_date": "2024-12-01",
    "end_date": "2024-12-31",
    "consultant_name": "Іван Петренко",
    "organization": "ТОВ Компанія",
    "worker_type": "worker"
  }' \
  --output report.pdf
```

### Параметри:
| Параметр | Обов'язковий | Приклад | Опис |
|----------|--------------|---------|------|
| repo_url | Так | https://github.com/user/repo | URL репозиторію |
| start_date | Ні | 2024-12-01 | Початок періоду (YYYY-MM-DD) |
| end_date | Ні | 2024-12-31 | Кінець періоду |
| consultant_name | Ні | Іван Петренко | Ім'я виконавця |
| organization | Ні | ТОВ Компанія | Назва організації |
| worker_type | Ні | worker/team | worker = макс 8г/день |

### Допомога по API:
```
GET https://audit2-production.up.railway.app/api/work-report/help
```

---

## 🖥️ Варіант 2: Claude Desktop MCP (Локально)

Кожен член команди може налаштувати MCP локально.

### Крок 1: Клонувати репозиторій
```bash
git clone https://github.com/Lazyarsenii/audit2.git
cd audit2/backend
pip install -r requirements.txt
```

### Крок 2: Налаштувати Claude Desktop

Відкрийте `%APPDATA%\Claude\claude_desktop_config.json` (Windows) або `~/Library/Application Support/Claude/claude_desktop_config.json` (Mac) і додайте:

```json
{
  "mcpServers": {
    "quick-auditor": {
      "command": "python",
      "args": ["C:/path/to/audit2/backend/mcp_quick_audit.py"],
      "env": {
        "PYTHONPATH": "C:/path/to/audit2/backend"
      }
    }
  }
}
```

### Крок 3: Перезапустити Claude Desktop

### Крок 4: Використовувати команди

В Claude Desktop тепер доступні:
- `analyze_local_project` - аналіз локального проекту
- `generate_work_report` - генерація work report PDF
- `get_project_stats` - швидка статистика

---

## 📝 Варіант 3: Slash Commands в Claude Code

Якщо використовуєте Claude Code CLI, доступні команди:

### /report
Покрокова генерація work report:
1. Шлях до проекту
2. Дата початку
3. Дата кінця
4. Ім'я консультанта
5. Організація
6. Тип (worker/team)

### /audit
Швидкий аналіз проекту з метриками.

---

## 🔗 Корисні посилання

- **Web UI**: https://audit2-production.up.railway.app/quick
- **API Docs**: https://audit2-production.up.railway.app/docs
- **Work Report Help**: https://audit2-production.up.railway.app/api/work-report/help

---

## ❓ Приклади використання

### Приклад 1: Згенерувати звіт за грудень
```bash
curl -X POST "https://audit2-production.up.railway.app/api/work-report" \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/company/project", "start_date": "2024-12-01", "end_date": "2024-12-31", "consultant_name": "Олена Коваль", "organization": "IT Solutions", "worker_type": "worker"}' \
  -o december_report.pdf
```

### Приклад 2: Звіт для команди (без обмеження годин)
```bash
curl -X POST "https://audit2-production.up.railway.app/api/work-report" \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/company/big-project", "worker_type": "team", "organization": "Dev Team"}' \
  -o team_report.pdf
```

### Приклад 3: В Claude Desktop
```
Згенеруй work report для C:/Projects/myapp
з 1 по 31 грудня 2024
консультант Петро Іваненко
організація ФОП Іваненко
тип worker
```
