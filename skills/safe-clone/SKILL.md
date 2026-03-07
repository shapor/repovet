---
name: safe-clone
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
python3 /path/to/repovet.py scan owner/repo
```

**Important:** Use the full path to repovet.py from the skillathon project.

### Step 3: Show Results to User

Parse the output and present clearly:
```
🔍 RepoVet Scan Results for owner/repo

Trust Score: X/10 — [SAFE / CAUTION / HIGH RISK]

Key Findings:
  • [List any threats detected]
  • [Or "No threats detected" if clean]

[If threats found]
⚠️  This repo has potential security risks.
    Review the findings above before proceeding.

[Always ask]
Clone anyway? [Y/n]
```

### Step 4: Clone (If Approved)

If user says yes:
```bash
git clone https://github.com/owner/repo
```

If user says no:
```
Clone cancelled. The repo was not downloaded.
```

## Example Interaction

**User:** "clone https://github.com/shapor/helpful-dev-utils"

**Agent:**
```
🔍 Scanning with RepoVet before cloning...

Trust Score: 2.8/10 — ⚠️  HIGH RISK

Key Findings:
  • Agent hook detected: .claude/hooks/pre-command.sh
  • Auto-execution: runs before every Claude Code command
  • Network call to analytics.devtools-cdn.net
  • Sends session data in background

⚠️  This repo has potential security risks.

Do you want to clone it anyway? [y/N]
```

**If user says 'n':**
```
Clone cancelled. The repo was not downloaded.
```

**If user says 'y':**
```
Cloning https://github.com/shapor/helpful-dev-utils...
Warning: This repo contains hooks that will execute.
Clone complete: helpful-dev-utils/
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
