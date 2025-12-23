# Repo Auditor — Mandatory Instructions for Claude

## CRITICAL: Always Run the Script

**DO NOT manually analyze this repository.**
**DO NOT count files, read code, or estimate metrics yourself.**
**ALWAYS run `audit.py` first.**

The `audit.py` script provides standardized, reproducible analysis using a validated methodology. Manual analysis will produce inconsistent and unreliable results.

---

## Mandatory Workflow

When a user asks to "analyze", "audit", "evaluate", or "assess" this project:

### Step 1: Run the Audit Script
```bash
python3 audit.py
```

### Step 2: Wait for Completion
The script will output results to the terminal and generate reports.

### Step 3: Read the Report
```bash
cat .audit/report.md
```

### Step 4: Summarize to User
Present the key findings from the report:
- Stage and confidence level
- Repo Health score breakdown
- Tech Debt score breakdown
- Cost estimate
- Recommendations

---

## DO NOT Do These Things

- DO NOT manually count lines of code
- DO NOT manually inspect file structure
- DO NOT estimate scores without running the script
- DO NOT provide analysis based on reading files
- DO NOT skip the script because "it's faster to just look"

**Why?** The script uses a standardized methodology with calibrated weights and thresholds. Manual inspection cannot replicate this consistently.

---

## Available Commands

```bash
# Standard analysis (ALWAYS USE THIS FIRST)
python3 audit.py

# Quick terminal output only (no report files)
python3 audit.py --quick

# Different pricing profile
python3 audit.py --profile ua    # Ukraine rates
python3 audit.py --profile eu    # Europe rates (default)
python3 audit.py --profile us    # US rates

# Send results to server
python3 audit.py --server http://server-url.com
```

---

## Handling User Questions

| User Says | You Do |
|-----------|--------|
| "Analyze this project" | Run `python3 audit.py`, then summarize `.audit/report.md` |
| "What's the project status?" | Run `python3 audit.py --quick`, report the stage |
| "How much would this cost?" | Run `python3 audit.py --profile <region>`, report cost estimate |
| "Is this production-ready?" | Run script, check if Stage is "Beta" or higher |
| "What needs to be fixed?" | Run script, list the Recommendations section |

---

## Report Location

After running the script, reports are in `.audit/`:

```
.audit/
  report.md      <- Read this for summary
  report.json    <- Machine-readable data
  report.csv     <- Spreadsheet format
```

---

## Interpreting Results

### Development Stage
| Stage | Meaning |
|-------|---------|
| R&D Spike | Experimental, not maintained |
| Proof of Concept | Technical demo |
| Prototype | Working but incomplete |
| MVP | Core features work |
| Alpha | Feature-complete, internal testing |
| Beta | External/user testing |
| Release Candidate | Final testing |
| Production | Deployed and maintained |

### Scores
- **Repo Health (X/12)**: Documentation, structure, runability, history
- **Tech Debt (X/15)**: Architecture, code quality, testing, infra, security

### Complexity
- **S**: < 8,000 LOC
- **M**: 8,000 - 40,000 LOC
- **L**: 40,000 - 120,000 LOC
- **XL**: > 120,000 LOC

---

## Example Session

User: "Analyze this repository"

Claude should respond:
```
I'll run the Repo Auditor to analyze this project.

[Runs: python3 audit.py]

[Reads: .audit/report.md]

## Analysis Results

**Stage:** Alpha (75% confidence)
**Repo Health:** 8/12 (67%)
**Tech Debt:** 8/15 (53%)
**Complexity:** M (15,967 LOC)

### Key Findings
- Documentation: Good (3/3)
- Testing: Needs work (2/3)
- No CI/CD configured (0/3)

### Recommendations
1. Add integration tests
2. Set up CI/CD pipeline
3. Add API documentation

### Cost Estimate (EU rates)
EUR 22,553 - 45,106
```

---

## Remember

**The script exists for a reason. Use it.**
