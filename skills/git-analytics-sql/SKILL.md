---
name: git-analytics-sql
description: |
  Run SQL analytics against git commit history, PR, and issue data using DuckDB.
  Use this skill when the user wants to query, analyze, slice, or explore git
  repository data. Trigger on: "who committed the most?", "show me commit
  velocity", "what languages are used?", "bus factor", "analyze contributors",
  "PR review time", "issue response time", "commit patterns", "how active is
  this repo?", "compare authors", any SQL or data analysis question about a
  git repo. Also use when building dashboards, charts, or reports from repo data.
  Do NOT use for security scanning or trust assessment — use repo-trust-assessment instead.
---

# Git Analytics SQL

Run SQL queries against git/GitHub CSV data using DuckDB. The CSVs are produced
by `git-commit-intel` and `github-project-intel` skills.

## When to Use

- User asks questions about repo history, contributors, activity, languages
- User wants to slice/filter/aggregate git data
- User wants a custom analysis not covered by canned reports
- User wants to build a dashboard or visualization from repo data
- User asks about PR review culture, issue health, contributor patterns

## Prerequisites

CSV files must exist (run data extraction skills first):
- `commits.csv` — from `git-commit-intel` skill
- `prs.csv` — from `github-project-intel` skill (optional)
- `issues.csv` — from `github-project-intel` skill (optional)

DuckDB must be installed: `pip install duckdb`

## How to Run Queries

### Option 1: Use the query script

```bash
python skills/git-analytics-sql/scripts/query.py \
  --commits commits.csv --prs prs.csv --issues issues.csv \
  "SELECT author_name, COUNT(*) as commits FROM commits GROUP BY 1 ORDER BY 2 DESC LIMIT 10"
```

### Option 2: Use the full analysis script

```bash
python scripts/repovet-analyze.py commits.csv --prs prs.csv --issues issues.csv
```

### Option 3: Write inline DuckDB Python

```python
import duckdb

db = duckdb.connect(":memory:")
db.execute("""
    CREATE VIEW commits AS
    SELECT *, TRY_CAST(author_date AS TIMESTAMP WITH TIME ZONE) AS author_ts
    FROM read_csv_auto('commits.csv', header=true, ignore_errors=true)
""")

result = db.execute("YOUR QUERY HERE").fetchall()
```

## Available Tables

### commits (from git-history-to-csv.py)

| Column | Type | Description |
|--------|------|-------------|
| repo_name | VARCHAR | Repository name |
| commit_hash | VARCHAR | Full SHA |
| author_name | VARCHAR | Author display name |
| author_email | VARCHAR | Author email |
| author_date | VARCHAR | ISO timestamp (also as `author_ts` TIMESTAMPTZ) |
| committer_name | VARCHAR | Committer name |
| committer_email | VARCHAR | Committer email |
| commit_date | VARCHAR | ISO timestamp (also as `commit_ts` TIMESTAMPTZ) |
| subject | VARCHAR | Commit message first line |
| body | VARCHAR | Commit message body |
| parent_hashes | VARCHAR | Space-separated parent SHAs |
| refs | VARCHAR | Branch/tag refs |
| is_merge | VARCHAR | 'True' or 'False' |
| files_changed | INTEGER | Number of files changed |
| insertions | INTEGER | Lines added |
| deletions | INTEGER | Lines removed |
| changed_files | VARCHAR | JSON array of filenames |
| lang_stats | VARCHAR | JSON: `{"Python": {"ins": 100, "dels": 20}, ...}` |
| dir_stats | VARCHAR | JSON: `{"src": {"ins": 100, "dels": 20}, ...}` |

### prs (from github-to-csv.py --prs)

| Column | Type | Description |
|--------|------|-------------|
| pr_number | INTEGER | PR number |
| pr_state | VARCHAR | OPEN, MERGED, CLOSED |
| pr_author | VARCHAR | GitHub login |
| pr_created_at | VARCHAR | ISO timestamp |
| pr_merged_at | VARCHAR | ISO timestamp (null if not merged) |
| pr_additions | INTEGER | Lines added |
| pr_deletions | INTEGER | Lines removed |
| pr_comment_count | INTEGER | Human comments |
| pr_bot_comment_count | INTEGER | Bot comments |
| pr_review_thread_count | INTEGER | Review threads |
| pr_reviewers | VARCHAR | JSON: `{"alice": "APPROVED", "bob": "COMMENTED"}` |
| pr_time_to_merge_hours | VARCHAR | Hours from creation to merge |
| pr_first_review_hours | VARCHAR | Hours from creation to first review |

### issues (from github-to-csv.py --issues)

| Column | Type | Description |
|--------|------|-------------|
| issue_number | INTEGER | Issue number |
| issue_state | VARCHAR | OPEN, CLOSED |
| issue_author | VARCHAR | GitHub login |
| issue_created_at | VARCHAR | ISO timestamp |
| issue_closed_at | VARCHAR | ISO timestamp |
| issue_comment_count | INTEGER | Comment count |
| issue_labels | VARCHAR | JSON array of label names |
| issue_time_to_close_hours | VARCHAR | Hours from creation to close |

## Example Queries

### Top contributors by commits
```sql
SELECT author_name, COUNT(*) AS commits,
       SUM(insertions) AS lines_added, SUM(deletions) AS lines_deleted
FROM commits
GROUP BY author_name
ORDER BY commits DESC
LIMIT 15
```

### Commit velocity by month
```sql
SELECT strftime(author_ts, '%Y-%m') AS month,
       COUNT(*) AS commits,
       COUNT(DISTINCT author_name) AS authors
FROM commits
GROUP BY month
ORDER BY month
```

### Bus factor (contributors covering 80% of recent work)
```sql
WITH recent AS (
    SELECT author_name, COUNT(*) AS commits
    FROM commits WHERE author_ts >= NOW() - INTERVAL '6 months'
    GROUP BY author_name ORDER BY commits DESC
),
cumul AS (
    SELECT *, SUM(commits) OVER (ORDER BY commits DESC) AS running,
           (SELECT SUM(commits) FROM recent) AS total
    FROM recent
)
SELECT COUNT(*) AS bus_factor FROM cumul WHERE running - commits < total * 0.8
```

### Language breakdown (parse JSON)
```sql
SELECT key AS language, SUM(CAST(value->>'ins' AS INT)) AS insertions
FROM commits,
LATERAL (SELECT UNNEST(from_json(lang_stats, '{"a":{"ins":0,"dels":0}}')) )
WHERE lang_stats IS NOT NULL AND lang_stats != '{}'
GROUP BY language ORDER BY insertions DESC
```

### PR review culture
```sql
SELECT
    MEDIAN(CAST(pr_time_to_merge_hours AS DOUBLE)) AS median_merge_h,
    AVG(CAST(pr_first_review_hours AS DOUBLE)) AS avg_first_review_h,
    COUNT(*) AS total_prs,
    COUNT(*) FILTER (WHERE pr_state = 'MERGED') AS merged
FROM prs
WHERE pr_time_to_merge_hours != '' AND pr_time_to_merge_hours IS NOT NULL
```

### Security-related commits
```sql
SELECT commit_hash[:12] AS hash, author_name, author_ts::DATE, subject
FROM commits
WHERE LOWER(subject) SIMILAR TO '%(secur|cve|vuln|xss|inject|exploit)%'
ORDER BY author_ts DESC
```

### Commit activity heatmap (day of week x hour)
```sql
SELECT
    dayname(author_ts) AS day,
    EXTRACT(HOUR FROM author_ts) AS hour_utc,
    COUNT(*) AS commits
FROM commits
GROUP BY day, hour_utc
ORDER BY CASE day
    WHEN 'Monday' THEN 1 WHEN 'Tuesday' THEN 2 WHEN 'Wednesday' THEN 3
    WHEN 'Thursday' THEN 4 WHEN 'Friday' THEN 5 WHEN 'Saturday' THEN 6
    ELSE 7 END, hour_utc
```

### Author deep dive (hiring eval)
```sql
SELECT
    author_name, author_email,
    COUNT(*) AS commits,
    SUM(insertions) AS lines_added,
    MIN(author_ts)::DATE AS first_commit,
    MAX(author_ts)::DATE AS last_commit,
    COUNT(DISTINCT strftime(author_ts, '%Y-%m')) AS active_months
FROM commits
WHERE LOWER(author_name) LIKE '%alice%'
GROUP BY author_name, author_email
```

## DuckDB Tips

- `read_csv_auto()` handles CSVs natively — no pandas needed
- Use `TRY_CAST` for dates that might be malformed
- JSON columns: use `->>'key'` for string access, `from_json()` + `UNNEST` for iteration
- `FILTER (WHERE ...)` works on aggregates — cleaner than CASE WHEN
- `MEDIAN()` is a built-in aggregate
- `strftime(ts, '%Y-%m')` for grouping by month

## Common Pitfalls

- **Always check if CSV exists** before creating the view
- **is_merge is a string** ('True'/'False'), not boolean — filter with `is_merge = 'True'`
- **lang_stats/dir_stats are JSON strings** — use DuckDB JSON functions to parse
- **Timestamps**: Use the `author_ts`/`commit_ts` computed columns (already cast) rather than raw string columns
- **Large repos**: DuckDB handles millions of rows easily, no need to sample
