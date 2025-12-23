# Repo Auditor  User Manual

Version 1.0 | December 2025

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Installation](#2-installation)
3. [Quick Start](#3-quick-start)
4. [Portable Module](#4-portable-module)
5. [Understanding Reports](#5-understanding-reports)
6. [Pricing Profiles](#6-pricing-profiles)
7. [Claude Desktop Integration](#7-claude-desktop-integration)
8. [API Reference](#8-api-reference)
9. [Configuration](#9-configuration)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Introduction

Repo Auditor is an automated repository analysis tool that evaluates source code repositories and produces structured assessments of project health, technical debt, maturity level, and cost estimates.

### Key Features

- Repository health scoring (documentation, structure, runability, history)
- Technical debt assessment (architecture, code quality, testing, infrastructure, security)
- Product maturity classification (R&D Spike to Production)
- Cost estimation with regional pricing profiles
- Actionable improvement task generation
- Multiple output formats (Markdown, JSON, CSV, PDF, Excel, Word)

### Use Cases

- R&D portfolio review
- Technical due diligence
- Project health monitoring
- Resource planning and budgeting
- Technical debt prioritization

---

## 2. Installation

### Requirements

- Python 3.8 or higher
- Git (for commit history analysis)
- Optional: Docker for containerized deployment

### Backend Installation

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Running the Server

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

### UI Installation (Optional)

```bash
cd ui
npm install
npm run dev
```

---

## 3. Quick Start

### Command Line Analysis

```bash
cd backend
python3 test_pipeline.py /path/to/repository
```

### API Analysis

```bash
curl -X POST "http://localhost:8000/api/analyze" \
  -H "Content-Type: application/json" \
  -d '{"repo_path": "/path/to/repository"}'
```

### Output Location

Reports are saved to `.audit/` directory within the analyzed repository:

```
repository/
  .audit/
    report.md      # Human-readable Markdown
    report.json    # Machine-readable JSON
    report.csv     # Spreadsheet format
```

---

## 4. Portable Module

The portable module (`portable/audit.py`) is a standalone script that can be dropped into any project.

### Setup

1. Copy files to your project:
```bash
cp portable/audit.py /path/to/your/project/
cp portable/CLAUDE.md /path/to/your/project/
```

2. Run analysis:
```bash
cd /path/to/your/project
python3 audit.py
```

### Command Line Options

| Option | Description |
|--------|-------------|
| `--profile <name>` | Pricing profile: `eu`, `ua`, `us` (default: `eu`) |
| `--quick` | Quick scan without generating report files |
| `--server <url>` | Send results to server |
| `--format <type>` | Output format: `markdown`, `json`, `csv` |
| `<path>` | Repository path (default: current directory) |

### Examples

```bash
# Basic analysis with EU pricing
python3 audit.py

# Ukraine pricing profile
python3 audit.py --profile ua

# Quick scan without reports
python3 audit.py --quick

# Analyze specific directory
python3 audit.py /path/to/other/project

# Send results to server
python3 audit.py --server http://your-server.com/api
```

### Environment Variables

| Variable | Description |
|----------|-------------|
| `REPO_AUDITOR_SERVER` | Default server URL for result upload |
| `REPO_AUDITOR_PROFILE` | Default pricing profile |

---

## 5. Understanding Reports

### Executive Summary

The report begins with key metrics:

| Metric | Description |
|--------|-------------|
| Stage | Development stage (R&D Spike to Production) |
| Confidence | Classification confidence percentage |
| Status | Maintenance status (Active, Legacy, etc.) |
| Readiness | Business readiness level |
| Complexity | Size classification (S/M/L/XL) |
| Repo Health | Repository health score (X/12) |
| Tech Debt | Technical debt score (X/15) |

### Repository Health Score (0-12)

| Category | Max | What It Measures |
|----------|-----|------------------|
| Documentation | 3 | README quality, usage instructions |
| Structure | 3 | Directory organization |
| Runability | 3 | Dependencies, Docker support |
| History | 3 | Commit count, author diversity |

**Interpretation:**
- 10-12: Excellent  ready for production
- 7-9: Good  minor improvements needed
- 4-6: Fair  several areas need work
- 0-3: Poor  significant work required

### Technical Debt Score (0-15)

| Category | Max | What It Measures |
|----------|-----|------------------|
| Architecture | 3 | Code organization, patterns |
| Code Quality | 3 | Standards, complexity |
| Testing | 3 | Test coverage |
| Infrastructure | 3 | CI/CD, deployment |
| Security | 3 | Vulnerabilities |

**Interpretation:**
- 13-15: Minimal debt  well-maintained
- 10-12: Low debt  some improvements needed
- 6-9: Moderate debt  noticeable issues
- 0-5: High debt  major refactoring needed

### Development Stage

| Stage | Description |
|-------|-------------|
| R&D Spike | Experimental, not for maintenance |
| Proof of Concept | Demonstrates feasibility |
| Prototype | Working but incomplete |
| MVP | Core features functional |
| Alpha | Feature-complete for testing |
| Beta | Stable for user testing |
| Release Candidate | Final testing phase |
| Production | Deployed and maintained |

### Business Readiness

| Level | Meaning |
|-------|---------|
| Not Ready | Cannot be used reliably |
| Internal Use Only | For internal teams only |
| Partner Ready | Can share with partners |
| Market Ready | Ready for public release |
| Enterprise Ready | Enterprise deployment capable |

### Cost Estimation

The cost estimate includes:

- **Estimated Hours**: Total effort based on complexity
- **Cost Range**: Min-max range based on pricing profile
- **Profile Applied**: Which regional rates were used

---

## 6. Pricing Profiles

### Available Profiles

| Profile | Currency | Junior | Middle | Senior | Overhead |
|---------|----------|--------|--------|--------|----------|
| EU Standard | EUR | 35 | 55 | 85 | 1.35x |
| Ukraine | USD | 15 | 30 | 50 | 1.20x |
| US Standard | USD | 50 | 85 | 130 | 1.40x |
| EU Enterprise | EUR | 50 | 80 | 120 | 1.50x |
| Fintech | EUR | 45 | 75 | 120 | 1.50x |
| Startup | EUR | 30 | 45 | 70 | 1.25x |

### Selecting a Profile

```bash
# Command line
python3 audit.py --profile ua

# API
curl -X POST "http://localhost:8000/api/analyze" \
  -d '{"repo_path": "/path", "profile": "eu_standard"}'
```

### Custom Profiles

Custom profiles can be defined in `config/evaluation_profiles.yaml`:

```yaml
custom_profile:
  pricing:
    currency: EUR
    hourly_rates:
      junior: 40
      middle: 60
      senior: 90
    overhead_multiplier: 1.30
  acceptance:
    min_repo_health: 7
    min_tech_debt: 8
    min_readiness: 70
```

---

## 7. Claude Desktop Integration

### MCP Server Setup

1. Start the MCP server:
```bash
cd backend
python3 mcp_server.py
```

2. Configure Claude Desktop to use the server.

### Available Tools

| Tool | Description |
|------|-------------|
| `analyze_repo` | Full repository analysis |
| `check_readiness` | Quick readiness assessment |
| `quick_scan` | Fast scan without reports |
| `list_profiles` | Show available pricing profiles |
| `generate_report` | Generate specific report format |

### Claude Desktop Usage

When Claude opens a folder containing `audit.py` and `CLAUDE.md`:

1. Claude reads `CLAUDE.md` for instructions
2. Runs `python3 audit.py` automatically
3. Analyzes the generated `.audit/report.md`
4. Provides a summary to the user

Example prompt: "Analyze this repository"

---

## 8. API Reference

### Endpoints

#### POST /api/analyze
Analyze a repository.

**Request:**
```json
{
  "repo_path": "/path/to/repo",
  "repo_url": "https://github.com/user/repo",
  "profile": "eu_standard"
}
```

**Response:**
```json
{
  "analysis_id": "uuid",
  "stage": "Alpha",
  "confidence": 75,
  "repo_health": {
    "total": 8,
    "documentation": 3,
    "structure": 3,
    "runability": 2,
    "history": 0
  },
  "tech_debt": {
    "total": 8,
    "architecture": 1,
    "code_quality": 2,
    "testing": 2,
    "infrastructure": 0,
    "security": 3
  },
  "cost_estimate": {
    "hours": 405,
    "cost_min": 22553,
    "cost_max": 45106,
    "currency": "EUR"
  }
}
```

#### GET /api/analysis/{id}
Retrieve analysis results.

#### GET /api/profiles
List available pricing profiles.

#### POST /api/documents/generate
Generate documents in various formats.

**Request:**
```json
{
  "analysis_id": "uuid",
  "format": "pdf",
  "template": "full_report"
}
```

---

## 9. Configuration

### Configuration Files

| File | Description |
|------|-------------|
| `config/scoring_profile.yaml` | Scoring thresholds and weights |
| `config/cost_profile.yaml` | Cost estimation parameters |
| `config/evaluation_profiles.yaml` | Regional pricing profiles |

### Scoring Configuration

```yaml
# scoring_profile.yaml
repo_health:
  documentation:
    weight: 0.25
    thresholds:
      poor: 0
      fair: 1
      good: 2
      excellent: 3

complexity:
  thresholds:
    S: 8000
    M: 40000
    L: 120000
```

### Cost Configuration

```yaml
# cost_profile.yaml
productivity:
  python: 25    # LOC per hour
  javascript: 20
  typescript: 18

multipliers:
  tech_debt_0_3: 2.5
  tech_debt_4_6: 2.0
  tech_debt_7_9: 1.5
  tech_debt_10_12: 1.2
  tech_debt_13_15: 1.0
```

---

## 10. Troubleshooting

### Common Issues

#### "No git repository found"

The repository must have a `.git` directory for history analysis. Initialize with:
```bash
git init
git add .
git commit -m "Initial commit"
```

#### "Module not found" errors

Ensure all dependencies are installed:
```bash
pip install -r requirements.txt
```

#### Report files not generated

Check write permissions for the `.audit/` directory:
```bash
mkdir -p .audit
chmod 755 .audit
```

#### Low confidence classification

Low confidence (< 60%) indicates ambiguous signals. Consider:
- Adding more documentation
- Improving test coverage
- Setting up CI/CD

### Getting Help

- Documentation: See `docs/METHODOLOGY.md` for scoring details
- Issues: Report bugs via the project repository
- API Errors: Check server logs in `backend/logs/`

---

## Appendix A: Mac Quick Action Setup

1. Open **Automator**
2. Create **Quick Action**
3. Set "Workflow receives" to **folders** in **Finder**
4. Add **Run Shell Script** action
5. Paste the contents of `mac-app/scan-repo.sh`
6. Save as "Scan Repository"

Usage: Right-click any folder, select Quick Actions, then Scan Repository.

---

## Appendix B: Glossary

| Term | Definition |
|------|------------|
| LOC | Lines of Code |
| Tech Debt | Accumulated cost of shortcuts and poor practices |
| CI/CD | Continuous Integration / Continuous Deployment |
| MCP | Model Context Protocol (for AI integration) |
| Overhead | Additional costs beyond direct labor |

---

*Repo Auditor User Manual v1.0*
