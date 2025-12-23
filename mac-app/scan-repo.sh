#!/bin/bash
# Repo Auditor — Mac Quick Action Script
#
# Installation:
# 1. Open Automator
# 2. Create new "Quick Action"
# 3. Workflow receives "folders" in "Finder"
# 4. Add "Run Shell Script" action
# 5. Pass input "as arguments"
# 6. Paste this script content
# 7. Save as "Scan Repository"
#
# Usage: Right-click folder → Quick Actions → Scan Repository

REPO_PATH="$1"
AUDITOR_PATH="$HOME/repo-auditor"
SERVER_URL="${REPO_AUDITOR_SERVER:-}"

# Check if path provided
if [ -z "$REPO_PATH" ]; then
    osascript -e 'display notification "No folder selected" with title "Repo Auditor"'
    exit 1
fi

# Show starting notification
osascript -e "display notification \"Scanning: $(basename "$REPO_PATH")\" with title \"Repo Auditor\" subtitle \"Analysis started...\""

# Run audit
cd "$REPO_PATH"

# Check for local audit.py first
if [ -f "audit.py" ]; then
    python3 audit.py --profile eu
elif [ -f "$AUDITOR_PATH/portable/audit.py" ]; then
    python3 "$AUDITOR_PATH/portable/audit.py" "$REPO_PATH" --profile eu
else
    osascript -e 'display notification "audit.py not found" with title "Repo Auditor" subtitle "Error"'
    exit 1
fi

# Check result
if [ -f ".audit/report.md" ]; then
    # Extract summary from report
    PRODUCT_LEVEL=$(grep "Product Level" .audit/report.json 2>/dev/null | head -1 | cut -d'"' -f4)
    HEALTH=$(grep -A1 '"repo_health"' .audit/report.json 2>/dev/null | grep "total" | head -1 | grep -o '[0-9]*')

    # Show completion notification
    osascript -e "display notification \"$PRODUCT_LEVEL | Health: $HEALTH/12\" with title \"Repo Auditor\" subtitle \"Analysis complete!\""

    # Open report in default markdown viewer
    open ".audit/report.md"

    # Send to server if configured
    if [ -n "$SERVER_URL" ]; then
        curl -s -X POST "$SERVER_URL/api/audit/submit" \
            -H "Content-Type: application/json" \
            -d @.audit/report.json > /dev/null 2>&1
    fi
else
    osascript -e 'display notification "Report generation failed" with title "Repo Auditor" subtitle "Error"'
    exit 1
fi
