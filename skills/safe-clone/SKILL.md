---
name: safe-clone
allowed-tools: Bash Read Glob Grep AskUserQuestion Task
description: >
  Clone GitHub repos safely by scanning them with RepoVet first. Use whenever
  the user wants to clone a repository. Trigger on "clone this repo", "git clone",
  "get the code from", or any variant of cloning/downloading a repo.
---

# Safe Clone — FOLLOW THESE STEPS EXACTLY

Extract OWNER and REPO from the URL (e.g. `github.com/shapor/helpful-dev-utils` → OWNER=`shapor`, REPO=`helpful-dev-utils`).

## Step 1: Scan

YOUR VERY FIRST ACTION must be this Bash call. No other tool calls before this. Do not search for scripts. Do not use Explore. Do not read cache. Do not ls. THIS EXACT COMMAND:

```
/home/shapor/src/skillathon/.venv/bin/python /home/shapor/src/skillathon/scripts/repovet.py scan OWNER/REPO
```

Show the trust score and findings to the user.

## Step 2: Ask the user

YOUR VERY NEXT ACTION after showing results must be calling AskUserQuestion with EXACTLY these 3 options. Not 2. THREE options. Do not invent your own question. Do not rephrase. Use this EXACT JSON:

```
{
  "questions": [{
    "question": "The scan found security concerns. What would you like to do?",
    "header": "Next step",
    "options": [
      {"label": "Deep dive analysis (Recommended)", "description": "Run 7 parallel threat analysis agents to inspect the hooks and scripts in detail"},
      {"label": "Clone anyway", "description": "Clone to current directory despite the findings"},
      {"label": "Cancel", "description": "Do not clone this repository"}
    ],
    "multiSelect": false
  }]
}
```

STOP. WAIT for the user to respond. Do not proceed until they choose.

## Step 3a: If user chose "Clone anyway"

Run: `git clone https://github.com/OWNER/REPO`

Done.

## Step 3b: If user chose "Cancel"

Say "Clone cancelled." Done.

## Step 3c: If user chose "Deep dive analysis"

Run these Bash commands one at a time. For each, check if the output already exists and skip if so.

**Create cache dir:**
```
mkdir -p /home/shapor/.repovet/cache/github.com/OWNER/REPO
```

**Clone repo (skip if `/home/shapor/.repovet/cache/github.com/OWNER/REPO/repo/.git` already exists):**
```
gh repo clone OWNER/REPO /home/shapor/.repovet/cache/github.com/OWNER/REPO/repo
```

**Extract commits (skip if `commits.csv` already exists):**
```
/home/shapor/src/skillathon/.venv/bin/python /home/shapor/src/skillathon/scripts/git-history-to-csv.py /home/shapor/.repovet/cache/github.com/OWNER/REPO/repo -o /home/shapor/.repovet/cache/github.com/OWNER/REPO/commits.csv
```

**Discover agent configs (skip if `discovery.json` already exists):**
```
/home/shapor/src/skillathon/.venv/bin/python /home/shapor/src/skillathon/scripts/repovet-config-discover.py /home/shapor/.repovet/cache/github.com/OWNER/REPO/repo -o /home/shapor/.repovet/cache/github.com/OWNER/REPO/discovery.json
```

**Show heatmap (tell user to press ctrl+o to expand):**
```
/home/shapor/src/skillathon/.venv/bin/python /home/shapor/src/skillathon/scripts/repovet-display.py /home/shapor/.repovet/cache/github.com/OWNER/REPO/commits.csv
```

**Launch 7 threat agents in parallel.** Send ONE message with 7 Task tool calls. Each uses `subagent_type: "general-purpose"`. The 7 prompts:

1. `Use the threat-auto-execution skill to analyze /home/shapor/.repovet/cache/github.com/OWNER/REPO/discovery.json and report all findings.`
2. `Use the threat-network-exfil skill to analyze /home/shapor/.repovet/cache/github.com/OWNER/REPO/discovery.json and report all findings.`
3. `Use the threat-remote-code-execution skill to analyze /home/shapor/.repovet/cache/github.com/OWNER/REPO/discovery.json and report all findings.`
4. `Use the threat-credential-access skill to analyze /home/shapor/.repovet/cache/github.com/OWNER/REPO/discovery.json and report all findings.`
5. `Use the threat-obfuscation skill to analyze /home/shapor/.repovet/cache/github.com/OWNER/REPO/discovery.json and report all findings.`
6. `Use the threat-repo-write skill to analyze /home/shapor/.repovet/cache/github.com/OWNER/REPO/discovery.json and report all findings.`
7. `Use the threat-prompt-injection skill to analyze /home/shapor/.repovet/cache/github.com/OWNER/REPO/discovery.json and report all findings.`

After all 7 complete, summarize the combined findings.

Then call AskUserQuestion again:

```
{
  "questions": [{
    "question": "Deep dive complete. What would you like to do?",
    "header": "Next step",
    "options": [
      {"label": "Clone", "description": "Clone to current directory"},
      {"label": "Cancel", "description": "Do not clone this repository"}
    ],
    "multiSelect": false
  }]
}
```

## THINGS YOU MUST NOT DO

- Do not use Explore or Glob to find repovet.py. The path is `/home/shapor/src/skillathon/scripts/repovet.py`. Use it.
- Do not use relative paths like `scripts/repovet.py` or `python3 scripts/repovet.py`. Use the full absolute paths shown above.
- Do not use `python3 -c` for anything. Use the scripts.
- Do not use `~` or `$HOME` or any shell variable in commands.
- Do not delete any clones or cached files.
- Do not skip the AskUserQuestion step. Do not make up your own question format.
- Do not load threat skills with the Skill tool. Launch them as Task agents.
- Do not proceed past Step 2 without user input.
