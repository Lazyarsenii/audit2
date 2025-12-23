# API Reference

Base URL: `http://localhost:7777`

## Health

### GET /health
Check service health.

**Response:**
```json
{
  "status": "ok",
  "service": "repo-auditor"
}
```

---

## Analysis

### POST /api/analyze
Start repository analysis.

**Request:**
```json
{
  "repo_url": "https://github.com/user/repo",
  "branch": "main",
  "profile": "default"
}
```

**Response:**
```json
{
  "analysis_id": "uuid",
  "status": "pending"
}
```

### GET /api/analyze/{analysis_id}
Get analysis status and results.

### GET /api/analyze/{analysis_id}/report
Get full analysis report.

### GET /api/analysis/{analysis_id}/progress
Get current analysis progress (REST fallback).

**Response:**
```json
{
  "analysis_id": "uuid",
  "stage": "collecting",
  "stage_progress": 45.5,
  "overall_progress": 32.7,
  "current_step": "Running security scan...",
  "collectors_completed": 5,
  "collectors_total": 13,
  "estimated_remaining_seconds": 120,
  "collectors": {
    "structure": {"name": "structure", "status": "completed", "metrics_collected": 12},
    "security": {"name": "security", "status": "running", "metrics_collected": 0}
  }
}
```

**Stages:** `queued` → `fetching` → `collecting` → `scoring` → `storing` → `reporting` → `completed` | `failed`

### WebSocket /api/ws/analysis/{analysis_id}/progress
Real-time progress updates via WebSocket.

**Connection:**
```javascript
const ws = new WebSocket('ws://localhost:8000/api/ws/analysis/{id}/progress');
ws.onmessage = (event) => {
  const progress = JSON.parse(event.data);
  console.log(`Progress: ${progress.overall_progress}%`);
};
```

**Messages received:**
- Progress updates (same format as REST endpoint)
- Heartbeat: `{"type": "heartbeat"}`

**Keep-alive:** Send `ping` to receive `pong` response.

---

## GitHub Integration

### GET /api/github/status
Check if GitHub PAT is configured.

**Response:**
```json
{
  "configured": true,
  "username": "user",
  "name": "Full Name",
  "avatar_url": "https://..."
}
```

### GET /api/github/orgs
List organizations the user has access to.

**Response:**
```json
{
  "orgs": [
    {"login": "org-name", "id": 123, "description": "..."}
  ]
}
```

### GET /api/github/repos
List repositories accessible via GitHub PAT.

**Query params:**
- `org` (optional): Organization name
- `type`: all, owner, public, private, member (default: all)
- `sort`: created, updated, pushed, full_name (default: updated)
- `per_page`: 1-100 (default: 100)

**Response:**
```json
{
  "repos": [
    {
      "id": 123,
      "name": "repo-name",
      "full_name": "owner/repo-name",
      "url": "https://github.com/owner/repo-name",
      "clone_url": "https://github.com/owner/repo-name.git",
      "private": false,
      "description": "...",
      "language": "TypeScript",
      "default_branch": "main",
      "updated_at": "2024-01-01T00:00:00Z"
    }
  ],
  "total": 25,
  "configured": true
}
```

### GET /api/github/repos/search
Search repositories.

**Query params:**
- `q` (required): Search query
- `org` (optional): Limit to organization
- `per_page`: 1-100 (default: 30)

---

## Contract Parser

### POST /api/contract-parser/upload
Upload and parse contract document.

**Request:** `multipart/form-data`
- `file`: Contract file (PDF, DOCX, TXT)
- `contract_name`: Optional custom name

**Response:**
```json
{
  "status": "success",
  "contract_id": "uuid",
  "filename": "contract.pdf",
  "parsed_at": "2024-01-01T00:00:00",
  "summary": {
    "activities_count": 5,
    "milestones_count": 4,
    "budget_lines_count": 6
  }
}
```

### GET /api/contract-parser/parsed
List all parsed contracts.

### GET /api/contract-parser/parsed/{contract_id}
Get parsed contract details.

### POST /api/contract-parser/compare
Compare contract with analysis.

**Request:**
```json
{
  "contract_id": "uuid",
  "analysis_data": {
    "repo_health": {},
    "tech_debt": {},
    "cost": {}
  },
  "project_progress": {}
}
```

### POST /api/contract-parser/demo
Create demo contract.

### POST /api/contract-parser/compare-demo
Run demo comparison.

### GET /api/contract-parser/capabilities
Get parser capabilities.

---

## Documents

### GET /api/documents/matrix/summary
Get document matrix summary.

### GET /api/documents/matrix/product-levels
Get product level definitions.

### GET /api/documents/matrix/{level}
Get documents for specific product level.

---

## Financial Documents

### POST /api/financial/generate/act
Generate act of acceptance.

**Request:**
```json
{
  "analysis_id": "uuid",
  "project_id": "uuid",
  "period_start": "2024-01-01",
  "period_end": "2024-01-31"
}
```

### POST /api/financial/generate/invoice
Generate invoice.

---

## Projects

### GET /api/projects
List all projects.

### POST /api/projects
Create new project.

### GET /api/projects/{project_id}
Get project details.

### PUT /api/projects/{project_id}
Update project.

### DELETE /api/projects/{project_id}
Delete project.

### GET /api/projects/{project_id}/activities
Get project activities.

### POST /api/projects/{project_id}/activities
Add activity to project.

---

## Settings

### GET /api/settings
Get current settings.

### PUT /api/settings
Update settings.

### GET /api/settings/profiles
List evaluation profiles.

### GET /api/settings/profiles/{profile_name}
Get profile details.

---

## Contracts (Compliance)

### GET /api/contracts/profiles
List compliance profiles.

### POST /api/contracts/check
Check contract compliance.

**Request:**
```json
{
  "analysis_id": "uuid",
  "profile": "global_fund_r13"
}
```

---

## LLM

### POST /api/llm/analyze
Analyze with LLM assistance.

### POST /api/llm/generate-summary
Generate analysis summary using LLM.

---

## Metrics

### GET /api/metrics
Get system metrics.

### GET /api/metrics/analysis/{analysis_id}
Get analysis metrics.
