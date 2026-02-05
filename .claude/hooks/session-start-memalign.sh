#!/usr/bin/env bash
# MemAlign RLHF Feedback Sync Hook
# Automatically syncs thumbs up/down feedback to dual-memory system

set -e

echo ""
echo "🧠 Hybrid Memory Sync - MemAlign + Cortex"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if pending feedback exists
PENDING_FILE=".claude/memory/pending_cortex_sync.jsonl"

if [ ! -f "$PENDING_FILE" ] || [ ! -s "$PENDING_FILE" ]; then
	echo "✅ No pending feedback - memory is up to date"
	echo ""
	exit 0
fi

# Count entries
ENTRY_COUNT=$(wc -l <"$PENDING_FILE" | tr -d ' ')

echo "📥 Found $ENTRY_COUNT pending feedback entries"
echo "🔄 Syncing to MemAlign dual-memory system..."
echo ""

# Run RLHF integration
if npx ts-node plugins/automation-plugin/skills/dynamic-agent-spawner/scripts/rlhf-integration.ts sync; then
	echo ""
	echo "✅ Hybrid memory sync complete"
	echo "   - MemAlign: Semantic principles + episodic memories updated"
	echo "   - Cortex: Human-readable audit trail appended"
	echo "   - Conflicts auto-resolved"
	echo ""
else
	echo ""
	echo "⚠️  Memory sync failed - will retry next session"
	echo ""
	exit 0 # Don't block session start on sync failure
fi
