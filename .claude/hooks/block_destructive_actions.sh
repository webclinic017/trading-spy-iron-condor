#!/bin/bash
# GUARDRAIL: Block CTO from closing positions without CEO approval
#
# This hook runs on every tool call and BLOCKS:
# - close_position() calls
# - MarketOrderRequest with SELL/BUY to close
# - Any position liquidation
#
# The CTO has a documented pattern of closing positions impulsively (LL-306, LL-325)
# This guardrail enforces Rule #1: Don't lose money

TOOL_INPUT="$1"

# Check if this is a position-closing action
if echo "$TOOL_INPUT" | grep -qiE "(close_position|close.*position|liquidat|SELL.*SPY[0-9]|BUY.*SPY[0-9].*P00)"; then
	echo "🚫 BLOCKED: Position closing requires CEO approval"
	echo ""
	echo "You are attempting to close a position. Per LL-306 and LL-325:"
	echo "- CTO has a pattern of closing positions impulsively"
	echo "- This violates Phil Town Rule #1 (Don't Lose Money)"
	echo ""
	echo "To proceed:"
	echo "1. Explain to CEO why this position should be closed"
	echo "2. Wait for explicit approval"
	echo "3. CEO will run the close command manually"
	echo ""
	echo "GUARDRAIL ACTIVE: Trust the guardrails, not the agent."
	exit 1
fi

exit 0
