#!/usr/bin/env python3
"""Analyze git/GitHub CSV data using DuckDB and produce a structured report.

Usage:
    # Analyze commits only
    python repovet-analyze.py commits.csv

    # Analyze commits + PRs + issues
    python repovet-analyze.py commits.csv --prs prs.csv --issues issues.csv

    # Output JSON instead of markdown
    python repovet-analyze.py commits.csv --json

    # Analyze a specific author (hiring eval mode)
    python repovet-analyze.py commits.csv --author "alice@example.com"

    # Save to file
    python repovet-analyze.py commits.csv -o report.md
"""

import argparse
import json
import sys
from datetime import datetime, timezone

import duckdb


def connect(commits_csv: str, prs_csv: str | None, issues_csv: str | None) -> duckdb.DuckDBPyConnection:
    """Create DuckDB connection with CSV files loaded as views."""
    db = duckdb.connect(":memory:")

    db.execute(f"""
        CREATE VIEW commits AS
        SELECT *,
               TRY_CAST(author_date AS TIMESTAMP WITH TIME ZONE) AS author_ts,
               TRY_CAST(commit_date AS TIMESTAMP WITH TIME ZONE) AS commit_ts
        FROM read_csv_auto('{commits_csv}', header=true, ignore_errors=true)
    """)

    if prs_csv:
        db.execute(f"""
            CREATE VIEW prs AS
            SELECT *,
                   TRY_CAST(pr_created_at AS TIMESTAMP WITH TIME ZONE) AS created_ts,
                   TRY_CAST(pr_merged_at AS TIMESTAMP WITH TIME ZONE) AS merged_ts,
                   TRY_CAST(pr_closed_at AS TIMESTAMP WITH TIME ZONE) AS closed_ts
            FROM read_csv_auto('{prs_csv}', header=true, ignore_errors=true)
        """)

    if issues_csv:
        db.execute(f"""
            CREATE VIEW issues AS
            SELECT *,
                   TRY_CAST(issue_created_at AS TIMESTAMP WITH TIME ZONE) AS created_ts,
                   TRY_CAST(issue_closed_at AS TIMESTAMP WITH TIME ZONE) AS closed_ts
            FROM read_csv_auto('{issues_csv}', header=true, ignore_errors=true)
        """)

    return db


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------

def repo_overview(db: duckdb.DuckDBPyConnection) -> dict:
    """Basic repo stats."""
    row = db.execute("""
        SELECT
            COUNT(*) AS total_commits,
            COUNT(DISTINCT author_name) AS unique_authors,
            MIN(author_ts) AS first_commit,
            MAX(author_ts) AS last_commit,
            SUM(insertions) AS total_insertions,
            SUM(deletions) AS total_deletions,
            SUM(files_changed) AS total_files_changed,
            COUNT(*) FILTER (WHERE is_merge = 'True' OR is_merge = 'true' OR is_merge = '1') AS merge_commits
        FROM commits
    """).fetchone()

    first = row[2]
    last = row[3]
    now = datetime.now(timezone.utc)
    age_days = (now - first).days if first else 0
    since_last = (now - last).days if last else 0

    return {
        "total_commits": row[0],
        "unique_authors": row[1],
        "first_commit": str(first) if first else None,
        "last_commit": str(last) if last else None,
        "age_days": age_days,
        "days_since_last_commit": since_last,
        "total_insertions": row[4] or 0,
        "total_deletions": row[5] or 0,
        "total_files_changed": row[6] or 0,
        "merge_commits": row[7],
    }


def top_contributors(db: duckdb.DuckDBPyConnection, limit: int = 20) -> list[dict]:
    """Top contributors by commits, lines, and date range."""
    rows = db.execute(f"""
        SELECT
            author_name,
            author_email,
            COUNT(*) AS commits,
            SUM(insertions) AS insertions,
            SUM(deletions) AS deletions,
            SUM(files_changed) AS files_changed,
            MIN(author_ts) AS first_commit,
            MAX(author_ts) AS last_commit,
            COUNT(DISTINCT strftime(author_ts, '%Y-%m')) AS active_months
        FROM commits
        GROUP BY author_name, author_email
        ORDER BY commits DESC
        LIMIT {limit}
    """).fetchall()

    return [
        {
            "name": r[0],
            "email": r[1],
            "commits": r[2],
            "insertions": r[3] or 0,
            "deletions": r[4] or 0,
            "files_changed": r[5] or 0,
            "first_commit": str(r[6]) if r[6] else None,
            "last_commit": str(r[7]) if r[7] else None,
            "active_months": r[8],
        }
        for r in rows
    ]


def bus_factor(db: duckdb.DuckDBPyConnection) -> dict:
    """Calculate bus factor: min contributors covering 80% of recent commits (last 6 months)."""
    row = db.execute("""
        WITH recent AS (
            SELECT author_name, COUNT(*) AS commits
            FROM commits
            WHERE author_ts >= NOW() - INTERVAL '6 months'
            GROUP BY author_name
            ORDER BY commits DESC
        ),
        total AS (
            SELECT SUM(commits) AS total FROM recent
        ),
        cumulative AS (
            SELECT
                author_name,
                commits,
                SUM(commits) OVER (ORDER BY commits DESC) AS running_total,
                (SELECT total FROM total) AS total
            FROM recent
        )
        SELECT
            COUNT(*) FILTER (WHERE running_total - commits < total * 0.8) AS bf,
            (SELECT total FROM total) AS recent_commits,
            (SELECT COUNT(DISTINCT author_name) FROM recent) AS recent_authors
        FROM cumulative
    """).fetchone()

    return {
        "bus_factor": row[0] if row[0] else 0,
        "recent_commits_6mo": row[1] or 0,
        "recent_authors_6mo": row[2] or 0,
    }


def commit_velocity(db: duckdb.DuckDBPyConnection) -> list[dict]:
    """Commits per month over time."""
    rows = db.execute("""
        SELECT
            strftime(author_ts, '%Y-%m') AS month,
            COUNT(*) AS commits,
            COUNT(DISTINCT author_name) AS authors,
            SUM(insertions) AS insertions,
            SUM(deletions) AS deletions
        FROM commits
        WHERE author_ts IS NOT NULL
        GROUP BY month
        ORDER BY month
    """).fetchall()

    return [
        {
            "month": r[0],
            "commits": r[1],
            "authors": r[2],
            "insertions": r[3] or 0,
            "deletions": r[4] or 0,
        }
        for r in rows
    ]


def language_breakdown(db: duckdb.DuckDBPyConnection) -> list[dict]:
    """Aggregate language stats from per-commit JSON."""
    rows = db.execute("""
        WITH parsed AS (
            SELECT
                key AS language,
                CAST(value->>'ins' AS INTEGER) AS ins,
                CAST(value->>'dels' AS INTEGER) AS dels
            FROM commits,
            LATERAL (SELECT UNNEST(from_json(lang_stats, '{"a":{"ins":0,"dels":0}}')) )
            WHERE lang_stats IS NOT NULL AND lang_stats != '{}'
        )
        SELECT
            language,
            SUM(ins) AS insertions,
            SUM(dels) AS deletions,
            SUM(ins) + SUM(dels) AS total_churn
        FROM parsed
        GROUP BY language
        ORDER BY total_churn DESC
    """).fetchall()

    return [
        {"language": r[0], "insertions": r[1], "deletions": r[2], "total_churn": r[3]}
        for r in rows
    ]


def directory_breakdown(db: duckdb.DuckDBPyConnection) -> list[dict]:
    """Aggregate directory stats from per-commit JSON."""
    rows = db.execute("""
        WITH parsed AS (
            SELECT
                key AS directory,
                CAST(value->>'ins' AS INTEGER) AS ins,
                CAST(value->>'dels' AS INTEGER) AS dels
            FROM commits,
            LATERAL (SELECT UNNEST(from_json(dir_stats, '{"a":{"ins":0,"dels":0}}')) )
            WHERE dir_stats IS NOT NULL AND dir_stats != '{}'
        )
        SELECT
            directory,
            SUM(ins) AS insertions,
            SUM(dels) AS deletions,
            SUM(ins) + SUM(dels) AS total_churn
        FROM parsed
        GROUP BY directory
        ORDER BY total_churn DESC
        LIMIT 20
    """).fetchall()

    return [
        {"directory": r[0], "insertions": r[1], "deletions": r[2], "total_churn": r[3]}
        for r in rows
    ]


def security_commits(db: duckdb.DuckDBPyConnection) -> list[dict]:
    """Find commits mentioning security keywords."""
    rows = db.execute("""
        SELECT
            commit_hash,
            author_name,
            author_ts,
            subject
        FROM commits
        WHERE
            LOWER(subject) SIMILAR TO '%(secur|cve|vuln|xss|inject|exploit|patch|fix.*auth|fix.*token|fix.*leak|fix.*cred)%'
            OR LOWER(body) SIMILAR TO '%(secur|cve|vuln|xss|inject|exploit)%'
        ORDER BY author_ts DESC
        LIMIT 50
    """).fetchall()

    return [
        {
            "hash": r[0][:12],
            "author": r[1],
            "date": str(r[2]) if r[2] else None,
            "subject": r[3],
        }
        for r in rows
    ]


def bot_analysis(db: duckdb.DuckDBPyConnection) -> dict:
    """Detect bot commits."""
    row = db.execute("""
        SELECT
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE
                LOWER(author_name) LIKE '%[bot]%'
                OR LOWER(author_email) LIKE '%[bot]%'
                OR LOWER(author_name) IN ('dependabot', 'renovate', 'github-actions', 'copilot', 'codecov')
            ) AS bot_commits
        FROM commits
    """).fetchone()

    total = row[0] or 1
    bots = row[1] or 0
    return {
        "total_commits": total,
        "bot_commits": bots,
        "human_commits": total - bots,
        "bot_percentage": round(100 * bots / total, 1),
    }


def timezone_distribution(db: duckdb.DuckDBPyConnection) -> list[dict]:
    """Infer contributor timezones from commit hour patterns."""
    rows = db.execute("""
        SELECT
            author_name,
            MODE(EXTRACT(HOUR FROM author_ts)) AS peak_hour_utc,
            COUNT(*) AS commits
        FROM commits
        WHERE author_ts IS NOT NULL
        GROUP BY author_name
        HAVING COUNT(*) >= 5
        ORDER BY commits DESC
        LIMIT 20
    """).fetchall()

    def guess_tz(hour_utc):
        if hour_utc is None:
            return "Unknown"
        h = int(hour_utc)
        if 6 <= h <= 12:
            return "Europe/Africa (UTC+0 to +3)"
        elif 13 <= h <= 18:
            return "Asia/Pacific (UTC+5 to +10)"
        elif 19 <= h <= 23:
            return "Americas West (UTC-8 to -5)"
        else:
            return "Americas East / Late night (UTC-5 to -3)"

    return [
        {
            "author": r[0],
            "peak_hour_utc": int(r[1]) if r[1] is not None else None,
            "inferred_region": guess_tz(r[1]),
            "commits": r[2],
        }
        for r in rows
    ]


def author_deep_dive(db: duckdb.DuckDBPyConnection, author_filter: str) -> dict:
    """Deep dive on a specific author (hiring eval mode)."""
    # Match by name or email
    rows = db.execute(f"""
        SELECT
            author_name,
            author_email,
            COUNT(*) AS commits,
            SUM(insertions) AS insertions,
            SUM(deletions) AS deletions,
            SUM(files_changed) AS files_changed,
            MIN(author_ts) AS first_commit,
            MAX(author_ts) AS last_commit,
            COUNT(DISTINCT strftime(author_ts, '%Y-%m')) AS active_months,
            COUNT(*) FILTER (WHERE is_merge = 'True' OR is_merge = 'true' OR is_merge = '1') AS merges
        FROM commits
        WHERE LOWER(author_name) LIKE '%{author_filter.lower()}%'
           OR LOWER(author_email) LIKE '%{author_filter.lower()}%'
        GROUP BY author_name, author_email
    """).fetchall()

    if not rows:
        return {"error": f"No commits found for author matching '{author_filter}'"}

    r = rows[0]
    name, email = r[0], r[1]

    # Languages this author works in
    langs = db.execute(f"""
        WITH parsed AS (
            SELECT key AS language, CAST(value->>'ins' AS INTEGER) AS ins
            FROM commits,
            LATERAL (SELECT UNNEST(from_json(lang_stats, '{{"a":{{"ins":0,"dels":0}}}}')) )
            WHERE (LOWER(author_name) LIKE '%{author_filter.lower()}%'
                   OR LOWER(author_email) LIKE '%{author_filter.lower()}%')
              AND lang_stats IS NOT NULL AND lang_stats != '{{}}'
        )
        SELECT language, SUM(ins) AS total_ins
        FROM parsed GROUP BY language ORDER BY total_ins DESC LIMIT 10
    """).fetchall()

    # Directories this author works in
    dirs = db.execute(f"""
        WITH parsed AS (
            SELECT key AS directory, CAST(value->>'ins' AS INTEGER) AS ins
            FROM commits,
            LATERAL (SELECT UNNEST(from_json(dir_stats, '{{"a":{{"ins":0,"dels":0}}}}')) )
            WHERE (LOWER(author_name) LIKE '%{author_filter.lower()}%'
                   OR LOWER(author_email) LIKE '%{author_filter.lower()}%')
              AND dir_stats IS NOT NULL AND dir_stats != '{{}}'
        )
        SELECT directory, SUM(ins) AS total_ins
        FROM parsed GROUP BY directory ORDER BY total_ins DESC LIMIT 10
    """).fetchall()

    # Monthly activity
    monthly = db.execute(f"""
        SELECT strftime(author_ts, '%Y-%m') AS month, COUNT(*) AS commits
        FROM commits
        WHERE LOWER(author_name) LIKE '%{author_filter.lower()}%'
           OR LOWER(author_email) LIKE '%{author_filter.lower()}%'
        GROUP BY month ORDER BY month
    """).fetchall()

    return {
        "name": name,
        "email": email,
        "commits": r[2],
        "insertions": r[3] or 0,
        "deletions": r[4] or 0,
        "files_changed": r[5] or 0,
        "first_commit": str(r[6]) if r[6] else None,
        "last_commit": str(r[7]) if r[7] else None,
        "active_months": r[8],
        "merge_commits": r[9],
        "languages": [{"language": l[0], "insertions": l[1]} for l in langs],
        "directories": [{"directory": d[0], "insertions": d[1]} for d in dirs],
        "monthly_activity": [{"month": m[0], "commits": m[1]} for m in monthly],
    }


# ---------------------------------------------------------------------------
# PR / Issue analysis (optional)
# ---------------------------------------------------------------------------

def pr_analysis(db: duckdb.DuckDBPyConnection) -> dict | None:
    """Analyze PR review culture."""
    try:
        row = db.execute("""
            SELECT
                COUNT(*) AS total_prs,
                COUNT(*) FILTER (WHERE pr_state = 'MERGED') AS merged,
                COUNT(*) FILTER (WHERE pr_state = 'OPEN') AS open_prs,
                COUNT(*) FILTER (WHERE pr_state = 'CLOSED' AND pr_merged_at IS NULL) AS closed_unmerged,
                AVG(CAST(pr_time_to_merge_hours AS DOUBLE)) FILTER (WHERE pr_time_to_merge_hours != '' AND pr_time_to_merge_hours IS NOT NULL) AS avg_merge_hours,
                MEDIAN(CAST(pr_time_to_merge_hours AS DOUBLE)) FILTER (WHERE pr_time_to_merge_hours != '' AND pr_time_to_merge_hours IS NOT NULL) AS median_merge_hours,
                AVG(CAST(pr_first_review_hours AS DOUBLE)) FILTER (WHERE pr_first_review_hours != '' AND pr_first_review_hours IS NOT NULL) AS avg_first_review_hours,
                AVG(pr_additions + pr_deletions) AS avg_pr_size,
                AVG(pr_comment_count) AS avg_comments,
                AVG(pr_bot_comment_count) AS avg_bot_comments
            FROM prs
        """).fetchone()

        return {
            "total_prs": row[0],
            "merged": row[1],
            "open": row[2],
            "closed_unmerged": row[3],
            "avg_merge_hours": round(row[4], 1) if row[4] else None,
            "median_merge_hours": round(row[5], 1) if row[5] else None,
            "avg_first_review_hours": round(row[6], 1) if row[6] else None,
            "avg_pr_size_lines": round(row[7]) if row[7] else None,
            "avg_human_comments": round(row[8], 1) if row[8] else None,
            "avg_bot_comments": round(row[9], 1) if row[9] else None,
        }
    except Exception:
        return None


def issue_analysis(db: duckdb.DuckDBPyConnection) -> dict | None:
    """Analyze issue health."""
    try:
        row = db.execute("""
            SELECT
                COUNT(*) AS total_issues,
                COUNT(*) FILTER (WHERE issue_state = 'OPEN') AS open_issues,
                COUNT(*) FILTER (WHERE issue_state = 'CLOSED') AS closed_issues,
                AVG(CAST(issue_time_to_close_hours AS DOUBLE)) FILTER (WHERE issue_time_to_close_hours != '' AND issue_time_to_close_hours IS NOT NULL) AS avg_close_hours,
                MEDIAN(CAST(issue_time_to_close_hours AS DOUBLE)) FILTER (WHERE issue_time_to_close_hours != '' AND issue_time_to_close_hours IS NOT NULL) AS median_close_hours,
                AVG(issue_comment_count) AS avg_comments
            FROM issues
        """).fetchone()

        return {
            "total_issues": row[0],
            "open": row[1],
            "closed": row[2],
            "avg_close_hours": round(row[3], 1) if row[3] else None,
            "median_close_hours": round(row[4], 1) if row[4] else None,
            "avg_comments": round(row[5], 1) if row[5] else None,
        }
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Health score
# ---------------------------------------------------------------------------

def calculate_health_score(overview: dict, bf: dict, pr_data: dict | None, issue_data: dict | None) -> dict:
    """Calculate a 0-10 health score from all analysis data."""
    score = 5.0  # Start neutral
    reasons = []

    # Staleness
    days = overview["days_since_last_commit"]
    if days <= 7:
        score += 1.5
        reasons.append(f"Active: last commit {days} days ago (+1.5)")
    elif days <= 30:
        score += 1.0
        reasons.append(f"Recent activity: {days} days ago (+1.0)")
    elif days <= 90:
        reasons.append(f"Slowing down: {days} days since last commit (+0)")
    elif days <= 180:
        score -= 1.0
        reasons.append(f"Stale: {days} days since last commit (-1.0)")
    else:
        score -= 2.0
        reasons.append(f"Abandoned: {days} days since last commit (-2.0)")

    # Bus factor
    bf_val = bf["bus_factor"]
    if bf_val >= 3:
        score += 1.0
        reasons.append(f"Healthy bus factor: {bf_val} (+1.0)")
    elif bf_val == 2:
        score += 0.5
        reasons.append(f"Bus factor: {bf_val} (+0.5)")
    elif bf_val == 1:
        score -= 0.5
        reasons.append(f"Bus factor: 1 — single point of failure (-0.5)")
    else:
        score -= 1.0
        reasons.append("No recent commits to calculate bus factor (-1.0)")

    # Contributor diversity
    authors = overview["unique_authors"]
    if authors >= 10:
        score += 1.0
        reasons.append(f"Diverse contributors: {authors} (+1.0)")
    elif authors >= 5:
        score += 0.5
        reasons.append(f"Moderate contributors: {authors} (+0.5)")
    elif authors == 1:
        score -= 0.5
        reasons.append("Solo contributor (-0.5)")

    # PR review culture
    if pr_data and pr_data["total_prs"] > 0:
        median = pr_data["median_merge_hours"]
        if median is not None:
            if 1 <= median <= 48:
                score += 1.0
                reasons.append(f"Good PR turnaround: {median}h median merge time (+1.0)")
            elif median <= 168:
                score += 0.5
                reasons.append(f"Acceptable PR turnaround: {median}h (+0.5)")
            elif median > 336:
                score -= 0.5
                reasons.append(f"Slow PR reviews: {median}h median merge (-0.5)")

        first_review = pr_data["avg_first_review_hours"]
        if first_review is not None and first_review <= 24:
            score += 0.5
            reasons.append(f"Fast first reviews: {first_review}h avg (+0.5)")

    # Issue responsiveness
    if issue_data and issue_data["total_issues"] > 0:
        open_ratio = issue_data["open"] / max(issue_data["total_issues"], 1)
        if open_ratio < 0.3:
            score += 0.5
            reasons.append(f"Good issue management: {open_ratio:.0%} open (+0.5)")
        elif open_ratio > 0.7:
            score -= 0.5
            reasons.append(f"Issues piling up: {open_ratio:.0%} open (-0.5)")

    score = max(0.0, min(10.0, score))

    return {
        "score": round(score, 1),
        "reasons": reasons,
    }


# ---------------------------------------------------------------------------
# Report formatting
# ---------------------------------------------------------------------------

def format_markdown(data: dict) -> str:
    """Format all analysis data as a markdown report."""
    lines = []

    overview = data["overview"]
    lines.append(f"# Repo Analysis: {overview.get('repo_name', 'unknown')}")
    lines.append("")

    # Health score
    health = data["health_score"]
    lines.append(f"## Health Score: {health['score']}/10")
    lines.append("")
    for r in health["reasons"]:
        lines.append(f"- {r}")
    lines.append("")

    # Overview
    lines.append("## Overview")
    lines.append("")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Total commits | {overview['total_commits']:,} |")
    lines.append(f"| Unique authors | {overview['unique_authors']} |")
    lines.append(f"| Age | {overview['age_days']} days |")
    lines.append(f"| Days since last commit | {overview['days_since_last_commit']} |")
    lines.append(f"| Lines added | {overview['total_insertions']:,} |")
    lines.append(f"| Lines deleted | {overview['total_deletions']:,} |")
    lines.append(f"| Merge commits | {overview['merge_commits']} |")
    lines.append("")

    # Bus factor
    bf = data["bus_factor"]
    lines.append(f"## Bus Factor: {bf['bus_factor']}")
    lines.append(f"- Recent commits (6mo): {bf['recent_commits_6mo']}")
    lines.append(f"- Recent authors (6mo): {bf['recent_authors_6mo']}")
    lines.append("")

    # Contributors
    lines.append("## Top Contributors")
    lines.append("")
    lines.append("| Author | Commits | Lines Added | Lines Deleted | Active Months |")
    lines.append("|--------|---------|-------------|---------------|---------------|")
    total_commits = overview["total_commits"] or 1
    for c in data["contributors"]:
        pct = round(100 * c["commits"] / total_commits, 1)
        lines.append(f"| {c['name']} | {c['commits']} ({pct}%) | {c['insertions']:,} | {c['deletions']:,} | {c['active_months']} |")
    lines.append("")

    # Bots
    bots = data["bots"]
    if bots["bot_commits"] > 0:
        lines.append(f"## Bot Activity")
        lines.append(f"- Bot commits: {bots['bot_commits']} ({bots['bot_percentage']}%)")
        lines.append(f"- Human commits: {bots['human_commits']}")
        lines.append("")

    # Languages
    if data["languages"]:
        lines.append("## Languages")
        lines.append("")
        lines.append("| Language | Insertions | Deletions | Total Churn |")
        lines.append("|----------|------------|-----------|-------------|")
        for l in data["languages"][:15]:
            lines.append(f"| {l['language']} | {l['insertions']:,} | {l['deletions']:,} | {l['total_churn']:,} |")
        lines.append("")

    # Directories
    if data["directories"]:
        lines.append("## Top Directories")
        lines.append("")
        lines.append("| Directory | Insertions | Deletions | Total Churn |")
        lines.append("|-----------|------------|-----------|-------------|")
        for d in data["directories"][:15]:
            lines.append(f"| {d['directory']} | {d['insertions']:,} | {d['deletions']:,} | {d['total_churn']:,} |")
        lines.append("")

    # Velocity
    velocity = data["velocity"]
    if velocity:
        lines.append("## Commit Velocity (Last 12 Months)")
        lines.append("")
        lines.append("| Month | Commits | Authors | Lines +/- |")
        lines.append("|-------|---------|---------|-----------|")
        for v in velocity[-12:]:
            lines.append(f"| {v['month']} | {v['commits']} | {v['authors']} | +{v['insertions']:,} / -{v['deletions']:,} |")
        lines.append("")

    # Timezones
    if data["timezones"]:
        lines.append("## Contributor Timezones (Inferred)")
        lines.append("")
        lines.append("| Author | Peak Hour (UTC) | Inferred Region |")
        lines.append("|--------|-----------------|-----------------|")
        for t in data["timezones"][:10]:
            lines.append(f"| {t['author']} | {t['peak_hour_utc']}:00 | {t['inferred_region']} |")
        lines.append("")

    # Security
    sec = data["security_commits"]
    if sec:
        lines.append("## Security-Related Commits")
        lines.append("")
        lines.append("| Hash | Author | Date | Subject |")
        lines.append("|------|--------|------|---------|")
        for s in sec[:20]:
            lines.append(f"| {s['hash']} | {s['author']} | {s['date'][:10] if s['date'] else ''} | {s['subject']} |")
        lines.append("")

    # PR analysis
    if data.get("pr_analysis"):
        pr = data["pr_analysis"]
        lines.append("## Pull Request Analysis")
        lines.append("")
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        lines.append(f"| Total PRs | {pr['total_prs']} |")
        lines.append(f"| Merged | {pr['merged']} |")
        lines.append(f"| Open | {pr['open']} |")
        lines.append(f"| Closed (unmerged) | {pr['closed_unmerged']} |")
        if pr["median_merge_hours"] is not None:
            lines.append(f"| Median merge time | {pr['median_merge_hours']}h |")
        if pr["avg_first_review_hours"] is not None:
            lines.append(f"| Avg first review | {pr['avg_first_review_hours']}h |")
        if pr["avg_pr_size_lines"] is not None:
            lines.append(f"| Avg PR size | {pr['avg_pr_size_lines']} lines |")
        if pr["avg_human_comments"] is not None:
            lines.append(f"| Avg human comments | {pr['avg_human_comments']} |")
        lines.append("")

    # Issue analysis
    if data.get("issue_analysis"):
        iss = data["issue_analysis"]
        lines.append("## Issue Analysis")
        lines.append("")
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        lines.append(f"| Total issues | {iss['total_issues']} |")
        lines.append(f"| Open | {iss['open']} |")
        lines.append(f"| Closed | {iss['closed']} |")
        if iss["median_close_hours"] is not None:
            lines.append(f"| Median close time | {iss['median_close_hours']}h |")
        if iss["avg_comments"] is not None:
            lines.append(f"| Avg comments | {iss['avg_comments']} |")
        lines.append("")

    # Author deep dive
    if data.get("author_deep_dive"):
        a = data["author_deep_dive"]
        if "error" not in a:
            lines.append(f"## Author Deep Dive: {a['name']}")
            lines.append("")
            lines.append(f"| Metric | Value |")
            lines.append(f"|--------|-------|")
            lines.append(f"| Email | {a['email']} |")
            lines.append(f"| Commits | {a['commits']} |")
            lines.append(f"| Lines added | {a['insertions']:,} |")
            lines.append(f"| Lines deleted | {a['deletions']:,} |")
            lines.append(f"| Active months | {a['active_months']} |")
            lines.append(f"| First commit | {a['first_commit'][:10] if a['first_commit'] else ''} |")
            lines.append(f"| Last commit | {a['last_commit'][:10] if a['last_commit'] else ''} |")
            lines.append(f"| Merge commits | {a['merge_commits']} |")
            lines.append("")

            if a["languages"]:
                lines.append("**Languages:**")
                for l in a["languages"]:
                    lines.append(f"- {l['language']}: {l['insertions']:,} lines")
                lines.append("")

            if a["directories"]:
                lines.append("**Directories:**")
                for d in a["directories"]:
                    lines.append(f"- {d['directory']}: {d['insertions']:,} lines")
                lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Analyze git/GitHub CSV data with DuckDB")
    parser.add_argument("commits", help="Path to commits.csv")
    parser.add_argument("--prs", help="Path to prs.csv")
    parser.add_argument("--issues", help="Path to issues.csv")
    parser.add_argument("--author", help="Deep dive on a specific author (name or email)")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of markdown")
    parser.add_argument("-o", "--output", help="Write output to file")
    args = parser.parse_args()

    db = connect(args.commits, args.prs, args.issues)

    # Run all analyses
    data = {
        "overview": repo_overview(db),
        "contributors": top_contributors(db),
        "bus_factor": bus_factor(db),
        "velocity": commit_velocity(db),
        "languages": [],
        "directories": [],
        "security_commits": security_commits(db),
        "bots": bot_analysis(db),
        "timezones": timezone_distribution(db),
    }

    # Language/directory parsing can fail on repos without lang_stats
    try:
        data["languages"] = language_breakdown(db)
    except Exception:
        pass

    try:
        data["directories"] = directory_breakdown(db)
    except Exception:
        pass

    # Optional analyses
    if args.prs:
        data["pr_analysis"] = pr_analysis(db)
    if args.issues:
        data["issue_analysis"] = issue_analysis(db)
    if args.author:
        data["author_deep_dive"] = author_deep_dive(db, args.author)

    # Health score
    data["health_score"] = calculate_health_score(
        data["overview"],
        data["bus_factor"],
        data.get("pr_analysis"),
        data.get("issue_analysis"),
    )

    # Add repo name to overview
    data["overview"]["repo_name"] = args.commits.split("/")[-2] if "/" in args.commits else "unknown"

    # Output
    if args.json:
        output = json.dumps(data, indent=2, default=str)
    else:
        output = format_markdown(data)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Report written to {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
