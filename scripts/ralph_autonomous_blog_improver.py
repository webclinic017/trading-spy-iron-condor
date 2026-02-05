#!/usr/bin/env python3
"""
Ralph-Style Autonomous Blog Improver

Inspired by:
- Ona's Ralph (autonomous AI loop)
- Ralph Wiggum approach (runs until task complete)

Continuously improves blog generation system until quality targets met.
No back-and-forth prompting - runs autonomously until done.

Usage:
    python3 ralph_autonomous_blog_improver.py

Exit criteria:
- Win rate >85% on test posts
- Human readability score >8/10
- <1 second generation time
- No bot slop in output
"""

import json
import subprocess  # nosec B404
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class BlogQualityMetrics:
    """Quality metrics for blog posts."""

    has_emotional_hook: bool  # Opens with feeling/emotion
    has_story_arc: bool  # problem → struggle → solution
    has_specific_details: bool  # Concrete examples, not abstractions
    has_lesson: bool  # Clear takeaway
    no_bot_slop: bool  # No Thompson Sampling diagrams, no "The Machine Learns"
    word_count: int
    generation_time_ms: int

    @property
    def score(self) -> float:
        """Calculate overall quality score (0-10)."""
        points = sum(
            [
                self.has_emotional_hook,
                self.has_story_arc,
                self.has_specific_details,
                self.has_lesson,
                self.no_bot_slop,
            ]
        )
        return (points / 5) * 10


class RalphBlogImprover:
    """Ralph-style autonomous blog improvement loop."""

    def __init__(self):
        self.iteration = 0
        self.max_iterations = 10
        self.target_score = 8.0
        self.target_time_ms = 1000
        self.progress_file = Path("data/ralph_blog_progress.json")
        self.test_cases = [
            ("positive", "browser automation failed, switched to API"),
            ("positive", "duplicate blog posts - added detection"),
            ("negative", "bot slop - templates creating generic content"),
            ("positive", "tests passing - caught position sizing bug"),
        ]

    def generate_test_post(self, signal: str, context: str) -> tuple[str, int]:
        """Generate blog post and measure time."""
        start = time.time()

        result = subprocess.run(  # nosec B603 B607 - safe python execution
            [
                "python3",
                "-c",
                f"""
from scripts.generate_blog_post import generate_blog_post
post = generate_blog_post('{signal}', '{context}')
print(post['content'])
""",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )

        elapsed_ms = int((time.time() - start) * 1000)
        return result.stdout, elapsed_ms

    def evaluate_quality(self, content: str, time_ms: int) -> BlogQualityMetrics:
        """Evaluate blog post quality."""
        content_lower = content.lower()

        # Check for bot slop indicators
        bot_slop_indicators = [
            "the machine learns",
            "thompson sampling",
            "```mermaid",
            "α=",
            "β=",
            "something worked",
        ]
        no_bot_slop = not any(
            indicator in content_lower for indicator in bot_slop_indicators
        )

        # Check for emotional hooks
        emotion_words = [
            "wasted",
            "frustrated",
            "screwed up",
            "embarrassing",
            "relieved",
            "excited",
        ]
        has_emotional_hook = any(word in content_lower for word in emotion_words)

        # Check for story structure
        has_story_arc = (
            "## the problem" in content_lower
            and (
                "## what actually worked" in content_lower
                or "## the fix" in content_lower
            )
            and "## the lesson" in content_lower
        )

        # Check for specific details (code blocks, specific numbers)
        has_specific_details = "```" in content or any(
            str(i) in content for i in [100, 1000, 5000, 101]
        )

        # Check for lesson
        has_lesson = "## the lesson" in content_lower

        return BlogQualityMetrics(
            has_emotional_hook=has_emotional_hook,
            has_story_arc=has_story_arc,
            has_specific_details=has_specific_details,
            has_lesson=has_lesson,
            no_bot_slop=no_bot_slop,
            word_count=len(content.split()),
            generation_time_ms=time_ms,
        )

    def run_iteration(self) -> dict:
        """Run one iteration of testing and improvement."""
        self.iteration += 1
        print(f"\n{'=' * 60}")
        print(f"Ralph Iteration {self.iteration}/{self.max_iterations}")
        print(f"{'=' * 60}\n")

        results = []
        total_score = 0

        for signal, context in self.test_cases:
            print(f"Testing: {signal} - {context[:50]}...")

            content, time_ms = self.generate_test_post(signal, context)
            metrics = self.evaluate_quality(content, time_ms)

            print(f"  Score: {metrics.score:.1f}/10")
            print(f"  Time: {time_ms}ms")
            print(f"  Emotional hook: {'✅' if metrics.has_emotional_hook else '❌'}")
            print(f"  Story arc: {'✅' if metrics.has_story_arc else '❌'}")
            print(f"  No bot slop: {'✅' if metrics.no_bot_slop else '❌'}")

            results.append(
                {
                    "signal": signal,
                    "context": context,
                    "score": metrics.score,
                    "time_ms": time_ms,
                    "metrics": {
                        "emotional_hook": metrics.has_emotional_hook,
                        "story_arc": metrics.has_story_arc,
                        "specific_details": metrics.has_specific_details,
                        "lesson": metrics.has_lesson,
                        "no_bot_slop": metrics.no_bot_slop,
                    },
                }
            )

            total_score += metrics.score

        avg_score = total_score / len(self.test_cases)
        avg_time = sum(r["time_ms"] for r in results) / len(results)

        iteration_result = {
            "iteration": self.iteration,
            "timestamp": datetime.now().isoformat(),
            "avg_score": avg_score,
            "avg_time_ms": avg_time,
            "results": results,
            "met_targets": avg_score >= self.target_score
            and avg_time <= self.target_time_ms,
        }

        # Save progress
        self.save_progress(iteration_result)

        print(f"\n{'=' * 60}")
        print(f"Iteration {self.iteration} Summary:")
        print(f"  Average Score: {avg_score:.1f}/10 (target: {self.target_score})")
        print(f"  Average Time: {avg_time:.0f}ms (target: {self.target_time_ms}ms)")
        print(
            f"  Status: {'✅ TARGETS MET' if iteration_result['met_targets'] else '❌ Keep improving'}"
        )
        print(f"{'=' * 60}\n")

        return iteration_result

    def save_progress(self, result: dict):
        """Save progress to file."""
        self.progress_file.parent.mkdir(parents=True, exist_ok=True)

        if self.progress_file.exists():
            with open(self.progress_file) as f:
                data = json.load(f)
        else:
            data = {"iterations": []}

        data["iterations"].append(result)

        with open(self.progress_file, "w") as f:
            json.dump(data, f, indent=2)

    def identify_improvements(self, results: list[dict]) -> list[str]:
        """Identify what needs improvement based on test results."""
        improvements = []

        # Analyze common failures
        low_scores = [r for r in results if r["score"] < 8.0]

        if low_scores:
            for result in low_scores:
                metrics = result["metrics"]

                if not metrics["emotional_hook"]:
                    improvements.append(
                        f"Add emotional hooks to {result['signal']} posts"
                    )

                if not metrics["story_arc"]:
                    improvements.append(
                        f"Improve story structure for {result['context'][:30]}..."
                    )

                if not metrics["no_bot_slop"]:
                    improvements.append(
                        "Remove bot slop (Thompson stats, mermaid diagrams)"
                    )

        return list(set(improvements))  # Dedupe

    def run(self) -> bool:
        """
        Run Ralph loop until targets met or max iterations reached.

        Returns True if targets met, False if max iterations reached.
        """
        print("\n" + "=" * 60)
        print("🤖 RALPH AUTONOMOUS BLOG IMPROVER")
        print("=" * 60)
        print("\nTargets:")
        print(f"  - Quality score: ≥{self.target_score}/10")
        print(f"  - Generation time: ≤{self.target_time_ms}ms")
        print(f"  - Max iterations: {self.max_iterations}")
        print("\n" + "=" * 60)

        while self.iteration < self.max_iterations:
            result = self.run_iteration()

            if result["met_targets"]:
                print("\n🎉 SUCCESS! All targets met.")
                print("\nFinal Results:")
                print(f"  Quality: {result['avg_score']:.1f}/10")
                print(f"  Speed: {result['avg_time_ms']:.0f}ms")
                print(f"  Iterations: {self.iteration}")
                return True

            # Identify improvements needed
            improvements = self.identify_improvements(result["results"])

            if improvements:
                print("\n📝 Improvements needed:")
                for improvement in improvements:
                    print(f"  - {improvement}")

            # In real Ralph, this would automatically implement improvements
            # For now, we just report what's needed
            print("\n⏳ Next iteration in 2 seconds...")
            time.sleep(2)

        print("\n❌ Max iterations reached without meeting targets.")
        print("Manual intervention needed.")
        return False


if __name__ == "__main__":
    ralph = RalphBlogImprover()
    success = ralph.run()

    exit(0 if success else 1)
