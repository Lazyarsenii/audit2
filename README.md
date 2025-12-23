# Repo Auditor

Automated repository analysis and evaluation platform with 8-step audit workflow.

## Overview

Repo Auditor inspects source-code repositories and produces structured assessments through an 8-step workflow:

1. **Setup** - Configure project settings and parameters
2. **Readiness** - Evaluate project readiness for formal evaluation
3. **Audit** - Full repository analysis
4. **Compliance** - Check against policies and requirements
5. **Cost** - Multi-methodology cost estimation
6. **Documents** - Generate acts, invoices, reports
7. **Compare** - Compare with contract specifications
8. **Complete** - Final review and export

### Scoring Dimensions

- **Repository Health** (0-12 pts) - documentation, structure, runability, commit history
- **Technical Debt** (0-15 pts) - architecture, code quality, testing, infrastructure, security
- **Product Level** - R&D Spike / Prototype / Internal Tool / Platform Module / Near-Product
- **Complexity** - S / M / L / XL classification
- **Cost Estimates** - multi-methodology forward-looking effort and cost (EU/UA rates)
- **Task Backlog** - actionable improvement tasks

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Docker (optional)
- Git

### Local Development

**Backend (Port 7777):**

```bash
cd backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 7777
```

**Frontend (Port 3333):**

```bash
cd ui
npm install
npm run dev -- -p 3333
```

**Access:**
- Frontend: http://localhost:3333
- Backend API: http://localhost:7777
- API Docs: http://localhost:7777/docs (DEBUG mode)

For a script-driven walkthrough (start local stack, test auth, deploy to Railway/Vercel) see `QUICKSTART.md`.

**Authentication:**
- API key protection is enabled by default. Set `API_KEYS` in your `.env` (comma-separated if multiple) and provide the key via the `X-API-Key` header for every backend request.
- Example: `curl -H "X-API-Key: YOUR_KEY" http://localhost:7777/health`
- If you leave `API_KEY_REQUIRED=true` without setting `API_KEYS`, the backend will refuse to start to avoid running unprotected.

### Using Docker Compose

```bash
cp .env.example .env
docker-compose up -d
```

> **Note:** With API key auth enabled by default, set `API_KEYS` in your `.env` before running Docker Compose. The container will refuse to start if authentication is required but keys are missing.

## Features

### 1. Readiness Assessment (Step 2)

Evaluates project readiness before formal audit:

```bash
curl -X POST http://localhost:7777/api/readiness/check \
  -H "Content-Type: application/json" \
  -d '{
    "repo_health": {"documentation": 2, "structure": 2, "runability": 2, "history": 2},
    "tech_debt": {"architecture": 2, "code_quality": 2, "testing": 1, "infrastructure": 2, "security": 2},
    "product_level": "beta",
    "complexity": "M"
  }'
```

Readiness levels:
- **Not Ready** (0-40) - Needs significant work
- **Needs Work** (40-60) - Some issues to address
- **Almost Ready** (60-80) - Minor improvements needed
- **Ready** (80-95) - Ready for formal evaluation
- **Exemplary** (95-100) - Exceeds expectations

### 2. Repository Analysis (Step 3)

```bash
curl -X POST http://localhost:7777/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/owner/repo", "branch": "main"}'
```

### 3. Cost Estimation (Step 5)

Multi-methodology estimation suite:

| Methodology | Description |
|-------------|-------------|
| **COCOMO II** | Constructive Cost Model - industry standard |
| **Gartner** | Enterprise IT cost benchmarking |
| **IEEE 1063** | Documentation effort standards |
| **Microsoft** | Agile/Sprint-based estimation |
| **Google** | Engineering productivity metrics |
| **PMI** | Project Management Institute standards |
| **SEI SLIM** | Software Lifecycle Management |
| **Function Points** | Feature-based measurement |
| **PERT** | Program Evaluation Review Technique |

```bash
curl -X POST http://localhost:7777/api/estimate/comprehensive \
  -H "Content-Type: application/json" \
  -d '{
    "total_files": 150,
    "total_lines": 15000,
    "complexity": "M",
    "tech_stack": ["Python", "FastAPI", "PostgreSQL"],
    "test_coverage": 60,
    "documentation_level": 2
  }'
```

### 4. Contract Parser (Step 7)

Parse and compare contracts (PDF, DOCX, DOC, TXT):

```bash
# Get parser capabilities
curl http://localhost:7777/api/contract-parser/capabilities

# Upload contract
curl -X POST http://localhost:7777/api/contract-parser/upload \
  -F "file=@contract.pdf" \
  -F "contract_name=Project Contract"

# Create demo contract
curl -X POST http://localhost:7777/api/contract-parser/demo \
  -H "Content-Type: application/json" \
  -d '{}'
```

### 5. Financial Documents (Step 6)

Generate financial documents:

```bash
# Act of Work
curl -X POST http://localhost:7777/api/financial/act \
  -H "Content-Type: application/json" \
  -d '{
    "project_name": "MyProject",
    "contractor": "Dev Company",
    "client": "Client Corp",
    "items": [{"description": "Development", "quantity": 160, "unit": "hours", "rate": 50}]
  }'

# Invoice
curl -X POST http://localhost:7777/api/financial/invoice

# Service Contract
curl -X POST http://localhost:7777/api/financial/contract
```

## Project Structure

```
repo-auditor/
├── backend/                    # FastAPI backend (Python 3.11+)
│   ├── app/
│   │   ├── api/routes/         # API endpoints
│   │   │   ├── analyze.py      # Repository analysis
│   │   │   ├── readiness.py    # Readiness assessment
│   │   │   ├── contract_parser.py  # Contract parsing
│   │   │   ├── financial_docs.py   # Document generation
│   │   │   └── ...
│   │   ├── core/
│   │   │   ├── scoring/        # RepoHealth, TechDebt, ProductLevel, Complexity
│   │   │   └── models/         # Database models
│   │   ├── services/
│   │   │   ├── estimation_suite.py  # Multi-methodology estimation
│   │   │   ├── readiness_assessor.py # Readiness checks
│   │   │   ├── contract_parser.py    # Contract parsing
│   │   │   └── cost_estimator.py     # Cost calculations
│   │   └── config/             # YAML configurations
│   ├── tests/
│   │   ├── unit/               # Unit tests
│   │   └── integration/        # Integration tests
│   └── requirements.txt
├── ui/                         # Next.js 14 frontend
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx        # Dashboard
│   │   │   ├── workflow/       # 8-step workflow
│   │   │   └── document-matrix/ # Document matrix
│   │   └── components/
│   ├── package.json
│   └── tailwind.config.ts
├── docs/
│   └── methodology.md          # Scoring methodology
├── infra/
│   └── docker/
├── scripts/
└── docker-compose.yml
```

## API Reference

### Health Check

```bash
curl http://localhost:7777/health
```

### Analysis Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/analyze` | Start repository analysis |
| GET | `/api/analysis/{id}` | Get analysis results |
| GET | `/api/analysis/{id}/report` | Export report |

### Readiness Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/readiness/check` | Run readiness assessment |
| GET | `/api/readiness/check/{analysis_id}` | Get readiness for analysis |
| GET | `/api/readiness/levels` | Get readiness level definitions |
| GET | `/api/readiness/checks` | List available checks |

### Estimation Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/estimate/comprehensive` | Multi-methodology estimate |
| GET | `/api/estimate/methodologies` | List methodologies |

### Contract Parser Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/contract-parser/upload` | Upload and parse contract |
| GET | `/api/contract-parser/parsed` | List parsed contracts |
| GET | `/api/contract-parser/parsed/{id}` | Get parsed contract |
| POST | `/api/contract-parser/demo` | Create demo contract |
| POST | `/api/contract-parser/compare` | Compare contract with analysis |
| GET | `/api/contract-parser/capabilities` | Get parser capabilities |

### Financial Documents Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/financial/act` | Generate Act of Work |
| POST | `/api/financial/invoice` | Generate Invoice |
| POST | `/api/financial/contract` | Generate Service Contract |

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/repo_auditor

# API Settings
DEBUG=true
API_KEY_REQUIRED=true
API_KEYS=enter-a-strong-api-key-here
CORS_ORIGINS=["http://localhost:3333"]

# Rate Limiting
RATE_LIMIT_PER_MINUTE=100
RATE_LIMIT_BURST=20

# LLM Providers (optional)
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
```

### Scoring Profile (`config/scoring_profile.yaml`)

Thresholds and weights for all scoring dimensions.

### Cost Profile (`config/cost_profile.yaml`)

Base hours, activity ratios, and regional rates (EU/UA).

## Testing

```bash
cd backend
pytest                        # Run all tests
pytest -v                     # Verbose output
pytest tests/unit/            # Unit tests only
pytest --cov=app              # With coverage
```

## UI Pages

| Route | Description |
|-------|-------------|
| `/` | Dashboard with quick actions |
| `/workflow` | 8-step audit workflow wizard |
| `/document-matrix` | Document requirements matrix |
| `/projects` | Project management |
| `/settings` | Application settings |

## Tech Stack

**Backend:**
- FastAPI 0.109+
- SQLAlchemy 2.0 (async)
- PostgreSQL 15+
- Pydantic 2.5+
- Semgrep (code analysis)
- Jinja2 (templates)

**Frontend:**
- Next.js 14
- React 18
- Tailwind CSS 3.3
- Lucide React (icons)
- TypeScript 5.3

## Documentation

- [Methodology](docs/methodology.md) - Full scoring methodology
- [API Docs](http://localhost:7777/docs) - Interactive Swagger UI

## License

MIT
