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

Query git/GitHub data with SQL using DuckDB CLI. No Python needed — just SQL.

## When to Use

- User asks questions about repo history, contributors, activity, languages
- User wants to slice/filter/aggregate git data
- User wants a custom analysis not covered by canned reports
- User asks about PR review culture, issue health, contributor patterns

## Step 1: Extract Data

Run the extraction scripts to produce CSV files:

```bash
# Git commit history → commits.csv
python scripts/git-history-to-csv.py /path/to/repo -o commits.csv

# GitHub PRs and issues (optional, requires gh CLI)
python scripts/github-to-csv.py /path/to/repo --prs --issues -o github.csv
# Produces: github_prs.csv and github_issues.csv
```

## Step 2: Query with DuckDB

Use the `duckdb` CLI directly on the CSV files. DuckDB reads CSVs natively — just reference the filename in SQL:

```bash
duckdb -c "SELECT author_name, COUNT(*) as commits FROM 'commits.csv' GROUP BY 1 ORDER BY 2 DESC LIMIT 10"
```

### Output Formats

```bash
# Default: box table
duckdb -c "QUERY"

# Markdown table
duckdb -markdown -c "QUERY"

# CSV output
duckdb -csv -c "QUERY"

# JSON output
duckdb -json -c "QUERY"
```

### Multi-line Queries

For complex queries, use heredoc:

```bash
duckdb -markdown <<'SQL'
SELECT author_name, COUNT(*) as commits, SUM(insertions) as lines_added
FROM 'commits.csv'
GROUP BY 1
ORDER BY 2 DESC
LIMIT 10;
SQL
```

## Step 3: Visual Report (optional)

For a full visual report with GitHub-style heatmap, colored bar charts, and sparklines:

```bash
python scripts/repovet-display.py commits.csv
```

For a markdown report with health score:

```bash
python scripts/repovet-analyze.py commits.csv
```

## Available Columns

### commits.csv

| Column | Type | Notes |
|--------|------|-------|
| repo_name | VARCHAR | Repository name |
| commit_hash | VARCHAR | Full SHA |
| author_name | VARCHAR | Author display name |
| author_email | VARCHAR | Author email |
| author_date | TIMESTAMP | ISO format, DuckDB auto-parses |
| committer_name | VARCHAR | Committer name |
| committer_email | VARCHAR | Committer email |
| commit_date | TIMESTAMP | ISO format |
| subject | VARCHAR | Commit message first line |
| body | VARCHAR | Commit message body |
| is_merge | VARCHAR | 'True' or 'False' (string, not boolean) |
| files_changed | INTEGER | Number of files changed |
| insertions | INTEGER | Lines added |
| deletions | INTEGER | Lines removed |
| changed_files | JSON | Array of filenames |
| lang_stats | JSON | `{"Python": {"ins": 100, "dels": 20}}` |
| dir_stats | JSON | `{"src": {"ins": 100, "dels": 20}}` |

### prs.csv (from github-to-csv.py --prs)

| Column | Type | Notes |
|--------|------|-------|
| pr_number | INTEGER | PR number |
| pr_state | VARCHAR | OPEN, MERGED, CLOSED |
| pr_author | VARCHAR | GitHub login |
| pr_created_at | TIMESTAMP | Creation time |
| pr_merged_at | TIMESTAMP | Merge time (null if not merged) |
| pr_additions | INTEGER | Lines added |
| pr_deletions | INTEGER | Lines removed |
| pr_comment_count | INTEGER | Human comments |
| pr_bot_comment_count | INTEGER | Bot comments |
| pr_reviewers | JSON | `{"alice": "APPROVED"}` |
| pr_time_to_merge_hours | FLOAT | Hours from creation to merge |
| pr_first_review_hours | FLOAT | Hours to first review |

### issues.csv (from github-to-csv.py --issues)

| Column | Type | Notes |
|--------|------|-------|
| issue_number | INTEGER | Issue number |
| issue_state | VARCHAR | OPEN, CLOSED |
| issue_author | VARCHAR | GitHub login |
| issue_created_at | TIMESTAMP | Creation time |
| issue_closed_at | TIMESTAMP | Close time |
| issue_comment_count | INTEGER | Comment count |
| issue_labels | JSON | Array of label names |
| issue_time_to_close_hours | FLOAT | Hours to close |

## Example Queries

### Top contributors
```bash
duckdb -markdown -c "
SELECT author_name, COUNT(*) AS commits,
       SUM(insertions) AS lines_added, SUM(deletions) AS lines_deleted
FROM 'commits.csv' GROUP BY 1 ORDER BY 2 DESC LIMIT 15"
```

### Monthly velocity
```bash
duckdb -markdown -c "
SELECT strftime(author_date::TIMESTAMPTZ, '%Y-%m') AS month,
       COUNT(*) AS commits, COUNT(DISTINCT author_name) AS authors
FROM 'commits.csv' GROUP BY 1 ORDER BY 1"
```

### Bus factor (who owns 80% of recent work)
```bash
duckdb -markdown <<'SQL'
WITH recent AS (
    SELECT author_name, COUNT(*) AS c FROM 'commits.csv'
    WHERE author_date::TIMESTAMPTZ >= NOW() - INTERVAL '6 months'
    GROUP BY 1 ORDER BY c DESC
),
cumul AS (
    SELECT *, SUM(c) OVER (ORDER BY c DESC) AS running,
           (SELECT SUM(c) FROM recent) AS total FROM recent
)
SELECT author_name, c AS commits FROM cumul WHERE running - c < total * 0.8;
SQL
```

### Language breakdown
```bash
duckdb -markdown -c "
SELECT key AS language, SUM(CAST(value->>'ins' AS INT)) AS insertions
FROM (SELECT UNNEST(from_json(lang_stats, '{\"a\":{\"ins\":0,\"dels\":0}}')) FROM 'commits.csv'
      WHERE lang_stats IS NOT NULL AND lang_stats != '{}')
GROUP BY 1 ORDER BY 2 DESC"
```

### PR review speed
```bash
duckdb -markdown -c "
SELECT MEDIAN(pr_time_to_merge_hours::DOUBLE) AS median_merge_h,
       AVG(pr_first_review_hours::DOUBLE) AS avg_first_review_h,
       COUNT(*) FILTER (WHERE pr_state = 'MERGED') AS merged_prs
FROM 'prs.csv'
WHERE pr_time_to_merge_hours != ''"
```

### Security-related commits
```bash
duckdb -markdown -c "
SELECT commit_hash[:12] AS hash, author_name, author_date::DATE AS date, subject
FROM 'commits.csv'
WHERE LOWER(subject) SIMILAR TO '%(secur|cve|vuln|xss|inject|exploit)%'
ORDER BY author_date DESC"
```

### Author deep dive (hiring eval)
```bash
duckdb -markdown -c "
SELECT author_name, COUNT(*) AS commits, SUM(insertions) AS added,
       MIN(author_date)::DATE AS first, MAX(author_date)::DATE AS last
FROM 'commits.csv' WHERE LOWER(author_name) LIKE '%alice%'
GROUP BY 1"
```

### Commit heatmap (day x hour)
```bash
duckdb -markdown -c "
SELECT dayname(author_date::TIMESTAMPTZ) AS day,
       EXTRACT(HOUR FROM author_date::TIMESTAMPTZ) AS hour_utc,
       COUNT(*) AS commits
FROM 'commits.csv'
GROUP BY 1, 2 ORDER BY
  CASE day WHEN 'Monday' THEN 1 WHEN 'Tuesday' THEN 2 WHEN 'Wednesday' THEN 3
  WHEN 'Thursday' THEN 4 WHEN 'Friday' THEN 5 WHEN 'Saturday' THEN 6 ELSE 7 END, 2"
```

## DuckDB Tips

- DuckDB auto-reads CSV files: just use `'file.csv'` as a table name
- Cast dates inline: `author_date::TIMESTAMPTZ`
- `FILTER (WHERE ...)` on aggregates is cleaner than CASE WHEN
- `MEDIAN()` is built-in
- JSON: `->>'key'` for strings, `from_json()` + `UNNEST` for iteration
- `strftime(ts, '%Y-%m')` for month grouping
- `-markdown` flag gives markdown tables (great for piping to docs)
- `is_merge` is a string ('True'/'False'), not boolean

## Common Pitfalls

- Always run data extraction before querying
- DuckDB snap can't read `/tmp/` — use local paths
- For large repos, DuckDB handles millions of rows — no sampling needed
