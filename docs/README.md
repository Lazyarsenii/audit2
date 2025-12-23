# Repo Auditor Documentation

Automated repository analysis and evaluation platform for grant contract management.

## Table of Contents

1. [Overview](#overview)
2. [Methodology](./methodology.md)
3. [Contract Comparison](./contract-comparison.md)
4. [API Reference](./api-reference.md)
5. [User Guide](./user-guide.md)
6. [Analysis Pipeline](./ANALYSIS_PIPELINE.md)
7. [User Instructions](./USER_INSTRUCTIONS.md)

## Overview

Repo Auditor is a comprehensive platform for:

- **Repository Analysis**: Automated code quality assessment
- **Cost Estimation**: Development effort and cost calculation
- **Contract Comparison**: Compare contract requirements with actual progress
- **Document Generation**: Acts, invoices, and reports
- **Project Management**: Track projects and activities

## Quick Start

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 7777
```

### Frontend

```bash
cd ui
npm install
npm run dev -- -p 3333
```

## Architecture

```
repo-auditor/
├── backend/           # FastAPI backend
│   ├── app/
│   │   ├── api/       # API routes
│   │   ├── services/  # Business logic
│   │   ├── scoring/   # Scoring algorithms
│   │   └── core/      # Core utilities
│   └── tests/         # Test suite
├── ui/                # Next.js frontend
│   └── src/
│       ├── app/       # Pages
│       └── components/ # UI components
└── docs/              # Documentation
```

## Key Features

### 1. Repository Health Scoring

Evaluates repositories across dimensions:
- Documentation quality
- Code structure
- Runability
- History/maintenance

### 2. Technical Debt Assessment

Measures technical debt:
- Architecture
- Code quality
- Testing coverage
- Infrastructure
- Security

### 3. Product Level Classification

Classifies repositories:
- Level 1: Prototype/PoC
- Level 2: Alpha
- Level 3: Beta
- Level 4: Production
- Level 5: Enterprise

### 4. Contract Comparison

Compares contract requirements with actual progress:
- Work plan vs completion
- Budget vs cost estimates
- Indicators vs metrics

### 5. Document Generation

Generates financial documents:
- Acts of acceptance
- Invoices
- Progress reports
