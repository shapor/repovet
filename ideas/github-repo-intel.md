# GitHub Repo Intel

## Elevator Pitch
A skill suite that turns any GitHub repo into a comprehensive intelligence report — who built it, how it evolved, what's risky, and whether you should trust it. Powered by scripts that extract and analyze git/GitHub metadata deterministically.

## Why This Wins
- **Genuinely useful**: everyone evaluates repos (hiring, due diligence, OSS adoption, security review)
- **Script-heavy**: real value is deterministic code extraction, not text generation — this is the "tools wrapped in skills" thesis
- **Verifiable**: outputs are factual and testable (top contributors, language breakdown, file flags)
- **Timely**: agent config files (.claude, .cursor, AGENTS.md) as attack surface is a live concern
- **Underserved**: no existing skill for this in any registry we surveyed
- **Fast to build**: existing git-history-to-csv.py and github-to-csv.py are the foundation

## Use Cases
1. **"Someone sent me a repo, WTF is this?"** — instant overview
2. **Hiring/interview prep** — "What did this candidate actually contribute?"
3. **Security review** — "Should I trust this repo? Malicious .claude files?"
4. **OSS adoption** — "Is this actively maintained? Bus factor?"
5. **Competitive intel** — "What's this company building? How fast? Who?"

## Existing Scripts (our head start)

### scripts/git-history-to-csv.py
Extracts per-commit data from any local git repo:
- commit hash, author name/email, committer, dates, subject, body
- parent hashes, refs, merge detection
- per-commit file stats: files changed, insertions, deletions
- per-commit language breakdown (40+ extension mappings)
- per-commit directory breakdown
- Optional `--github` flag enriches with PR data via GraphQL (pr_number, title, author, labels, reviewers, time-to-merge)
- Supports multiple repos, commit limits, all-branches mode

### scripts/github-to-csv.py
Extracts full GitHub project data via GraphQL API:
- **PRs**: state, author, reviewers, review decisions, review timing, labels, additions/deletions, commit count, comment counts (human vs bot separated), review thread counts (resolved vs unresolved, bot vs human), time-to-merge, time-to-close, draft status, branch names, body text
- **Issues**: state, author, assignees, labels, milestone, comment count, state reason, time-to-close, body text
- Bot detection built in (copilot, dependabot, renovate, etc.)
- Paginated GraphQL for complete data extraction

## Sub-Skills Architecture

### Tier 1: Data Extraction (run scripts → produce CSVs)

#### 1. git-commit-intel
**What it does**: Clones/accesses the repo, runs git-history-to-csv.py, outputs structured commit data.
**Script**: Thin wrapper around existing git-history-to-csv.py
**Output**: `commits.csv` with all git metadata + language/directory stats
**When to trigger**: Any time user mentions a repo and wants to understand its history, contributors, or evolution

#### 2. github-project-intel
**What it does**: Runs github-to-csv.py to extract PR and issue data.
**Script**: Thin wrapper around existing github-to-csv.py with `--prs --issues`
**Output**: `prs.csv` + `issues.csv` with full project management data
**When to trigger**: When user wants to understand project health, review culture, issue patterns, or contributor dynamics beyond just commits
**Requires**: `gh` CLI authenticated

### Tier 2: Analysis (read CSVs → produce insights)

#### 3. contributor-analysis
**What it does**: Reads commit + PR CSVs, computes contributor intelligence.
**Key analyses**:
- Top contributors by commits, lines, and review activity
- Bus factor calculation (min contributors covering 80% of recent commits)
- Bot vs human commit ratio
- Per-author: first/last commit, active period, languages touched, dirs owned
- For hiring: isolate a specific author's commits, PR review patterns, complexity
- Timezone inference from commit timestamps
**Output**: Structured contributor report (markdown or JSON)

#### 4. repo-health-analysis
**What it does**: Reads all CSVs, computes project health metrics.
**Key analyses**:
- Commit velocity (weekly/monthly trends, acceleration/deceleration)
- PR review culture: median time-to-first-review, time-to-merge, review participation
- Issue health: open/closed ratio, median time-to-close, stale issue count
- Bot automation level (what % of threads/comments are bots)
- Activity gaps and staleness indicators
- Language evolution over time
**Output**: Structured health report

### Tier 3: Security (the differentiator)

#### 5. claude-config-audit
**What it does**: Scans repo for agent configuration files and evaluates them for security risks.
**This is the novel/timely angle — nobody else is doing this.**

**What it scans**:
- `.claude/` directory: settings.json, commands/, hooks
- `CLAUDE.md` / `.claude.md` files (at root and nested)
- `.cursorrules`, `.cursor/` directory
- `AGENTS.md`, `.github/copilot-instructions.md`
- Skills directories: any `SKILL.md` files and their `scripts/` subdirs
- `.github/workflows/` for CI that runs agent tools

**What it flags**:

*High severity*:
- Shell commands in hooks (pre/post command hooks that run arbitrary code)
- `dangerouslySkipPermissions` or equivalent permission bypasses
- Network calls in skill scripts (curl, wget, requests, fetch to external URLs)
- Data exfiltration patterns (piping file contents to external services)
- Encoded/obfuscated payloads (base64, hex-encoded strings that decode to commands)
- Prompt injection patterns ("ignore previous instructions", "you are now", role overrides)

*Medium severity*:
- Overly permissive tool allowlists (allowing Bash with no restrictions)
- File system writes outside the project directory
- Environment variable access (reading secrets, tokens, credentials)
- Instructions to disable safety features or skip verification

*Low severity / informational*:
- Presence of any agent config files (just awareness)
- Custom commands defined
- Skill count and sources
- Which agent tools are configured

**Output**: Security report with severity-rated findings, file paths, line numbers, and explanations

## Skill Composition (how they work together)

For the hackathon task, the scenario would be:

> "My team is evaluating this open-source library for adoption. Clone it and tell me: who maintains it, is it healthy, and are there any security concerns — especially in its agent configuration files."

The agent would:
1. Clone the repo
2. Run **git-commit-intel** → commits.csv
3. Run **github-project-intel** → prs.csv, issues.csv
4. Run **contributor-analysis** on the CSVs → contributor report
5. Run **repo-health-analysis** on the CSVs → health report
6. Run **claude-config-audit** on the repo → security report
7. Synthesize into a final intel report

Skills 1-2 are scripts that produce data. Skills 3-4 are analysis prompts that read data. Skill 5 is the security scanner. The final synthesis is what the LLM does naturally.

## What Makes This Benchmarkable

Deterministic verifiers (pytest assertions):
- Top 3 contributors by commit count match expected? ✓
- Bus factor calculated correctly? ✓
- Language breakdown within 5% tolerance? ✓
- Specific .claude hook with shell command detected? ✓
- Prompt injection pattern in CLAUDE.md flagged? ✓
- PR review median time-to-merge within tolerance? ✓
- Bot commit ratio correct? ✓
- All required report sections present? ✓

## Build Plan

| Step | What | Time | Dependencies |
|------|------|------|-------------|
| 1 | Adapt git-history-to-csv.py into skill script (minor CLI tweaks) | 30 min | — |
| 2 | Adapt github-to-csv.py into skill script | 30 min | — |
| 3 | Write claude-config-audit.py (the new code) | 2 hours | — |
| 4 | Write SKILL.md files for each sub-skill | 1 hour | 1-3 |
| 5 | Create test repo with known properties + malicious .claude files | 1 hour | 3 |
| 6 | Write pytest verifiers | 1 hour | 4-5 |
| 7 | Write instruction.md (conversational task description) | 30 min | 4 |
| 8 | Write task.toml + Dockerfile | 30 min | all |
| 9 | Test end-to-end with and without skills | 1 hour | all |
| **Total** | | **~7-8 hours** | |

## Competition Assessment
- No existing skill for repo intelligence in any registry
- GitHub's own insights page is limited and not agent-accessible
- Tools like git-fame, git-quick-stats exist but aren't packaged as skills
- The claude-config-audit angle is completely novel and topical
- Nobody at the hackathon pitched anything like this

## Open Questions
- Should we package as one umbrella skill or 5 separate skills? (Leaning: separate, because the hackathon values "composing 2-3 skills together")
- How much of the analysis should be in scripts vs letting the LLM analyze the CSVs? (Leaning: scripts for deterministic stuff like bus factor, LLM for synthesis)
- Do we need a task for the Harbor benchmark format or just publish the skills? (Need to check what track we're targeting)
