#!/bin/bash
#
# Verify RAG/LanceDB data completeness on session start
# Prevents the "5 lessons indexed when 178 exist" failure
#

TRADING_LESSONS_DIR="/Users/ganapolsky_i/workspace/git/igor/trading/rag_knowledge/lessons_learned"
LANCE_SCRIPT="/Users/ganapolsky_i/workspace/git/igor/.claude/scripts/feedback/semantic-memory-v2.py"
VENV_PYTHON="/Users/ganapolsky_i/workspace/git/igor/.claude/scripts/feedback/venv/bin/python3"

# Count markdown files
FILE_COUNT=$(find "$TRADING_LESSONS_DIR" -name "*.md" 2>/dev/null | wc -l | tr -d ' ')

# Get LanceDB count
LANCE_OUTPUT=$("$VENV_PYTHON" "$LANCE_SCRIPT" --status 2>/dev/null)
LANCE_COUNT=$(echo "$LANCE_OUTPUT" | grep "Lessons:" | awk '{print $2}')

# Default to 0 if not found
LANCE_COUNT=${LANCE_COUNT:-0}
FILE_COUNT=${FILE_COUNT:-0}

# Calculate percentage
if [ "$FILE_COUNT" -gt 0 ]; then
    PERCENT=$((LANCE_COUNT * 100 / FILE_COUNT))
else
    PERCENT=0
fi

# Alert if less than 80% indexed
if [ "$PERCENT" -lt 80 ]; then
    cat <<EOF
═══════════════════════════════════════════════════════════
🚨 RAG COMPLETENESS ALERT
═══════════════════════════════════════════════════════════
LanceDB has $LANCE_COUNT lessons indexed
But there are $FILE_COUNT lesson files ($PERCENT% coverage)

⚠️  DATA IS INCOMPLETE - Run reindex:
$VENV_PYTHON $LANCE_SCRIPT --index
═══════════════════════════════════════════════════════════
EOF
else
    echo "✅ RAG: $LANCE_COUNT/$FILE_COUNT lessons indexed ($PERCENT%)"
fi
