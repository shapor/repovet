# Skillathon Repository Structure Plan

## Current State (What We Have)

```
skillathon/
├── hackathon.md                    # Hackathon guide (comprehensive)
├── IDEAS.md                        # Early brainstorming
├── NOTES.md                        # Random notes
├── README.md                       # Current: brief RepoVet intro
├── ideas/                          # RepoVet design docs (7 files)
├── scripts/                        # Git analysis scripts
│   ├── git-history-to-csv.py
│   └── github-to-csv.py
├── skills/                         # Judge panel skills (8 skills)
│   ├── judge-*/ (x7)
│   └── judge-panel/
├── src/                            # Cloned external repos
│   ├── harbor/
│   ├── skillsbench/
│   ├── anthropic-skills/
│   └── ...
├── build_dashboard.py              # Dashboard generator
├── gather_stats.py                 # Stats collector
├── skills_dashboard.html           # Generated dashboard
└── skill_stats.json                # Stats data
```

## What We Need to Present

### 1. RepoVet (Main Project)
- 13 skills for repo trust assessment
- Scripts that do the heavy lifting
- Design documentation
- Example usage

### 2. Judge Panel (Supporting Tool)
- 8 judge skills for evaluating submissions
- Dashboard for viewing skill stats
- Used during hackathon judging

### 3. Harbor Task (Evaluation)
- Benchmark task for proving RepoVet works
- Test repos with known properties
- Deterministic verifiers

### 4. Research/Context
- Hackathon guide
- SkillsBench paper notes
- Competitive intelligence

---

## Proposed Structure (Final)

```
skillathon/
├── README.md                       # HIGH-LEVEL: "Two projects from Skillathon 2026"
│                                   # 1. RepoVet - trust assessment
│                                   # 2. Judge Panel - hackathon judging tools
│
├── docs/                           # Documentation & research
│   ├── hackathon-guide.md          # Moved from hackathon.md
│   ├── competitive-intel.md        # Lightning pitches analysis
│   ├── skillsbench-notes.md        # Paper findings
│   └── presentation.md             # Slides/demo script
│
├── repovet/                        # MAIN PROJECT
│   ├── README.md                   # Full RepoVet documentation
│   ├── skills/                     # The 13 RepoVet skills
│   │   ├── repo-trust-assessment/  # Orchestrator
│   │   ├── git-commit-intel/
│   │   ├── github-project-intel/
│   │   ├── contributor-analysis/
│   │   ├── repo-health-analysis/
│   │   ├── security-history-analysis/
│   │   ├── threat-auto-execution/
│   │   ├── threat-network-exfil/
│   │   ├── threat-remote-code-execution/
│   │   ├── threat-credential-access/
│   │   ├── threat-obfuscation/
│   │   ├── threat-repo-write/
│   │   └── threat-prompt-injection/
│   ├── scripts/                    # Shared scripts
│   │   ├── git-history-to-csv.py
│   │   ├── github-to-csv.py
│   │   └── repovet-config-discover.py
│   ├── design/                     # Design docs (moved from ideas/)
│   │   ├── overview.md
│   │   ├── architecture.md
│   │   ├── threat-model.md
│   │   ├── agent-config-inventory.md
│   │   ├── data-storage.md
│   │   └── future-enhancements.md
│   ├── examples/                   # Example usage
│   │   ├── analyze-anthropic-sdk.md
│   │   └── test-repos/             # Sample repos for testing
│   │       ├── safe-repo/
│   │       ├── malicious-repo/
│   │       └── borderline-repo/
│   └── harbor-task/                # Harbor benchmark task
│       ├── task.toml
│       ├── instruction.md
│       ├── environment/
│       │   ├── Dockerfile
│       │   └── skills/             # Symlink to ../skills/
│       ├── solution/
│       │   └── solve.sh
│       └── tests/
│           ├── test.sh
│           └── test_trust.py
│
├── judge-panel/                    # SUPPORTING PROJECT
│   ├── README.md                   # Judge panel documentation
│   ├── skills/                     # The 8 judge skills
│   │   ├── judge-panel/            # Orchestrator
│   │   ├── judge-bence-nagy/
│   │   ├── judge-ryan-marten/
│   │   ├── judge-xiangyi-li/
│   │   ├── judge-belinda-mo/
│   │   ├── judge-furqan-rydhan/
│   │   ├── judge-roey-ben-chaim/
│   │   └── judge-grace-zhang/
│   ├── tools/                      # Dashboard & analysis
│   │   ├── build_dashboard.py
│   │   ├── gather_stats.py
│   │   └── skills_dashboard.html
│   └── data/
│       └── skill_stats.json
│
└── archive/                        # Historical/deprecated
    ├── IDEAS.md                    # Early brainstorming
    ├── NOTES.md                    # Random notes
    └── partial-transcript-includes-lightning-pitches-at-end.txt
```

---

## File Movement Plan

### Phase 1: Reorganize Existing
```bash
# Create new structure
mkdir -p repovet/{skills,scripts,design,examples,harbor-task}
mkdir -p judge-panel/{skills,tools,data}
mkdir -p docs archive

# Move RepoVet design docs
mv ideas/* repovet/design/

# Move judge skills
mv skills/judge-* judge-panel/skills/

# Move judge tools
mv build_dashboard.py judge-panel/tools/
mv gather_stats.py judge-panel/tools/
mv skills_dashboard.html judge-panel/tools/
mv skill_stats.json judge-panel/data/

# Move scripts (already in right place, just reference)
mv scripts/* repovet/scripts/

# Move docs
mv hackathon.md docs/hackathon-guide.md
mv IDEAS.md archive/
mv NOTES.md archive/
mv partial-transcript-includes-lightning-pitches-at-end.txt archive/
```

### Phase 2: Create New Content
```bash
# New READMEs
- Root README.md (overview of both projects)
- repovet/README.md (full RepoVet docs)
- judge-panel/README.md (judge panel docs)

# New design docs
- docs/presentation.md (demo script)
- docs/competitive-intel.md (lightning pitches analysis)

# RepoVet skills (to build)
- repovet/skills/* (13 SKILL.md files)

# Harbor task (to build)
- repovet/harbor-task/* (full Harbor structure)

# Test repos (to create)
- repovet/examples/test-repos/*
```

---

## Root README.md Structure (New)

```markdown
# Skillathon 2026 — Two Projects

Work from the March 7, 2026 Agent Skills Hackathon (SF).

## 1. RepoVet — Trust Assessment for Code Repositories

**"Should I trust this repo?"**

A comprehensive trust assessment system that analyzes git history, project
health, and agent configuration files to detect security threats.

→ [Full documentation](repovet/README.md)

**Highlights**:
- 13 composable skills for repo intelligence
- Novel threat detection: scans Claude, Cursor, Copilot config files
- Script-heavy: deterministic analysis, not just LLM generation
- Trust score (0-10) across 3 pillars: health, security, config safety

**Use cases**: OSS adoption due diligence, hiring evaluation, security review

---

## 2. Judge Panel — Hackathon Judging Tools

Meta-skills for evaluating agent skill submissions during the hackathon.

→ [Documentation](judge-panel/README.md)

**Components**:
- 8 judge personas (one per hackathon judge/organizer)
- Panel orchestrator for multi-judge consensus
- Dashboard for analyzing 86K+ skills from registries

---

## Documentation

- [Hackathon Guide](docs/hackathon-guide.md) — SkillsBench findings, task format
- [Competitive Intel](docs/competitive-intel.md) — Other teams' pitches
- [Presentation](docs/presentation.md) — Demo script

---

## Repository Structure

See [REPO-STRUCTURE.md](REPO-STRUCTURE.md) for full layout.
```

---

## Presentation Flow (For Demo)

### Act 1: The Problem (2 min)
"You clone a repo someone sent you. Should you trust it?
 - Will it run malicious hooks in Claude Code?
 - Is it actively maintained?
 - Who built it?

Today, you manually check commits, search for CVEs, hope you don't miss anything."

### Act 2: The Solution (3 min)
"RepoVet answers: Trust this? Yes/Caution/No + detailed evidence.

Three pillars:
1. Project Health (git/GitHub analysis) → your existing scripts
2. Code Security (CVE history, secrets)
3. Config Safety (scans .claude, .cursorrules, copilot configs)

13 skills work together. Scripts do heavy lifting. Novel: nobody's scanning
agent config files for malicious code."

### Act 3: The Demo (3 min)
"Let me show you three repos:
1. Safe repo → Trust score 8.5/10
2. Malicious repo → 2.1/10, CRITICAL: hook sends ~/.bashrc to external URL
3. Borderline → 5.8/10, USE WITH CAUTION

Skills compose: data extraction → analysis → threat detection → trust score."

### Act 4: The Proof (2 min)
"We built a Harbor benchmark task. Without skills: agent scores X%.
With RepoVet skills: Y%. Delta: +Zpp.

Deterministic verifiers. Reproducible. Real-world useful beyond the benchmark."

### Bonus: Judge Panel (1 min if time)
"Meta: we also built judge skills for evaluating submissions.
8 judge personas, panel consensus. Used to analyze this hackathon."

---

## Priority Actions

### Today (Building Phase)
1. **Keep current layout** for development (don't move files mid-work)
2. **Build the skills** first (repovet/skills/*)
3. **Build discovery script** (repovet-config-discover.py)

### Before Demo (Polish Phase)
4. **Reorganize** files per structure above
5. **Write READMEs** (root, repovet/, judge-panel/)
6. **Create test repos** with known properties
7. **Build Harbor task** for eval

### For Presentation (Proof Phase)
8. **Run evals** with/without skills → measure delta
9. **Create demo script** (docs/presentation.md)
10. **Generate slides** or live demo plan

---

## Questions to Resolve

1. **Do we submit RepoVet as a task to SkillsBench?**
   - Yes → need Harbor task fully built
   - No → just publish skills to registries, demo live

2. **Do we demo Judge Panel at all?**
   - Yes → brief mention as meta-work
   - No → focus 100% on RepoVet

3. **Do we want the git scripts in repovet/ or keep them shared?**
   - Probably move into repovet/ for cleaner packaging

4. **Should archive/ be kept or deleted?**
   - Keep for now (historical context), can delete post-hackathon

---

## Next Immediate Step

**Option A**: Reorganize now (takes 30 min, cleaner going forward)
**Option B**: Keep building, reorganize before demo (faster now, cleanup later)

**Recommendation**: Option B — keep building skills, reorganize during polish phase.

The current layout works fine for development. We'll move things around when
we're ready to present/submit.
