---
name: git-commit-intel
allowed-tools: Bash Read
description: |
  Extract comprehensive git commit history from any repository into a structured
  CSV for analysis. Use this when assessing repository trust, analyzing contributor
  patterns, measuring development velocity, or investigating security-relevant
  commits. Trigger when the user asks about a repo's history, maintenance status,
  who contributes, or whether a project is actively developed. Do NOT use for
  GitHub-specific data like PRs or issues — use github-project-intel for that.
---

# Git Commit Intel

Extract git commit history into CSV for downstream analysis by other RepoVet skills.

## When to Use

- **Trust assessment**: Evaluating whether a repository is actively maintained
- **Contributor analysis**: Understanding who works on the code, bus factor, org diversity
- **Velocity measurement**: Commit frequency, merge patterns, code churn
- **Security history**: Finding security-related commits, force-pushes, suspicious patterns
- **Pre-adoption review**: Before depending on a library, assess its development health

## Prerequisites

- Python 3.10+
- The target repository must be cloned locally (the script reads from the git log)
- Optional: `gh` CLI authenticated for GitHub PR enrichment (`--github` flag)

## How to Run

The script lives at `scripts/git-history-to-csv.py` relative to the skillathon project root.

### Basic: current repo

```bash
.venv/bin/python scripts/git-history-to-csv.py -o /home/shapor/.repovet/cache/{repo-name}/commits.csv
```

### Specify a repo path

```bash
.venv/bin/python scripts/git-history-to-csv.py /path/to/repo -o /home/shapor/.repovet/cache/{repo-name}/commits.csv
```

### Multiple repos at once

```bash
.venv/bin/python scripts/git-history-to-csv.py /path/to/repo1 /path/to/repo2 -o commits.csv
```

### Limit to last N commits (faster for large repos)

```bash
.venv/bin/python scripts/git-history-to-csv.py -n 500 /path/to/repo -o commits.csv
```

### Include all branches (not just current)

```bash
.venv/bin/python scripts/git-history-to-csv.py --all /path/to/repo -o commits.csv
```

### Enrich with GitHub PR data

```bash
.venv/bin/python scripts/git-history-to-csv.py --github /path/to/repo -o commits.csv
```

This adds PR metadata to each commit by querying the GitHub GraphQL API. Requires
the `gh` CLI to be installed and authenticated.

## Output Location

Store output in the RepoVet cache:

```
/home/shapor/.repovet/cache/{repo-name}/commits.csv
```

For GitHub-hosted repos, use the full path:

```
/home/shapor/.repovet/cache/github.com/{owner}/{repo}/commits.csv
```

## CSV Fields

### Git Fields (always present)

| Field | Description |
|---|---|
| `repo_name` | Repository directory name |
| `commit_hash` | Full SHA-1 hash |
| `tree_hash` | Tree object hash |
| `author_name` | Author display name |
| `author_email` | Author email address |
| `author_date` | ISO 8601 authoring timestamp |
| `committer_name` | Committer display name (differs from author on cherry-picks, rebases) |
| `committer_email` | Committer email address |
| `commit_date` | ISO 8601 commit timestamp |
| `subject` | First line of commit message |
| `body` | Remaining commit message text |
| `parent_hashes` | Space-separated parent SHAs |
| `refs` | Branch/tag refs pointing at this commit |
| `is_merge` | `True` if commit has multiple parents |
| `files_changed` | Number of files modified |
| `insertions` | Lines added |
| `deletions` | Lines removed |
| `changed_files` | JSON array of file paths touched |
| `lang_stats` | JSON object: `{language: {ins: N, dels: N}}` |
| `dir_stats` | JSON object: `{top_dir: {ins: N, dels: N}}` |

### GitHub PR Fields (with `--github` flag)

| Field | Description |
|---|---|
| `pr_number` | Associated PR number |
| `pr_url` | PR URL on GitHub |
| `pr_title` | PR title |
| `pr_author` | PR author login |
| `pr_created_at` | PR creation timestamp |
| `pr_merged_at` | PR merge timestamp |
| `pr_merged_by` | Who merged the PR |
| `pr_labels` | JSON array of label names |
| `pr_reviewers` | JSON object: `{login: review_state}` |
| `pr_time_to_merge_hours` | Hours from PR creation to merge |

## Interpreting the Data

### Key signals for trust assessment

- **Commit frequency**: Regular commits over months/years = healthy. Bursts then silence = risk.
- **Contributor count**: Multiple active contributors = lower bus factor.
- **Merge commits**: Presence of merges suggests a review process exists.
- **`committer != author`**: Indicates patches are reviewed and applied by maintainers.
- **`lang_stats`**: Shows what languages dominate; useful for understanding scope.
- **`dir_stats`**: Reveals which parts of the codebase are actively changed.

### Security-relevant patterns

- Commit subjects containing "CVE", "security", "vulnerability", "fix", "patch"
- Large deletion-only commits (potential history rewriting)
- Commits touching sensitive paths (`.env`, `credentials`, `secrets`)
- `is_merge=False` on main branch with rewritten committer dates

## Workflow Example

Assess a repo before adoption:

```
1. Clone the repo locally
2. Run: .venv/bin/python scripts/git-history-to-csv.py --all -n 1000 /path/to/repo \
       -o /home/shapor/.repovet/cache/github.com/owner/repo/commits.csv
3. Pass commits.csv to contributor-analysis skill
4. Pass commits.csv to repo-health-analysis skill
5. Pass commits.csv to security-history-analysis skill
```

## Common Pitfalls

- **Shallow clones**: If the repo was cloned with `--depth`, the history will be
  truncated. Run `git fetch --unshallow` first.
- **Large repos**: Repos with 100k+ commits will be slow. Use `-n` to limit.
  Start with `-n 1000` for a quick assessment.
- **Detached HEAD**: The script works fine, but `--all` is recommended to capture
  the full picture rather than just the current branch.
- **GitHub rate limits**: The `--github` flag makes batched GraphQL calls (50
  commits per request). For repos with 10k+ commits, this may hit rate limits.
  Use `-n` to limit, or omit `--github` and use the `github-project-intel` skill
  separately for PR data.
- **Binary files**: Numstat reports `-` for binary file insertions/deletions.
  The script handles this by treating them as 0, so binary-heavy repos will
  undercount churn.
- **Bot filtering**: The `--github` PR enrichment filters out bot reviewers
  (dependabot, renovate, copilot, etc.) from the `pr_reviewers` field. The
  commit-level author data is unfiltered.
