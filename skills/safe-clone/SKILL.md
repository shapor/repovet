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

Run this exact command (replace owner/repo with actual values):
```bash
/home/shapor/src/skillathon/.venv/bin/python /home/shapor/src/skillathon/scripts/repovet.py scan owner/repo
```

Do NOT search for repovet.py. It is at `/home/shapor/src/skillathon/scripts/repovet.py`. Just run it.

### Step 3: Show Results and Ask User

Parse the RepoVet output and present it clearly to the user.

**If score >= 7 (safe):**
Show 2 options:
1. Yes, clone it
2. No, cancel

**If score < 7 (threats detected):**

**YOU MUST show EXACTLY 3 options using AskUserQuestion. NOT 2. THREE options:**

1. **Deep dive analysis** — Clone to cache, run all 10 threat detection agents in parallel to analyze exactly what the malicious code does. This is the most useful option for the user.
2. **Clone anyway** — Clone despite the security findings.
3. **Cancel** — Do not clone.

**The "Deep dive analysis" option MUST be the FIRST option** because it's the most useful when threats are found. The user wants to understand WHAT the threats do before deciding.

Use AskUserQuestion with these exact labels:
- "Deep dive analysis" (description: "Clone to cache, run 10 threat analysis agents to inspect what the hooks/scripts actually do")
- "Clone anyway" (description: "Clone despite findings — hooks will be present")
- "Cancel" (description: "Do not clone")

### Step 4a: Clone

**If user chooses "Yes, clone it":**
```bash
git clone https://github.com/owner/repo
```

### Step 4b: Deep Dive Analysis

**If user chooses "Deep dive analysis":**

1. Clone repo to temp location (RepoVet already did this, use the cache at `~/.repovet/cache/owner-repo/`)

2. Run the relevant threat detection skills based on what RepoVet found:
   - If "Auto-execution hook" detected → `/skill threat-auto-execution ~/.repovet/cache/owner-repo/`
   - If "Network exfiltration" detected → `/skill threat-network-exfil ~/.repovet/cache/owner-repo/`
   - If "Credential access" detected → `/skill threat-credential-access ~/.repovet/cache/owner-repo/`
   - If "Remote code execution" detected → `/skill threat-remote-code-execution ~/.repovet/cache/owner-repo/`
   - If "Obfuscation" detected → `/skill threat-obfuscation ~/.repovet/cache/owner-repo/`
   - If "Prompt injection" detected → `/skill threat-prompt-injection ~/.repovet/cache/owner-repo/`

3. Show the detailed threat analysis to the user

4. Ask again: "Clone to your workspace anyway? [y/N]"
   - If yes → `git clone https://github.com/owner/repo`
   - If no → done

### Step 4c: Cancel

**If user chooses "No, cancel":**

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
