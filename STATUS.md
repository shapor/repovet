# Skillathon Status — March 7, 2026

---

## Project: RepoVet

**"Should I trust this repo?"** — Trust assessment for code repositories.

### What It Does

Takes a repo, analyzes git history + project health + agent config files, outputs a trust score (0-10) with detailed evidence and recommendation (Trust / Caution / Do Not Trust).

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
| `scripts/git-history-to-csv.py` | DONE | 506 | Git commits → CSV (authors, languages, file stats, PR enrichment) |
| `scripts/github-to-csv.py` | DONE | 492 | GitHub PRs + issues → CSV via GraphQL (reviews, bot detection, timing) |
| `scripts/repovet-config-discover.py` | DONE | ~310 | Finds all agent config files, extracts executables → JSON |

### Skills (13 total)

| Skill | Tier | Status | Purpose |
|-------|------|--------|---------|
| `git-commit-intel` | Data Extraction | DONE | Wraps git-history-to-csv.py |
| `github-project-intel` | Data Extraction | DONE | Wraps github-to-csv.py |
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

### Test Repos

| Repo | Status | Expected Score | Key Features |
|------|--------|---------------|-------------|
| `examples/test-repos/safe-repo/` | DONE | 8-9/10 | Clean, no threats, benign CLAUDE.md |
| `examples/test-repos/malicious-repo/` | DONE | 1-3/10 | Malicious hooks, exfil, nested config, obfuscation, prompt injection |
| `examples/test-repos/borderline-repo/` | DONE | 5-7/10 | Overly permissive but not malicious |

### Discovery Script Test Results

```
safe-repo:       2 config files, 0 executables, 0 nested, 0 permissions
malicious-repo:  7 config files, 4 executables, 1 nested, 4 permissions
borderline-repo: 3 config files, 0 executables, 0 nested, 3 permissions
```

### Judge Panel (Side Project)

| Component | Status |
|-----------|--------|
| 7 individual judge skills | DONE |
| judge-panel orchestrator | DONE |
| build_dashboard.py | DONE |
| gather_stats.py | DONE |
| skills_dashboard.html | DONE |

---

## What's NOT Done

| Item | Priority | Time Estimate | Notes |
|------|----------|--------------|-------|
| Harbor benchmark task | HIGH | 1-2 hours | task.toml, instruction.md, Dockerfile, tests |
| End-to-end eval (with/without skills) | HIGH | 1 hour | Proves the delta for judges |
| Repo reorganization | MEDIUM | 30 min | Move files into repovet/ and judge-panel/ dirs |
| Presentation/demo script | MEDIUM | 30 min | What to say, what to show |
| Publish skills to Sundial Hub | LOW | 30 min | `npx sundial-hub add` |

---

## File Tree (What Exists)

```
skillathon/
├── README.md                          ✅ Updated
├── BUILD-GUIDE.md                     ✅ Full build specs
├── REPO-STRUCTURE.md                  ✅ Planned final layout
├── STATUS.md                          ✅ This file
│
├── scripts/
│   ├── git-history-to-csv.py          ✅ 506 lines
│   ├── github-to-csv.py              ✅ 492 lines
│   └── repovet-config-discover.py    ✅ ~310 lines, tested
│
├── skills/
│   ├── git-commit-intel/SKILL.md     ✅
│   ├── github-project-intel/SKILL.md ✅
│   ├── contributor-analysis/SKILL.md ✅
│   ├── repo-health-analysis/SKILL.md ✅
│   ├── security-history-analysis/SKILL.md ✅
│   ├── threat-auto-execution/SKILL.md ✅
│   ├── threat-network-exfil/SKILL.md ✅
│   ├── threat-remote-code-execution/SKILL.md ✅
│   ├── threat-credential-access/SKILL.md ✅
│   ├── threat-obfuscation/SKILL.md   ✅
│   ├── threat-repo-write/SKILL.md    ✅
│   ├── threat-prompt-injection/SKILL.md ✅
│   ├── repo-trust-assessment/SKILL.md ✅
│   ├── judge-panel/                   ✅ (side project)
│   ├── judge-bence-nagy/              ✅
│   ├── judge-ryan-marten/             ✅
│   ├── judge-xiangyi-li/              ✅
│   ├── judge-belinda-mo/              ✅
│   ├── judge-furqan-rydhan/           ✅
│   ├── judge-roey-ben-chaim/          ✅
│   └── judge-grace-zhang/             ✅
│
├── examples/
│   └── test-repos/
│       ├── safe-repo/                 ✅ 5 files
│       ├── malicious-repo/            ✅ 10 files
│       └── borderline-repo/           ✅ 5 files
│
├── ideas/                             ✅ 7 design docs
│   ├── repovet-overview.md
│   ├── claude-config-audit-design.md
│   ├── github-repo-intel.md
│   ├── agent-config-files-inventory.md
│   ├── data-storage-architecture.md
│   ├── future-enhancements.md
│   └── repovet-background.md
│
├── hackathon.md                       ✅ Research/strategy
├── IDEAS.md                           ✅ Early brainstorming
├── NOTES.md                           ✅ Notes
├── skillsbench.pdf                    ✅ Paper
├── build_dashboard.py                 ✅ Judge dashboard
├── gather_stats.py                    ✅ Stats collector
├── skills_dashboard.html              ✅ Generated dashboard
├── skill_stats.json                   ✅ Stats data
└── src/                               ✅ Cloned reference repos
    ├── harbor/
    ├── skillsbench/
    └── ...
```

---

## Key Design Decisions

1. **Name**: RepoVet ("veterinary checkups for code repositories")
2. **Storage**: `~/.repovet/cache/{repo-name}/` — global cache, shareable via git
3. **Recursive scanning**: Every subdirectory is a potential agent launch point
4. **Multi-agent support**: Scans Claude, Cursor, Copilot, Aider, Continue, Windsurf configs
5. **Hybrid approach**: Scripts do deterministic extraction, skills do semantic analysis
6. **Trust score**: Weighted average of 3 pillars, config threats dominate when critical

---

## Demo Script (If Presenting)

### Act 1: Problem (2 min)
"You clone a repo. Claude Code asks: trust this? You have no idea. You scroll commits. You hope."

### Act 2: Solution (3 min)
"RepoVet answers that question. Three pillars: health, security, config safety. 13 skills. Scripts do the work."

### Act 3: Live Demo (3 min)
Run discovery script on test repos. Show safe vs malicious comparison:
```bash
python3 scripts/repovet-config-discover.py examples/test-repos/malicious-repo
```
"4 executables found. Nested config at depth 2. Pre-command hook sends ~/.bashrc to external URL."

### Act 4: Proof (2 min)
"Harbor benchmark: without skills X%, with skills Y%. Delta: +Zpp."

### Bonus: Judge Panel (1 min)
"We also built 8 judge persona skills for evaluating submissions."

---

## Next Actions (In Priority Order)

1. **Build Harbor task** — Need this to prove delta for judges
2. **Run end-to-end eval** — With and without skills
3. **Reorganize repo** — Move into clean structure
4. **Prep demo** — Know what to show, what to say
