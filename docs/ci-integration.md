# CI/CD Integration Guide

This guide explains how to integrate Repo Auditor with your CI/CD pipeline.

## GitHub Actions

### Quick Setup (Copy-Paste)

Create `.github/workflows/audit.yml` in your repository:

```yaml
name: Repo Audit

on:
  pull_request:
    types: [opened, synchronize]

jobs:
  audit:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: write
      contents: read

    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install tools
        run: pip install safety bandit

      - name: Security Scan
        id: security
        run: |
          # Check dependencies
          if [ -f requirements.txt ]; then
            VULN=$(safety check -r requirements.txt --json 2>/dev/null | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo 0)
          else
            VULN=0
          fi
          echo "vulnerabilities=$VULN" >> $GITHUB_OUTPUT

          # Check code
          HIGH=$(bandit -r . -f json 2>/dev/null | python3 -c "import sys,json; print(sum(1 for r in json.load(sys.stdin).get('results',[]) if r.get('issue_severity')=='HIGH'))" 2>/dev/null || echo 0)
          echo "high_issues=$HIGH" >> $GITHUB_OUTPUT

      - name: Post Results
        uses: actions/github-script@v7
        with:
          script: |
            const vuln = '${{ steps.security.outputs.vulnerabilities }}';
            const high = '${{ steps.security.outputs.high_issues }}';

            const status = high > 0 ? '🔴 Critical' : vuln > 0 ? '🟡 Warning' : '✅ Clean';

            await github.rest.issues.createComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: context.issue.number,
              body: `## Security Scan ${status}\n\n- Vulnerabilities: ${vuln}\n- High Issues: ${high}`
            });

      - name: Fail on Critical
        if: steps.security.outputs.high_issues > 0
        run: exit 1
```

### Full Integration (with Repo Auditor API)

For complete analysis including cost estimation and detailed metrics:

```yaml
name: Full Repo Audit

on:
  pull_request:
    types: [opened, synchronize]

env:
  AUDITOR_API: https://auditor-production-f8be.up.railway.app
  AUDITOR_KEY: ${{ secrets.REPO_AUDITOR_KEY }}

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Create ZIP
        run: |
          zip -r repo.zip . -x "*.git*" -x "*node_modules*" -x "*venv*"

      - name: Upload & Analyze
        id: analyze
        run: |
          # Upload repository
          UPLOAD=$(curl -s -X POST "$AUDITOR_API/api/upload/zip" \
            -H "X-API-Key: $AUDITOR_KEY" \
            -F "file=@repo.zip")

          PATH=$(echo $UPLOAD | jq -r '.path')

          # Start analysis
          RESULT=$(curl -s -X POST "$AUDITOR_API/api/analyze" \
            -H "X-API-Key: $AUDITOR_KEY" \
            -H "Content-Type: application/json" \
            -d "{\"repo_url\": \"$PATH\", \"source_type\": \"local\"}")

          ANALYSIS_ID=$(echo $RESULT | jq -r '.analysis_id')
          echo "analysis_id=$ANALYSIS_ID" >> $GITHUB_OUTPUT

      - name: Wait for Results
        run: |
          for i in {1..30}; do
            STATUS=$(curl -s "$AUDITOR_API/api/analysis/${{ steps.analyze.outputs.analysis_id }}" \
              -H "X-API-Key: $AUDITOR_KEY" | jq -r '.status')

            if [ "$STATUS" = "completed" ]; then
              echo "Analysis complete!"
              break
            fi
            echo "Waiting... ($i/30)"
            sleep 10
          done

      - name: Get Results
        id: results
        run: |
          RESULT=$(curl -s "$AUDITOR_API/api/analysis/${{ steps.analyze.outputs.analysis_id }}" \
            -H "X-API-Key: $AUDITOR_KEY")

          echo "product_level=$(echo $RESULT | jq -r '.product_level')" >> $GITHUB_OUTPUT
          echo "complexity=$(echo $RESULT | jq -r '.complexity')" >> $GITHUB_OUTPUT
          echo "repo_health=$(echo $RESULT | jq -r '.repo_health.total')" >> $GITHUB_OUTPUT
          echo "tech_debt=$(echo $RESULT | jq -r '.tech_debt.total')" >> $GITHUB_OUTPUT
```

## GitLab CI

Create `.gitlab-ci.yml`:

```yaml
repo-audit:
  stage: test
  image: python:3.11
  script:
    - pip install safety bandit
    - safety check -r requirements.txt || true
    - bandit -r . -f json -o bandit-report.json || true
  artifacts:
    reports:
      sast: bandit-report.json
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `REPO_AUDITOR_KEY` | API key for Repo Auditor | For full analysis |
| `REPO_AUDITOR_API` | API URL (default: production) | No |

## Getting API Key

1. Go to https://ui-three-rho.vercel.app/settings
2. Generate or copy your API key
3. Add it as a GitHub Secret: `REPO_AUDITOR_KEY`

## What Gets Analyzed

- **Security**: Dependency vulnerabilities (Safety), code issues (Bandit)
- **Quality**: Lines of code, test coverage, documentation
- **Structure**: Project organization, CI/CD presence
- **Cost**: Development effort estimation (COCOMO II)

## PR Comments

The action automatically posts a summary comment on PRs with:
- Security score (0-3)
- Vulnerability count
- Code metrics
- Recommendations
