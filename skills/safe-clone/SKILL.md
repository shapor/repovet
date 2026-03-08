---
name: safe-clone
allowed-tools: Bash Read Glob Grep
description: >
  Clone GitHub repos safely by scanning them with RepoVet first. Use whenever
  the user wants to clone a repository. Trigger on "clone this repo", "git clone",
  "get the code from", or any variant of cloning/downloading a repo.
---

# Safe Clone

Scan a repo with RepoVet BEFORE cloning it.

## Step 1: Scan

```bash
/home/shapor/src/skillathon/.venv/bin/python /home/shapor/src/skillathon/scripts/repovet.py scan OWNER/REPO
```

## Step 2: Present results and ask user

After showing the trust score and findings, use AskUserQuestion to ask the user what to do.

If score >= 7: offer "Clone" and "Cancel".

If score < 7: offer EXACTLY these 3 options in this order:
1. "Deep dive" — "Clone to cache, run threat analysis agents to inspect what the code actually does before you decide"
2. "Clone anyway" — "Clone despite findings"
3. "Cancel" — "Do not clone"

DO NOT skip this question. DO NOT auto-proceed. DO NOT read files instead of asking.

## Step 3a: If user picks "Deep dive"

Use the repo-trust-assessment skill to do a full Phase 2 deep dive:
- Clone to /home/shapor/.repovet/cache/github.com/OWNER/REPO/repo/
- Extract commits, run config discovery
- Run all threat detection skills in parallel
- Show the visual display
- Then ask again: clone to workspace or cancel?

## Step 3b: If user picks "Clone anyway"

```bash
git clone https://github.com/OWNER/REPO
```

## Step 3c: If user picks "Cancel"

Say "Clone cancelled."
