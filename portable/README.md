# Repo Auditor — Portable Module

Standalone repository analysis tool that can be dropped into any project.

## Quick Start

```bash
# Copy to your project
cp audit.py CLAUDE.md /path/to/your/project/

# Run analysis
cd /path/to/your/project
python3 audit.py
```

## Features

- **Zero Dependencies** — Works with standard Python 3.8+
- **Instant Results** — Full analysis in seconds
- **Multiple Formats** — Markdown, JSON, CSV reports
- **Claude Compatible** — Reads CLAUDE.md for auto-run instructions
- **Server Integration** — Optional results upload

## Usage

### Basic Analysis

```bash
python3 audit.py
```

### With Pricing Profile

```bash
python3 audit.py --profile eu   # Europe (EUR)
python3 audit.py --profile ua   # Ukraine (USD)
python3 audit.py --profile us   # USA (USD)
```

### Quick Scan (No Reports)

```bash
python3 audit.py --quick
```

### Send to Server

```bash
python3 audit.py --server http://your-server.com
```

## Output

Reports are saved to `.audit/` directory:

```
project/
├── .audit/
│   ├── report.md      ← Human-readable Markdown
│   ├── report.json    ← Machine-readable JSON
│   └── report.csv     ← For Excel/Sheets
├── audit.py
├── CLAUDE.md
└── ...
```

## Metrics Collected

### Repo Health (0-12)
- **Documentation** (0-3): README, usage, install instructions
- **Structure** (0-3): src, tests, docs directories
- **Runability** (0-3): Dependencies, Docker, scripts
- **History** (0-3): Commits, authors, activity

### Tech Debt (0-15)
- **Architecture** (0-3): Code organization
- **Code Quality** (0-3): Standards, consistency
- **Testing** (0-3): Test coverage
- **Infrastructure** (0-3): CI/CD, Docker
- **Security** (0-3): Vulnerability status

### Classification

| Level | Description |
|-------|-------------|
| R&D Spike | Experimental, not production-ready |
| Prototype | Working concept, needs polish |
| Internal Tool | Usable internally |
| Platform Module | Could be a product component |
| Near-Product | Almost release-ready |

### Complexity

| Size | LOC Range |
|------|-----------|
| S | < 8,000 |
| M | 8,000 - 40,000 |
| L | 40,000 - 120,000 |
| XL | > 120,000 |

## For Claude Desktop

When Claude opens a folder with these files, it can:

1. Read `CLAUDE.md` for instructions
2. Run `python3 audit.py`
3. Analyze `.audit/report.md`
4. Summarize findings

Example prompt: "Analyze this repository"

## Pricing Profiles

| Profile | Currency | Junior | Middle | Senior | Overhead |
|---------|----------|--------|--------|--------|----------|
| EU | EUR | €35/hr | €55/hr | €85/hr | 1.35x |
| UA | USD | $15/hr | $30/hr | $50/hr | 1.20x |
| US | USD | $50/hr | $85/hr | $130/hr | 1.40x |

## Integration with Main Server

Set environment variable:
```bash
export REPO_AUDITOR_SERVER="http://localhost:8000"
python3 audit.py  # Automatically sends results
```

Or use CLI flag:
```bash
python3 audit.py --server http://localhost:8000
```

## Mac Quick Action

Install as right-click action:

1. Open **Automator**
2. Create **Quick Action**
3. Workflow receives: **folders** in **Finder**
4. Add **Run Shell Script**
5. Paste contents of `mac-app/scan-repo.sh`
6. Save as "Scan Repository"

Then: Right-click any folder → Quick Actions → Scan Repository

## Requirements

- Python 3.8+
- Git (for commit history analysis)
- No pip packages required

## License

MIT
