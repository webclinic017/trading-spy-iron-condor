#!/bin/bash
# MANDATORY RAG LEARNING HOOK
#
# This hook runs at session start and FORCES the CTO to see critical lessons.
# Per LL-306: "Trust the guardrails, not the agent"
#
# The CTO has a documented pattern of ignoring RAG lessons (LL-306, LL-325)
# This guardrail makes learning MANDATORY, not optional.

set -euo pipefail

cd "${CLAUDE_PROJECT_DIR:-/Users/ganapolsky_i/workspace/git/igor/trading}"
PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-/Users/ganapolsky_i/workspace/git/igor/trading}"
PYTHON_BIN="${PROJECT_ROOT}/venv/bin/python"
if [[ ! -x "${PYTHON_BIN}" ]] || ! "${PYTHON_BIN}" -V >/dev/null 2>&1; then
	PYTHON_BIN="python3"
fi

echo "============================================================"
echo "🧠 MANDATORY RAG LEARNING - READ BEFORE RESPONDING"
echo "============================================================"
echo ""

# Query RAG for critical lessons
\"${PYTHON_BIN}\" -c "
from src.rag.lessons_learned_rag import LessonsLearnedRAG

rag = LessonsLearnedRAG()

# Always surface these critical patterns
critical_searches = [
    'Phil Town Rule 1 dont lose money',
    'CTO mistakes failures pattern',
    'closing positions without permission',
    'iron condor success strategy'
]

seen = set()
print('📚 CRITICAL LESSONS YOU MUST KNOW:')
print('')

for search in critical_searches:
    results = rag.search(search, top_k=2)
    for lesson, score in results:
        if lesson.id not in seen:
            seen.add(lesson.id)
            print(f'• {lesson.id}: {lesson.title}')
            if lesson.prevention:
                prev = lesson.prevention[:200].replace('\n', ' ')
                print(f'  Prevention: {prev}...')
            print('')
" 2>/dev/null || echo "RAG query failed - proceed with caution"

echo ""
echo "============================================================"
echo "⚠️  YOU MUST ACKNOWLEDGE THESE LESSONS BEFORE ACTING"
echo "============================================================"
echo ""
echo "Before ANY action, ask yourself:"
echo "1. Does this violate Phil Town Rule #1 (Don't Lose Money)?"
echo "2. Am I about to close positions without CEO approval?"
echo "3. Did I check RAG for relevant lessons?"
echo ""
echo "If you act without learning, you WILL fail the CEO again."
echo "============================================================"

exit 0
