---
name: repo-trust-assessment
allowed-tools: Bash Read Glob Grep Write Task
description: |
  Assess trust and analyze any code repository. This is the top-level RepoVet
  skill. Use whenever someone shares a GitHub URL or mentions a repo and wants
  to understand it: "Should I trust this repo?", "Tell me about this repo",
  "What is this repo?", "Analyze this repo", "Who built this?", "Is this
  maintained?", "Is this safe to clone?", "Review this repo", "Repo overview",
  "Due diligence", "Supply chain check", "Dependency trust check",
  "Show me the heatmap", "Visualize this repo", "Show activity".
  Trigger whenever the user shares a GitHub URL and wants to understand it.
  After deep dive, ALWAYS offer to show the visual display (heatmap, charts).
  Do NOT use for writing code or non-repo-related tasks.
---

# RepoVet: Repository Trust Assessment

Two-phase trust assessment: quick scan first (no clone), deep dive on request.

## When to Use

- Someone shares a GitHub URL and wants to know about it
- Evaluating a dependency, library, or tool before adoption
- Security review before cloning or opening in an AI coding agent
- Hiring evaluation of a candidate's repository

## Phase 1: Quick Scan (No Clone)

**Always start here.** Uses `repovet.py` to scan via GitHub API without cloning.
This is fast (~10 seconds) and safe (nothing is executed locally).

```bash
.venv/bin/python scripts/repovet.py scan <owner/repo-or-url>
```

This produces:
- Trust score (0-10)
- Repo metadata (stars, forks, age, last push, contributors)
- Config file detection (found .claude/, .cursorrules, etc. via API tree)
- Threat findings (auto-execution, network exfil, credential access, etc.)
- Health signals (staleness, bus factor, activity)
- Recommendation (Trustworthy / Caution / Do Not Trust)

**Present the quick scan results to the user.** Then:

### Decision Point

Based on quick scan results, offer the user a choice:

- **Score 8-10, no threats**: "Looks clean. Want me to clone and do a full analytics deep dive?"
- **Score 5-7, minor concerns**: "Some concerns found. Want me to clone and investigate further before you use it?"
- **Score 0-4, serious threats**: "Significant risks detected. I recommend NOT cloning this. Want me to do a deeper remote analysis of the specific threats?"
- **User asks "tell me more" / "analyze contributors" / etc.**: Proceed to Phase 2.

**Do NOT automatically proceed to Phase 2.** Let the user decide.

## Phase 2: Deep Dive (Clone + Full Analysis)

Only proceed here if the user asks for more detail.

**CRITICAL RULES — READ BEFORE DOING ANYTHING:**
- **NEVER clone to /tmp/**. Clone to `/home/shapor/.repovet/cache/github.com/OWNER/REPO/repo/`
- **NEVER `rm -rf` any clone.** Clones are cached and reused.
- **NEVER re-extract data that already exists.** Check with `ls` first.
- **NEVER use shell variables like $CACHE or $REPO_PATH** — they trigger permission prompts. Use literal paths in every command.
- **Run each command separately** — do NOT chain with `&&` or use `if` blocks.

### Step 1: Create cache directory

Replace OWNER/REPO with actual values (e.g. `shapor/helpful-dev-utils`):

```bash
mkdir -p /home/shapor/.repovet/cache/github.com/OWNER/REPO
```

### Step 2: Clone (or skip if exists)

First check if already cloned:
```bash
ls /home/shapor/.repovet/cache/github.com/OWNER/REPO/repo/.git 2>/dev/null
```

If that shows `.git` exists, skip cloning. Otherwise clone:
```bash
gh repo clone OWNER/REPO /home/shapor/.repovet/cache/github.com/OWNER/REPO/repo
```

### Step 3: Extract data (skip if cached)

Check what's already cached:
```bash
ls /home/shapor/.repovet/cache/github.com/OWNER/REPO/
```

Only run extraction for files that DON'T already exist:

```bash
.venv/bin/python scripts/git-history-to-csv.py /home/shapor/.repovet/cache/github.com/OWNER/REPO/repo -o /home/shapor/.repovet/cache/github.com/OWNER/REPO/commits.csv
```

```bash
.venv/bin/python scripts/repovet-config-discover.py /home/shapor/.repovet/cache/github.com/OWNER/REPO/repo -o /home/shapor/.repovet/cache/github.com/OWNER/REPO/discovery.json
```

```bash
.venv/bin/python scripts/github-to-csv.py /home/shapor/.repovet/cache/github.com/OWNER/REPO/repo --prs -o /home/shapor/.repovet/cache/github.com/OWNER/REPO/prs.csv
```

```bash
.venv/bin/python scripts/github-to-csv.py /home/shapor/.repovet/cache/github.com/OWNER/REPO/repo --issues -o /home/shapor/.repovet/cache/github.com/OWNER/REPO/issues.csv
```

### Step 2: Run Analytics

Use DuckDB directly on the CSVs. Run queries based on what the user wants to know:

**Contributor analysis:**
```bash
scripts/repovet-query --markdown "
SELECT author_name, COUNT(*) as commits, SUM(insertions) as lines_added
FROM '/home/shapor/.repovet/cache/github.com/OWNER/REPO/commits.csv'
GROUP BY 1 ORDER BY 2 DESC LIMIT 15"
```

**Monthly velocity:**
```bash
scripts/repovet-query --markdown "
SELECT strftime(author_date::TIMESTAMPTZ, '%Y-%m') AS month,
       COUNT(*) AS commits, COUNT(DISTINCT author_name) AS authors
FROM '/home/shapor/.repovet/cache/github.com/OWNER/REPO/commits.csv' GROUP BY 1 ORDER BY 1"
```

**Bus factor:**
```bash
scripts/repovet-query --markdown "
WITH recent AS (
    SELECT author_name, COUNT(*) AS c FROM '/home/shapor/.repovet/cache/github.com/OWNER/REPO/commits.csv'
    WHERE author_date::TIMESTAMPTZ >= NOW() - INTERVAL '6 months'
    GROUP BY 1 ORDER BY c DESC
),
cumul AS (
    SELECT *, SUM(c) OVER (ORDER BY c DESC) AS running,
           (SELECT SUM(c) FROM recent) AS total FROM recent
)
SELECT author_name, c as commits FROM cumul WHERE running - c < total * 0.8"
```

**ALWAYS run the visual display after extracting data — this is the showpiece.**
**Tell the user to press ctrl+o to expand the output — it will be collapsed by default.**

```bash
.venv/bin/python scripts/repovet-display.py "/home/shapor/.repovet/cache/github.com/OWNER/REPO/commits.csv"
```

This produces a GitHub-style contribution heatmap, colored contributor bar charts,
language breakdown, velocity sparklines, and activity heatmap — all in the terminal.
Run this FIRST before any custom queries. It gives the user an instant visual overview.

After running it, tell the user: "Press ctrl+o on the output above to see the full
visual display with contribution heatmap, charts, and sparklines."

**Full markdown report (alternative):**
```bash
.venv/bin/python scripts/repovet-analyze.py "/home/shapor/.repovet/cache/github.com/OWNER/REPO/commits.csv"
```

**For ALL follow-up data questions (language breakdown, author stats, LOC, etc.)
use the `duckdb` CLI directly. NEVER write Python to parse CSVs.**

```bash
# Example: language breakdown for a specific author
scripts/repovet-query --markdown "
SELECT key AS language, SUM(CAST(value->>'ins' AS INT)) AS lines_added
FROM read_csv_auto('/home/shapor/.repovet/cache/github.com/OWNER/REPO/commits.csv'),
LATERAL (SELECT UNNEST(from_json(lang_stats, '{\"a\":{\"ins\":0,\"dels\":0}}')) )
WHERE author_name = 'AuthorName' AND lang_stats != '{}'
GROUP BY 1 ORDER BY 2 DESC"
```

See the `git-analytics-sql` skill for full schema and more example queries.

### Step 3: Threat Deep Dive (if needed)

If the quick scan flagged threats, run detailed analysis on discovery.json.
Launch threat analysis skills in parallel as Task agents:

- `threat-auto-execution` — examine hooks line by line
- `threat-network-exfil` — trace where data goes
- `threat-credential-access` — identify what secrets are accessed
- `threat-obfuscation` — decode any encoded payloads
- `threat-prompt-injection` — analyze instruction override patterns

Each reads `/home/shapor/.repovet/cache/github.com/OWNER/REPO/discovery.json` and produces detailed findings with
file paths, line numbers, and explanations.

### Step 4: Final Report

Synthesize all findings into a trust report:

```markdown
# RepoVet Trust Report: <repo-name>

**Trust Score**: X/10 — <Recommendation>

## Quick Scan Summary
<results from Phase 1>

## Deep Dive Findings

### Contributors
<top contributors, bus factor, patterns>

### Activity
<velocity, staleness, trends>

### Security
<threat findings, config analysis>

## Recommendations
<numbered actionable steps>
```

Write to `/home/shapor/.repovet/cache/github.com/OWNER/REPO/trust-report.md` and present key findings to the user.

## Trust Score

**Three pillars** (each 0-10):
- **Project Health**: contributors, velocity, bus factor, maintenance
- **Code Security**: CVE history, security commits, secrets
- **Config Safety**: agent config threats (hooks, exfil, injection)

**Formula** (config threats dominate when serious):
```
If config_safety < 5:  trust = 0.2*health + 0.2*security + 0.6*config_safety
Else:                  trust = 0.4*health + 0.3*security + 0.3*config_safety
```

| Score | Recommendation |
|-------|---------------|
| 8-10  | Trustworthy |
| 5-7   | Use with caution |
| 0-4   | Do not trust |

## Cache Layout

Everything for a repo lives in one place:

```
/home/shapor/.repovet/cache/github.com/<owner>/<repo>/
├── repo/              ← persistent clone (NEVER delete)
├── commits.csv        ← extracted once, reused
├── prs.csv            ← extracted once, reused
├── issues.csv         ← extracted once, reused
├── discovery.json     ← re-run each time (fast, catches changes)
└── trust-report.md    ← generated report
```

**Rules:**
- Clone lives in `/home/shapor/.repovet/cache/github.com/OWNER/REPO/repo/`, NOT `/tmp/`. Never delete it.
- Before extracting, check if the file exists. Skip if cached.
- Re-running on same repo is fast because data is cached.
- User can `rm /home/shapor/.repovet/cache/github.com/owner/repo/*.csv` to force refresh.

## Common Pitfalls

- **Always start with Phase 1** (quick scan). Never clone first.
- **Never auto-proceed to Phase 2**. Let the user decide.
- **Never execute discovered code**. Read and analyze only.
- **Never delete the clone** (`/home/shapor/.repovet/cache/github.com/OWNER/REPO/repo/`). User may want it later.
- **Never re-extract if cached**. Check `[ -f "/home/shapor/.repovet/cache/github.com/OWNER/REPO/commits.csv" ]` first.
- **Never clone to /tmp/**. Always clone to `/home/shapor/.repovet/cache/github.com/OWNER/REPO/repo/`.
- **Use DuckDB CLI directly** for queries, not Python wrappers.
- **Watch for nested configs** — `is_nested: true` in discovery.json signals hidden intent.
