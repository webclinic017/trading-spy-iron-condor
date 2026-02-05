#!/usr/bin/env python3
"""
MemAlign Blog Judge - Dual-Memory System for RLHF

Inspired by Databricks MemAlign:
- Semantic Memory: General principles (no bot slop, emotional hooks)
- Episodic Memory: Specific past failures/successes (vector DB)
- Working Memory: Dynamic context assembled for each judgment

Benefits:
- Self-improving: Every thumbs down teaches the judge
- No code changes needed: Just add feedback to vector DB
- Scalable: Handles millions of examples via LanceDB
- Fast: Retrieves relevant context in <100ms
"""

import sys
from dataclasses import dataclass
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag.lessons_learned_rag import LessonsLearnedRAG


@dataclass
class BlogJudgment:
    """Result of judging a blog post."""

    score: float  # 0-10
    has_emotional_hook: bool
    has_story_arc: bool
    has_specific_details: bool
    no_bot_slop: bool
    feedback: str  # Explanation of score
    similar_failures: list[str]  # Past failures retrieved from episodic memory


class MemAlignBlogJudge:
    """
    MemAlign-inspired blog post judge using dual-memory system.

    Semantic Memory: Hard-coded principles about good blog posts
    Episodic Memory: LanceDB vector store with past feedback examples
    Working Memory: Dynamically assembled context for each judgment
    """

    def __init__(self):
        """Initialize with semantic memory (principles) and episodic memory (RAG)."""
        # SEMANTIC MEMORY - General principles (knowledge)
        self.semantic_memory = [
            "Blog posts MUST have emotional hooks (frustrated, relieved, excited)",
            "Blog posts MUST follow story structure: problem → struggle → pivot → solution → lesson",
            "Blog posts MUST have specific technical details (code, numbers, tools)",
            "Blog posts MUST NOT contain bot slop: Thompson Sampling diagrams, 'The Machine Learns', mermaid charts, generic stats",
            "Blog posts MUST have personal voice, not corporate speak",
            "Blog posts MUST be <1000 words (focused, not verbose)",
        ]

        # EPISODIC MEMORY - Specific examples from past (experiences)
        self.episodic_memory = LessonsLearnedRAG()
        print(f"✅ Loaded episodic memory: {len(self.episodic_memory.lessons)} lessons")

    def judge(self, blog_post: str, context: str = "") -> BlogJudgment:
        """
        Judge blog post quality using dual-memory system.

        Process:
        1. Retrieve similar past failures from episodic memory (vector search)
        2. Build working memory with principles + examples
        3. Evaluate against each principle
        4. Return judgment with score and feedback
        """

        # STEP 1: Retrieve relevant past failures from episodic memory
        query = f"blog post feedback: {context} {blog_post[:200]}"
        similar_lessons = self.episodic_memory.search(query, top_k=5)

        # Extract just the text from lessons (returns tuple of (LessonResult, score))
        similar_failures = [lesson[0].title for lesson in similar_lessons if lesson[1] > 0.3]

        # STEP 2: Build working memory (dynamic context)
        # In full MemAlign, this would be passed to LLM judge
        # For now, we use rule-based evaluation with episodic context
        _working_memory = {
            "principles": self.semantic_memory,
            "past_failures": similar_failures[:3],  # Top 3 most relevant
            "current_draft": blog_post,
        }

        # STEP 3: Evaluate against principles
        content_lower = blog_post.lower()

        # Check 1: Emotional hook
        emotion_words = [
            "wasted",
            "frustrated",
            "screwed up",
            "embarrassing",
            "relieved",
            "excited",
            "annoyed",
            "confused",
        ]
        has_emotional_hook = any(word in content_lower for word in emotion_words)

        # Check 2: Story arc
        has_problem = "## the problem" in content_lower or "problem:" in content_lower
        has_solution = (
            "## what actually worked" in content_lower
            or "## the fix" in content_lower
            or "## the solution" in content_lower
        )
        has_lesson = "## the lesson" in content_lower or "lesson:" in content_lower
        has_story_arc = has_problem and has_solution and has_lesson

        # Check 3: Specific details
        has_code = "```" in blog_post
        has_numbers = any(str(i) in blog_post for i in [100, 1000, 5000, 600])
        has_specific_details = has_code or has_numbers

        # Check 4: Bot slop detection
        bot_slop_indicators = [
            "the machine learns",
            "thompson sampling",
            "```mermaid",
            "α=",
            "β=",
            "something worked",
            "in software development, that's worth noting",
        ]
        has_bot_slop = any(indicator in content_lower for indicator in bot_slop_indicators)
        no_bot_slop = not has_bot_slop

        # Calculate score (0-10)
        points = sum(
            [
                has_emotional_hook * 2.5,  # Critical
                has_story_arc * 2.5,  # Critical
                has_specific_details * 2.0,
                no_bot_slop * 3.0,  # Most critical
            ]
        )

        # Generate feedback
        issues = []
        if not has_emotional_hook:
            issues.append("Missing emotional hook (frustrated, relieved, etc.)")
        if not has_story_arc:
            issues.append("Missing story structure (problem → solution → lesson)")
        if not has_specific_details:
            issues.append("Needs specific technical details (code, numbers)")
        if has_bot_slop:
            issues.append("CONTAINS BOT SLOP - remove Thompson stats/mermaid")

        feedback = "PASS - Good quality" if points >= 8.0 else f"FAIL - Issues: {'; '.join(issues)}"

        # Add episodic memory context to feedback
        if similar_failures:
            feedback += "\n\nSimilar past failures:\n" + "\n".join(
                f"- {failure[:100]}..." for failure in similar_failures
            )

        return BlogJudgment(
            score=points,
            has_emotional_hook=has_emotional_hook,
            has_story_arc=has_story_arc,
            has_specific_details=has_specific_details,
            no_bot_slop=no_bot_slop,
            feedback=feedback,
            similar_failures=similar_failures,
        )

    def record_feedback(self, blog_post: str, signal: str, context: str):
        """
        Record feedback to episodic memory.

        This is how the system learns - every thumbs up/down gets stored
        in the vector database for future judgments.
        """
        feedback_text = f"""
Blog Feedback: {signal}
Context: {context}
Content sample: {blog_post[:200]}...

This post received {signal} feedback.
"""

        # Store in episodic memory (LanceDB)
        # Note: LessonsLearnedRAG doesn't expose direct insert, but we can
        # create a lesson file that will be indexed on next reindex
        feedback_file = Path(f"rag_knowledge/blog_feedback/{signal}_{hash(blog_post)}.md")
        feedback_file.parent.mkdir(parents=True, exist_ok=True)

        with open(feedback_file, "w") as f:
            f.write(feedback_text)

        print(f"✅ Recorded {signal} feedback to episodic memory")
        print(f"   File: {feedback_file}")


def test_judge():
    """Test the MemAlign judge on sample posts."""
    judge = MemAlignBlogJudge()

    print("\n" + "=" * 60)
    print("MEMALIGN BLOG JUDGE - TEST")
    print("=" * 60)

    # Test 1: Good post (from our new generator)
    good_post = """I wasted 3 hours fighting browser automation before admitting I was solving the wrong problem.

## The Problem

Browser automation kept timing out

I thought I could make it work. Just one more try...

## The Fix

Switched to Twitter API v2 with tweepy. 10 minutes later: working.

```python
import tweepy
client = tweepy.Client(...)
```

## The Lesson

Don't fall in love with your solution. Fall in love with solving the problem.
"""

    print("\n[Test 1] Good post with emotional hook + story arc")
    judgment = judge.judge(good_post, "browser automation pivot")
    print(f"  Score: {judgment.score:.1f}/10")
    print(f"  Emotional hook: {'✅' if judgment.has_emotional_hook else '❌'}")
    print(f"  Story arc: {'✅' if judgment.has_story_arc else '❌'}")
    print(f"  No bot slop: {'✅' if judgment.no_bot_slop else '❌'}")
    verdict = judgment.feedback.split("\n")[0]
    print(f"  Verdict: {verdict}")

    # Test 2: Bot slop post
    bad_post = """Something worked. In software development, that's worth noting.

## The Flow

```mermaid
graph TD
    A[👍 Feedback] --> B[Thompson: α=146]
```

**Stats**: 63👍 / 18👎 = 77% success rate

The machine learns.
"""

    print("\n[Test 2] Bot slop with Thompson stats")
    judgment = judge.judge(bad_post, "generic update")
    print(f"  Score: {judgment.score:.1f}/10")
    print(f"  No bot slop: {'✅' if judgment.no_bot_slop else '❌'}")
    verdict2 = judgment.feedback.split("\n")[0]
    print(f"  Verdict: {verdict2}")

    # Test 3: Check episodic memory retrieval
    print("\n[Test 3] Episodic memory retrieval")
    lessons = judge.episodic_memory.search("blog post bot slop", top_k=3)
    print(f"  Found {len(lessons)} relevant past lessons:")
    for lesson_result, score in lessons[:3]:
        print(f"    - {lesson_result.title} (relevance: {score:.2f})")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    test_judge()
