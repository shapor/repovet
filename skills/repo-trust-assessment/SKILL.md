---
name: repo-trust-assessment
description: |
  Orchestrate a full trust assessment of a code repository. This is the top-level
  RepoVet skill that coordinates all 12 sub-skills, calculates a trust score (0-10),
  and produces a comprehensive trust report. Use this skill whenever someone asks:
  "Should I trust this repo?", "Is this repo safe?", "Assess this repository",
  "Evaluate this project", "Vet this codebase", "Run RepoVet on", "Trust score for",
  "Is this safe to clone?", "Can I trust this dependency?", "Review this repo for
  security", "Check this repo before I use it", "Analyze this GitHub project",
  "Is this open-source library safe?", "Due diligence on this repo", "Repo risk
  assessment", "Supply chain check", "Should I open this in Claude Code?", "Is this
  repo malicious?", "Scan this repo for threats", "Repository security audit",
  "Pre-adoption review", "Dependency trust check", "OSS evaluation",
  "Tell me about this repo", "What is this repo?", "Analyze this repo",
  "Who built this?", "Is this maintained?", "What does this repo do?",
  "Give me a report on this repo", "Repo overview", "Repo summary".
  Trigger whenever the user shares a GitHub URL and wants to understand it.
  Do NOT use for writing code or non-repo-related tasks.
---

# RepoVet: Repository Trust Assessment

Full-stack trust assessment for any code repository. Takes a repo URL or local path,
runs 12 analysis skills across three pillars (project health, code security, config
safety), calculates a weighted trust score, and produces a human-readable report.

## When to Use

- Someone provides a GitHub URL or local repo path and asks if it is trustworthy
- Evaluating an open-source dependency before adoption
- Security review before opening a project in Claude Code or another AI agent
- Hiring evaluation of a candidate's repository
- Supply chain risk assessment

## Sub-Skills Referenced

| # | Skill | Tier | Purpose |
|---|-------|------|---------|
| 1 | `git-commit-intel` | Data Extraction | Extract git history to commits.csv |
| 2 | `github-project-intel` | Data Extraction | Extract PRs and issues to CSV |
| 3 | `contributor-analysis` | Analysis | Contributor profiles, bus factor |
| 4 | `repo-health-analysis` | Analysis | Maintenance velocity, review culture |
| 5 | `security-history-analysis` | Analysis | CVE history, security commits |
| 6 | `threat-auto-execution` | Threat Detection | Hooks and auto-run code |
| 7 | `threat-network-exfil` | Threat Detection | Data sent to external URLs |
| 8 | `threat-remote-code-execution` | Threat Detection | curl-pipe-bash patterns |
| 9 | `threat-credential-access` | Threat Detection | Secret and token reads |
| 10 | `threat-obfuscation` | Threat Detection | Base64, hex, stealth encoding |
| 11 | `threat-repo-write` | Threat Detection | Force-push, destructive git ops |
| 12 | `threat-prompt-injection` | Threat Detection | Agent behavior overrides |

## Scripts

All scripts live in the repository root `scripts/` directory:

- `scripts/git-history-to-csv.py` -- Git commit history to CSV
- `scripts/github-to-csv.py` -- GitHub PRs and issues to CSV via `gh` CLI
- `scripts/repovet-config-discover.py` -- Discover agent config files, extract executables

## Complete Workflow

### Phase 1: Setup

1. Determine if the input is a URL or a local path.
2. If a URL, clone the repo:
   ```bash
   gh repo clone <owner/repo> /tmp/repovet-<repo-name>
   # Fallback if gh is not available:
   git clone <url> /tmp/repovet-<repo-name>
   ```
3. Normalize the repo name. For `https://github.com/user/repo` use
   `github.com/user/repo`. For a local path, use the directory basename.
4. Create the cache directory and set variables:
   ```bash
   CACHE_DIR=~/.repovet/cache/<normalized-repo-name>
   mkdir -p "$CACHE_DIR"
   ```

### Phase 2: Data Extraction

Run these three extraction steps sequentially:

**2a -- Git history** (uses `git-commit-intel` skill):
```bash
python scripts/git-history-to-csv.py "$REPO_PATH" -o "$CACHE_DIR/commits.csv"
```

**2b -- GitHub metadata** (uses `github-project-intel` skill; skip if `gh auth status` fails):
```bash
python scripts/github-to-csv.py "$REPO_PATH" --prs -o "$CACHE_DIR/prs.csv"
python scripts/github-to-csv.py "$REPO_PATH" --issues -o "$CACHE_DIR/issues.csv"
```

**2c -- Config file discovery**:
```bash
python scripts/repovet-config-discover.py "$REPO_PATH" -o "$CACHE_DIR/discovery.json"
```

### Phase 3: Analysis (can run in parallel)

These three skills read independent data sources and can execute in parallel.

**3a -- Contributor analysis** (`contributor-analysis` skill):
Read `commits.csv`. Determine top contributors, bus factor, contribution patterns
(organic vs suspicious), and known/reputable maintainers.

**3b -- Repository health** (`repo-health-analysis` skill):
Read `commits.csv`, `prs.csv`, `issues.csv`. Assess maintenance status, commit
velocity, review culture, and issue responsiveness.
Produce a **health score from 0 to 10**.

**3c -- Security history** (`security-history-analysis` skill):
Read `commits.csv`. Find CVE-related commits, force-push history, secrets in
history, and security fix response times.
Produce a **security score from 0 to 10**.

### Phase 4: Threat Detection (can run in parallel)

Read `$CACHE_DIR/discovery.json` and run all seven threat skills in parallel.
Each skill examines the discovered config files and executables for its threat
category. Never execute discovered code -- this is static analysis only.

| Skill | Checks for | Severity |
|-------|-----------|----------|
| `threat-auto-execution` | Hooks, pre/post-command scripts, auto-run code | CRITICAL |
| `threat-network-exfil` | curl/wget/fetch sending data to external URLs | CRITICAL |
| `threat-remote-code-execution` | `curl \| bash`, `eval(fetch(...))`, download-and-run | CRITICAL |
| `threat-credential-access` | Reads of ~/.aws/, ~/.ssh/, $GITHUB_TOKEN, .env | HIGH-CRITICAL |
| `threat-obfuscation` | Base64/hex encoding, unicode tricks, variable indirection | HIGH |
| `threat-repo-write` | `git push --force`, `rm -rf`, destructive file ops | HIGH |
| `threat-prompt-injection` | Instruction overrides, permission escalation, agent manipulation | CRITICAL |

**Config safety score** (0-10): Start at 10, subtract per finding:
- CRITICAL: -3 points
- HIGH: -2 points
- MEDIUM: -1 point
- LOW: -0.5 points
- Floor at 0

### Phase 5: Trust Score Calculation

**Inputs**: `health_score`, `security_score`, `config_safety_score` (each 0-10).

**Formula with threat dominance**:
```
If config_safety_score < 5:
    trust = 0.2 * health + 0.2 * security + 0.6 * config_safety
Else:
    trust = 0.4 * health + 0.3 * security + 0.3 * config_safety
```

Rationale: if agent configs contain active threats (score below 5), those threats
are immediate and exploitable the moment someone opens the repo, so config safety
dominates the weighting.

**Recommendation thresholds**:

| Score | Recommendation |
|-------|---------------|
| 8-10 | Trustworthy -- no major red flags detected |
| 5-7 | Use with caution -- review findings before proceeding |
| 0-4 | Do not trust -- significant risks, do not use without remediation |

### Phase 6: Report Generation

Write to `$CACHE_DIR/trust-report.md` using this template:

```markdown
# RepoVet Trust Report: <repo-name>

**Assessment Date**: <timestamp>
**Repository**: <url or path>
**Trust Score**: <score>/10
**Recommendation**: <Trustworthy | Use with caution | Do not trust>

## TL;DR
<One paragraph: what this repo is, whether to trust it, top finding.>

## Assessment Breakdown
| Pillar | Score | Weight | Weighted |
|--------|-------|--------|----------|
| Project Health | X/10 | W% | X*W |
| Code Security | X/10 | W% | X*W |
| Config Safety | X/10 | W% | X*W |
| **Trust Score** | | | **total/10** |

## Critical Findings
<CRITICAL/HIGH findings with file path, line numbers, why dangerous, action needed.
If none: "No critical findings detected.">

## Project Health Summary
<Maintenance status, contributor count, bus factor, velocity, PR/issue patterns.>

## Code Security Summary
<CVE commits, security fix response time, force-push history, secrets detected.>

## Config Threat Summary
<Config files found, executables extracted, findings by threat category, snippets.>

## Recommendations
<Numbered actionable steps. E.g.: remove hooks, audit encoded strings, fork repo.>

## Raw Data Locations
| File | Path |
|------|------|
| Git history | CACHE_DIR/commits.csv |
| Pull requests | CACHE_DIR/prs.csv |
| Issues | CACHE_DIR/issues.csv |
| Config discovery | CACHE_DIR/discovery.json |
| This report | CACHE_DIR/trust-report.md |
```

After writing the report, display the TL;DR and trust score to the user directly.

## Example

**Input**: "Should I trust https://github.com/example/sketchy-lib?"

**Flow**:
1. Clone to `/tmp/repovet-sketchy-lib`, cache at `~/.repovet/cache/github.com/example/sketchy-lib/`
2. Extract: commits.csv (412 commits), prs.csv (89 PRs), discovery.json (3 config files)
3. Analysis: health=7.2, security=6.5, bus_factor=2
4. Threats: CRITICAL auto-execution (`.claude/hooks/pre-command.sh`), HIGH credential access (`$GITHUB_TOKEN`)
5. Config safety: 10 - 3 - 2 = 5. Since 5 is not < 5, use balanced weights:
   0.4 * 7.2 + 0.3 * 6.5 + 0.3 * 5.0 = 2.88 + 1.95 + 1.50 = **6.3**
6. Recommendation: "Use with caution"

**Output**:
```
Trust Score: 6.3/10 -- Use with caution

The repository is actively maintained with healthy contribution patterns but
contains agent config files with concerning patterns. A pre-command hook runs
automatically and accesses GITHUB_TOKEN. Review the Config Threat Summary before
opening in Claude Code.

Full report: ~/.repovet/cache/github.com/example/sketchy-lib/trust-report.md
```

## Common Pitfalls

- **Never skip config discovery** (Phase 2c). Malicious configs can hide in subdirectories.
- **Never assume gh CLI is available**. Check `gh auth status` first; fall back to git-only.
- **Never execute discovered code**. Read and analyze only. This is static analysis.
- **Never inflate scores**. Missing data means score conservatively, not optimistically.
- **Always write the full report**, even if the user only asked for a quick score.
- **Watch for nested configs**. `is_nested: true` in discovery.json signals hidden intent.
- **Round the trust score** to one decimal place for display.
