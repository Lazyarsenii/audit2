# Contract Comparison System

## Overview

The Contract Comparison system allows comparing parsed contract requirements with actual repository analysis results and project progress.

## Contract Parsing

### Supported Formats

- PDF (`.pdf`)
- Microsoft Word (`.docx`, `.doc`)
- Plain Text (`.txt`)

### Extracted Data

#### 1. Work Plan
- Activity ID
- Activity name
- Description
- Start/End dates
- Deliverables
- Status

#### 2. Milestones
- Milestone ID
- Name
- Due date
- Deliverables
- Payment linked
- Payment amount

#### 3. Budget
- Budget line ID
- Category (personnel, equipment, travel, etc.)
- Description
- Unit/Quantity/Unit cost
- Total amount
- Currency

#### 4. Indicators (KPIs)
- Indicator ID
- Name
- Description
- Baseline value
- Target value
- Unit of measurement
- Measurement frequency

#### 5. Policy Requirements
- Policy ID
- Title
- Description
- Category (reporting, financial, compliance, technical)
- Priority (low, medium, high, critical)

#### 6. Document Templates
- Template ID
- Name
- Description
- Frequency (monthly, quarterly, annually, once)
- Format (pdf, docx, xlsx)
- Required flag

---

## Comparison Logic

### Work Plan Comparison

Compares planned activities with actual progress:

| Status | Criteria |
|--------|----------|
| On Track | Completion >= 80% of expected |
| At Risk | Completion 30-80% of expected |
| Behind | Completion < 30% of expected |

### Budget Comparison

Compares planned budget with cost estimates:

| Status | Variance |
|--------|----------|
| On Track | Within +/- 10% |
| At Risk | +/- 10-20% |
| Over Budget | > 20% over |
| Under Budget | > 20% under |

### Indicator Comparison

Maps analysis metrics to contract indicators:

| Analysis Metric | Contract Indicator |
|-----------------|-------------------|
| Documentation score | Documentation quality |
| Testing score | Test coverage |
| Security score | Security assessment |
| Code quality | Code quality metrics |

Achievement calculation:
```
Achievement % = (Actual Value / Target Value) × 100
```

---

## API Endpoints

### Upload Contract
```
POST /api/contract-parser/upload
Content-Type: multipart/form-data

file: <contract file>
contract_name: "Optional custom name"
```

### Create Demo Contract
```
POST /api/contract-parser/demo
Content-Type: application/json

{
  "contract_name": "Demo Contract",
  "total_budget": 150000,
  "currency": "USD"
}
```

### List Parsed Contracts
```
GET /api/contract-parser/parsed
```

### Get Parsed Contract
```
GET /api/contract-parser/parsed/{contract_id}
```

### Compare Contract
```
POST /api/contract-parser/compare
Content-Type: application/json

{
  "contract_id": "contract_001",
  "analysis_data": {
    "repo_health": {...},
    "tech_debt": {...},
    "cost": {...}
  },
  "project_progress": {
    "ACT_1": {"status": "completed", "completion": 100},
    "ACT_2": {"status": "in_progress", "completion": 60}
  }
}
```

### Run Demo Comparison
```
POST /api/contract-parser/compare-demo
```

### Get Parser Capabilities
```
GET /api/contract-parser/capabilities
```

---

## Comparison Report

### Structure

```json
{
  "contract_id": "contract_001",
  "analysis_id": "analysis_001",
  "compared_at": "2024-01-01T00:00:00",
  "overall_status": "on_track",
  "overall_score": 85.0,
  "work_plan": {
    "status": "on_track",
    "total": 5,
    "on_track": 4,
    "at_risk": 1,
    "behind": 0,
    "details": [...]
  },
  "budget": {
    "status": "on_track",
    "planned": 150000,
    "estimated": 145000,
    "variance": -5000,
    "variance_percent": -3.33,
    "details": [...]
  },
  "indicators": {
    "status": "on_track",
    "total": 4,
    "met": 3,
    "at_risk": 1,
    "not_met": 0,
    "details": [...]
  },
  "recommendations": [...],
  "risks": [...]
}
```

### Overall Score Calculation

```
Score = (Work Plan Score × 35%) + (Budget Score × 40%) + (Indicator Score × 25%)
```

| Score Range | Status |
|-------------|--------|
| 80-100 | On Track |
| 60-79 | At Risk |
| 0-59 | Behind |

---

## User Interface

### Tabs

1. **Upload Contract** - Upload and parse contract documents
2. **Parsed Data** - View extracted contract data
3. **Comparison** - Run and view comparison results

### Features

- File upload with drag-and-drop
- Demo contract for testing
- Visual progress indicators
- Risk highlighting
- Recommendation display
