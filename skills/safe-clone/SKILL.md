---
name: safe-clone
allowed-tools: Bash Read Glob Grep AskUserQuestion
description: >
  Clone GitHub repos safely by scanning them with RepoVet first. Use whenever
  the user wants to clone a repository. Trigger on "clone this repo", "git clone",
  "get the code from", or any variant of cloning/downloading a repo.
---

# Safe Clone

Scan a repo with RepoVet BEFORE cloning it. Follow these steps EXACTLY.

## MANDATORY RULES

- You MUST use AskUserQuestion after scanning. No exceptions.
- You MUST NOT skip the question or auto-proceed to reading files.
- You MUST NOT run python3 -c inline scripts. Ever.
- You MUST NOT try to analyze hook contents before asking the user.
- You MUST follow steps 1, 2, 3 in order. Do not deviate.

## Step 1: Scan

Run this exact command (replace OWNER/REPO with actual values):

```bash
/home/shapor/src/skillathon/.venv/bin/python /home/shapor/src/skillathon/scripts/repovet.py scan OWNER/REPO
```

Show the trust score and key findings to the user.

## Step 2: Ask the user what to do

IMMEDIATELY after showing scan results, you MUST call the AskUserQuestion tool.

If score < 7, provide EXACTLY these 3 options:

Question: "This repo has security concerns. What would you like to do?"
Options:
1. label: "Deep dive analysis", description: "Clone to cache and run 10 threat analysis agents to inspect exactly what the hooks and scripts do"
2. label: "Clone anyway", description: "Clone to current directory despite the findings"
3. label: "Cancel", description: "Do not clone this repository"

If score >= 7, provide 2 options:

Question: "Scan looks clean. Clone this repo?"
Options:
1. label: "Yes, clone it", description: "Clone to current directory"
2. label: "Cancel", description: "Do not clone"

STOP HERE AND WAIT FOR THE USER'S RESPONSE. Do not proceed until they answer.

## Step 3: Act on user's choice

### If "Deep dive analysis":

Invoke the repo-trust-assessment skill for a full Phase 2 deep dive:
- Clone to /home/shapor/.repovet/cache/github.com/OWNER/REPO/repo/
- Extract commits.csv and discovery.json
- Run all threat detection skills in parallel (threat-auto-execution, threat-network-exfil, threat-remote-code-execution, threat-credential-access, threat-obfuscation, threat-repo-write, threat-prompt-injection)
- Show the visual display with repovet-display.py
- Then ask: "Now that you've seen the details, clone to your workspace or cancel?"

### If "Clone anyway" or "Yes, clone it":

```bash
git clone https://github.com/OWNER/REPO
```

### If "Cancel":

Say "Clone cancelled. The repo was not downloaded."
