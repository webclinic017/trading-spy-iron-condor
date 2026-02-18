# Blog SEO System

## Overview

Autonomous SEO monitoring and optimization for blog content published to GitHub Pages, Dev.to, and LinkedIn.

## Components

### 1. SEO Health Check (`scripts/seo_health_check.py`)

Autonomous validator that checks:
- ✅ Title optimization (<60 chars)
- ✅ Meta description (120-160 chars)
- ✅ Canonical URLs (HTTPS, trailing slash)
- ✅ Tags/categories presence
- ✅ Internal linking opportunities
- ✅ Image alt text
- ✅ Schema.org structured data (already in templates)

**Scoring:** 0-100 based on issues found
- Errors: -20 points each (block merge)
- Warnings: -5 points each (report only)
- Info: -1 point each (suggestions)

**Usage:**
```bash
python3 scripts/seo_health_check.py
```

**CI Integration:** Runs on every PR touching blog content (`.github/workflows/seo-validation.yml`)

### 2. Search Console Submission (`scripts/submit_to_search_console.py`)

Auto-submits URLs to Google for indexing.

**Setup:**
1. Enable Google Indexing API: https://console.cloud.google.com/apis/library/indexing.googleapis.com
2. Create service account: https://console.cloud.google.com/apis/credentials
3. Set `GOOGLE_SEARCH_CONSOLE_KEY` env var with service account JSON

**Usage:**
```bash
# Single URL
python3 scripts/submit_to_search_console.py https://example.com/post/

# Batch submit
python3 scripts/submit_to_search_console.py --batch docs/_posts/*.md
```

### 3. Cross-Platform Publishing (`scripts/cross_publish.py`)

Enhanced with automatic Search Console submission.

**Publishes to:**
- GitHub Pages (canonical source)
- Dev.to (with canonical URL back to GH Pages)
- LinkedIn (excerpt + link)
- Google Search Console (for indexing)

**Usage:**
```bash
python3 scripts/cross_publish.py docs/_posts/2026-02-18-my-post.md
python3 scripts/cross_publish.py docs/_posts/2026-02-18-my-post.md --skip-search-console
```

### 4. CI Workflow (`.github/workflows/seo-validation.yml`)

Runs on:
- Every PR touching blog content
- Every push to main
- Manual dispatch

**Actions:**
- ✅ Validates all posts
- ✅ Comments PR with SEO score
- ✅ Blocks merge if errors found
- ✅ Tracks SEO score over time in `data/metrics/seo_history.jsonl`

## Current Status

As of Feb 18, 2026:
- **Score:** 0/100 (83 issues: 0 errors, 54 warnings, 29 info)
- **Main issues:**
  - 54 posts missing tags/categories
  - 29 posts with long titles (>60 chars)
  - Some missing meta descriptions

## Improvement Opportunities

1. **Batch fix tags** - Add tags to all `lessons-learned.md` posts
2. **Shorten titles** - Optimize for search display
3. **Add meta descriptions** - Missing on ~15 posts
4. **Internal linking** - Automated related post suggestions

## Testing

Full test coverage:
```bash
pytest tests/test_blog_seo.py tests/test_seo_health_check.py -v
```

## Rules

1. All blog posts MUST have:
   - Title (<60 chars recommended)
   - Description (120-160 chars recommended)
   - Tags array (minimum 1 tag)
   - Canonical URL (auto-generated if missing)

2. CI blocks merge if SEO errors found (warnings OK)

3. Cross-publish script auto-submits to Search Console (can skip with flag)

4. SEO score tracked over time - monitor `data/metrics/seo_history.jsonl`
