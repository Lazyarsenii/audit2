# User Instructions / Інструкції для користувача

## English

### Purpose
Use these instructions to run repository audits, interpret outputs, and know where results are stored.

### How to Run an Audit
1. **Backend API**
   - Start the API: `cd backend && uvicorn app.main:app --reload --port 8000`.
   - Trigger analysis via HTTP:
     ```bash
     curl -X POST "http://localhost:8000/api/analyze" \
       -H "Content-Type: application/json" \
       -d '{"repo_path": "/path/to/repository", "branch": "main"}'
     ```
2. **Portable script**
   - Run from the repository you want to audit: `python3 portable/audit.py [--profile eu|ua|us] [--quick] [--server URL] [PATH]`.
3. **Pipeline expectations**
   - The system fetches the repository, aggregates structure and static metrics, applies the scoring engine, then saves metrics and reports (Markdown + JSON) into a `.audit/` directory.

### Reading Results
- **Scores**: Repo Health (0–12) and Technical Debt (0–15) with product level and complexity verdicts.
- **Reports**: Review and summary files are listed in API responses and stored locally when `generate_reports` is enabled.
- **Tasks**: Improvement tasks are included in API results and database storage when the server is connected.

### Troubleshooting
- If cloning fails, verify repository URL/credentials (see `RepoFetchError` messages).
- Ensure Python and Node dependencies are installed for backend/UI as described in `docs/README.md`.
- For persistent failures, clear temporary clones and rerun with `--quick` to isolate report-generation issues.

## Українська

### Призначення
Використовуйте ці інструкції, щоб запускати аудит репозиторіїв, розуміти результати та знаходити сформовані звіти.

### Як запустити аудит
1. **Backend API**
   - Запустіть API: `cd backend && uvicorn app.main:app --reload --port 8000`.
   - Викличте аналіз через HTTP:
     ```bash
     curl -X POST "http://localhost:8000/api/analyze" \
       -H "Content-Type: application/json" \
       -d '{"repo_path": "/path/to/repository", "branch": "main"}'
     ```
2. **Портативний скрипт**
   - Запускайте з каталогу, який потрібно проаналізувати: `python3 portable/audit.py [--profile eu|ua|us] [--quick] [--server URL] [PATH]`.
3. **Очікувана робота пайплайну**
   - Система отримує репозиторій, збирає структурні та статичні метрики, застосовує механізм оцінювання й зберігає метрики та звіти (Markdown + JSON) у каталозі `.audit/`.

### Читання результатів
- **Оцінки**: Repo Health (0–12) і Technical Debt (0–15) з вердиктами рівня продукту та складності.
- **Звіти**: Огляди та підсумки повертаються у відповідях API та зберігаються локально, якщо увімкнене `generate_reports`.
- **Завдання**: Поліпшувальні задачі додаються у відповіді API та базу даних, коли сервер підключений.

### Вирішення проблем
- Якщо клонування завершується помилкою, перевірте URL/доступ (див. повідомлення `RepoFetchError`).
- Переконайтеся, що залежності Python і Node встановлені для backend/UI відповідно до `docs/README.md`.
- За постійних збоїв видаліть тимчасові клони та запустіть із `--quick`, щоб локалізувати проблеми генерації звітів.
