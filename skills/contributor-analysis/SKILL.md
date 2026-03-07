---
name: contributor-analysis
description: |
  Reads commits.csv (produced by git-commit-intel) and generates contributor
  intelligence for a repository. Use when the user asks about who maintains a
  project, bus factor, contributor breakdown, hiring evaluation, or author-level
  stats. Do NOT use for PR review culture or issue health — those belong to
  repo-health-analysis.
---

# Contributor Analysis

## When to use this

- User asks "who maintains this repo?" or "what's the bus factor?"
- User wants to evaluate a specific developer's contributions (hiring eval)
- User asks about contributor diversity, bot ratio, or timezone spread
- You have a `commits.csv` file at `~/.repovet/cache/{repo}/commits.csv`

## Input

CSV file with these columns (produced by `git-commit-intel`):

```
repo_name, commit_hash, author_name, author_email, author_date,
committer_name, committer_email, commit_date, subject, body,
parent_hashes, refs, is_merge, files_changed, insertions, deletions,
changed_files, lang_stats, dir_stats
```

Location: `~/.repovet/cache/{repo}/commits.csv`

## Workflow

### 1. Load and parse the CSV

```python
import csv, json
from collections import defaultdict, Counter
from datetime import datetime

rows = []
with open(csv_path, newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        row['author_date'] = datetime.fromisoformat(row['author_date'])
        row['insertions'] = int(row['insertions'] or 0)
        row['deletions'] = int(row['deletions'] or 0)
        row['files_changed'] = int(row['files_changed'] or 0)
        row['lang_stats'] = json.loads(row['lang_stats'] or '{}')
        row['dir_stats'] = json.loads(row['dir_stats'] or '{}')
        rows.append(row)
```

### 2. Top contributors by commit count, lines added, files touched

Group by `author_email` (normalize to lowercase). For each author compute:

- **Commit count**: number of rows
- **Lines added**: sum of `insertions`
- **Lines removed**: sum of `deletions`
- **Files touched**: sum of `files_changed`
- **Net impact**: insertions - deletions

Rank authors by each metric. Report the top 10 for each.

### 3. Bus factor

Calculate how many contributors cover 80% of commits in the last 6 months:

1. Filter commits to the most recent 6 months by `author_date`.
2. Count commits per author.
3. Sort descending. Walk the list, accumulating percentages.
4. The bus factor is the count when cumulative percentage reaches 80%.

A bus factor of 1 is a critical risk. Under 3 is a warning.

### 4. Bot vs human ratio

Identify bots by checking:

- `author_name` contains `[bot]` (case-insensitive)
- `author_email` matches known bot patterns: `*@users.noreply.github.com` with `[bot]`, `dependabot`, `renovate`, `greenkeeper`, `snyk-bot`, `github-actions`
- `author_name` matches: `dependabot`, `renovate[bot]`, `github-actions[bot]`, `codecov[bot]`, `mergify[bot]`

Report:
- Total commits by bots vs humans
- Percentage breakdown
- List of identified bot accounts

### 5. Per-author stats

For each author (top 20 by commit count), compute:

| Metric | How |
|--------|-----|
| First commit | min(`author_date`) |
| Last commit | max(`author_date`) |
| Active period | last - first (in days) |
| Top languages | Aggregate `lang_stats` JSON across their commits, rank by line count |
| Top directories | Aggregate `dir_stats` JSON across their commits, rank by file count |
| Avg commit size | mean of `insertions + deletions` |
| Merge ratio | count where `is_merge` is true / total |

### 6. Hiring eval mode

When the user names a specific author (by name or email):

1. Filter all rows where `author_name` or `author_email` matches (case-insensitive, partial match).
2. Report full per-author stats from step 5.
3. Add: list of commit subjects (most recent 20), typical commit days/times, languages worked in, directories owned.
4. Highlight: consistency (gaps > 30 days), scope (broad vs narrow), code volume trends over time.

### 7. Timezone inference

Extract timezone offset from `author_date` ISO timestamps. Group by author:

- Most common UTC offset = likely timezone
- Map offsets to regions: UTC-8 = US Pacific, UTC-5 = US Eastern, UTC+1 = Central Europe, UTC+5:30 = India, UTC+8 = China/Singapore, UTC+9 = Japan/Korea

Report contributor geographic distribution.

## Output format

Produce a structured markdown report:

```markdown
# Contributor Analysis: {repo_name}

## Summary
- **Total contributors**: N
- **Bus factor**: N (covers 80% of recent commits)
- **Bot ratio**: X% of commits are automated
- **Active contributors (last 6 months)**: N

## Top Contributors

| Rank | Author | Commits | Lines Added | Files Touched |
|------|--------|---------|-------------|---------------|
| 1    | ...    | ...     | ...         | ...           |

## Bus Factor Analysis
[Details and risk assessment]

## Bot Activity
[Bot list and breakdown]

## Geographic Distribution
[Timezone breakdown]

## Per-Author Profiles
[Detailed stats for top contributors]
```

## Common Pitfalls

- **Do NOT deduplicate authors by name alone.** The same person may use different names but the same email. Normalize by lowercased `author_email`.
- **Do NOT count merge commits in "lines added" metrics.** Merge commits inflate numbers. Filter where `is_merge` is false for code contribution metrics.
- **Do NOT assume all noreply emails are bots.** GitHub privacy emails (`user@users.noreply.github.com`) are human. Only flag those containing `[bot]`.
- **Handle empty lang_stats/dir_stats gracefully.** Some commits may have empty JSON objects.
- **Timezone offsets can change for the same author** (travel, DST). Use the mode, not the first value.
