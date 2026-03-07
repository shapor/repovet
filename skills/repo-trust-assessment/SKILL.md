---
name: repo-trust-assessment
allowed-tools: Bash Read Glob Grep Write Task
description: |
  Assess trust and analyze any code repository. This is the top-level RepoVet
  skill. Use whenever someone shares a GitHub URL or mentions a repo and wants
  to understand it: "Should I trust this repo?", "Tell me about this repo",
  "What is this repo?", "Analyze this repo", "Who built this?", "Is this
  maintained?", "Is this safe to clone?", "Review this repo", "Repo overview",
  "Due diligence", "Supply chain check", "Dependency trust check".
  Trigger whenever the user shares a GitHub URL and wants to understand it.
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

Only proceed here if the user asks for more detail. This clones the repo and
runs full analytics with DuckDB.

### Step 1: Clone and Extract

```bash
# Clone
gh repo clone <owner/repo> /tmp/repovet-<repo-name>
REPO_PATH=/tmp/repovet-<repo-name>
CACHE=~/.repovet/cache/github.com/<owner>/<repo>
mkdir -p "$CACHE"

# Extract git history (fast, ~10s)
.venv/bin/python scripts/git-history-to-csv.py "$REPO_PATH" -o "$CACHE/commits.csv"

# Extract config files (fast, ~5s)
.venv/bin/python scripts/repovet-config-discover.py "$REPO_PATH" -o "$CACHE/discovery.json"

# Extract GitHub PRs and issues (slower, run in background)
.venv/bin/python scripts/github-to-csv.py "$REPO_PATH" --prs --issues -o "$CACHE/github.csv" &
```

### Step 2: Run Analytics

Use DuckDB directly on the CSVs. Run queries based on what the user wants to know:

**Contributor analysis:**
```bash
duckdb -markdown -c "
SELECT author_name, COUNT(*) as commits, SUM(insertions) as lines_added
FROM '$CACHE/commits.csv'
GROUP BY 1 ORDER BY 2 DESC LIMIT 15"
```

**Monthly velocity:**
```bash
duckdb -markdown -c "
SELECT strftime(author_date::TIMESTAMPTZ, '%Y-%m') AS month,
       COUNT(*) AS commits, COUNT(DISTINCT author_name) AS authors
FROM '$CACHE/commits.csv' GROUP BY 1 ORDER BY 1"
```

**Bus factor:**
```bash
duckdb -markdown -c "
WITH recent AS (
    SELECT author_name, COUNT(*) AS c FROM '$CACHE/commits.csv'
    WHERE author_date::TIMESTAMPTZ >= NOW() - INTERVAL '6 months'
    GROUP BY 1 ORDER BY c DESC
),
cumul AS (
    SELECT *, SUM(c) OVER (ORDER BY c DESC) AS running,
           (SELECT SUM(c) FROM recent) AS total FROM recent
)
SELECT author_name, c as commits FROM cumul WHERE running - c < total * 0.8"
```

**Rich visual display (heatmap, charts, sparklines):**
```bash
.venv/bin/python scripts/repovet-display.py "$CACHE/commits.csv"
```

**Full markdown report:**
```bash
.venv/bin/python scripts/repovet-analyze.py "$CACHE/commits.csv"
```

For any question about the repo data, write a DuckDB SQL query. See the
`git-analytics-sql` skill for schema details and example queries.

### Step 3: Threat Deep Dive (if needed)

If the quick scan flagged threats, run detailed analysis on discovery.json.
Launch threat analysis skills in parallel as Task agents:

- `threat-auto-execution` — examine hooks line by line
- `threat-network-exfil` — trace where data goes
- `threat-credential-access` — identify what secrets are accessed
- `threat-obfuscation` — decode any encoded payloads
- `threat-prompt-injection` — analyze instruction override patterns

Each reads `$CACHE/discovery.json` and produces detailed findings with
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

Write to `$CACHE/trust-report.md` and present key findings to the user.

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

## Common Pitfalls

- **Always start with Phase 1** (quick scan). Never clone first.
- **Never auto-proceed to Phase 2**. Let the user decide.
- **Never execute discovered code**. Read and analyze only.
- **Use DuckDB CLI directly** for queries, not Python wrappers.
- **Watch for nested configs** — `is_nested: true` in discovery.json signals hidden intent.
