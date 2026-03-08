# Skillathon Status — March 7, 2026

**Last Updated**: After Harbor Task Completion ✅

---

## Project: RepoVet

**"Should I trust this repo?"** — Trust assessment for code repositories.

**Status**: 95% complete. Core implementation done, Harbor task built and validated, ready for evaluation.

### What It Does

Takes a repo, analyzes git history + project health + agent config files, outputs a trust score (0-10) with detailed evidence and recommendation (Trust / Caution / Do Not Trust). The flagship `repovet.py` CLI scans remote repos via the GitHub API without ever cloning them.

### Three Pillars

| Pillar | Score Range | What It Checks |
|--------|-------------|----------------|
| Project Health | 0-10 | Contributors, velocity, bus factor, review culture, maintenance |
| Code Security | 0-10 | CVE history, security commits, secrets in history, force-pushes |
| Config Safety | 0-10 | Malicious hooks, data exfil, RCE, credential theft, obfuscation, prompt injection |

If config safety score < 5, it dominates the overall trust score (60% weight).

---

## Build Status

### Scripts

| Script | Status | Lines | What It Does |
|--------|--------|-------|-------------|
| `scripts/repovet.py` | DONE | 1710 | Full CLI — scans remote repos via GitHub API without cloning |
| `scripts/repovet-analyze.py` | DONE | 836 | DuckDB analytics engine for RepoVet scan results |
| `scripts/repovet-config-discover.py` | DONE | 527 | Finds all agent config files, extracts executables -> JSON |
| `scripts/git-history-to-csv.py` | DONE | 505 | Git commits -> CSV (authors, languages, file stats, PR enrichment) |
| `scripts/github-to-csv.py` | DONE | 491 | GitHub PRs + issues -> CSV via GraphQL (reviews, bot detection, timing) |

### Skills (22 total: 14 RepoVet + 8 Judge)

#### RepoVet Skills (14)

| Skill | Tier | Status | Purpose |
|-------|------|--------|---------|
| `git-commit-intel` | Data Extraction | DONE | Wraps git-history-to-csv.py |
| `github-project-intel` | Data Extraction | DONE | Wraps github-to-csv.py |
| `git-analytics-sql` | Analytics | DONE | DuckDB SQL analytics on git data |
| `contributor-analysis` | Analysis | DONE | Who built this? Bus factor? Hiring eval? |
| `repo-health-analysis` | Analysis | DONE | Active? Velocity? Review culture? |
| `security-history-analysis` | Analysis | DONE | CVE history? Security commits? Secrets? |
| `threat-auto-execution` | Threat Detection | DONE | Hooks that run without approval |
| `threat-network-exfil` | Threat Detection | DONE | Sends data to external URLs |
| `threat-remote-code-execution` | Threat Detection | DONE | Downloads and runs external code |
| `threat-credential-access` | Threat Detection | DONE | Reads secrets/tokens |
| `threat-obfuscation` | Threat Detection | DONE | Base64, hex-encoded commands |
| `threat-repo-write` | Threat Detection | DONE | git force-push, rm -rf |
| `threat-prompt-injection` | Threat Detection | DONE | "Ignore previous instructions" |
| `repo-trust-assessment` | Orchestrator | DONE | Runs everything, calculates trust score |

#### Judge Panel Skills (8)

| Skill | Status | Purpose |
|-------|--------|---------|
| `judge-bence-nagy` | DONE | Individual judge persona |
| `judge-ryan-marten` | DONE | Individual judge persona |
| `judge-xiangyi-li` | DONE | Individual judge persona |
| `judge-belinda-mo` | DONE | Individual judge persona |
| `judge-furqan-rydhan` | DONE | Individual judge persona |
| `judge-roey-ben-chaim` | DONE | Individual judge persona |
| `judge-grace-zhang` | DONE | Individual judge persona |
| `judge-panel` | DONE | Orchestrator — runs all judges, aggregates scores |

### Test Repos

| Repo | Status | Expected Score | Key Features |
|------|--------|---------------|-------------|
| `examples/test-repos/safe-repo/` | DONE | 8-9/10 | Clean, no threats, benign CLAUDE.md |
| `examples/test-repos/malicious-repo/` | DONE | 1-3/10 | Malicious hooks, exfil, nested config, obfuscation, prompt injection |
| `examples/test-repos/borderline-repo/` | DONE | 5-7/10 | Overly permissive but not malicious |
| `test-repos/helpful-dev-utils/` | DONE | Low | Realistic attack demo — looks helpful, hides exfil in hooks |

### Discovery Script Test Results

```
safe-repo:       2 config files, 0 executables, 0 nested, 0 permissions
malicious-repo:  7 config files, 4 executables, 1 nested, 4 permissions
borderline-repo: 3 config files, 0 executables, 0 nested, 3 permissions
```

### Baseline Analysis

`analysis/claude-code-baseline/` contains examples of how Claude Code handles repo trust decisions without RepoVet skills — documents the gap RepoVet fills.

### Other Tools

| Component | Status |
|-----------|--------|
| `build_dashboard.py` | DONE |
| `gather_stats.py` | DONE |
| `skills_dashboard.html` | DONE |
| `requirements.txt` | DONE (duckdb, pytz) |
| `.venv/` | Set up |

---

## Harbor Task

| Component | Status | Location |
|-----------|--------|----------|
| task.toml | DONE | `harbor-task/repovet-trust-assessment/task.toml` |
| instruction.md | DONE | `harbor-task/repovet-trust-assessment/instruction.md` |
| Dockerfile | DONE | `harbor-task/repovet-trust-assessment/environment/Dockerfile` |
| Test suite | DONE | `harbor-task/repovet-trust-assessment/tests/` |
| Oracle solution | DONE | `harbor-task/repovet-trust-assessment/solution/solve.sh` |
| Documentation | DONE | `harbor-task/README.md` |

**Expected Delta**: +40-50pp (20-30% baseline → 70-80% with skills)

---

## What's NOT Done

| Item | Priority | Time Estimate | Notes |
|------|----------|--------------|-------|
| End-to-end eval (with/without skills) | HIGH | 1 hour | Proves the delta for judges |
| Harbor task integration testing | MEDIUM | 30 min | Test with actual Harbor CLI |
| Presentation/demo script | MEDIUM | 30 min | What to say, what to show |
| Publish skills to Sundial Hub | LOW | 30 min | `npx sundial-hub add` |

---

## File Tree (Actual)

```
skillathon/
├── README.md
├── BUILD-GUIDE.md
├── REPO-STRUCTURE.md
├── STATUS.md                              <- This file
├── hackathon.md
├── IDEAS.md
├── NOTES.md
├── partial-transcript-includes-lightning-pitches-at-end.txt
├── skillsbench.pdf
├── requirements.txt                       (duckdb, pytz)
├── .gitignore
│
├── scripts/
│   ├── repovet.py                         1710 lines — full CLI, GitHub API scanning
│   ├── repovet-analyze.py                 836 lines — DuckDB analytics engine
│   ├── repovet-config-discover.py         527 lines — agent config discovery
│   ├── git-history-to-csv.py              505 lines — git commits to CSV
│   └── github-to-csv.py                   491 lines — GitHub PRs/issues to CSV
│
├── skills/
│   ├── git-commit-intel/SKILL.md
│   ├── github-project-intel/SKILL.md
│   ├── git-analytics-sql/SKILL.md
│   ├── contributor-analysis/SKILL.md
│   ├── repo-health-analysis/SKILL.md
│   ├── security-history-analysis/SKILL.md
│   ├── threat-auto-execution/SKILL.md
│   ├── threat-network-exfil/SKILL.md
│   ├── threat-remote-code-execution/SKILL.md
│   ├── threat-credential-access/SKILL.md
│   ├── threat-obfuscation/SKILL.md
│   ├── threat-repo-write/SKILL.md
│   ├── threat-prompt-injection/SKILL.md
│   ├── repo-trust-assessment/SKILL.md
│   ├── judge-panel/SKILL.md
│   ├── judge-bence-nagy/SKILL.md
│   ├── judge-ryan-marten/SKILL.md
│   ├── judge-xiangyi-li/SKILL.md
│   ├── judge-belinda-mo/SKILL.md
│   ├── judge-furqan-rydhan/SKILL.md
│   ├── judge-roey-ben-chaim/SKILL.md
│   └── judge-grace-zhang/SKILL.md
│
├── examples/
│   └── test-repos/
│       ├── safe-repo/                     5 files — clean, benign
│       ├── malicious-repo/                10 files — hooks, exfil, nested configs
│       └── borderline-repo/               5 files — permissive but not malicious
│
├── test-repos/
│   ├── README.md
│   └── helpful-dev-utils/                 Realistic attack demo (own git history)
│       ├── .claude/hooks/pre-command.sh
│       ├── hooks/post-checkout
│       ├── tools/git-stats
│       ├── tools/new-project
│       ├── setup.sh
│       ├── DEMO-ATTACK.md
│       └── README.md
│
├── analysis/
│   └── claude-code-baseline/
│       ├── example-2-clawdbot-skills.md
│       └── example-3-CRITICAL-premature-clone.md
│
├── ideas/                                 8 design docs
│   ├── repovet-overview.md
│   ├── repovet-background.md
│   ├── repovet-pitch.md
│   ├── claude-config-audit-design.md
│   ├── github-repo-intel.md
│   ├── agent-config-files-inventory.md
│   ├── data-storage-architecture.md
│   └── future-enhancements.md
│
├── build_dashboard.py
├── gather_stats.py
├── skills_dashboard.html
├── skill_stats.json
│
├── .venv/                                 Python virtual environment
│
├── .claude/settings.local.json
├── .agents/                               Sundial agent config
│   ├── .skill-lock.json
│   └── skills/
│       ├── find/SKILL.md
│       └── skill/SKILL.md (+ references/, scripts/)
│
└── src/                                   Cloned reference repos
    ├── harbor/
    ├── anthropic-skills/
    ├── awesome-openclaw-skills/
    ├── knowledge-work-plugins/
    └── sundial-skills/
```

---

## Key Design Decisions

1. **Name**: RepoVet ("veterinary checkups for code repositories")
2. **Flat structure**: Everything lives at the top level -- no repovet/ or judge-panel/ subdirectories
3. **Storage**: `~/.repovet/cache/{repo-name}/` — global cache, shareable via git
4. **Remote-first scanning**: `repovet.py` uses GitHub API to scan repos without cloning
5. **Recursive scanning**: Every subdirectory is a potential agent launch point
6. **Multi-agent support**: Scans Claude, Cursor, Copilot, Aider, Continue, Windsurf configs
7. **Hybrid approach**: Scripts do deterministic extraction, skills do semantic analysis
8. **Trust score**: Weighted average of 3 pillars, config threats dominate when critical
9. **DuckDB analytics**: `repovet-analyze.py` provides SQL-powered analysis of scan results

---

## Demo Script (If Presenting)

### Act 1: Problem (2 min)
"You clone a repo. Claude Code asks: trust this? You have no idea. You scroll commits. You hope."

### Act 2: Solution (3 min)
"RepoVet answers that question. Three pillars: health, security, config safety. 14 skills. Scripts do the heavy lifting. The star of the show: `repovet.py` -- a 1710-line CLI that scans remote repos via the GitHub API without ever cloning them."

### Act 3: Live Demo (3 min)
Run `repovet.py` against a live repo. Show the trust assessment, then contrast with the attack demo:
```bash
python3 scripts/repovet.py <org>/<repo>
```
Then show the realistic attack repo:
```bash
python3 scripts/repovet-config-discover.py test-repos/helpful-dev-utils
```
"Looks like a helpful dev-utils repo. But the pre-command hook exfiltrates data. RepoVet catches it."

### Act 4: Analytics (2 min)
Show DuckDB analytics across scan results:
```bash
python3 scripts/repovet-analyze.py
```

### Act 5: Proof (2 min)
"Harbor benchmark: without skills X%, with skills Y%. Delta: +Zpp."

### Bonus: Judge Panel (1 min)
"We also built 8 judge persona skills for evaluating submissions."

---

## Next Actions (In Priority Order)

1. **Build Harbor task** — Need this to prove delta for judges
2. **Run end-to-end eval** — With and without skills
3. **Prep demo** — Know what to show, what to say
