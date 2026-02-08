#!/usr/bin/env python3
"""
Cortex RLHF Sync - Bridge between local feedback and ShieldCortex memory

This module manages the pending queue for feedback that needs to be synced
to the persistent memory system (ShieldCortex via MCP tools).

Architecture:
┌─────────────────────┐    ┌──────────────────────┐    ┌─────────────────┐
│  User Feedback      │    │  pending_cortex_     │    │  ShieldCortex   │
│  (thumbs up/down)   │───►│  sync.jsonl          │───►│  (MCP memory)   │
└─────────────────────┘    └──────────────────────┘    └─────────────────┘
        │                           │                          │
        ▼                           ▼                          ▼
  post-tool-use.sh           session-start.sh           Claude recalls
  captures signal             syncs pending              past mistakes

Usage:
    # Queue feedback for Cortex sync
    python cortex_sync.py --queue --signal positive --intensity 3 --context "Fixed bug"

    # List pending entries
    python cortex_sync.py --list

    # Generate MCP calls for Claude
    python cortex_sync.py --generate-mcp-calls

    # Clear pending after sync
    python cortex_sync.py --clear

LOCAL ONLY - Do not commit to repository
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent
PENDING_FILE = PROJECT_ROOT / ".claude" / "memory" / "feedback" / "pending_cortex_sync.jsonl"
FEEDBACK_LOG = PROJECT_ROOT / ".claude" / "memory" / "feedback" / "feedback-log.jsonl"
SESSION_STATE = PROJECT_ROOT / ".claude" / "memory" / "session" / "state.json"


def ensure_dirs():
    """Ensure required directories exist."""
    PENDING_FILE.parent.mkdir(parents=True, exist_ok=True)


def queue_feedback(
    signal: str,
    intensity: int = 2,
    context: Optional[str] = None,
    tool_name: Optional[str] = None,
    source: str = "user"
) -> dict:
    """Queue a feedback entry for Cortex sync.

    Args:
        signal: "positive" or "negative"
        intensity: 1-5 scale (1=minor, 5=critical)
        context: What triggered the feedback
        tool_name: Last tool used (for attribution)
        source: "user" (manual), "auto" (detected), "hook" (from hooks)

    Returns:
        The queued entry
    """
    ensure_dirs()

    # Get session state for additional context
    last_action = ""
    last_files = []
    if SESSION_STATE.exists():
        try:
            state = json.loads(SESSION_STATE.read_text())
            last_action = state.get("last_action", "")
            last_files = state.get("files_touched", [])[-3:]  # Last 3 files
        except (json.JSONDecodeError, OSError):
            pass

    entry = {
        "id": f"fb_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{signal[:3]}",
        "timestamp": datetime.now().isoformat(),
        "signal": signal,
        "intensity": intensity,
        "context": context or last_action,
        "tool_name": tool_name or "unknown",
        "files": last_files,
        "source": source,
        "synced": False,
    }

    # Append to pending file
    with open(PENDING_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")

    # Also log to main feedback log for Thompson Sampling
    feedback_entry = {
        "timestamp": entry["timestamp"],
        "feedback": signal,
        "reward": intensity if signal == "positive" else -intensity,
        "source": source,
        "tool_name": tool_name or "unknown",
        "context": context or last_action,
        "tags": [source, signal, tool_name or "unknown"],
    }
    with open(FEEDBACK_LOG, "a") as f:
        f.write(json.dumps(feedback_entry) + "\n")

    return entry


def list_pending() -> list:
    """List all pending entries that need Cortex sync."""
    if not PENDING_FILE.exists():
        return []

    entries = []
    with open(PENDING_FILE) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entry = json.loads(line)
                    if not entry.get("synced", False):
                        entries.append(entry)
                except json.JSONDecodeError:
                    continue
    return entries


def generate_mcp_calls() -> list:
    """Generate MCP memory calls for Claude to execute.

    Returns a list of dicts with:
    - tool: "mcp__memory__remember"
    - content: What to remember
    - category: RLHF category
    - tags: Relevant tags
    """
    pending = list_pending()
    if not pending:
        return []

    calls = []
    for entry in pending:
        signal = entry.get("signal", "unknown")
        intensity = entry.get("intensity", 2)
        context = entry.get("context", "")
        tool_name = entry.get("tool_name", "unknown")
        files = entry.get("files", [])

        # Build memory content
        if signal == "positive":
            emoji = "✅" if intensity >= 3 else "👍"
            memory_type = "Success" if intensity >= 4 else "Good"
        else:
            emoji = "❌" if intensity >= 3 else "👎"
            memory_type = "Failure" if intensity >= 4 else "Mistake"

        content_parts = [
            f"{emoji} RLHF {memory_type} (intensity {intensity}/5)",
            f"Signal: {signal}",
        ]

        if context:
            content_parts.append(f"Context: {context}")
        if tool_name and tool_name != "unknown":
            content_parts.append(f"Tool: {tool_name}")
        if files:
            content_parts.append(f"Files: {', '.join(files)}")

        # Add actionable lesson for negative feedback
        if signal == "negative":
            content_parts.append("")
            content_parts.append("Lesson: AVOID this pattern in future sessions")

        calls.append({
            "id": entry.get("id"),
            "tool": "mcp__memory__remember",
            "content": "\n".join(content_parts),
            "category": "RLHF",
            "tags": ["rlhf", signal, f"intensity_{intensity}"],
        })

    return calls


def clear_pending():
    """Clear all pending entries (call after successful sync)."""
    if PENDING_FILE.exists():
        # Mark all as synced instead of deleting
        entries = []
        with open(PENDING_FILE) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entry = json.loads(line)
                        entry["synced"] = True
                        entry["synced_at"] = datetime.now().isoformat()
                        entries.append(entry)
                    except json.JSONDecodeError:
                        continue

        # Rewrite with synced status
        with open(PENDING_FILE, "w") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")


def print_session_start_message():
    """Print message for session-start hook about pending entries."""
    pending = list_pending()
    if not pending:
        return

    print()
    print("=" * 60)
    print("🧠 CORTEX SYNC REQUIRED")
    print("=" * 60)
    print()
    print(f"ACTION REQUIRED: Sync {len(pending)} pending feedback entries")
    print()
    print("Pending entries:")
    for entry in pending[:5]:  # Show first 5
        signal = entry.get("signal", "?")
        intensity = entry.get("intensity", 0)
        context = (entry.get("context", "") or "")[:50]
        emoji = "👍" if signal == "positive" else "👎"
        print(f"  {emoji} [{intensity}/5] {context}...")
    if len(pending) > 5:
        print(f"  ... and {len(pending) - 5} more")
    print()
    print(f"Pending file: {PENDING_FILE}")
    print()
    print("Claude MUST call mcp__memory__remember for each entry, then clear.")
    print("=" * 60)
    print()


def main():
    parser = argparse.ArgumentParser(description="Cortex RLHF Sync Manager")
    parser.add_argument("--queue", action="store_true", help="Queue new feedback")
    parser.add_argument("--signal", choices=["positive", "negative"], help="Feedback signal")
    parser.add_argument("--intensity", type=int, default=2, help="1-5 scale")
    parser.add_argument("--context", type=str, help="Feedback context")
    parser.add_argument("--tool", type=str, help="Tool name")
    parser.add_argument("--source", type=str, default="user", help="Source: user/auto/hook")
    parser.add_argument("--list", action="store_true", help="List pending entries")
    parser.add_argument("--generate-mcp-calls", action="store_true", help="Generate MCP calls")
    parser.add_argument("--clear", action="store_true", help="Clear pending (after sync)")
    parser.add_argument("--session-start", action="store_true", help="Print session-start message")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    if args.queue:
        if not args.signal:
            parser.error("--signal required with --queue")
        entry = queue_feedback(
            signal=args.signal,
            intensity=args.intensity,
            context=args.context,
            tool_name=args.tool,
            source=args.source
        )
        if args.json:
            print(json.dumps(entry))
        else:
            print(f"Queued: {entry['id']}")

    elif args.list:
        pending = list_pending()
        if args.json:
            print(json.dumps(pending, indent=2))
        else:
            if not pending:
                print("No pending entries")
            else:
                for entry in pending:
                    print(f"  [{entry.get('signal')}] {entry.get('context', '')[:50]}")

    elif args.generate_mcp_calls:
        calls = generate_mcp_calls()
        if args.json:
            print(json.dumps(calls, indent=2))
        else:
            for call in calls:
                print(f"\n--- {call['id']} ---")
                print(f"Tool: {call['tool']}")
                print(f"Content:\n{call['content']}")

    elif args.clear:
        clear_pending()
        if args.json:
            print(json.dumps({"status": "cleared"}))
        else:
            print("Pending entries cleared")

    elif args.session_start:
        print_session_start_message()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
