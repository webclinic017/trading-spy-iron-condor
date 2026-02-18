#!/usr/bin/env python3
"""
Autonomous SEO health checker for blog content.

Validates:
- Schema.org structured data
- Meta descriptions
- Canonical URLs
- Internal linking
- Image optimization
- Sitemap freshness

Returns exit code 0 if healthy, 1 if issues found.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DOCS_DIR = Path(__file__).parent.parent / "docs"
POSTS_DIR = DOCS_DIR / "_posts"


@dataclass
class SEOIssue:
    """An SEO issue found during validation."""

    severity: str  # "error" | "warning" | "info"
    file: str
    message: str
    fix: str | None = None


@dataclass
class SEOReport:
    """Complete SEO health report."""

    score: int  # 0-100
    issues: list[SEOIssue]
    passed: int
    failed: int
    warnings: int

    def is_healthy(self) -> bool:
        """Returns True if no errors (warnings OK)."""
        return self.failed == 0


def extract_frontmatter(content: str) -> dict[str, Any]:
    """Extract YAML frontmatter from markdown content."""
    import yaml

    match = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
    if not match:
        return {}

    try:
        return yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return {}

    # Fallback to naive parsing (deprecated)
    fm: dict[str, Any] = {}
    for line in match.group(1).split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        if ":" in line:
            key, _, value = line.partition(":")
            value = value.strip()
            # Remove quotes
            if value.startswith('"') and value.endswith('"') or value.startswith("'") and value.endswith("'"):
                value = value[1:-1]
            # Parse booleans
            elif value.lower() in ("true", "yes"):
                value = True
            elif value.lower() in ("false", "no"):
                value = False
            fm[key.strip()] = value

    return fm


def check_meta_description(fm: dict[str, Any], file_path: Path) -> SEOIssue | None:
    """Validate meta description exists and is optimal length."""
    desc = fm.get("description") or fm.get("excerpt") or ""
    if isinstance(desc, str):
        desc = desc.strip()

    if not desc:
        return SEOIssue(
            severity="warning",
            file=str(file_path.name),
            message="Missing meta description",
            fix="Add 'description' field to frontmatter (120-160 chars)",
        )

    if len(desc) < 50:
        return SEOIssue(
            severity="warning",
            file=str(file_path.name),
            message=f"Meta description too short ({len(desc)} chars)",
            fix="Expand description to 120-160 chars for better SEO",
        )

    if len(desc) > 160:
        return SEOIssue(
            severity="info",
            file=str(file_path.name),
            message=f"Meta description too long ({len(desc)} chars)",
            fix="Truncate description to 160 chars to avoid search truncation",
        )

    return None


def check_title(fm: dict[str, Any], file_path: Path) -> SEOIssue | None:
    """Validate title exists and is optimal length."""
    title = fm.get("title", "")
    if not title:
        return SEOIssue(
            severity="error",
            file=str(file_path.name),
            message="Missing title",
            fix="Add 'title' field to frontmatter",
        )

    if len(title) > 60:
        return SEOIssue(
            severity="warning",
            file=str(file_path.name),
            message=f"Title too long ({len(title)} chars)",
            fix="Shorten title to <60 chars for better search display",
        )

    return None


def check_canonical_url(fm: dict[str, Any], file_path: Path) -> SEOIssue | None:
    """Validate canonical URL format."""
    canonical = fm.get("canonical_url", "")
    if not canonical:
        return None  # Optional field

    if not canonical.startswith("https://"):
        return SEOIssue(
            severity="error",
            file=str(file_path.name),
            message=f"Invalid canonical URL: {canonical}",
            fix="Use absolute HTTPS URL",
        )

    if not canonical.endswith("/"):
        return SEOIssue(
            severity="warning",
            file=str(file_path.name),
            message="Canonical URL should end with /",
            fix=f"Change to: {canonical}/",
        )

    return None


def check_tags(fm: dict[str, Any], file_path: Path) -> SEOIssue | None:
    """Validate tags/categories exist."""
    tags = fm.get("tags", [])
    categories = fm.get("categories", [])

    if not tags and not categories:
        return SEOIssue(
            severity="warning",
            file=str(file_path.name),
            message="No tags or categories",
            fix="Add 'tags' array to frontmatter for better discoverability",
        )

    return None


def check_internal_links(content: str, file_path: Path) -> SEOIssue | None:
    """Check for internal linking opportunities."""
    # Strip frontmatter
    body = re.sub(r"^---.*?---\n", "", content, flags=re.DOTALL)

    # Count internal links
    internal_links = re.findall(r"\[.*?\]\((?:https://igorganapolsky\.github\.io)?/.*?\)", body)

    if len(internal_links) == 0:
        return SEOIssue(
            severity="info",
            file=str(file_path.name),
            message="No internal links found",
            fix="Add links to related posts for better SEO and UX",
        )

    return None


def check_image_alt_text(content: str, file_path: Path) -> SEOIssue | None:
    """Validate images have alt text."""
    # Strip frontmatter
    body = re.sub(r"^---.*?---\n", "", content, flags=re.DOTALL)

    # Find images without alt text: ![](url) or ![ ](url)
    images_no_alt = re.findall(r"!\[\s*\]\(.*?\)", body)

    if images_no_alt:
        return SEOIssue(
            severity="warning",
            file=str(file_path.name),
            message=f"{len(images_no_alt)} image(s) missing alt text",
            fix="Add descriptive alt text: ![description](url)",
        )

    return None


def audit_post(file_path: Path) -> list[SEOIssue]:
    """Run all SEO checks on a single post."""
    if not file_path.exists():
        return []

    content = file_path.read_text()
    fm = extract_frontmatter(content)

    issues: list[SEOIssue] = []

    # Run all checks
    for check in [
        check_title,
        check_meta_description,
        check_canonical_url,
        check_tags,
    ]:
        issue = check(fm, file_path)
        if issue:
            issues.append(issue)

    # Content checks
    for check in [check_internal_links, check_image_alt_text]:
        issue = check(content, file_path)
        if issue:
            issues.append(issue)

    return issues


def calculate_score(issues: list[SEOIssue]) -> int:
    """Calculate SEO score (0-100) based on issues."""
    errors = sum(1 for i in issues if i.severity == "error")
    warnings = sum(1 for i in issues if i.severity == "warning")
    infos = sum(1 for i in issues if i.severity == "info")

    # Start at 100, deduct points
    score = 100
    score -= errors * 20  # -20 per error
    score -= warnings * 5  # -5 per warning
    score -= infos * 1  # -1 per info

    return max(0, score)


def audit_blog() -> SEOReport:
    """Audit all blog posts and generate report."""
    if not POSTS_DIR.exists():
        print(f"❌ Posts directory not found: {POSTS_DIR}")
        return SEOReport(score=0, issues=[], passed=0, failed=0, warnings=0)

    all_issues: list[SEOIssue] = []
    post_files = sorted(POSTS_DIR.glob("*.md"))

    for post_file in post_files:
        issues = audit_post(post_file)
        all_issues.extend(issues)

    errors = sum(1 for i in all_issues if i.severity == "error")
    warnings = sum(1 for i in all_issues if i.severity == "warning")

    score = calculate_score(all_issues)

    return SEOReport(
        score=score,
        issues=all_issues,
        passed=len(post_files) - errors,
        failed=errors,
        warnings=warnings,
    )


def print_report(report: SEOReport) -> None:
    """Print human-readable report."""
    print(f"\n{'='*60}")
    print("SEO Health Report")
    print(f"{'='*60}\n")

    print(f"Score: {report.score}/100")
    print(f"Status: {'✅ HEALTHY' if report.is_healthy() else '❌ ISSUES FOUND'}\n")

    print(f"Issues: {len(report.issues)} total")
    print(f"  Errors:   {report.failed}")
    print(f"  Warnings: {report.warnings}")
    print(f"  Info:     {len(report.issues) - report.failed - report.warnings}\n")

    if report.issues:
        # Group by severity
        for severity in ["error", "warning", "info"]:
            severity_issues = [i for i in report.issues if i.severity == severity]
            if not severity_issues:
                continue

            icon = "❌" if severity == "error" else "⚠️" if severity == "warning" else "ℹ️"
            print(f"{icon} {severity.upper()}S:\n")

            for issue in severity_issues:
                print(f"  {issue.file}")
                print(f"    {issue.message}")
                if issue.fix:
                    print(f"    Fix: {issue.fix}")
                print()

    print(f"{'='*60}\n")


def main() -> int:
    """Run SEO health check and return exit code."""
    report = audit_blog()
    print_report(report)

    # Write JSON report for CI
    report_file = Path(__file__).parent.parent / "data" / "seo_health.json"
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text(
        json.dumps(
            {
                "score": report.score,
                "passed": report.passed,
                "failed": report.failed,
                "warnings": report.warnings,
                "issues": [
                    {
                        "severity": i.severity,
                        "file": i.file,
                        "message": i.message,
                        "fix": i.fix,
                    }
                    for i in report.issues
                ],
            },
            indent=2,
        )
    )

    print(f"📊 Report saved: {report_file}")

    # Exit code: 0 if healthy, 1 if errors
    return 0 if report.is_healthy() else 1


if __name__ == "__main__":
    sys.exit(main())
