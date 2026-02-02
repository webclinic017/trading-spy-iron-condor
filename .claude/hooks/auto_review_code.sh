#!/bin/bash
# Auto-Review Hook (Stop hook)
# Based on: https://www.oreilly.com/radar/auto-reviewing-claudes-code/
#
# Triggers when Claude finishes work to catch:
# - Verification failures (LL-325)
# - Date hallucinations (LL-324)
# - Phil Town Rule #1 violations
# - Position sizing errors

# Get list of modified files from git
MODIFIED_FILES=$(git diff --name-only HEAD~1 2>/dev/null | grep -E '\.(py|js|ts|sh)$' | head -10)

if [[ -z "$MODIFIED_FILES" ]]; then
    # No code files modified, skip review
    exit 0
fi

cat << 'EOF'
═══════════════════════════════════════════════════════════
🔍 AUTO-REVIEW: Code Quality Gate
═══════════════════════════════════════════════════════════

Reviewing modified files for:
✓ Verification protocol compliance
✓ Phil Town Rule #1 (capital protection)
✓ Position sizing logic
✓ Hardcoded values that should be configurable
✓ Date/calendar claims without verification

CHECKLIST BEFORE CLAIMING DONE:
□ Did I test the endpoint/function?
□ Did I show evidence of success?
□ Are position sizes within 5% limit?
□ Is risk defined for all trades?
□ Did I verify any date claims?

═══════════════════════════════════════════════════════════
EOF

# Check for common issues in modified Python files
for file in $MODIFIED_FILES; do
    if [[ -f "$file" && "$file" == *.py ]]; then
        # Check for hardcoded position sizes
        if grep -q "position_size\s*=\s*[0-9]" "$file" 2>/dev/null; then
            echo "⚠️  WARNING: Hardcoded position_size in $file - should use config"
        fi

        # Check for missing error handling on API calls
        if grep -q "requests\.\(get\|post\)" "$file" 2>/dev/null; then
            if ! grep -q "try:" "$file" 2>/dev/null; then
                echo "⚠️  WARNING: API calls without try/except in $file"
            fi
        fi
    fi
done

# Always succeed (advisory only) - can be made blocking by returning non-zero
exit 0
