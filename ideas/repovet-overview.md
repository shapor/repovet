# RepoVet — Veterinary Checkups for Code Repositories

**"Should I trust this repo?"** — We answer that question.

---

## The Problem

You're about to:
- Clone a repo someone sent you
- Install an open-source library
- Point Claude Code at a new project
- Evaluate a candidate's GitHub portfolio
- Review code for security/supply chain risks

**The question**: Should I trust this repo?

**Current reality**: You manually:
- Scroll through commits
- Check contributor profiles
- Search for "security" or "CVE" in issues
- Maybe run `npm audit` or scan for secrets
- Hope you don't miss anything

**What you want**: An automated, comprehensive trust assessment.

---

## The Solution: RepoVet

**Input**: GitHub repo URL (or local repo path)

**Output**: Trust recommendation + detailed evidence

```bash
repovet assess https://github.com/user/suspicious-repo
```

**Result**:
```
🎯 Trust Recommendation: ⚠ USE WITH CAUTION
Trust Score: 4.2/10 — Significant risks detected

🚨 CRITICAL: Auto-execution + network exfiltration detected
   .claude/hooks/pre-command.sh sends ~/.bashrc to external URL

📈 Project Health: 7.5/10 ✓ Good
   - Active maintenance (last commit 2 days ago)
   - 12 contributors, 3 core maintainers
   - Healthy bus factor

🔒 Code Security: 6.8/10 ⚠ Some concerns
   - 2 outdated dependencies with known CVEs
   - Force-pushed to main once (3 months ago)

⚙️ Claude Config Safety: 1.5/10 ✗ Major risks
   - 2 auto-execution points (hooks)
   - 1 network exfiltration pattern
   - 1 credential access pattern

💡 Recommendation: Do not open in Claude Code as-is.
   Fork it and remove .claude/hooks/ first.
```

---

## How It Works

### Phase 1: Data Extraction (Your Existing Scripts)
Uses your battle-tested git analysis tools:
- **git-history-to-csv.py** → commits, authors, language stats, file changes
- **github-to-csv.py** → PRs, issues, review patterns, bot activity

### Phase 2: Multi-Pillar Assessment

#### Pillar 1: Project Health
- Is it actively maintained or abandoned?
- Who are the maintainers? Known contributors?
- Contribution patterns: organic growth or suspicious?
- Bus factor: resilient or one-person show?
- Issue/PR responsiveness

**Data source**: Git/GitHub history CSVs
**Skills**: contributor-analysis, repo-health-analysis

#### Pillar 2: Code Security
- CVE history for this repo
- GitHub Security Advisories for dependencies
- Security-related commits (fixes)
- Secrets in git history
- Force-pushed commits (hidden history?)

**Data source**: Git history + CVE databases
**Skills**: security-history-analysis

#### Pillar 3: Claude Config Safety (The Novel Part)
Scans for threats in agent configuration files:
- **Auto-execution**: Hooks that run on startup
- **Network exfiltration**: Sending data to external URLs
- **Remote code execution**: `curl | bash` patterns
- **Credential access**: Reading ~/.aws/credentials, $GITHUB_TOKEN
- **Obfuscation**: Base64-encoded commands, stealth tactics

**Data source**: New repovet-config-discover.py script
**Skills**: 6 threat-* analysis skills

### Phase 3: Trust Score Calculation
Weighted average with threat dominance:
```python
if claude_safety_score < 5:
    # Immediate threat matters most
    trust_score = 0.2 * project_health + 0.2 * code_security + 0.6 * claude_safety
else:
    # Balanced assessment
    trust_score = 0.4 * project_health + 0.3 * code_security + 0.3 * claude_safety
```

**Recommendation**:
- 8-10: ✓ Trustworthy
- 5-7: ⚠ Use with caution
- 0-4: ✗ Do not trust

---

## Architecture

### Storage: `~/.repovet/`
```
~/.repovet/
├── cache/
│   └── github.com/user/repo/
│       ├── commits.csv              # Git history
│       ├── prs.csv, issues.csv      # GitHub project data
│       ├── discovery.json           # Config files + executables
│       ├── threats.json             # Threat analysis results
│       ├── trust-report.md          # Human-readable report
│       └── metadata.json            # Score, timestamp, commit
├── config/
│   └── settings.json
└── skills/                          # The skills themselves
    ├── repo-trust-assessment/
    ├── git-commit-intel/
    ├── contributor-analysis/
    └── threat-*/
```

### Skills (Composable)

**Tier 1: Data Extraction**
1. **git-commit-intel** — Runs git-history-to-csv.py → commits.csv
2. **github-project-intel** — Runs github-to-csv.py → prs.csv, issues.csv

**Tier 2: Analysis**
3. **contributor-analysis** — Who maintains this? Bus factor? Hiring eval?
4. **repo-health-analysis** — Active? Velocity? Review culture?
5. **security-history-analysis** — CVE history? Security commits? Secrets?

**Tier 3: Threat Detection**
6. **threat-auto-execution** — Code that runs without approval
7. **threat-network-exfil** — Sends data to external URLs
8. **threat-remote-code-execution** — Downloads and runs external code
9. **threat-credential-access** — Reads secrets/tokens
10. **threat-obfuscation** — Hides intent (base64, hex encoding)
11. **threat-repo-write** — Destructive git ops (force push, rm -rf)
12. **threat-prompt-injection** — Overrides agent behavior

**Orchestrator**
13. **repo-trust-assessment** — Runs all sub-skills, calculates trust score

### Scripts

**Existing** (your head start):
- `scripts/git-history-to-csv.py` — Git commit extraction
- `scripts/github-to-csv.py` — PR/issue extraction

**New** (to build):
- `scripts/repovet-config-discover.py` — Find config files, extract executables

---

## Use Cases

### 1. "Someone sent me a repo, WTF is this?"
```bash
repovet assess https://github.com/stranger/unknown-project
```
**Answer**: Instant overview of who built it, if it's maintained, and safety.

### 2. Hiring / Interview Prep
```bash
repovet assess https://github.com/candidate/portfolio
```
**Answer**: What did they really contribute? Core maintainer or drive-by?

### 3. OSS Adoption Due Diligence
```bash
repovet assess https://github.com/org/potential-dependency
```
**Answer**: Is this actively maintained? Security track record? Safe to use?

### 4. Security Review Before Using with Claude Code
```bash
repovet assess https://github.com/team/project-with-claude-config
```
**Answer**: Will this run malicious hooks? Exfiltrate data? Safe to open?

### 5. Competitive Intelligence
```bash
repovet assess https://github.com/competitor/product
```
**Answer**: Who's building it? How fast? What's the team structure?

---

## What Makes This Win the Hackathon

### 1. Genuinely Useful
Everyone evaluates repos. Nobody has a tool that does this comprehensively.

### 2. Script-Heavy (Proves the Thesis)
- Your existing git scripts do the heavy lifting (deterministic, fast)
- Skills wrap scripts and add semantic analysis
- **This is the "tools wrapped in skills" thesis come to life**

### 3. Novel & Timely
- Agent config files as attack surface is a **live concern** (Snyk just wrote about it)
- Nobody else is scanning .claude files for malicious code
- **We're first to market on this threat vector**

### 4. Composable
- 13 skills that work together
- Each can be used independently
- Easy to add new threat-* skills as attacks evolve

### 5. Benchmarkable
- Create test repos with known properties
- Verify: "Top 3 contributors correct? ✓"
- Verify: "Malicious hook detected? ✓"
- Deterministic outputs = easy pytest assertions

### 6. Fast to Build
- ~7-8 hours total
- Your git scripts are 80% done already
- Biggest new code: repovet-config-discover.py (~2 hours)
- Rest is skill orchestration and threat analysis prompts

---

## Competition

**At the hackathon**: Nobody pitched anything like this.

**In the wild**:
- No skill for repo intelligence in any registry
- GitHub's insights page is limited and not agent-accessible
- Tools like git-fame, git-quick-stats exist but aren't packaged as skills
- **The Claude config scanning angle is completely novel**

---

## Build Plan (8 hours)

| Step | What | Time |
|------|------|------|
| 1 | Adapt git-history-to-csv.py into skill wrapper | 30 min |
| 2 | Adapt github-to-csv.py into skill wrapper | 30 min |
| 3 | Write repovet-config-discover.py | 2 hours |
| 4 | Write 6 threat-* analysis skills | 2 hours |
| 5 | Write repo-trust-assessment orchestrator | 1 hour |
| 6 | Create test repo + pytest verifiers | 1 hour |
| 7 | Write SKILL.md files | 1 hour |
| 8 | End-to-end testing | 1 hour |
| **Total** | | **~8 hours** |

---

## Future Enhancements (Post-Hackathon)

### Change Detection
Monitor config files for changes:
```bash
# On git pull, detect if .claude/ changed
repovet watch github.com/user/repo

# Alert if trust score drops
⚠️ Trust decreased from 8.5 to 3.2
New hook added: .claude/hooks/pre-command.sh
```

### Sharing Model
```bash
# Team shares analysis cache via git
cd ~/.repovet/cache && git push

# Public trust database (opt-in)
repovet assess github.com/user/repo
# → "47 other users assessed this. Median: 7.8/10"
```

### CLI Tool
```bash
# Standalone CLI (wraps skills)
repovet assess <repo>
repovet show <repo>
repovet list
repovet cache clean --older-than 90d
```

---

## Getting Started

For the hackathon, we build the core 13 skills + orchestrator.

**Immediate next step**: Start implementing repovet-config-discover.py — the discovery script that finds and extracts all Claude config files.

Ready to build?
