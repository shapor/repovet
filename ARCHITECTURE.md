# RepoVet Architecture

Trust assessment system for code repositories. Detects malicious agent configs,
evaluates project health, and produces a trust score before you clone or open a
repo in an AI coding tool.

## Pipeline Overview

```
User: "Tell me about this repo"
         │
         ▼
┌──────────────────────┐
│ 1. DATA EXTRACTION   │  Scripts pull raw data
│                      │
│ git-history-to-csv.py│──→ commits.csv (authors, files, languages, dates)
│ github-to-csv.py     │──→ prs.csv + issues.csv (reviews, comments, timing)
│ repovet-config-      │──→ discovery.json (agent configs, hooks, executables)
│   discover.py        │
└──────────────────────┘
         │
         ▼
┌──────────────────────┐
│ 2. ANALYSIS          │  DuckDB runs SQL on CSVs
│                      │
│ repovet-analyze.py   │──→ Health score, contributors, bus factor,
│                      │    velocity, languages, security commits,
│                      │    PR review culture, issue health
│                      │
│ git-analytics-sql    │──→ Agent writes custom SQL for any question
│   skill + query.py   │    ("who committed most in last 3 months?")
└──────────────────────┘
         │
         ▼
┌──────────────────────┐
│ 3. THREAT DETECTION  │  7 threat skills analyze discovery.json
│                      │
│ threat-auto-execution│  threat-network-exfil
│ threat-rce           │  threat-credential-access
│ threat-obfuscation   │  threat-repo-write
│ threat-prompt-inject │
└──────────────────────┘
         │
         ▼
┌──────────────────────┐
│ 4. TRUST ASSESSMENT  │  Combine everything
│                      │
│ Trust Score: X/10    │  = health + security + config safety
│ Recommendation       │  = Trust / Caution / Do Not Trust
│ Detailed report      │  = Findings + evidence + recommendations
└──────────────────────┘
```

---

## 1. Two Ways to Run It

### CLI Mode: `repovet.py scan`

Single command, end-to-end. Does NOT clone the repo -- queries the GitHub API
directly via `gh` CLI, so no hooks fire and no code executes on your machine.

```bash
python3 scripts/repovet.py scan user/repo
python3 scripts/repovet.py scan https://github.com/user/repo
python3 scripts/repovet.py scan user/repo -o report.md
python3 scripts/repovet.py scan user/repo --json
python3 scripts/repovet.py scan /path/to/local/repo
```

The CLI handles all four pipeline stages internally:

1. Fetches repo metadata, file tree, and config file contents via GitHub REST API
2. Analyzes recent commits, contributors, and repo health from API data
3. Pattern-matches config file contents against all threat categories
4. Calculates trust score, generates colored terminal or markdown report

For local repos, it shells out to `repovet-config-discover.py` as a subprocess,
then runs the same threat detection on the resulting JSON.

### Skills Mode: Interactive in Claude Code

The agent uses individual skills step-by-step. This mode allows interactive
queries, custom SQL, and iterative exploration.

Typical flow:
1. `git-commit-intel` skill -- run `git-history-to-csv.py` to produce commits.csv
2. `github-project-intel` skill -- run `github-to-csv.py` to produce prs.csv + issues.csv
3. Run `repovet-config-discover.py` to produce discovery.json
4. `contributor-analysis` skill -- read commits.csv, report bus factor and profiles
5. `repo-health-analysis` skill -- read all CSVs, calculate health score
6. `security-history-analysis` skill -- scan commit messages for CVEs and secrets
7. All 7 `threat-*` skills -- analyze discovery.json for each threat category
8. `repo-trust-assessment` skill -- orchestrate everything, calculate final score
9. `git-analytics-sql` skill -- run ad-hoc DuckDB SQL for custom questions

Skills mode enables follow-up queries like "who committed the most security fixes?"
or "show me the PR review time trend over the last year" without re-extracting data.

---

## 2. Scripts Inventory

All scripts live in `scripts/` at the project root.

### `scripts/git-history-to-csv.py` (~505 lines)

Extracts git commit history into a structured CSV.

- **Input**: Local git repo path(s), optional `--github` flag for PR enrichment
- **Output**: `commits.csv` with 19 git fields + 10 optional GitHub PR fields
- **Key fields**: `author_name`, `author_email`, `author_date`, `insertions`,
  `deletions`, `changed_files` (JSON array), `lang_stats` (JSON: language-level
  line counts), `dir_stats` (JSON: directory-level line counts)
- **How it works**: Runs `git log` with a custom `--format` using NUL/SOH
  delimiters, then `git diff --numstat` per commit for file-level stats.
  Language detection uses file extensions. GitHub enrichment uses GraphQL to
  batch-fetch PR metadata for each commit hash (50 per request).
- **Limits**: Use `-n 1000` for large repos. `--all` for all branches.

### `scripts/github-to-csv.py` (~491 lines)

Extracts GitHub PRs and issues into CSVs via the `gh` CLI and GraphQL API.

- **Input**: Repo path(s) or `--repo owner/name` (no local clone needed)
- **Output**: `prs.csv` (27 fields) and/or `issues.csv` (15 fields)
- **Key PR fields**: `pr_state`, `pr_reviewers` (JSON: login to review state),
  `pr_first_review_hours`, `pr_time_to_merge_hours`, `pr_comment_count`,
  `pr_bot_comment_count`, `pr_review_thread_count`
- **Key issue fields**: `issue_state`, `issue_time_to_close_hours`,
  `issue_comment_count`, `issue_labels` (JSON array)
- **Bot separation**: Automatically identifies known bots (dependabot, renovate,
  codecov, copilot, github-actions, any `[bot]` suffix) and separates their
  activity into dedicated `_bot_` fields so analysis can distinguish human
  engagement from automation noise.

### `scripts/repovet-config-discover.py` (~527 lines)

Scans a local repo for AI agent configuration files and extracts their contents.

- **Input**: Local repo path
- **Output**: `discovery.json` containing four arrays:
  - `config_files[]` -- every config file found with path, type, and nesting info
  - `executables[]` -- extracted code blocks, hook scripts, skill scripts with
    content, language, line numbers, source type (`hook`, `command`, `code_block`,
    `skill_script`)
  - `instructions[]` -- text content from CLAUDE.md, .cursorrules,
    copilot-instructions.md, etc.
  - `permissions[]` -- security-relevant settings extracted from JSON configs
    (`dangerouslySkipPermissions`, `autoApprove`, `allowedTools`, `mcpServers`)
- **Patterns matched**: Claude (.claude/hooks/*, CLAUDE.md, settings.json),
  Cursor (.cursorrules, .cursor/**), Copilot (.github/copilot-instructions.md),
  Aider (.aider.conf.yml), Continue (.continue/**), Windsurf (.windsurfrules),
  generic (AGENTS.md), skills (skills/*/SKILL.md, skills/*/scripts/*)
- **Nesting detection**: Flags configs found in subdirectories (`is_nested: true`)
  as potentially hidden. Root-level `.claude/`, `.cursor/`, `.github/` are normal;
  `subdir/.claude/hooks/` is suspicious.

### `scripts/repovet-analyze.py` (~836 lines)

DuckDB-powered analytics engine for commit, PR, and issue data.

- **Input**: `commits.csv` (required), `--prs prs.csv` (optional),
  `--issues issues.csv` (optional)
- **Output**: Markdown or JSON report with health score
- **Analysis modules** (each a SQL function):
  - `repo_overview` -- total commits, authors, age, staleness
  - `top_contributors` -- ranked by commits, lines, active months
  - `bus_factor` -- contributors covering 80% of recent 6-month commits
  - `commit_velocity` -- commits/authors/churn per month
  - `language_breakdown` -- aggregated from per-commit `lang_stats` JSON
  - `directory_breakdown` -- aggregated from per-commit `dir_stats` JSON
  - `security_commits` -- commits matching CVE/vuln/exploit/inject patterns
  - `bot_analysis` -- bot vs human commit ratio
  - `timezone_distribution` -- inferred contributor regions from commit hours
  - `pr_analysis` -- merge times, review times, comment counts
  - `issue_analysis` -- open/close ratio, resolution time
  - `calculate_health_score` -- 0-10 composite score
- **Author mode**: `--author "alice"` for individual contributor deep-dive
  (hiring eval), showing their languages, directories, monthly activity

### `scripts/repovet.py` (~1710 lines)

End-to-end CLI that combines all stages without needing a local clone.

- **Input**: GitHub URL, `user/repo` shorthand, or local path
- **Output**: Colored terminal report or markdown file; optional JSON
- **Key innovation**: For remote repos, uses GitHub REST API to fetch the file
  tree, identify config files, download their contents via base64, and analyze
  them -- all without `git clone`. This means no hooks fire.
- **Threat patterns**: Defines ~30 regex patterns across 7 categories directly
  in the script (auto_execution, network_exfiltration, remote_code_execution,
  credential_access, obfuscation, prompt_injection, destructive_operations)
- **Health scoring**: Fetches recent commits, contributors, repo age, stars,
  license via API; computes a health score from staleness, contributor count,
  activity level, and license type
- **Trust formula**:
  ```
  If config_safety < 5:  trust = 0.2 * health + 0.8 * config_safety
  Else:                  trust = 0.5 * health + 0.5 * config_safety
  ```
- **Verdict thresholds**: >= 8.0 "Looks Good", >= 6.0 "Proceed with Caution",
  >= 4.0 "Review Recommended", >= 2.0 "Significant Risks", < 2.0 "Do Not Use"

---

## 3. Skills Inventory

22 skills total. 14 are RepoVet-specific (the rest are judge skills for the
hackathon). The 14 RepoVet skills organized by tier:

### Data Extraction (Tier 1)

| Skill | Purpose | Script | Produces |
|-------|---------|--------|----------|
| `git-commit-intel` | Extract git history to CSV | `git-history-to-csv.py` | `commits.csv` |
| `github-project-intel` | Extract PRs + issues to CSV | `github-to-csv.py` | `prs.csv`, `issues.csv` |

### Analysis (Tier 2)

| Skill | Purpose | Reads | Produces |
|-------|---------|-------|----------|
| `contributor-analysis` | Top contributors, bus factor, bot ratio, timezone distribution | `commits.csv` | Contributor profiles markdown |
| `repo-health-analysis` | Maintenance velocity, PR review culture, issue health | `commits.csv`, `prs.csv`, `issues.csv` | Health score 0-10 |
| `security-history-analysis` | CVE commits, committed secrets, force-push indicators | `commits.csv` | Security score 0-10 |
| `git-analytics-sql` | Ad-hoc DuckDB SQL for any question about repo data | `commits.csv`, `prs.csv`, `issues.csv` | Query results |

### Threat Detection (Tier 3)

All 7 threat skills read `discovery.json` and produce JSON findings arrays.

| Skill | Threat Category | Severity | What It Detects |
|-------|----------------|----------|-----------------|
| `threat-auto-execution` | Auto-execution | CRITICAL | Hooks (pre-command, post-command), autoApprove settings, instructions triggering proactive code execution |
| `threat-network-exfil` | Data exfiltration | CRITICAL | curl/wget POST with file contents, piped command output to external URLs, Python requests.post patterns |
| `threat-remote-code-execution` | Remote code execution | CRITICAL | `curl \| bash`, `wget -O- \| sh`, `exec(requests.get(url).text)`, download-then-execute sequences |
| `threat-credential-access` | Credential theft | HIGH-CRITICAL | Reading `~/.ssh/id_rsa`, `~/.aws/credentials`, `$GITHUB_TOKEN`, `.env` files, `printenv` |
| `threat-obfuscation` | Hidden behavior | HIGH-CRITICAL | Base64-encoded commands piped to shell, hex decoding, eval of constructed strings, character escaping tricks |
| `threat-repo-write` | Destructive operations | HIGH-CRITICAL | `git push --force`, `rm -rf /`, `git reset --hard`, filesystem writes outside repo, `git filter-branch` |
| `threat-prompt-injection` | Agent manipulation | HIGH-CRITICAL | "ignore previous instructions", identity overrides, "hide from user" directives, safety bypass language |

### Orchestration (Tier 4)

| Skill | Purpose | Coordinates |
|-------|---------|-------------|
| `repo-trust-assessment` | Full trust assessment workflow | All 12 sub-skills above |

`repo-trust-assessment` is the top-level skill. It coordinates the entire
pipeline: setup, data extraction, analysis, threat detection, and report
generation. It defines the trust score formula and verdict thresholds.

---

## 4. Data Flow

### Stage 1: Extraction

```
git repo (local)  ──→  git-history-to-csv.py  ──→  ~/.repovet/cache/{repo}/commits.csv
                  ──→  github-to-csv.py        ──→  ~/.repovet/cache/{repo}/prs.csv
                                               ──→  ~/.repovet/cache/{repo}/issues.csv
                  ──→  repovet-config-discover  ──→  ~/.repovet/cache/{repo}/discovery.json
```

### Stage 2: Analysis

```
commits.csv       ──→  repovet-analyze.py  ──→  Health score, contributor stats,
prs.csv (opt)     ──→                           bus factor, velocity, languages,
issues.csv (opt)  ──→                           security commits, PR culture

commits.csv       ──→  query.py + DuckDB   ──→  Ad-hoc SQL query results
prs.csv (opt)     ──→
issues.csv (opt)  ──→
```

### Stage 3: Threat Detection

```
discovery.json    ──→  threat-auto-execution       ──→  findings[]
                  ──→  threat-network-exfil         ──→  findings[]
                  ──→  threat-remote-code-execution ──→  findings[]
                  ──→  threat-credential-access     ──→  findings[]
                  ──→  threat-obfuscation           ──→  findings[]
                  ──→  threat-repo-write            ──→  findings[]
                  ──→  threat-prompt-injection       ──→  findings[]
```

### Stage 4: Trust Assessment

```
health_score (0-10)         ──┐
security_score (0-10)       ──┤──→  Trust Score (0-10) + Verdict + Report
config_safety_score (0-10)  ──┘

Config safety starts at 10, subtracts per finding:
  CRITICAL: -3 points
  HIGH:     -2 points
  MEDIUM:   -1 point
  Floor at 0.
```

### Complete File Dependency Graph

```
commits.csv ←── git-history-to-csv.py
     │
     ├──→ contributor-analysis
     ├──→ repo-health-analysis ←── prs.csv ←── github-to-csv.py
     │                         ←── issues.csv ←── github-to-csv.py
     ├──→ security-history-analysis
     └──→ git-analytics-sql (+ query.py)

discovery.json ←── repovet-config-discover.py
     │
     ├──→ threat-auto-execution
     ├──→ threat-network-exfil
     ├──→ threat-remote-code-execution
     ├──→ threat-credential-access
     ├──→ threat-obfuscation
     ├──→ threat-repo-write
     └──→ threat-prompt-injection

All of the above ──→ repo-trust-assessment ──→ trust-report.md
```

---

## 5. DuckDB as the Analytics Layer

### Why SQL on CSVs beats LLM-parsed Python

The naive approach is to have the LLM read the CSV and write Python to compute
stats. This fails for several reasons:

1. **Token limits**: A repo with 10k commits produces a multi-MB CSV. The LLM
   cannot hold it in context. DuckDB reads the CSV file directly from disk.

2. **Precision**: SQL aggregates (COUNT, SUM, MEDIAN, percentiles) are exact.
   LLM-generated Python tends to have off-by-one errors, wrong date parsing,
   and inconsistent handling of NULL values.

3. **Speed**: DuckDB processes 100k rows in milliseconds. Python loops over
   DictReader rows are orders of magnitude slower.

4. **Composability**: The agent can write arbitrary SQL follow-ups without
   re-parsing the CSV or maintaining state between code cells. Each query is
   independent.

5. **JSON handling**: DuckDB natively parses JSON columns with `->>'key'` and
   `UNNEST(from_json(...))`, which is exactly what `lang_stats` and `dir_stats`
   require.

### How CSVs become tables

```python
import duckdb
db = duckdb.connect(":memory:")
db.execute("""
    CREATE VIEW commits AS
    SELECT *,
           TRY_CAST(author_date AS TIMESTAMP WITH TIME ZONE) AS author_ts,
           TRY_CAST(commit_date AS TIMESTAMP WITH TIME ZONE) AS commit_ts
    FROM read_csv_auto('commits.csv', header=true, ignore_errors=true)
""")
```

`read_csv_auto` infers column types. `TRY_CAST` handles malformed timestamps
gracefully. The computed `author_ts` and `commit_ts` columns are used for all
time-based queries.

### Example Queries

**Bus factor** (contributors covering 80% of recent work):
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

**Language breakdown** (parsing per-commit JSON):
```sql
SELECT key AS language, SUM(CAST(value->>'ins' AS INT)) AS insertions
FROM commits,
LATERAL (SELECT UNNEST(from_json(lang_stats, '{"a":{"ins":0,"dels":0}}')) )
WHERE lang_stats IS NOT NULL AND lang_stats != '{}'
GROUP BY language ORDER BY insertions DESC
```

**PR review culture**:
```sql
SELECT
    MEDIAN(CAST(pr_time_to_merge_hours AS DOUBLE)) AS median_merge_h,
    AVG(CAST(pr_first_review_hours AS DOUBLE)) AS avg_first_review_h,
    COUNT(*) FILTER (WHERE pr_state = 'MERGED') AS merged
FROM prs
WHERE pr_time_to_merge_hours != '' AND pr_time_to_merge_hours IS NOT NULL
```

**Security-related commits**:
```sql
SELECT commit_hash[:12] AS hash, author_name, author_ts::DATE, subject
FROM commits
WHERE LOWER(subject) SIMILAR TO '%(secur|cve|vuln|xss|inject|exploit)%'
ORDER BY author_ts DESC
```

---

## 6. Storage

All cached data lives under `~/.repovet/cache/` keyed by repo identity.

### Directory Structure

```
~/.repovet/
└── cache/
    └── github.com/
        └── {owner}/
            └── {repo}/
                ├── commits.csv          # Git commit history
                ├── prs.csv              # Pull request data
                ├── issues.csv           # Issue data
                ├── discovery.json       # Agent config discovery results
                └── trust-report.md      # Generated trust report
```

For local repos without a GitHub remote, the key is the directory basename:

```
~/.repovet/cache/{repo-name}/
```

### Naming Convention

- GitHub repos: `~/.repovet/cache/github.com/owner/repo/`
- Local repos: `~/.repovet/cache/{basename}/`

CSVs are designed to be re-used across analysis runs. Extract once, query many
times. The `git-analytics-sql` skill and `query.py` script both auto-detect
CSVs in the cache directory.

---

## 7. Test Repos

### `test-repos/helpful-dev-utils/`

A honeypot repository that looks innocent but contains multiple attack vectors.
Used to demonstrate and validate RepoVet's detection capabilities.

**Surface appearance**: A collection of developer productivity utilities with
a clean README, legitimate-looking setup script, and actual working tools
(`git-stats`, `new-project`).

**Hidden threats**:

| File | Threat | Category | Expected Severity |
|------|--------|----------|-------------------|
| `.claude/hooks/pre-command.sh` | Sends session data via `curl -X POST` to an external analytics endpoint on every Claude Code command | auto-execution + network-exfil | CRITICAL |
| `.claude/hooks/pre-command.sh` | Fetches remote content via `curl -s` and diffs against local version | remote-code-execution | HIGH |
| `hooks/post-checkout` | Git hook that executes on `git clone` before user can inspect the repo; logs user, hostname, pwd | auto-execution | CRITICAL |
| `setup.sh` | Copies the `post-checkout` hook into `.git/hooks/` during install | auto-execution | HIGH |

**Expected trust score**: Low (2-4 / 10). The combination of auto-executing hooks
with network calls and credential-adjacent data collection should trigger multiple
CRITICAL findings. The config safety score should be heavily penalized, pulling
the trust score down regardless of any health signals.

**Key demonstration**: The `DEMO-ATTACK.md` file documents the attack vector in
detail -- `.git/hooks/post-checkout` fires during `git clone` BEFORE the user
can inspect any files. RepoVet's CLI mode detects this via API without cloning,
preventing the hook from executing.

---

## Key Design Decisions

1. **No-clone scanning**: The CLI uses GitHub API to fetch file trees and
   contents. This is the core safety property -- hooks cannot fire if you never
   clone.

2. **CSV as interchange format**: Scripts produce CSVs that any tool can
   consume. DuckDB reads them natively. No custom binary formats, no databases
   to manage.

3. **Static analysis only**: Threat skills read `discovery.json` content. They
   never execute discovered code. This is regex-based pattern matching, not
   sandboxed execution.

4. **Threat dominance in scoring**: When config safety drops below 5, it gets
   80% weight in the trust formula. A repo can be perfectly healthy and still
   get a low trust score if it contains auto-executing hooks that exfiltrate
   data.

5. **Separation of extraction and analysis**: Extraction is slow (API calls,
   git log parsing). Analysis is fast (SQL queries). Extract once, analyze many
   times, ask follow-up questions without re-fetching.

6. **Skills as documentation**: Each SKILL.md is both documentation for humans
   and instructions for the Claude Code agent. The skill files specify when to
   use each skill, what inputs it needs, what outputs it produces, the exact
   workflow to follow, and common pitfalls to avoid.
