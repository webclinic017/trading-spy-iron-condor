#!/bin/bash
# HARD BLOCK: CTO cannot close positions
# Only iron-condor-guardian.yml workflow can close positions
# Per LL-306, LL-325: "Trust the guardrails, not the agent"

INPUT="$1"

# Block ANY position closing attempt
if echo "$INPUT" | grep -qiE "(close_position|close.*position|submit_order.*SELL|submit_order.*BUY.*close|liquidat)"; then
	echo "🚫 HARD BLOCK: Position closing disabled for CTO"
	echo ""
	echo "Only the iron-condor-guardian workflow can close positions."
	echo "This is enforced by LL-306 and LL-325."
	echo ""
	echo "Guardian closes automatically when:"
	echo "  - 50% profit reached"
	echo "  - 200% stop loss hit"
	echo "  - 7 DTE reached"
	echo ""
	echo "You cannot override this. Phil Town Rule #1."
	exit 1
fi
exit 0
