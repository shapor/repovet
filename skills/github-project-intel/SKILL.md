---
name: github-project-intel
allowed-tools: Bash Read
description: |
  Extract GitHub pull request and issue data into structured CSVs for analysis.
  Use this when assessing project health, review culture, issue responsiveness,
  or community engagement. Trigger when the user asks about PR review practices,
  issue triage speed, project governance, or contributor collaboration patterns.
  Do NOT use for git commit history — use git-commit-intel for that. This skill
  requires the `gh` CLI authenticated with GitHub.
---

# GitHub Project Intel

Extract PR and issue data from GitHub repositories into CSV for downstream
analysis by other RepoVet skills.

## When to Use

- **Review culture assessment**: Do PRs get reviewed? How fast? By whom?
- **Project health**: Are issues being triaged and closed? Stale issue ratio?
- **Community engagement**: External contributors? Issue response times?
- **Governance analysis**: Review decisions, approval patterns, draft PR usage
- **Bot activity audit**: How much CI/bot noise vs. human interaction?

## Prerequisites

- Python 3.10+
- `gh` CLI installed and authenticated (`gh auth status` to verify)
- No local clone needed if using `--repo` flag (queries GitHub API directly)

## How to Run

The script lives at `scripts/github-to-csv.py` relative to the skillathon project root.

### Export PRs from current repo

```bash
python scripts/github-to-csv.py --prs -o ~/.repovet/cache/{repo-name}/prs.csv
```

### Export issues from current repo

```bash
python scripts/github-to-csv.py --issues -o ~/.repovet/cache/{repo-name}/issues.csv
```

### Export both (output splits into two files automatically)

```bash
python scripts/github-to-csv.py --prs --issues -o ~/.repovet/cache/{repo-name}/data.csv
```

This produces `data_prs.csv` and `data_issues.csv`.

### Explicit GitHub repo (no local clone needed)

```bash
python scripts/github-to-csv.py --prs --issues \
    --repo owner/repo-name \
    -o ~/.repovet/cache/github.com/owner/repo-name/data.csv
```

### Multiple repos

```bash
python scripts/github-to-csv.py --prs --issues \
    --repo owner/repo1 --repo owner/repo2 \
    -o output.csv
```

### From local repo directories

```bash
python scripts/github-to-csv.py --prs ~/src/my-repo -o prs.csv
```

The script auto-detects the GitHub remote from the git origin URL.

## Output Location

Store output in the RepoVet cache:

```
~/.repovet/cache/github.com/{owner}/{repo}/prs.csv
~/.repovet/cache/github.com/{owner}/{repo}/issues.csv
```

## CSV Fields

### PR Fields (`--prs`)

| Field | Description |
|---|---|
| `repo_name` | Short repository name |
| `pr_number` | PR number |
| `pr_url` | Full URL to the PR |
| `pr_title` | PR title |
| `pr_body` | PR description text |
| `pr_state` | `MERGED`, `OPEN`, or `CLOSED` |
| `pr_author` | PR author GitHub login |
| `pr_created_at` | Creation timestamp |
| `pr_merged_at` | Merge timestamp (empty if not merged) |
| `pr_closed_at` | Close timestamp (empty if still open) |
| `pr_merged_by` | Login of the person who merged |
| `pr_is_draft` | Whether the PR is/was a draft |
| `pr_base_branch` | Target branch (e.g., `main`) |
| `pr_head_branch` | Source branch name |
| `pr_additions` | Lines added |
| `pr_deletions` | Lines removed |
| `pr_changed_files` | Number of files changed |
| `pr_commit_count` | Commits in the PR |
| `pr_comment_count` | Human comment count (bots excluded) |
| `pr_bot_comment_count` | Bot comment count |
| `pr_commenters` | JSON object: `{login: count}` (humans only) |
| `pr_review_thread_count` | Total review threads |
| `pr_resolved_thread_count` | Resolved review threads |
| `pr_bot_thread_count` | Review threads started by bots |
| `pr_bot_resolved_thread_count` | Bot threads that were resolved |
| `pr_labels` | JSON array of label names |
| `pr_reviewers` | JSON object: `{login: strongest_review_state}` |
| `pr_requested_reviewers` | JSON array of pending reviewer logins |
| `pr_review_decision` | `APPROVED`, `CHANGES_REQUESTED`, `REVIEW_REQUIRED`, or empty |
| `pr_review_times` | JSON object: `{login: hours_to_first_review}` |
| `pr_first_review_hours` | Hours from PR creation to first human review |
| `pr_time_to_merge_hours` | Hours from creation to merge |
| `pr_time_to_close_hours` | Hours from creation to close |

### Issue Fields (`--issues`)

| Field | Description |
|---|---|
| `repo_name` | Short repository name |
| `issue_number` | Issue number |
| `issue_url` | Full URL to the issue |
| `issue_title` | Issue title |
| `issue_body` | Issue description text |
| `issue_state` | `OPEN` or `CLOSED` |
| `issue_author` | Issue author GitHub login |
| `issue_created_at` | Creation timestamp |
| `issue_closed_at` | Close timestamp (empty if still open) |
| `issue_assignees` | JSON array of assignee logins |
| `issue_labels` | JSON array of label names |
| `issue_comment_count` | Total comment count |
| `issue_milestone` | Milestone title (if assigned) |
| `issue_state_reason` | `COMPLETED`, `NOT_PLANNED`, or empty |
| `issue_time_to_close_hours` | Hours from creation to close |

## Interpreting the Data

### PR review culture signals

- **`pr_first_review_hours`**: Median under 24h = strong review culture
- **`pr_reviewers` diversity**: Multiple reviewers across PRs = healthy
- **`pr_review_decision`**: Frequent `APPROVED` = formal review process
- **`pr_comment_count` vs `pr_bot_comment_count`**: High bot ratio may indicate
  heavy automation but thin human review
- **`pr_time_to_merge_hours`**: Very fast merges (< 1h) with no reviewers = risk

### Issue health signals

- **`issue_time_to_close_hours`**: Median time shows responsiveness
- **`issue_state_reason`**: High `NOT_PLANNED` ratio may indicate triaging or abandonment
- **Open vs. closed ratio**: Many old open issues = potential maintenance burden
- **`issue_assignees`**: Empty assignees on old issues = no ownership

### Bot detection

The script automatically identifies and separates bot activity for these known bots:
`copilot`, `copilot-pull-request-reviewer`, `copilot-swe-agent`, `github-actions`,
`dependabot`, `renovate`, `codecov`. Any login containing `[bot]` is also detected.

Bot data is separated into dedicated fields (`pr_bot_comment_count`,
`pr_bot_thread_count`, `pr_bot_resolved_thread_count`) so analysis skills can
distinguish human engagement from automation noise.

## Workflow Example

Assess a repo's project health:

```
1. Run: python scripts/github-to-csv.py --prs --issues \
       --repo owner/repo \
       -o ~/.repovet/cache/github.com/owner/repo/data.csv
2. This produces data_prs.csv and data_issues.csv
3. Pass prs.csv to repo-health-analysis skill (review culture metrics)
4. Pass issues.csv to repo-health-analysis skill (responsiveness metrics)
5. Join with git-commit-intel output on repo_name + pr_number to correlate
   commit-level detail with PR-level metadata
```

## Common Pitfalls

- **Authentication**: `gh` CLI must be authenticated. Run `gh auth status` first.
- **Rate limits**: GraphQL API allows 5,000 points/hour. Repos with 10k+ PRs
  may exhaust this. Monitor stderr for API errors.
- **Large repos**: PRs fetch at 25/page (heavy nested data); issues at 100/page.
- **Private repos**: Ensure your `gh` token has appropriate scope for org repos.
- **Dual output naming**: With both `--prs` and `--issues`, output auto-splits
  into `{base}_prs.csv` and `{base}_issues.csv`. Avoid `_prs`/`_issues` suffixes
  in your `-o` filename.
