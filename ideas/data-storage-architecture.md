# Data Storage Architecture

## The Question
Where do we store:
- CSV exports (commits.csv, prs.csv, issues.csv)
- Discovery JSON (config files found, executables extracted)
- Threat analysis results
- Trust assessment reports
- Cache/hashes for change detection (future)

## Options Evaluated

### ❌ Option 1: In the repo being analyzed (`.claude-intel/`)
```
analyzed-repo/
├── .claude-intel/
│   ├── commits.csv
│   ├── prs.csv
│   ├── discovery.json
│   └── trust-report.md
```

**Pros**: Co-located with the repo, easy to find
**Cons**:
- Pollutes the repo you're analyzing
- Needs to be gitignored
- Conflicts if multiple people analyze the same repo
- Weird if you're analyzing someone else's repo (you're writing to their code)

**Verdict**: No.

---

### ❌ Option 2: In current working directory
```
~/projects/
├── analyzed-repo/  (the repo)
└── analyzed-repo-intel/  (our data)
    ├── commits.csv
    ├── prs.csv
    └── trust-report.md
```

**Pros**: Keeps data separate from analyzed repo
**Cons**:
- Clutters workspace with parallel directories
- Hard to find later ("where did I put that trust report?")
- No central cache across multiple analyses

**Verdict**: No.

---

### ✅ Option 3: Global cache directory (`~/.repovet/`)

```
~/.repovet/
├── cache/
│   └── github.com/
│       └── user/
│           └── repo-name/
│               ├── metadata.json         # repo info, last analyzed, trust score
│               ├── commits.csv
│               ├── prs.csv
│               ├── issues.csv
│               ├── discovery.json        # config files + executables
│               ├── threats.json          # threat analysis results
│               ├── trust-report.md       # human-readable report
│               └── hashes.json           # for change detection (future)
│
├── config/
│   ├── settings.json                     # user preferences
│   └── policy.yml                        # trust policies (future)
│
├── skills/
│   ├── repo-trust-assessment/            # the skills themselves
│   ├── git-commit-intel/
│   ├── contributor-analysis/
│   └── threat-*/
│
└── shared/                               # shared trust database (future)
    └── trust-scores.db                   # crowd-sourced scores
```

**Pros**:
- Centralized: Easy to find all past analyses
- Clean: Doesn't pollute repos or workspace
- Cacheable: Re-analyzing a repo can reuse data
- Shareable: Natural place for syncing/sharing (see below)
- Future-proof: Room for config, policies, plugins

**Cons**:
- Not immediately visible when working in a repo
- Needs path normalization (different clone paths → same cache key)

**Verdict**: Yes, this is the way.

---

## Naming: What's the "XXX" in `~/.XXX`?

### Candidates

**repovet** ✓
- Clear purpose (guarding repos)
- Professional sounding
- Not Claude-specific (could work with other agents)
- Short, easy to type

**repo-trust**
- Descriptive but generic
- A bit boring

**repo-intel**
- Matches "GitHub Repo Intel" concept
- Broader than just trust/security
- Could be confused with espionage tooling?

**claudeguard**
- Claude-specific
- Clear it's about Claude Code security
- Might be too narrow if we expand beyond Claude

**trustkit**
- Generic, could be anything
- Sounds like a framework, not a tool

**reposcope**
- Kinda cool, implies examining repos
- Not immediately obvious what it does

### Top Candidates

1. **repotrust** (`~/.repotrust/`)
   - Simple, direct, memorable
   - "Repo trust assessment" maps perfectly
   - Short CLI: `repotrust assess <repo>`
   - Could brand as "RepoTrust" with capital T

2. **repoaudit** (`~/.repoaudit/`)
   - Audit implies thoroughness
   - Professional/enterprise feel
   - `repoaudit assess`, `repoaudit show`
   - Downside: "audit" might imply compliance focus

3. **reposcope** (`~/.reposcope/`)
   - Cool name, implies examining/inspecting
   - `reposcope scan`, `reposcope report`
   - Memorable, brandable
   - Downside: Not immediately obvious it's about trust/security

4. **repovault** (`~/.repovault/`)
   - Implies security, storing assessments
   - `repovault check <repo>`
   - Strong security connotation
   - Downside: Might imply it stores repos themselves

5. **repovet** (`~/.repovet/`)
   - "Vet" = investigate thoroughly, verify credentials
   - Super short CLI: `repovet <repo>`
   - Clever double meaning: veterinary checkup for repos
   - Very memorable, fun but serious

6. **gitguard** (`~/.gitguard/`)
   - More specific than "repo" (it's really about git repos)
   - `gitguard trust <repo>`
   - Clear security focus
   - Downside: "Guard" is overused (AuthGuard, AppGuard, etc.)

7. **trustkit** (`~/.trustkit/`)
   - Developer-friendly "kit" suffix
   - `trustkit assess`, `trustkit score`
   - Modern tooling feel
   - Downside: Generic, could be for anything

8. **repoprobe** (`~/.repoprobe/`)
   - Probe = investigate, examine
   - `repoprobe scan <repo>`
   - Technical/precise feel
   - Alliterative, easy to remember

9. **reposcan** (`~/.reposcan/`)
   - Simple, clear purpose
   - `reposcan <repo>` (shortest possible)
   - Downside: Very generic, might conflict with existing tools

10. **safetycheck** or **repocheck** (`~/.repocheck/`)
    - Extremely clear what it does
    - `repocheck <repo>` is intuitive
    - Downside: "Check" is bland, not very brandable

### Recommendation: `~/.repovet/` or `~/.repotrust/`

**repovet** (my favorite):
- Shortest to type: `repovet https://github.com/user/repo`
- Clever wordplay (vet = verify + veterinary checkup)
- Memorable and unique
- Not overused in security tools
- Good brand potential: "RepoVet — Trust assessment for code repositories"

**repotrust** (safe choice):
- Most direct mapping to what it does
- Professional, clear
- Easy to explain: "It's called RepoTrust, it assesses repo trust"
- Less clever but more obvious

**Vote**: I'd go with **`repovet`** for personality + brevity, but **`repotrust`** if you want maximum clarity.

---

## Path Normalization

Different ways to reference the same repo need to map to the same cache:

```python
def normalize_repo_path(repo: str) -> str:
    """
    Normalize different repo references to a canonical cache path.

    Examples:
    - "https://github.com/user/repo" -> "github.com/user/repo"
    - "git@github.com:user/repo.git" -> "github.com/user/repo"
    - "~/code/repo" (with git remote) -> "github.com/user/repo"
    - "/tmp/clone123" -> hash of git remote URL
    """

    # If it's a URL, extract owner/repo
    if repo.startswith(('https://', 'git@')):
        return parse_git_url(repo)

    # If it's a local path, check git remote
    if os.path.isdir(repo):
        remote = get_git_remote(repo)
        if remote:
            return parse_git_url(remote)
        else:
            # No remote, use absolute path hash
            return f"local/{hash_path(os.path.abspath(repo))}"

    # Unknown format, use as-is
    return repo.replace('/', '_')
```

Cache key: `~/.repovet/cache/{normalized_path}/`

---

## Sharing Model (Future Feature)

### Use Case 1: Team sharing
Your team analyzes the same repos. Instead of everyone running analysis individually:

```bash
# Set up shared cache on NFS/S3/git
repovet config set shared-cache s3://company-bucket/repovet/

# Or use git
cd ~/.repovet/cache
git init
git remote add origin git@github.com:company/repovet-cache.git

# Now when you analyze a repo:
repovet assess github.com/external/some-lib
# -> Writes to cache, commits, pushes

# Teammate pulls:
cd ~/.repovet/cache && git pull
repovet show github.com/external/some-lib
# -> Instant results, no re-analysis needed
```

**Benefits**:
- Shared trust assessments across team
- Audit trail (git history of when/who analyzed what)
- Consistency (everyone sees same trust scores)

### Use Case 2: Public trust database
Crowd-sourced trust scores, like a "malware database" for repos:

```bash
# Opt-in to public database
repovet config set share-scores true

# When you analyze a repo:
repovet assess github.com/user/repo
# -> Submits anonymized trust score + threat types to public DB

# When assessing a popular repo:
repovet assess github.com/user/popular-repo
# -> "Note: 47 other users assessed this repo. Median score: 7.8/10"
```

**Privacy considerations**:
- Only share: repo URL, trust score, threat categories (not detailed findings)
- Opt-in, not default
- Anonymous (no user identification)
- Can query without contributing

**Implementation**:
- Simple REST API: `POST /scores`, `GET /scores/{owner}/{repo}`
- SQLite DB: `~/.repovet/shared/trust-scores.db`
- Periodic sync with central server (optional)

---

## Data Lifecycle

### On first analysis:
```bash
repovet assess https://github.com/user/repo

1. Clone/access repo
2. Run scripts → CSVs
3. Run analysis → JSON results
4. Generate report → markdown
5. Write everything to ~/.repovet/cache/github.com/user/repo/
6. Create metadata.json:
   {
     "repo": "github.com/user/repo",
     "analyzed_at": "2026-03-07T10:30:00Z",
     "trust_score": 7.5,
     "commit_analyzed": "abc123...",
     "threat_summary": { "critical": 0, "high": 2, "medium": 5 }
   }
```

### On re-analysis:
```bash
repovet assess github.com/user/repo --refresh

1. Check cache: Is there existing data?
2. Compare: Last analyzed commit vs current HEAD
3. Incremental: Only re-analyze if commits changed
4. Update: Write new data, keep old data as history
5. metadata.json gets updated with new timestamp + score
```

### On query:
```bash
repovet show github.com/user/repo

1. Check cache: ~/.repovet/cache/github.com/user/repo/
2. If exists: Display trust-report.md
3. If missing: "Not analyzed yet. Run: repovet assess github.com/user/repo"
```

### On cleanup:
```bash
# Remove old analyses
repovet cache clean --older-than 90d

# Remove specific repo
repovet cache remove github.com/user/repo

# Clear everything
repovet cache clear
```

---

## Integration with Skills

Skills run from Claude Code, which doesn't have a CLI called `repovet`. So:

### Option A: Skills write directly to `~/.repovet/`
```python
# In skill script
import os
CACHE_DIR = os.path.expanduser("~/.repovet/cache")
repo_cache = f"{CACHE_DIR}/{normalize_repo(repo_url)}"
os.makedirs(repo_cache, exist_ok=True)

# Write data
with open(f"{repo_cache}/commits.csv", "w") as f:
    write_commits_csv(f)
```

**Pro**: Simple, direct
**Con**: Skills are tied to this directory structure

### Option B: Skills output to CWD, orchestrator moves to cache
```python
# Skill outputs to current dir
./commits.csv
./prs.csv
./discovery.json

# Orchestrator skill moves them:
import shutil
shutil.move("commits.csv", f"~/.repovet/cache/{repo}/commits.csv")
```

**Pro**: Skills are directory-agnostic
**Con**: Extra moving step, clutters CWD temporarily

### Option C: Skills take output path as parameter
```bash
# Orchestrator calls skills with cache path
python git-history-to-csv.py -o ~/.repovet/cache/github.com/user/repo/commits.csv
```

**Pro**: Flexible, skills don't assume locations
**Con**: Long paths in commands

**Recommendation**: **Option A** for now (direct write to `~/.repovet/`), can refactor later.

---

## CLI vs Skills

### Standalone CLI tool: `repovet`
```bash
repovet assess <repo-url>
repovet show <repo-url>
repovet list
repovet cache clean
```

Use when: Running outside Claude Code, batch processing, CI/CD

### Skills within Claude Code
```
User: "Should I trust this repo?"
Claude: [Uses repo-trust-assessment skill]
        [Writes to ~/.repovet/cache/...]
        [Returns trust report]
```

Use when: Interactive analysis during development

**They share the same cache**, so CLI and skills see the same data.

---

## Summary

| Decision | Choice |
|----------|--------|
| **Storage location** | `~/.repovet/` (global cache) |
| **Tool name** | RepoVet |
| **Cache structure** | `cache/{github.com}/{user}/{repo}/` |
| **Path normalization** | Parse git remotes to canonical form |
| **Sharing model** | Git-based (team) + optional public DB (future) |
| **Skills write to** | `~/.repovet/` directly |
| **CLI name** | `repovet` (can wrap skills or run standalone) |

---

## Next Steps

1. Implement cache directory structure in orchestrator skill
2. Add path normalization logic
3. Create `metadata.json` schema
4. Build simple CLI wrapper (post-hackathon)
5. Design sharing protocol (future)
