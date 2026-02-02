#!/bin/bash
# Hook: Verify date/calendar claims before publishing
# Triggered by: UserPromptSubmit (when writing content with dates)
# Purpose: Prevent hallucinations like "Super Bowl weekend" on wrong date (LL-324)

# February 2026 Calendar Reference (verified via web search)
# - Super Bowl LX: February 8, 2026 (Sunday) at Levi's Stadium
# - Presidents Day: February 16, 2026 (Monday)
# - Valentine's Day: February 14, 2026 (Saturday)
# - Groundhog Day: February 2, 2026 (Monday)
# - Ash Wednesday: February 18, 2026

cat << 'EOF'
═══════════════════════════════════════════════════════════
📅 DATE VERIFICATION REMINDER (LL-324 Prevention)
═══════════════════════════════════════════════════════════

Before writing ANY date-specific content:

FEBRUARY 2026 KEY DATES:
• Super Bowl LX: Feb 8 (NOT Feb 1!)
• Presidents Day: Feb 16
• Valentine's Day: Feb 14
• Ash Wednesday: Feb 18

⚠️  VERIFICATION PROTOCOL:
1. Run `date` to confirm current date
2. Use WebSearch to verify event dates
3. Prefer generic phrasing over specific claims
4. When uncertain, say "I need to verify this date"

🚫 NEVER assume calendar knowledge is correct!
═══════════════════════════════════════════════════════════
EOF
