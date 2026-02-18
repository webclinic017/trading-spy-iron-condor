#!/usr/bin/env python3
"""
Auto-fix changed blog posts to satisfy scripts/lint_blog_posts.py --changed --strict.

This is intentionally deterministic and dependency-light:
- Adds missing `description` and `image` fields to frontmatter.
- Ensures a `## Answer Block` section exists (or inserts one).
- Ensures an evidence link to the repo exists.
- Normalizes titles to avoid strict linter warnings (length + ALL CAPS words).

Why: CI runs `scripts/lint_blog_posts.py --changed --strict` and fails PRs if
any changed posts have warnings/errors. This script prevents "fix-by-hand"
tech debt by making compliance automatic and testable.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
POSTS_DIR = REPO_ROOT / "docs" / "_posts"

# Must exist in the GH Pages site so editors don't have to manage per-post images.
IMAGE_DEFAULT = "/assets/snapshots/progress_latest.png"
EVIDENCE_URL = "https://github.com/IgorGanapolsky/trading"

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)
_TITLE_LINE_RE = re.compile(r"^title:\s*(?P<val>.+?)\s*$", re.IGNORECASE | re.MULTILINE)
_HAS_DESC_RE = re.compile(r"^(description|summary|excerpt):\s*.+$", re.IGNORECASE | re.MULTILINE)
_HAS_IMAGE_RE = re.compile(
    r"^(image|image_url|image_path|cover_image|hero_image):\s*.+$",
    re.IGNORECASE | re.MULTILINE,
)

_ANSWER_HEADING_RE = re.compile(r"^##\s+Answer Block\b", re.IGNORECASE | re.MULTILINE)
_ANSWER_QUOTE_RE = re.compile(r"^>\s*\*\*Answer Block:\*\*", re.IGNORECASE | re.MULTILINE)
_EVIDENCE_RE = re.compile(
    r"https://github\.com/IgorGanapolsky/trading/(?:blob|tree|commit)/|https://github\.com/IgorGanapolsky/trading/?",
    re.IGNORECASE,
)

_ALL_CAPS_WORD_RE = re.compile(r"\b([A-Z]{4,})\b")


def _run(cmd: list[str]) -> str:
    result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    return (result.stdout or "").strip()


def _collect_changed_posts(base_ref: str) -> list[Path]:
    # Match behavior in scripts/lint_blog_posts.py (PR diff against origin/<base_ref>...HEAD).
    diff = _run(["git", "diff", "--name-only", "--diff-filter=ACMR", f"origin/{base_ref}...HEAD"])
    paths = []
    for line in diff.splitlines():
        p = (REPO_ROOT / line).resolve()
        if p.suffix.lower() != ".md":
            continue
        if POSTS_DIR in p.parents:
            paths.append(p)
    return sorted(set(paths))


def _strip_quotes(val: str) -> str:
    v = (val or "").strip()
    if len(v) >= 2 and ((v[0] == v[-1] == '"') or (v[0] == v[-1] == "'")):
        return v[1:-1]
    return v


def _json_quote(val: str) -> str:
    # YAML is a superset of JSON; using JSON escaping keeps output safe.
    return json.dumps(val, ensure_ascii=True)


def _extract_first_h1(body: str) -> str:
    m = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
    return (m.group(1).strip() if m else "").strip()


def _extract_answer_block_summary(body: str) -> str:
    # Prefer existing Answer Block quote if present.
    m = re.search(r"^>\s*\*\*Answer Block:\*\*\s*(.+)$", body, re.IGNORECASE | re.MULTILINE)
    if m:
        return re.sub(r"\s+", " ", m.group(1).strip())[:160]

    # Otherwise use first meaningful paragraph.
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", body) if p.strip()]
    for p in paragraphs:
        if p.startswith(("#", ">", "```", "|", "- ")):
            continue
        clean = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", p)
        clean = re.sub(r"[*_`]", "", clean)
        clean = re.sub(r"\s+", " ", clean).strip()
        if len(clean) >= 60:
            return clean[:160].rstrip()

    # Fallback: stable default.
    return "Engineering lessons from building an autonomous AI trading system."


def _normalize_title(title: str) -> str:
    t = re.sub(r"\s+", " ", (title or "").strip())
    if not t:
        return t

    # Replace ALL-CAPS words (len>=4) with Title-case to satisfy strict lint.
    t = _ALL_CAPS_WORD_RE.sub(lambda m: m.group(1).title(), t)

    # If still too long, aggressively shorten but keep meaning.
    if len(t) > 70:
        t2 = re.sub(r"\s*\([^)]*\)\s*$", "", t).strip()
        if t2:
            t = t2
    if len(t) > 70 and ":" in t:
        left, right = [s.strip() for s in t.split(":", 1)]
        right = right[:30].rstrip(" ,;:-")
        candidate = f"{left}: {right}".strip()
        if len(candidate) <= 70 and len(candidate) >= 20:
            t = candidate
    if len(t) > 70:
        t = t[:67].rstrip(" ,;:-") + "..."

    return t


def _replace_title_line(frontmatter: str, new_title: str) -> tuple[str, bool]:
    m = _TITLE_LINE_RE.search(frontmatter)
    if not m:
        # Insert title at end if missing.
        normalized = _normalize_title(new_title)
        return frontmatter.rstrip() + f"\ntitle: {_json_quote(normalized)}\n", True

    current_val = _strip_quotes(m.group("val"))
    normalized = _normalize_title(current_val)
    if normalized == current_val:
        return frontmatter, False

    # YAML is a superset of JSON; always emit JSON-quoted values for safety.
    repl = "title: " + _json_quote(normalized)

    updated = _TITLE_LINE_RE.sub(repl, frontmatter, count=1)
    return updated, True


def _ensure_frontmatter_keys(frontmatter: str, body: str) -> tuple[str, bool]:
    changed = False

    title_in_body = _extract_first_h1(body)
    frontmatter, title_changed = _replace_title_line(frontmatter, title_in_body or "Post")
    changed = changed or title_changed

    if not _HAS_DESC_RE.search(frontmatter):
        desc = _extract_answer_block_summary(body)
        frontmatter = frontmatter.rstrip() + f"\ndescription: {_json_quote(desc)}\n"
        changed = True

    if not _HAS_IMAGE_RE.search(frontmatter):
        frontmatter = frontmatter.rstrip() + f"\nimage: {_json_quote(IMAGE_DEFAULT)}\n"
        changed = True

    return frontmatter, changed


def _ensure_answer_block(body: str) -> tuple[str, bool]:
    if _ANSWER_HEADING_RE.search(body):
        return body, False

    if _ANSWER_QUOTE_RE.search(body):
        # Insert heading directly above the existing Answer Block quote.
        updated = _ANSWER_QUOTE_RE.sub("## Answer Block\n\n\\g<0>", body, count=1)
        return updated, True

    summary = _extract_answer_block_summary(body)

    # Insert after the first H1 if present, otherwise at top.
    lines = body.splitlines()
    for i, line in enumerate(lines[:30]):
        if line.startswith("# "):
            insert_at = i + 1
            # Ensure a blank line after H1 block.
            while insert_at < len(lines) and lines[insert_at].strip() == "":
                insert_at += 1
            block = [
                "",
                "## Answer Block",
                "",
                f"> **Answer Block:** {summary}",
                "",
            ]
            updated_lines = lines[:insert_at] + block + lines[insert_at:]
            return "\n".join(updated_lines).lstrip("\n"), True

    prefix = f"## Answer Block\n\n> **Answer Block:** {summary}\n\n"
    return prefix + body.lstrip("\n"), True


def _ensure_evidence_link(body: str) -> tuple[str, bool]:
    if _EVIDENCE_RE.search(body):
        return body, False
    suffix = f"\n\n---\n\nEvidence: {EVIDENCE_URL}\n"
    return body.rstrip() + suffix, True


def fix_post(path: Path) -> bool:
    text = path.read_text(encoding="utf-8", errors="ignore")
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return False

    frontmatter = m.group(1).rstrip()
    body = m.group(2).lstrip("\n")

    frontmatter, fm_changed = _ensure_frontmatter_keys(frontmatter, body)
    body, ab_changed = _ensure_answer_block(body)
    body, ev_changed = _ensure_evidence_link(body)

    changed = fm_changed or ab_changed or ev_changed
    if not changed:
        return False

    updated = f"---\n{frontmatter}\n---\n\n{body.rstrip()}\n"
    path.write_text(updated, encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Fix changed posts for strict lint")
    parser.add_argument("--base-ref", default=os.environ.get("GITHUB_BASE_REF") or "main")
    parser.add_argument("--paths", nargs="*", help="Explicit post paths (overrides --base-ref)")
    args = parser.parse_args()

    if args.paths:
        candidates = [(REPO_ROOT / p).resolve() for p in args.paths]
        posts = [p for p in candidates if p.exists() and POSTS_DIR in p.parents]
    else:
        posts = _collect_changed_posts(str(args.base_ref))

    if not posts:
        print("No changed posts to fix.")
        return 0

    updated = 0
    for p in posts:
        if fix_post(p):
            updated += 1

    print(f"Fixed {updated}/{len(posts)} changed post(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
