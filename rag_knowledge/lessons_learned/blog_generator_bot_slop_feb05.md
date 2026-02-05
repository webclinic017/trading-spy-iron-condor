# LL-326: Blog Generator Still Producing Bot Slop

**Date**: February 5, 2026
**Severity**: HIGH
**Category**: Content Quality, RLHF

## Problem

Despite implementing a two-stage blog generator (Instacart-inspired), the system published bot slop content with:

- Mermaid diagrams showing Thompson Sampling stats (α=146, β=)
- Generic "The Machine Learns" titles
- Formulaic structure without real narrative

**Root cause**: Published using OLD generator (`publish_rlhf_blog.py`) instead of NEW two-stage generator (`generate_blog_post.py` + `blog_narrative_generators.py`)

## Bot Slop Indicators (MUST AVOID)

1. **Thompson Sampling diagrams** - `mermaid graph TD A[👍 Feedback] --> B[Thompson: α=146]`
2. **"The Machine Learns"** - Generic title from old templates
3. **"Something worked. In software development, that's worth noting."** - Bot slop opening
4. **α=, β=** - Raw model parameters in content
5. **Formulaic mermaid charts** - Any diagram with Thompson stats

## What User Wanted

User gave thumbs up for:

1. Implementing two-stage generator
2. MemAlign judge system
3. Closing GitHub issues
4. Fixing authentication

Expected: Blog posts about THESE achievements using NEW narrative generator

Got: Generic bot slop from OLD template system

## Solution

1. **ALWAYS use new two-stage generator** (`scripts/generate_blog_post.py`)
2. **Delete `publish_rlhf_blog.py`** - it generates bot slop
3. **Create new publisher** that:
   - Uses `blog_intent_classifier.py` + `blog_narrative_generators.py`
   - Passes MemAlign judge before publishing
   - NO mermaid diagrams with Thompson stats
   - NO generic templates

## MemAlign Judge Scores

- Bot slop post: Would score 2/10 (has mermaid + α= + generic structure)
- Good post: Should score 8+/10 (emotional hook + story arc + no bot slop)

## Prevention

```python
# CORRECT workflow:
from blog_intent_classifier import classify_intent, extract_context
from blog_narrative_generators import generate_narrative
from memalign_blog_judge import MemAlignBlogJudge

# 1. Generate using TWO-STAGE system
intent = classify_intent(signal, context, commits)
ctx = extract_context(signal, context, commits, intent)
content = generate_narrative(ctx)

# 2. Judge BEFORE publishing
judge = MemAlignBlogJudge()
judgment = judge.judge(content, context)

# 3. Only publish if score >= 8
if judgment.score >= 8.0:
    publish_to_devto(content)
else:
    print(f"BLOCKED: Score {judgment.score}/10 - {judgment.feedback}")
```

## Files to Delete

- `scripts/publish_rlhf_blog.py` - OLD bot slop generator
- Any posts with "The Machine Learns" in title
- Any posts with mermaid Thompson diagrams

## Verified Clean

- Dev.to: ✅ No "Machine Learns" titles
- Dev.to: ✅ No "Mistake Made. Lesson Learned" bot slop
- Local: Need to scan and remove old posts

## Tags

`content-quality`, `bot-slop`, `rlhf`, `blog-generation`, `memalign`, `two-stage-generation`
