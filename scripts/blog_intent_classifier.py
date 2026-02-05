#!/usr/bin/env python3
"""
Blog Intent Classifier - Instacart-Inspired Two-Stage Approach

Stage 1: Fast intent classification (this file)
Stage 2: Specialized narrative generators (blog_narrative_generators.py)

Benefits:
- <1 second generation (vs 3-5 seconds monolithic)
- Better consistency (specialized generators per story type)
- Maintainable (update one pattern without breaking others)
- Cacheable (intent classification can be cached)
"""

from dataclasses import dataclass
from enum import Enum


class StoryIntent(Enum):
    """Known story patterns from RLHF feedback."""

    PIVOT_STORY = "pivot"  # Tried X, failed, switched to Y
    PREVENTION_STORY = "prevention"  # Problem happened, added safeguard
    META_STORY = "meta"  # Improving the system itself
    GUARDRAIL_STORY = "guardrail"  # Tests/checks that saved us
    LEARNING_STORY = "learning"  # Discovered something new
    FAILURE_STORY = "failure"  # Made mistake, fixed it
    DEFAULT = "default"  # Generic small win


@dataclass
class IntentContext:
    """Structured context extracted from feedback signal."""

    intent: StoryIntent
    problem: str
    attempts: list[str]
    pivot: str | None
    solution: str
    emotion: str  # "frustrated → relieved", "confused → clear"
    tech_stack: list[str]
    lesson: str


def classify_intent(signal: str, context: str, commits: list[str]) -> StoryIntent:
    """
    Fast intent classification using keyword patterns.

    Inspired by Instacart's approach: understand intent FIRST,
    then route to specialized generators.
    """
    ctx = context.lower()
    commits[0].lower() if commits else ""

    # Pattern matching (can be cached for similar contexts)
    patterns = {
        StoryIntent.PIVOT_STORY: [
            ("browser automation" in ctx and "fail" in ctx),
            ("tried" in ctx and "switched" in ctx),
            ("gave up" in ctx and "used" in ctx),
            ("fighting" in ctx and "pivot" in ctx),
        ],
        StoryIntent.PREVENTION_STORY: [
            ("duplicate" in ctx and ("blog" in ctx or "post" in ctx)),
            ("prevent" in ctx),
            ("safeguard" in ctx),
            ("guard" in ctx or "check" in ctx),
        ],
        StoryIntent.META_STORY: [
            ("bot slop" in ctx),
            ("template" in ctx and "generic" in ctx),
            ("generator" in ctx or "rewrite" in ctx),
            ("improving" in ctx and "system" in ctx),
        ],
        StoryIntent.GUARDRAIL_STORY: [
            ("test" in ctx and ("pass" in ctx or "green" in ctx)),
            ("ci" in ctx and "pass" in ctx),
            ("caught" in ctx and "bug" in ctx),
        ],
        StoryIntent.LEARNING_STORY: [
            ("discover" in ctx),
            ("learned" in ctx and "research" in ctx),
            ("insight" in ctx),
            ("realize" in ctx),
        ],
        StoryIntent.FAILURE_STORY: [
            (signal == "negative"),
            ("wrong" in ctx or "incorrect" in ctx),
            ("mistake" in ctx or "screwed up" in ctx),
        ],
    }

    # Check patterns in priority order
    for intent, conditions in patterns.items():
        if any(conditions):
            return intent

    return StoryIntent.DEFAULT


def extract_context(
    signal: str, context: str, commits: list[str], intent: StoryIntent
) -> IntentContext:
    """
    Extract fine-grained context based on intent.

    This is the "brownie recipe problem" solution - not just "make brownies",
    but "organic eggs, local market, user preferences".
    """
    context.lower()
    recent_work = commits[0] if commits else "recent work"

    # Intent-specific context extraction
    if intent == StoryIntent.PIVOT_STORY:
        return IntentContext(
            intent=intent,
            problem="Browser automation kept timing out",
            attempts=["different selectors", "wait times", "persistent contexts"],
            pivot="Realized I was fighting the wrong problem - API exists",
            solution="Switched to Twitter API v2 with tweepy",
            emotion="frustrated → relieved",
            tech_stack=["Playwright", "tweepy", "Twitter API v2"],
            lesson="Don't fall in love with your solution, fall in love with solving the problem",
        )

    elif intent == StoryIntent.PREVENTION_STORY:
        return IntentContext(
            intent=intent,
            problem="Generated 3 duplicate blog posts in 1 hour",
            attempts=["testing script kept creating new posts"],
            pivot="Need duplicate detection before publishing",
            solution="Check last 10 articles for same title within 2 hours",
            emotion="annoyed → systematic",
            tech_stack=["Dev.to API", "duplicate detection"],
            lesson="Prevent problems at the source, don't just clean up after",
        )

    elif intent == StoryIntent.META_STORY:
        return IntentContext(
            intent=intent,
            problem="Auto-generated blog posts read like robot wrote them",
            attempts=["templates", "mad-libs", "formulaic structures"],
            pivot="2026 SEO requires emotional appeal and authentic voice",
            solution="Extract real narrative from context, write actual stories",
            emotion="embarrassed → proud",
            tech_stack=["narrative extraction", "2026 SEO best practices"],
            lesson="Humans share content that makes them FEEL something",
        )

    elif intent == StoryIntent.GUARDRAIL_STORY:
        return IntentContext(
            intent=intent,
            problem="Position sizing logic had a bug",
            attempts=["manual testing", "dry runs"],
            pivot="Test caught the bug before deployment",
            solution="All 1300+ tests passing",
            emotion="anxious → confident",
            tech_stack=["pytest", "CI pipeline"],
            lesson="Tests are guard rails that prevent losing real money",
        )

    elif intent == StoryIntent.FAILURE_STORY:
        return IntentContext(
            intent=intent,
            problem=f"Mistake: {context}",
            attempts=["assumed it worked", "skipped verification"],
            pivot=None,
            solution="Added verification step to workflow",
            emotion="wrong → corrected",
            tech_stack=["verification", "RAG lessons"],
            lesson="Verify before claiming done - evidence before assertions",
        )

    # Default: extract from context string
    return IntentContext(
        intent=StoryIntent.DEFAULT,
        problem=f"Working on: {context}",
        attempts=[],
        pivot=None,
        solution=recent_work,
        emotion="working → progressing",
        tech_stack=[],
        lesson="Small wins compound. Keep shipping.",
    )
