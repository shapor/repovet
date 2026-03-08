# Skill Fix Brief

## The Problem

The `safe-clone` skill does not work as intended. When a user says "clone github.com/user/repo", the agent:

1. Skips the RepoVet scan
2. Goes straight to reading cached files from `~/.repovet/`
3. Loads all 7 threat skills directly instead of as Task agents
4. Never asks the user what they want to do (no AskUserQuestion)
5. Searches for `repovet.py` instead of using the absolute path in the skill
6. Uses `python3 -c` inline scripts instead of our tools
7. Deletes clones from `/tmp/` after analysis

## What We Want

### Flow

```
User: "clone github.com/shapor/helpful-dev-utils"

Step 1: Agent runs repovet.py scan (fast, no clone, GitHub API only)
        → Shows trust score + findings

Step 2: Agent asks user with AskUserQuestion (3 options):
        1. "Deep dive analysis" — run 7 threat agents in parallel
        2. "Clone anyway"
        3. "Cancel"

Step 3a (if deep dive):
        → Clone to ~/.repovet/cache/ (if not already there)
        → Extract commits.csv, discovery.json (if not already there)
        → Run repovet-display.py (heatmap/charts)
        → Launch 7 threat skills as PARALLEL TASK AGENTS
        → Show combined findings
        → Ask again: clone or cancel?

Step 3b (if clone): git clone
Step 3c (if cancel): done
```

### Key Requirements

- Step 1 ALWAYS happens first — no skipping, no shortcuts
- Step 2 ALWAYS asks the user — no auto-proceeding
- Deep dive runs the 7 threat skills as Task agents, not inline
- Use absolute paths: `/home/shapor/src/skillathon/.venv/bin/python /home/shapor/src/skillathon/scripts/repovet.py`
- Never use shell variables ($CACHE, $HOME, ~) — they trigger permission prompts
- Never use `python3 -c` inline — use our scripts
- Never delete clones
- Reuse cached data if it exists (don't re-clone, don't re-extract)
- DuckDB queries use `scripts/repovet-query` not inline python

## Files To Fix

- `skills/safe-clone/SKILL.md` — the main skill
- `.claude/settings.local.json` — permissions (already allows Bash, gh, git, scripts)

## Files That Exist (context)

### Scripts
- `/home/shapor/src/skillathon/scripts/repovet.py` — CLI scan tool (1710 lines, scans via GitHub API without cloning)
- `/home/shapor/src/skillathon/scripts/repovet-config-discover.py` — finds agent config files in local repos
- `/home/shapor/src/skillathon/scripts/repovet-display.py` — terminal heatmap/charts
- `/home/shapor/src/skillathon/scripts/repovet-analyze.py` — DuckDB analytics
- `/home/shapor/src/skillathon/scripts/repovet-query` — DuckDB SQL query tool
- `/home/shapor/src/skillathon/scripts/git-history-to-csv.py` — git commits to CSV
- `/home/shapor/src/skillathon/scripts/github-to-csv.py` — PRs/issues to CSV

### Skills (in `~/.claude/skills/` symlinked to `/home/shapor/src/skillathon/skills/`)
- `repo-trust-assessment` — orchestrator
- `git-analytics-sql` — DuckDB queries
- `git-commit-intel` — wraps git-history-to-csv.py
- `github-project-intel` — wraps github-to-csv.py
- `safe-clone` — THE BROKEN ONE
- `threat-auto-execution`, `threat-network-exfil`, `threat-remote-code-execution`, `threat-credential-access`, `threat-obfuscation`, `threat-repo-write`, `threat-prompt-injection`

### Cache
- `/home/shapor/.repovet/cache/github.com/OWNER/REPO/` — where clones + CSVs + discovery.json live

### Known Claude Code Gotchas
- `~` and `$HOME` and `$VAR` in Bash commands trigger "Shell expansion syntax requires manual approval"
- `python` doesn't exist, must use `python3` or `.venv/bin/python`
- Snap duckdb can't read ~/.repovet/ (use scripts/repovet-query instead)
- `!=` in SQL gets escaped by bash (use `<>` instead)
- Long Bash output gets collapsed (tell user to press ctrl+o)
- `allowed-tools` in skill frontmatter pre-approves tools only within skill context
- Agent often ignores skill instructions and "optimizes" by taking shortcuts
