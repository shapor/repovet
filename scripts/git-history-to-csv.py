#!/usr/bin/env python3
"""Export git commit history to CSV for ingestion into QueryStory.

Usage:
    # Export current repo (git-only)
    python scripts/git-history-to-csv.py -o commits.csv

    # All QueryStory repos with GitHub PR data
    python scripts/git-history-to-csv.py --github --all \
        ~/src/qs-app ~/src/qs-infra ~/src/qsi-automation -o commits.csv

    # With GitHub PR data (requires `gh` CLI and auth)
    python scripts/git-history-to-csv.py --github -o commits.csv

    # Export last 500 commits per repo
    python scripts/git-history-to-csv.py -n 500 -o commits.csv

    # Upload to QueryStory
    python scripts/git-history-to-csv.py --github -o commits.csv
    qscli datasource upload --file commits.csv --name "Git Commits"

Fields exported (git):
    repo_name, commit_hash, tree_hash, author_name, author_email, author_date,
    committer_name, committer_email, commit_date, subject, body,
    parent_hashes, refs, is_merge, files_changed, insertions, deletions,
    changed_files, lang_stats, dir_stats

Additional fields with --github:
    pr_number, pr_url, pr_title, pr_author, pr_created_at, pr_merged_at,
    pr_merged_by, pr_labels, pr_reviewers, pr_time_to_merge_hours
"""

import argparse
import csv
import json
import os
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone

# NUL-separated fields, SOH as record separator
LOG_FORMAT = "%x01%H%x00%T%x00%an%x00%ae%x00%aI%x00%cn%x00%ce%x00%cI%x00%P%x00%D%x00%s%x00%b"

GIT_FIELDS = [
    "repo_name",
    "commit_hash",
    "tree_hash",
    "author_name",
    "author_email",
    "author_date",
    "committer_name",
    "committer_email",
    "commit_date",
    "subject",
    "body",
    "parent_hashes",
    "refs",
    "is_merge",
    "files_changed",
    "insertions",
    "deletions",
    "changed_files",
    "lang_stats",
    "dir_stats",
]

GITHUB_FIELDS = [
    "pr_number",
    "pr_url",
    "pr_title",
    "pr_author",
    "pr_created_at",
    "pr_merged_at",
    "pr_merged_by",
    "pr_labels",
    "pr_reviewers",
    "pr_time_to_merge_hours",
]

# Extension to language mapping
EXT_LANG = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".go": "Go",
    ".rs": "Rust",
    ".java": "Java",
    ".rb": "Ruby",
    ".php": "PHP",
    ".c": "C",
    ".h": "C",
    ".cpp": "C++",
    ".cc": "C++",
    ".hpp": "C++",
    ".cs": "C#",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".scala": "Scala",
    ".sh": "Shell",
    ".bash": "Shell",
    ".zsh": "Shell",
    ".sql": "SQL",
    ".html": "HTML",
    ".htm": "HTML",
    ".css": "CSS",
    ".scss": "CSS",
    ".less": "CSS",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".toml": "TOML",
    ".xml": "XML",
    ".md": "Markdown",
    ".rst": "reStructuredText",
    ".tf": "Terraform",
    ".hcl": "Terraform",
    ".proto": "Protobuf",
    ".graphql": "GraphQL",
    ".jinja2": "Jinja",
    ".j2": "Jinja",
    ".dockerfile": "Docker",
}

BOT_LOGINS = {
    "copilot",
    "copilot-pull-request-reviewer",
    "copilot-swe-agent",
    "github-actions",
    "dependabot",
    "renovate",
    "codecov",
}


def is_bot(login: str) -> bool:
    low = login.lower()
    return low in BOT_LOGINS or "[bot]" in low


# GraphQL fragment for PR data from a commit
GQL_COMMIT_FRAGMENT = """
    ... on Commit {
        associatedPullRequests(first: 1) {
            nodes {
                number
                title
                url
                createdAt
                mergedAt
                author { login }
                mergedBy { login }
                labels(first: 10) { nodes { name } }
                reviews(first: 20) { nodes { author { login } state } }
            }
        }
    }
"""

GITHUB_BATCH_SIZE = 50


def run_git(args: list[str], repo_path: str) -> str:
    result = subprocess.run(
        ["git", "-C", repo_path, *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        print(f"git error: {result.stderr.strip()}", file=sys.stderr)
        sys.exit(1)
    return result.stdout


def lang_for_file(fname: str) -> str:
    """Map filename to language. Handles special filenames like Dockerfile, Makefile."""
    basename = os.path.basename(fname).lower()
    if basename in ("dockerfile", "containerfile"):
        return "Docker"
    if basename in ("makefile", "gnumakefile"):
        return "Makefile"
    _, ext = os.path.splitext(basename)
    return EXT_LANG.get(ext, "Other")


def top_dir(fname: str) -> str:
    """Get top-level directory, or '.' for root files."""
    parts = fname.split("/", 1)
    return parts[0] if len(parts) > 1 else "."


def get_numstats(repo_path: str, limit: int | None, all_branches: bool = False) -> dict:
    """Get per-commit file stats with language and directory breakdowns."""
    cmd = ["log", "--format=%H", "--numstat"]
    if all_branches:
        cmd.append("--all")
    if limit:
        cmd += [f"-{limit}"]
    raw = run_git(cmd, repo_path)

    stats = {}
    current_hash = None
    files_changed = insertions = deletions = 0
    files: list[str] = []
    lang_ins: dict[str, int] = defaultdict(int)
    lang_dels: dict[str, int] = defaultdict(int)
    dir_ins: dict[str, int] = defaultdict(int)
    dir_dels: dict[str, int] = defaultdict(int)

    def save() -> None:
        nonlocal current_hash, files_changed, insertions, deletions, files
        nonlocal lang_ins, lang_dels, dir_ins, dir_dels
        if current_hash:
            stats[current_hash] = {
                "files_changed": files_changed,
                "insertions": insertions,
                "deletions": deletions,
                "files": files,
                "lang_stats": {
                    k: {"ins": lang_ins[k], "dels": lang_dels[k]} for k in lang_ins | lang_dels
                },
                "dir_stats": {
                    k: {"ins": dir_ins[k], "dels": dir_dels[k]} for k in dir_ins | dir_dels
                },
            }
        current_hash = None
        files_changed = insertions = deletions = 0
        files = []
        lang_ins = defaultdict(int)
        lang_dels = defaultdict(int)
        dir_ins = defaultdict(int)
        dir_dels = defaultdict(int)

    for raw_line in raw.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if len(line) == 40 and "\t" not in line:
            save()
            current_hash = line
        else:
            parts = line.split("\t")
            if len(parts) == 3:
                ins_s, dels_s, fname = parts
                ins = int(ins_s) if ins_s != "-" else 0
                dels = int(dels_s) if dels_s != "-" else 0
                files_changed += 1
                insertions += ins
                deletions += dels
                files.append(fname)
                lang = lang_for_file(fname)
                lang_ins[lang] += ins
                lang_dels[lang] += dels
                d = top_dir(fname)
                dir_ins[d] += ins
                dir_dels[d] += dels
    save()

    return stats


def get_commits(repo_path: str, limit: int | None, all_branches: bool = False) -> list[dict]:
    cmd = ["log", f"--format={LOG_FORMAT}"]
    if all_branches:
        cmd.append("--all")
    if limit:
        cmd += [f"-{limit}"]
    raw = run_git(cmd, repo_path)

    records = raw.split("\x01")
    commits = []
    for raw_record in records:
        record = raw_record.strip()
        if not record:
            continue
        parts = record.split("\x00")
        if len(parts) < 12:
            continue

        commit_hash = parts[0]
        parents = parts[8].strip()
        commits.append(
            {
                "commit_hash": commit_hash,
                "tree_hash": parts[1],
                "author_name": parts[2],
                "author_email": parts[3],
                "author_date": parts[4],
                "committer_name": parts[5],
                "committer_email": parts[6],
                "commit_date": parts[7],
                "parent_hashes": parents,
                "refs": parts[9].strip(),
                "subject": parts[10],
                "body": parts[11].strip(),
                "is_merge": len(parents.split()) > 1,
            }
        )

    return commits


def repo_name(repo_path: str) -> str:
    """Get repository name from the directory name of the git toplevel."""
    toplevel = run_git(["rev-parse", "--show-toplevel"], repo_path).strip()
    return os.path.basename(toplevel)


def detect_github_repo(repo_path: str) -> str | None:
    """Detect owner/repo from git remote origin URL."""
    try:
        url = run_git(["remote", "get-url", "origin"], repo_path).strip()
    except SystemExit:
        return None
    # git@github.com:owner/repo.git or https://github.com/owner/repo.git
    for prefix in ("git@github.com:", "https://github.com/"):
        if url.startswith(prefix):
            return url[len(prefix) :].removesuffix(".git")
    return None


def get_github_pr_data(hashes: list[str], github_repo: str) -> dict:
    """Fetch PR data for commits via GitHub GraphQL API in batches."""
    owner, repo = github_repo.split("/", 1)
    result = {}

    for batch_start in range(0, len(hashes), GITHUB_BATCH_SIZE):
        batch = hashes[batch_start : batch_start + GITHUB_BATCH_SIZE]
        batch_num = batch_start // GITHUB_BATCH_SIZE + 1
        total_batches = (len(hashes) + GITHUB_BATCH_SIZE - 1) // GITHUB_BATCH_SIZE
        print(
            f"  Fetching GitHub data: batch {batch_num}/{total_batches} "
            f"({batch_start + 1}-{batch_start + len(batch)} of {len(hashes)} commits)",
            file=sys.stderr,
        )

        # Build batched GraphQL query
        fields = []
        for i, h in enumerate(batch):
            fields.append(f'c{i}: object(expression: "{h}") {{ {GQL_COMMIT_FRAGMENT} }}')
        query = f'{{ repository(owner: "{owner}", name: "{repo}") {{ {" ".join(fields)} }} }}'

        proc = subprocess.run(
            ["gh", "api", "graphql", "-f", f"query={query}"],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            print(f"  GitHub API error: {proc.stderr.strip()}", file=sys.stderr)
            # Continue with partial data rather than failing
            continue

        data = json.loads(proc.stdout).get("data", {}).get("repository", {})
        for i, h in enumerate(batch):
            obj = data.get(f"c{i}")
            if not obj:
                continue
            nodes = obj.get("associatedPullRequests", {}).get("nodes", [])
            if not nodes:
                continue
            pr = nodes[0]
            reviews = pr.get("reviews", {}).get("nodes", [])
            # Deduplicate reviewers: keep strongest state per reviewer
            state_priority = {"APPROVED": 3, "CHANGES_REQUESTED": 2, "COMMENTED": 1}
            reviewer_map = {}
            for r in reviews:
                login = (r.get("author") or {}).get("login", "")
                if not login or is_bot(login):
                    continue
                state = r.get("state", "")
                prev = reviewer_map.get(login, "")
                if state_priority.get(state, 0) > state_priority.get(prev, 0):
                    reviewer_map[login] = state

            # Calculate time to merge
            ttm = ""
            created = pr.get("createdAt", "")
            merged = pr.get("mergedAt", "")
            if created and merged:
                fmt = "%Y-%m-%dT%H:%M:%SZ"
                try:
                    dt = datetime.strptime(merged, fmt).replace(
                        tzinfo=timezone.utc
                    ) - datetime.strptime(created, fmt).replace(tzinfo=timezone.utc)
                    ttm = round(dt.total_seconds() / 3600, 1)
                except ValueError:
                    pass

            result[h] = {
                "pr_number": pr.get("number", ""),
                "pr_url": pr.get("url", ""),
                "pr_title": pr.get("title", ""),
                "pr_author": (pr.get("author") or {}).get("login", ""),
                "pr_created_at": created,
                "pr_merged_at": merged,
                "pr_merged_by": (pr.get("mergedBy") or {}).get("login", ""),
                "pr_labels": json.dumps([n["name"] for n in pr.get("labels", {}).get("nodes", [])]),
                "pr_reviewers": json.dumps(dict(reviewer_map.items())),
                "pr_time_to_merge_hours": ttm,
            }

    return result


def process_repo(
    repo_path: str, limit: int | None, github: bool, all_branches: bool = False
) -> list[dict]:
    """Extract commits from a single repo, with optional GitHub enrichment."""
    name = repo_name(repo_path)
    branch_msg = " (all branches)" if all_branches else ""
    print(f"Processing {name}{branch_msg} ({repo_path})...", file=sys.stderr)

    commits = get_commits(repo_path, limit, all_branches)
    numstats = get_numstats(repo_path, limit, all_branches)

    # Merge numstat data
    empty_stats = {
        "files_changed": 0,
        "insertions": 0,
        "deletions": 0,
        "files": [],
        "lang_stats": {},
        "dir_stats": {},
    }
    for commit in commits:
        commit["repo_name"] = name
        s = numstats.get(commit["commit_hash"], empty_stats)
        commit["files_changed"] = s["files_changed"]
        commit["insertions"] = s["insertions"]
        commit["deletions"] = s["deletions"]
        commit["changed_files"] = json.dumps(s["files"])
        commit["lang_stats"] = json.dumps(s["lang_stats"])
        commit["dir_stats"] = json.dumps(s["dir_stats"])

    # GitHub enrichment
    if github:
        gh_repo = detect_github_repo(repo_path)
        if not gh_repo:
            print(
                f"  Warning: could not detect GitHub repo for {name}, skipping",
                file=sys.stderr,
            )
        else:
            print(f"  Fetching GitHub PR data for {gh_repo}...", file=sys.stderr)
            hashes = [c["commit_hash"] for c in commits]
            pr_data = get_github_pr_data(hashes, gh_repo)
            print(
                f"  Found PR data for {len(pr_data)}/{len(commits)} commits",
                file=sys.stderr,
            )
            empty_pr = dict.fromkeys(GITHUB_FIELDS, "")
            for commit in commits:
                commit.update(pr_data.get(commit["commit_hash"], empty_pr))

    print(f"  {len(commits)} commits from {name}", file=sys.stderr)
    return commits


def main():
    parser = argparse.ArgumentParser(description="Export git history to CSV")
    parser.add_argument(
        "repos", nargs="*", default=["."], help="Git repo paths (default: current dir)"
    )
    parser.add_argument("-o", "--output", default="-", help="Output CSV file (default: stdout)")
    parser.add_argument("-n", "--limit", type=int, help="Max number of commits per repo")
    parser.add_argument(
        "--github",
        action="store_true",
        help="Enrich with GitHub PR data (requires `gh` CLI)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Include commits from all branches, not just the current one",
    )
    args = parser.parse_args()

    fields = GIT_FIELDS + GITHUB_FIELDS if args.github else GIT_FIELDS
    all_commits = []
    for repo_path in args.repos:
        all_commits.extend(process_repo(repo_path, args.limit, args.github, args.all))

    if args.output == "-":
        writer = csv.DictWriter(sys.stdout, fieldnames=fields)
        writer.writeheader()
        writer.writerows(all_commits)
        print(f"Exported {len(all_commits)} commits", file=sys.stderr)
    else:
        with open(args.output, "w", newline="", encoding="utf-8") as out:
            writer = csv.DictWriter(out, fieldnames=fields)
            writer.writeheader()
            writer.writerows(all_commits)
        repo_summary = ", ".join(repo_name(r) for r in args.repos)
        print(
            f"Exported {len(all_commits)} commits from {repo_summary} to {args.output}",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
