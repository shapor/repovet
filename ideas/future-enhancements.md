# Future Enhancements — Beyond the Hackathon

Ideas that are out of scope for the initial build but worth tracking.

---

## Config Change Detection & Monitoring

### The Problem
You trust a repo today, but what about tomorrow? Malicious actors could:
- Add a `.claude/hooks/pre-command.sh` in a later commit
- Modify `CLAUDE.md` to include prompt injection
- Update a skill script to exfiltrate data
- Change settings.json to bypass permissions

**Current state**: Trust assessment is point-in-time. User has to manually re-run.

**Desired state**: Continuous monitoring that alerts on suspicious changes.

### Implementation Ideas

#### Option 1: Hash-based change detection
```bash
# On first trust assessment, store hashes
.repovet-cache.json:
{
  "assessed_at": "2026-03-07T10:30:00Z",
  "trust_score": 7.5,
  "config_hashes": {
    ".claude/settings.json": "a1b2c3d4...",
    "CLAUDE.md": "e5f6g7h8...",
    ".claude/hooks/pre-command.sh": "i9j0k1l2...",
    "skills/deploy/SKILL.md": "m3n4o5p6..."
  },
  "last_commit": "abc123..."
}

# On git pull or file change (via inotify/fswatch)
- Rehash config files
- If any hash changed → trigger alert
- Show diff + re-run trust assessment on changed files
```

**Triggers**:
- **Git pull**: Post-merge git hook that runs hash check
- **File edits**: inotify/fswatch watching `.claude/`, `CLAUDE.md`, `skills/`
- **Manual**: User runs `/check-trust` command

**Alert UX**:
```
⚠️  Claude config files changed since last trust assessment

Changed files:
  - .claude/hooks/pre-command.sh (new file)
  - CLAUDE.md (modified)

Would you like to re-assess trust? [Y/n]
```

#### Option 2: Git-based monitoring
```bash
# Watch for commits that touch config files
git log --oneline --since="last assessment" -- .claude/ CLAUDE.md skills/

# If commits found:
- Show commit messages + authors
- Diff the config changes
- Re-run threat analysis on changed sections only
```

#### Option 3: Continuous background monitoring
```python
# Daemon process (or Claude Code extension feature)
while True:
    for repo in watched_repos:
        if config_files_changed(repo):
            assessment = run_trust_assessment(repo, incremental=True)
            if assessment.trust_score < previous_score - threshold:
                notify_user(f"⚠️ Trust decreased in {repo}")
    sleep(3600)  # check hourly
```

### What to Monitor

**High-priority files** (changes should always alert):
- `.claude/hooks/*.sh` — auto-execution
- `.claude/settings.json` — permission bypasses
- `CLAUDE.md` / `.claude.md` — instruction injection
- `skills/*/scripts/*` — executable skill code

**Medium-priority** (alert if suspicious patterns detected):
- `skills/*/SKILL.md` — check for new bash/python code blocks
- `.github/workflows/*.yml` — CI that might invoke agent tools
- Dependency files if they add known-vulnerable packages

**Low-priority** (log but don't alert):
- README changes, docs, comments
- Test files, CI config (unless they execute agent tools)

### Integration Points

**Git hooks** (`.git/hooks/post-merge`):
```bash
#!/bin/bash
# Run after git pull
repovet check --alert-on-change
```

**File watchers** (inotify on Linux, FSEvents on macOS):
```bash
# Watch for edits while Claude Code is open
fswatch .claude/ CLAUDE.md skills/ | while read file; do
  echo "Config file changed: $file"
  repovet check --incremental "$file"
done
```

**Claude Code integration** (ideal future state):
- Built into Claude Code itself
- Automatic trust check on repo open
- Background monitoring while repo is active
- UI notification on suspicious changes

### Data Storage

**Where to store trust cache?**

Option A: `.repovet-cache.json` in repo (gitignored)
- Pro: Per-repo, easy to access
- Con: Clutters repo, needs to be gitignored

Option B: `~/.config/repovet/repos/` (global cache)
- Pro: Centralized, doesn't touch repo
- Con: Needs to map repo paths, syncing across machines

Option C: Git notes (hidden git metadata)
```bash
git notes --ref=repovet add -m "trust_score: 7.5, assessed: 2026-03-07"
```
- Pro: Lives in git, can be pushed/pulled
- Con: Obscure, not many people use git notes

**Recommended**: Option B (global cache) for initial implementation.

---

## Other Future Enhancements

### 1. Supply Chain Attack Detection
- Monitor for dependency confusion (internal package names on public registries)
- Track maintainer changes on dependencies (has this npm package changed hands?)
- Detect typosquatting (is "reqeusts" really "requests"?)

### 2. Comparison Mode
```bash
# Compare two repos
repovet compare user/repo-a user/repo-b

# Or compare before/after
repovet compare repo@v1.0 repo@v2.0
```

### 3. Trust Score History
```bash
# Graph trust score over time
repovet history user/repo --graph

# Show when trust dropped and why
2026-01-15: 8.5/10 ✓
2026-02-03: 8.3/10 ⚠ (1 outdated dependency)
2026-03-07: 4.2/10 ✗ (malicious hook added)
```

### 4. Team/Org Policy Enforcement
```yaml
# .repovet-policy.yml
min_trust_score: 6.0
block_threats:
  - auto-execution
  - network-exfil
  - credential-access
allow_threats:
  - repo-write  # We use git automation, that's OK

notify_on_change:
  slack_webhook: https://hooks.slack.com/...
  email: security@company.com
```

### 5. Contribution Source Analysis
- Are commits from known GitHub accounts or anonymous/new accounts?
- Have any commits come from compromised accounts? (check against GitHub's security advisories)
- Sudden change in commit patterns (account takeover detection)

### 6. Integration with Claude Code Permissions
```json
// Auto-adjust permission mode based on trust score
{
  "trust_score": 8.5,
  "auto_permission_mode": "normal",  // 8-10: normal, 5-7: ask, 0-4: block
  "blocked_tools": [],
  "require_approval_for": ["Bash"]
}
```

---

## Implementation Priority (Post-Hackathon)

**P0** (Do this first):
- Hash-based change detection on git pull
- Simple alert UX
- Global cache in `~/.config/repovet/`

**P1** (High value):
- File watcher (inotify) for real-time monitoring
- Trust score history tracking
- Incremental re-assessment (only changed files)

**P2** (Nice to have):
- Supply chain attack detection
- Team/org policy enforcement
- Comparison mode

**P3** (Future research):
- Integration with Claude Code permission system
- Contribution source analysis (account compromise detection)
- Distributed trust network (crowd-sourced repo trust scores)

---

## Why Not Now?

These are all out of scope for the hackathon because:
1. **Time**: We have ~8 hours, need to focus on core functionality
2. **Complexity**: Change detection is a product feature, not a skill demo
3. **Dependencies**: Requires Claude Code integration or daemon process
4. **Polish over proof**: Hackathon needs proof-of-concept, not production features

But definitely worth building post-hackathon if the core idea resonates.
