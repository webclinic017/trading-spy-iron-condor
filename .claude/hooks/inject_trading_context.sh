#!/bin/bash
# Trading context injection hook
# Provides market hours, dates, and trading context to Claude sessions

set -euo pipefail

# All date/time operations use Eastern Time (trading timezone)
TODAY=$(TZ=America/New_York date +%Y-%m-%d)
FULL_DATE=$(TZ=America/New_York date "+%A, %B %d, %Y")
DAY_OF_WEEK=$(TZ=America/New_York date +%A)
DAY_NUM=$(TZ=America/New_York date +%u)
CURRENT_HOUR=$(TZ=America/New_York date +%H)
CURRENT_MIN=$(TZ=America/New_York date +%M)

# Weekend detection
IS_WEEKEND="false"
if [[ ${DAY_NUM} -ge 6 ]]; then
	IS_WEEKEND="true"
fi

# Market hours: 9:30 AM - 4:00 PM ET
MARKET_OPEN="false"
if [[ ${IS_WEEKEND} == "false" ]]; then
	if [[ ${CURRENT_HOUR} -ge 9 ]] && [[ ${CURRENT_HOUR} -lt 16 ]]; then
		if [[ ${CURRENT_HOUR} -eq 9 ]] && [[ ${CURRENT_MIN} -lt 30 ]]; then
			MARKET_OPEN="false"
		else
			MARKET_OPEN="true"
		fi
	fi
fi

# Calculate days since last system_state update
SYSTEM_STATE="${CLAUDE_PROJECT_DIR}/data/system_state.json"
DAYS_OLD=0
if [[ -f ${SYSTEM_STATE} ]]; then
	LAST_UPDATE=$(grep -o '"last_updated": "[^"]*"' "${SYSTEM_STATE}" | head -1 | cut -d'"' -f4 | cut -d'T' -f1 2>/dev/null || echo "")
	if [[ -n ${LAST_UPDATE} ]]; then
		CURRENT_TS=$(TZ=America/New_York date +%s)
		LAST_TS=$(TZ=America/New_York date -j -f "%Y-%m-%d" "${LAST_UPDATE}" +%s 2>/dev/null || printf '%s' "${CURRENT_TS}")
		DAYS_OLD=$(((CURRENT_TS - LAST_TS) / 86400))
	fi
fi

# Output trading context
echo "<trading-context>"
echo "Date: ${FULL_DATE}"
echo "Market Open: ${MARKET_OPEN}"
echo "Weekend: ${IS_WEEKEND}"
if [[ ${DAYS_OLD} -gt 1 ]]; then
	echo "WARNING: System state is ${DAYS_OLD} days old"
fi
echo "</trading-context>"

# Export variables for potential downstream use
export TODAY FULL_DATE DAY_OF_WEEK MARKET_OPEN IS_WEEKEND

exit 0
