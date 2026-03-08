---
name: safe-clone
allowed-tools: Bash Read Glob Grep AskUserQuestion
description: >
  Clone GitHub repos safely by scanning them with RepoVet first. Use whenever
  the user wants to clone a repository. Trigger on "clone this repo", "git clone",
  "get the code from", or any variant of cloning/downloading a repo.
---

# Safe Clone

## Instructions

When this skill is activated, execute ONLY these tool calls in this EXACT order. Do not add any other tool calls between them.

### Tool Call 1: Run RepoVet scan

Call the Bash tool with:
```
/home/shapor/src/skillathon/.venv/bin/python /home/shapor/src/skillathon/scripts/repovet.py scan OWNER/REPO
```

### Tool Call 2: Summarize scan results

Output a short summary of the trust score and findings as text to the user. Do not call any tools in this step.

### Tool Call 3: Ask the user

Call the AskUserQuestion tool with this exact structure:

```json
{
  "questions": [{
    "question": "What would you like to do?",
    "header": "Next step",
    "options": [
      {"label": "Deep dive analysis (Recommended)", "description": "Clone to cache and run 10 parallel threat analysis agents to inspect what the hooks and scripts actually do before you decide"},
      {"label": "Clone anyway", "description": "Clone to current directory despite the security findings"},
      {"label": "Cancel", "description": "Do not clone this repository"}
    ],
    "multiSelect": false
  }]
}
```

If the scan score was >= 7 (no threats), use only 2 options: "Clone" and "Cancel".

### Tool Call 4: Act on response

- If "Deep dive": You MUST do ALL of these steps:
  1. Check if clone exists: `ls /home/shapor/.repovet/cache/github.com/OWNER/REPO/repo/.git`
     - If it exists: skip cloning, reuse it
     - If not: `gh repo clone OWNER/REPO /home/shapor/.repovet/cache/github.com/OWNER/REPO/repo`
  2. Check if data exists: `ls /home/shapor/.repovet/cache/github.com/OWNER/REPO/commits.csv`
     - If it exists: skip extraction, reuse it
     - If not: `.venv/bin/python scripts/git-history-to-csv.py /home/shapor/.repovet/cache/github.com/OWNER/REPO/repo -o /home/shapor/.repovet/cache/github.com/OWNER/REPO/commits.csv`
  3. Check if discovery exists: `ls /home/shapor/.repovet/cache/github.com/OWNER/REPO/discovery.json`
     - If it exists: skip, reuse it
     - If not: `.venv/bin/python scripts/repovet-config-discover.py /home/shapor/.repovet/cache/github.com/OWNER/REPO/repo -o /home/shapor/.repovet/cache/github.com/OWNER/REPO/discovery.json`
  4. Show visual display: `.venv/bin/python scripts/repovet-display.py /home/shapor/.repovet/cache/github.com/OWNER/REPO/commits.csv`
  5. Launch ALL 7 threat skills as parallel Task agents reading /home/shapor/.repovet/cache/github.com/OWNER/REPO/discovery.json: threat-auto-execution, threat-network-exfil, threat-remote-code-execution, threat-credential-access, threat-obfuscation, threat-repo-write, threat-prompt-injection
  6. Show combined findings and ask clone or cancel
  Do NOT just read the hook files yourself. You MUST run the threat skills as Task agents.
  REUSE CACHED DATA. Do NOT re-clone or re-extract if files already exist.
- If "Clone anyway": Run `git clone https://github.com/OWNER/REPO`
- If "Cancel": Say "Clone cancelled."

## What NOT to do

- Do NOT read any files from the repo before asking the user
- Do NOT run python3 -c inline scripts
- Do NOT try to cat or analyze hook contents before step 3
- Do NOT skip the AskUserQuestion call
- Do NOT add extra analysis steps between steps 1 and 3
