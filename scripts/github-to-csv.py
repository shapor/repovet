#!/usr/bin/env python3
"""Export GitHub PRs and issues to CSV for ingestion into QueryStory.

Usage:
    # Export PRs and issues from current repo
    python scripts/github-to-csv.py --prs -o prs.csv
    python scripts/github-to-csv.py --issues -o issues.csv

    # All QueryStory repos (auto-detect from git remotes)
    python scripts/github-to-csv.py --prs --issues \
        ~/src/qs-app ~/src/qs-infra ~/src/qsi-automation -o github.csv

    # Explicit GitHub repos (no local clone needed)
    python scripts/github-to-csv.py --prs --issues \
        --repo querystory/qs-app --repo querystory/qs-infra \
        --repo querystory/qsi-automation -o github.csv

Requires: `gh` CLI authenticated with GitHub.

Joins with git-history-to-csv.py output on repo_name + pr_number.
"""

import argparse
import csv
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

GITHUB_PAGE_SIZE = 100

PR_FIELDS = [
    "repo_name",
    "pr_number",
    "pr_url",
    "pr_title",
    "pr_body",
    "pr_state",
    "pr_author",
    "pr_created_at",
    "pr_merged_at",
    "pr_closed_at",
    "pr_merged_by",
    "pr_is_draft",
    "pr_base_branch",
    "pr_head_branch",
    "pr_additions",
    "pr_deletions",
    "pr_changed_files",
    "pr_commit_count",
    "pr_comment_count",
    "pr_bot_comment_count",
    "pr_commenters",
    "pr_review_thread_count",
    "pr_resolved_thread_count",
    "pr_bot_thread_count",
    "pr_bot_resolved_thread_count",
    "pr_labels",
    "pr_reviewers",
    "pr_requested_reviewers",
    "pr_review_decision",
    "pr_review_times",
    "pr_first_review_hours",
    "pr_time_to_merge_hours",
    "pr_time_to_close_hours",
]

ISSUE_FIELDS = [
    "repo_name",
    "issue_number",
    "issue_url",
    "issue_title",
    "issue_body",
    "issue_state",
    "issue_author",
    "issue_created_at",
    "issue_closed_at",
    "issue_assignees",
    "issue_labels",
    "issue_comment_count",
    "issue_milestone",
    "issue_state_reason",
    "issue_time_to_close_hours",
]

BOT_LOGINS = {
    "copilot",
    "copilot-pull-request-reviewer",
    "copilot-swe-agent",
    "github-actions",
    "dependabot",
    "renovate",
    "codecov",
}

# PRs have heavy nested data (comments, threads, reviews) so use smaller pages
PR_PAGE_SIZE = 25

GQL_PR_FRAGMENT = """
    number title url state createdAt mergedAt closedAt
    author { login }
    mergedBy { login }
    additions deletions changedFiles
    commits { totalCount }
    comments(first: 100) { nodes { author { login } } }
    reviewThreads(first: 100) {
        nodes { isResolved comments(first: 1) { nodes { author { login } } } }
    }
    reviews(first: 20) { nodes { author { login } state submittedAt } }
    reviewRequests(first: 10) { nodes { requestedReviewer { ... on User { login } } } }
    reviewDecision
    labels(first: 10) { nodes { name } }
    isDraft
    baseRefName headRefName
    body
"""

GQL_ISSUE_FRAGMENT = """
    number title url state stateReason createdAt closedAt
    author { login }
    assignees(first: 10) { nodes { login } }
    labels(first: 10) { nodes { name } }
    milestone { title }
    comments { totalCount }
    body
"""


def run_gh_graphql(query: str) -> dict | None:
    proc = subprocess.run(
        ["gh", "api", "graphql", "-f", f"query={query}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        print(f"  GitHub API error: {proc.stderr.strip()}", file=sys.stderr)
        return None
    return json.loads(proc.stdout)


def hours_between(start: str, end: str) -> str:
    """Calculate hours between two ISO timestamps. Returns '' on failure."""
    if not start or not end:
        return ""
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    try:
        dt = datetime.strptime(end, fmt).replace(tzinfo=timezone.utc) - datetime.strptime(
            start, fmt
        ).replace(tzinfo=timezone.utc)
        return str(round(dt.total_seconds() / 3600, 1))
    except ValueError:
        return ""


def is_bot(login: str) -> bool:
    low = login.lower()
    return low in BOT_LOGINS or "[bot]" in low


def process_reviews(reviews: list[dict], pr_created: str) -> tuple[dict, dict, str]:
    """Process human reviews into deduplicated states and per-reviewer timing.

    Returns (reviewer_states, review_times, first_review_hours) where:
    - reviewer_states: {login: strongest_state} (humans only)
    - review_times: {login: hours_from_pr_creation_to_first_review} (humans only)
    - first_review_hours: hours from PR creation to earliest human review
    """
    state_priority = {"APPROVED": 3, "CHANGES_REQUESTED": 2, "COMMENTED": 1}
    reviewer_states = {}
    first_review_at = {}  # login -> earliest submittedAt
    for r in reviews:
        login = (r.get("author") or {}).get("login", "")
        if not login or is_bot(login):
            continue
        state = r.get("state", "")
        submitted = r.get("submittedAt", "")
        prev = reviewer_states.get(login, "")
        if state_priority.get(state, 0) > state_priority.get(prev, 0):
            reviewer_states[login] = state
        if submitted and (login not in first_review_at or submitted < first_review_at[login]):
            first_review_at[login] = submitted
    review_times = {login: hours_between(pr_created, ts) for login, ts in first_review_at.items()}
    all_times = [t for t in review_times.values() if t != ""]
    first_review_hours = min(all_times) if all_times else ""
    return reviewer_states, review_times, first_review_hours


def detect_github_repo(repo_path: str) -> str | None:
    """Detect owner/repo from git remote origin URL."""
    result = subprocess.run(
        ["git", "-C", repo_path, "remote", "get-url", "origin"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    url = result.stdout.strip()
    for prefix in ("git@github.com:", "https://github.com/"):
        if url.startswith(prefix):
            return url[len(prefix) :].removesuffix(".git")
    return None


def repo_display_name(github_repo: str) -> str:
    """Get short repo name from owner/repo."""
    return github_repo.rsplit("/", maxsplit=1)[-1]


def fetch_prs(github_repo: str) -> list[dict]:
    """Fetch all PRs from a GitHub repo via paginated GraphQL."""
    owner, repo = github_repo.split("/", 1)
    name = repo_display_name(github_repo)
    all_prs = []
    cursor = ""
    page = 0

    while True:
        page += 1
        after = f', after: "{cursor}"' if cursor else ""
        query = f"""{{
            repository(owner: "{owner}", name: "{repo}") {{
                pullRequests(first: {PR_PAGE_SIZE}, states: [MERGED, OPEN, CLOSED],
                             orderBy: {{field: CREATED_AT, direction: DESC}}{after}) {{
                    pageInfo {{ hasNextPage endCursor }}
                    nodes {{ {GQL_PR_FRAGMENT} }}
                }}
            }}
        }}"""

        print(
            f"  Fetching PRs page {page} ({len(all_prs)} so far)...",
            file=sys.stderr,
        )
        resp = run_gh_graphql(query)
        if not resp:
            break

        data = resp.get("data", {}).get("repository", {}).get("pullRequests", {})
        for pr in data.get("nodes", []):
            created = pr.get("createdAt", "")
            merged = pr.get("mergedAt", "")
            closed = pr.get("closedAt", "")
            reviewer_states, review_times, first_review_hours = process_reviews(
                pr.get("reviews", {}).get("nodes", []), created
            )
            # Comment stats (separate bots from humans)
            comment_nodes = pr.get("comments", {}).get("nodes", [])
            commenter_counts = {}
            human_count = bot_count = 0
            for c in comment_nodes:
                login = (c.get("author") or {}).get("login", "")
                if not login:
                    continue
                if is_bot(login):
                    bot_count += 1
                else:
                    human_count += 1
                    commenter_counts[login] = commenter_counts.get(login, 0) + 1
            # Review thread stats: split bot vs human, track resolution
            thread_nodes = pr.get("reviewThreads", {}).get("nodes", [])
            resolved = bot_threads = bot_resolved = 0
            for t in thread_nodes:
                starter = ((t.get("comments", {}).get("nodes") or [{}])[0].get("author") or {}).get(
                    "login", ""
                )
                if t.get("isResolved"):
                    resolved += 1
                    if is_bot(starter):
                        bot_resolved += 1
                if is_bot(starter):
                    bot_threads += 1
            # Requested reviewers (pending, not yet reviewed)
            req_reviewers = [
                (n.get("requestedReviewer") or {}).get("login", "")
                for n in pr.get("reviewRequests", {}).get("nodes", [])
            ]

            all_prs.append(
                {
                    "repo_name": name,
                    "pr_number": pr.get("number", ""),
                    "pr_url": pr.get("url", ""),
                    "pr_title": pr.get("title", ""),
                    "pr_body": (pr.get("body") or "").strip(),
                    "pr_state": pr.get("state", ""),
                    "pr_author": (pr.get("author") or {}).get("login", ""),
                    "pr_created_at": created,
                    "pr_merged_at": merged,
                    "pr_closed_at": closed,
                    "pr_merged_by": (pr.get("mergedBy") or {}).get("login", ""),
                    "pr_is_draft": pr.get("isDraft", False),
                    "pr_base_branch": pr.get("baseRefName", ""),
                    "pr_head_branch": pr.get("headRefName", ""),
                    "pr_additions": pr.get("additions", 0),
                    "pr_deletions": pr.get("deletions", 0),
                    "pr_changed_files": pr.get("changedFiles", 0),
                    "pr_commit_count": pr.get("commits", {}).get("totalCount", 0),
                    "pr_comment_count": human_count,
                    "pr_bot_comment_count": bot_count,
                    "pr_commenters": json.dumps(commenter_counts),
                    "pr_review_thread_count": len(thread_nodes),
                    "pr_resolved_thread_count": resolved,
                    "pr_bot_thread_count": bot_threads,
                    "pr_bot_resolved_thread_count": bot_resolved,
                    "pr_labels": json.dumps(
                        [n["name"] for n in pr.get("labels", {}).get("nodes", [])]
                    ),
                    "pr_reviewers": json.dumps(reviewer_states),
                    "pr_requested_reviewers": json.dumps([r for r in req_reviewers if r]),
                    "pr_review_decision": pr.get("reviewDecision", ""),
                    "pr_review_times": json.dumps(review_times),
                    "pr_first_review_hours": first_review_hours,
                    "pr_time_to_merge_hours": hours_between(created, merged),
                    "pr_time_to_close_hours": hours_between(created, closed),
                }
            )

        page_info = data.get("pageInfo", {})
        if not page_info.get("hasNextPage"):
            break
        cursor = page_info["endCursor"]

    print(f"  {len(all_prs)} PRs from {name}", file=sys.stderr)
    return all_prs


def fetch_issues(github_repo: str) -> list[dict]:
    """Fetch all issues from a GitHub repo via paginated GraphQL."""
    owner, repo = github_repo.split("/", 1)
    name = repo_display_name(github_repo)
    all_issues = []
    cursor = ""
    page = 0

    while True:
        page += 1
        after = f', after: "{cursor}"' if cursor else ""
        query = f"""{{
            repository(owner: "{owner}", name: "{repo}") {{
                issues(first: {GITHUB_PAGE_SIZE}, states: [OPEN, CLOSED],
                       orderBy: {{field: CREATED_AT, direction: DESC}}{after}) {{
                    pageInfo {{ hasNextPage endCursor }}
                    nodes {{ {GQL_ISSUE_FRAGMENT} }}
                }}
            }}
        }}"""

        print(
            f"  Fetching issues page {page} ({len(all_issues)} so far)...",
            file=sys.stderr,
        )
        resp = run_gh_graphql(query)
        if not resp:
            break

        data = resp.get("data", {}).get("repository", {}).get("issues", {})
        for issue in data.get("nodes", []):
            created = issue.get("createdAt", "")
            closed = issue.get("closedAt", "")

            all_issues.append(
                {
                    "repo_name": name,
                    "issue_number": issue.get("number", ""),
                    "issue_url": issue.get("url", ""),
                    "issue_title": issue.get("title", ""),
                    "issue_body": (issue.get("body") or "").strip(),
                    "issue_state": issue.get("state", ""),
                    "issue_author": (issue.get("author") or {}).get("login", ""),
                    "issue_created_at": created,
                    "issue_closed_at": closed,
                    "issue_assignees": json.dumps(
                        [n["login"] for n in issue.get("assignees", {}).get("nodes", [])]
                    ),
                    "issue_labels": json.dumps(
                        [n["name"] for n in issue.get("labels", {}).get("nodes", [])]
                    ),
                    "issue_comment_count": issue.get("comments", {}).get("totalCount", 0),
                    "issue_milestone": (issue.get("milestone") or {}).get("title", ""),
                    "issue_state_reason": issue.get("stateReason", ""),
                    "issue_time_to_close_hours": hours_between(created, closed),
                }
            )

        page_info = data.get("pageInfo", {})
        if not page_info.get("hasNextPage"):
            break
        cursor = page_info["endCursor"]

    print(f"  {len(all_issues)} issues from {name}", file=sys.stderr)
    return all_issues


def write_csv(rows: list[dict], fields: list[str], output: str):
    if output == "-":
        writer = csv.DictWriter(sys.stdout, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    else:
        with open(output, "w", newline="", encoding="utf-8") as out:
            writer = csv.DictWriter(out, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)


def resolve_repos(dirs: list[str], explicit_repos: list[str]) -> list[str]:
    """Resolve list of GitHub owner/repo strings from dirs and explicit repos."""
    repos = list(explicit_repos)
    for d in dirs:
        gh_repo = detect_github_repo(d)
        if gh_repo:
            repos.append(gh_repo)
        else:
            print(
                f"Warning: could not detect GitHub repo for {d}, skipping",
                file=sys.stderr,
            )
    repos = list(dict.fromkeys(repos))  # dedup preserving order
    if not repos:
        print(
            "Error: no GitHub repos found. Use --repo or pass git repo dirs.",
            file=sys.stderr,
        )
        sys.exit(1)
    return repos


def main():
    parser = argparse.ArgumentParser(description="Export GitHub PRs and issues to CSV")
    parser.add_argument(
        "dirs",
        nargs="*",
        default=["."],
        help="Git repo dirs to detect GitHub repos from (default: current dir)",
    )
    parser.add_argument(
        "--repo",
        action="append",
        default=[],
        help="Explicit GitHub owner/repo (can be repeated)",
    )
    parser.add_argument("--prs", action="store_true", help="Export pull requests")
    parser.add_argument("--issues", action="store_true", help="Export issues")
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Output CSV file. With both --prs and --issues, used as prefix (prs_X.csv, issues_X.csv)",
    )
    args = parser.parse_args()

    if not args.prs and not args.issues:
        parser.error("Specify --prs, --issues, or both")

    # If dirs are explicitly given, don't include default "."
    dirs = args.dirs if args.dirs != ["."] or not args.repo else []
    github_repos = resolve_repos(dirs, args.repo)

    if args.prs:
        all_prs = []
        for gh_repo in github_repos:
            print(f"Fetching PRs from {gh_repo}...", file=sys.stderr)
            all_prs.extend(fetch_prs(gh_repo))
        pr_output = args.output or "-"
        if args.issues and args.output and args.output != "-":
            # Both modes: derive filenames from output
            base, ext = os.path.splitext(args.output)
            pr_output = f"{base}_prs{ext}" if not base.endswith("_prs") else args.output
        write_csv(all_prs, PR_FIELDS, pr_output)
        if pr_output != "-":
            print(f"Exported {len(all_prs)} PRs to {pr_output}", file=sys.stderr)

    if args.issues:
        all_issues = []
        for gh_repo in github_repos:
            print(f"Fetching issues from {gh_repo}...", file=sys.stderr)
            all_issues.extend(fetch_issues(gh_repo))
        issue_output = args.output or "-"
        if args.prs and args.output and args.output != "-":
            base, ext = os.path.splitext(args.output)
            issue_output = f"{base}_issues{ext}" if not base.endswith("_issues") else args.output
        write_csv(all_issues, ISSUE_FIELDS, issue_output)
        if issue_output != "-":
            print(f"Exported {len(all_issues)} issues to {issue_output}", file=sys.stderr)


if __name__ == "__main__":
    main()
