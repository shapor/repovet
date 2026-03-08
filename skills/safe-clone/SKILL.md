---
name: safe-clone
allowed-tools: Bash Read Glob Grep AskUserQuestion
description: >
  Clone GitHub repos safely by scanning them with RepoVet first. Use whenever
  the user wants to clone a repository. Trigger on "clone this repo", "git clone",
  "get the code from", or any variant of cloning/downloading a repo.
---

# Safe Clone

## Step 1: Scan (DO THIS FIRST, NOTHING ELSE)

Run EXACTLY this command. Do not search for repovet.py. Do not check cache. Do not ls anything. Just run it:

```bash
/home/shapor/src/skillathon/.venv/bin/python /home/shapor/src/skillathon/scripts/repovet.py scan OWNER/REPO
```

Replace OWNER/REPO with the actual owner and repo name.

Show the trust score and findings to the user.

## Step 2: Ask user (MANDATORY — do not skip)

Call AskUserQuestion with these options if score < 7:

```json
{
  "questions": [{
    "question": "What would you like to do?",
    "header": "Next step",
    "options": [
      {"label": "Deep dive analysis (Recommended)", "description": "Run 7 parallel threat analysis agents to inspect what the hooks and scripts actually do"},
      {"label": "Clone anyway", "description": "Clone to current directory despite the security findings"},
      {"label": "Cancel", "description": "Do not clone this repository"}
    ],
    "multiSelect": false
  }]
}
```

STOP and WAIT for user response.

## Step 3: Act on choice

If "Deep dive": Run these commands in order. Skip any step where the file already exists:

```bash
mkdir -p /home/shapor/.repovet/cache/github.com/OWNER/REPO
```
```bash
gh repo clone OWNER/REPO /home/shapor/.repovet/cache/github.com/OWNER/REPO/repo
```
```bash
/home/shapor/src/skillathon/.venv/bin/python /home/shapor/src/skillathon/scripts/git-history-to-csv.py /home/shapor/.repovet/cache/github.com/OWNER/REPO/repo -o /home/shapor/.repovet/cache/github.com/OWNER/REPO/commits.csv
```
```bash
/home/shapor/src/skillathon/.venv/bin/python /home/shapor/src/skillathon/scripts/repovet-config-discover.py /home/shapor/.repovet/cache/github.com/OWNER/REPO/repo -o /home/shapor/.repovet/cache/github.com/OWNER/REPO/discovery.json
```
```bash
/home/shapor/src/skillathon/.venv/bin/python /home/shapor/src/skillathon/scripts/repovet-display.py /home/shapor/.repovet/cache/github.com/OWNER/REPO/commits.csv
```

Then launch 7 threat analysis Task agents in parallel, each reading /home/shapor/.repovet/cache/github.com/OWNER/REPO/discovery.json.

If "Clone anyway": `git clone https://github.com/OWNER/REPO`

If "Cancel": Say "Clone cancelled."
