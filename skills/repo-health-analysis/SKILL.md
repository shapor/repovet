---
name: repo-health-analysis
description: |
  Reads commits.csv, prs.csv, and issues.csv to calculate an overall project
  health score (0-10). Use when the user asks about project activity, velocity,
  review culture, issue management, or maintenance status. Do NOT use for
  individual contributor profiles (use contributor-analysis) or security
  concerns (use security-history-analysis).
---

# Repo Health Analysis

## When to use this

- User asks "is this project actively maintained?"
- User wants to know about PR review culture or issue response time
- User asks for a health score or activity assessment
- You have CSV files at `~/.repovet/cache/{repo}/`

## Input files

All located at `~/.repovet/cache/{repo}/`:

- **commits.csv** (required): columns include `author_date`, `commit_date`, `author_name`, `author_email`, `is_merge`, `insertions`, `deletions`, `lang_stats`
- **prs.csv** (optional): columns include `number`, `title`, `state`, `author`, `created_at`, `merged_at`, `closed_at`, `review_comments`, `reviewers`, `first_review_at`
- **issues.csv** (optional): columns include `number`, `title`, `state`, `author`, `created_at`, `closed_at`, `comments`, `labels`

If prs.csv or issues.csv are missing, score those sections as N/A and note the gap.

## Workflow

### 1. Commit velocity (weight: 25%)

Group commits by week and by month using `author_date`:

```python
from collections import defaultdict
weekly = defaultdict(int)
for row in commits:
    week_key = row['author_date'].isocalendar()[:2]  # (year, week)
    weekly[week_key] += 1
```

Calculate:
- **Commits per week** (last 12 weeks): mean and trend (increasing/decreasing/stable)
- **Commits per month** (last 12 months): mean and trend
- **Days since last commit**: if > 90 days, flag as stale
- **Activity gaps**: periods > 30 days with zero commits

Scoring:
| Condition | Score |
|-----------|-------|
| Active last 30 days, stable or increasing trend | 9-10 |
| Active last 90 days, stable trend | 7-8 |
| Active last 180 days, decreasing trend | 5-6 |
| Last commit 180-365 days ago | 3-4 |
| Last commit > 1 year ago | 1-2 |

### 2. PR review culture (weight: 25%)

Skip if prs.csv is unavailable. Parse dates from ISO format.

Calculate:
- **Time-to-merge**: for merged PRs, `merged_at - created_at` in hours. Report median.
- **Time-to-first-review**: `first_review_at - created_at` in hours. Report median.
- **Reviewer participation**: count of unique reviewers across all PRs in last 6 months.
- **Review coverage**: percentage of merged PRs that had at least one review comment.
- **Self-merge ratio**: PRs where author = merger with zero review comments.

Scoring:
| Condition | Score |
|-----------|-------|
| Median review < 24h, coverage > 80%, multiple reviewers | 9-10 |
| Median review < 72h, coverage > 50% | 7-8 |
| Median review < 7 days, some review activity | 5-6 |
| Slow reviews, low coverage | 3-4 |
| No review process visible | 1-2 |

### 3. Issue health (weight: 20%)

Skip if issues.csv is unavailable.

Calculate:
- **Open/closed ratio**: `open_count / total_count`. Healthy is < 0.5.
- **Time-to-close**: for closed issues, `closed_at - created_at` in days. Report median.
- **Stale issues**: open issues with no activity in 90+ days.
- **Response rate**: percentage of issues with at least one comment.
- **Label usage**: percentage of issues with at least one label (indicates triage process).

Scoring:
| Condition | Score |
|-----------|-------|
| Open ratio < 0.3, median close < 7 days, good triage | 9-10 |
| Open ratio < 0.5, median close < 30 days | 7-8 |
| Open ratio < 0.7, some responsiveness | 5-6 |
| High open ratio, slow response | 3-4 |
| Issues ignored or disabled | 1-2 |

### 4. Bot activity level (weight: 10%)

Across all data sources, identify bot accounts (same patterns as contributor-analysis):

- In commits: `author_name` contains `[bot]` or matches known bot names
- In PRs: `author` contains `[bot]`
- In issues: `author` contains `[bot]`

Calculate:
- Percentage of PR comments/activity from bots
- Percentage of commits from bots (CI, dependabot, etc.)
- Whether automated dependency updates exist (dependabot, renovate)

Scoring:
| Condition | Score |
|-----------|-------|
| Healthy automation (dependabot/renovate active, CI bots) | 9-10 |
| Some automation present | 7-8 |
| Minimal automation | 5-6 |
| No automation at all | 3-4 |
| Bots dominate with no human oversight | 1-2 |

### 5. Staleness and gaps (weight: 10%)

Combine: days since last commit, days since last merged PR, days since last closed issue, longest gap in last 12 months.

### 6. Language evolution (weight: 10%)

Parse `lang_stats` JSON from commits, group by month. Report current primary languages, languages added/removed over time, and polyglot indicator (languages with > 5% share).

## Output format

```markdown
# Repo Health Report: {repo_name}

## Overall Health Score: X.X / 10

| Category | Score | Weight | Weighted |
|----------|-------|--------|----------|
| Commit Velocity | X/10 | 25% | X.XX |
| PR Review Culture | X/10 | 25% | X.XX |
| Issue Health | X/10 | 20% | X.XX |
| Bot/Automation | X/10 | 10% | X.XX |
| Staleness | X/10 | 10% | X.XX |
| Language Health | X/10 | 10% | X.XX |

## Commit Velocity
[Weekly/monthly trends, charts if possible]

## PR Review Culture
[Merge times, reviewer stats]

## Issue Health
[Open/closed ratio, response times]

## Automation
[Bot activity summary]

## Language Evolution
[Language trends over time]

## Risks
- [List specific health risks found]
```

## Calculating the final score

```python
weights = {
    'velocity': 0.25,
    'pr_review': 0.25,
    'issue_health': 0.20,
    'automation': 0.10,
    'staleness': 0.10,
    'language': 0.10,
}

# If a category is N/A (missing data), redistribute its weight equally
available = {k: v for k, v in weights.items() if scores[k] is not None}
total_weight = sum(available.values())
health_score = sum(scores[k] * (v / total_weight) for k, v in available.items())
```

## Common Pitfalls

- **Do NOT fail if prs.csv or issues.csv are missing.** Many repos only have commit data. Score what you can and note the gaps.
- **Do NOT treat all merged PRs equally.** Filter out bot-authored PRs (dependabot, renovate) when calculating review culture metrics.
- **Normalize dates carefully.** CSV timestamps may have varying timezone formats. Always parse with timezone awareness.
- **Do NOT penalize low bot activity.** Small projects may not need automation. Score 5 (neutral) not 1 for absent bots.
- **Watch for repos that use squash merges.** Commit count may be lower than actual PR count. Cross-reference with prs.csv when available.
- **Stale issue count can be misleading.** Some repos use issues as long-term tracking. Check labels for "enhancement" or "feature-request" before penalizing.
