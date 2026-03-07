#!/usr/bin/env python3
"""Run a DuckDB SQL query against RepoVet CSV files.

Usage:
    python query.py "SELECT author_name, COUNT(*) FROM commits GROUP BY 1 ORDER BY 2 DESC LIMIT 10"
    python query.py "SELECT * FROM prs WHERE pr_state = 'OPEN'" --prs prs.csv
    python query.py --file query.sql
    python query.py --schema  # Show available tables and columns

CSV files are loaded as tables named: commits, prs, issues
"""

import argparse
import sys

import duckdb


def load_db(commits: str | None, prs: str | None, issues: str | None) -> duckdb.DuckDBPyConnection:
    db = duckdb.connect(":memory:")

    if commits:
        db.execute(f"""
            CREATE VIEW commits AS
            SELECT *,
                   TRY_CAST(author_date AS TIMESTAMP WITH TIME ZONE) AS author_ts,
                   TRY_CAST(commit_date AS TIMESTAMP WITH TIME ZONE) AS commit_ts
            FROM read_csv_auto('{commits}', header=true, ignore_errors=true)
        """)

    if prs:
        db.execute(f"""
            CREATE VIEW prs AS
            SELECT *,
                   TRY_CAST(pr_created_at AS TIMESTAMP WITH TIME ZONE) AS created_ts,
                   TRY_CAST(pr_merged_at AS TIMESTAMP WITH TIME ZONE) AS merged_ts
            FROM read_csv_auto('{prs}', header=true, ignore_errors=true)
        """)

    if issues:
        db.execute(f"""
            CREATE VIEW issues AS
            SELECT *,
                   TRY_CAST(issue_created_at AS TIMESTAMP WITH TIME ZONE) AS created_ts,
                   TRY_CAST(issue_closed_at AS TIMESTAMP WITH TIME ZONE) AS closed_ts
            FROM read_csv_auto('{issues}', header=true, ignore_errors=true)
        """)

    return db


def show_schema(db: duckdb.DuckDBPyConnection):
    for view in db.execute("SELECT table_name FROM information_schema.tables WHERE table_type='VIEW'").fetchall():
        name = view[0]
        print(f"\n=== {name} ===")
        cols = db.execute(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name='{name}' ORDER BY ordinal_position").fetchall()
        for col_name, col_type in cols:
            print(f"  {col_name:40s} {col_type}")


def main():
    parser = argparse.ArgumentParser(description="Run DuckDB SQL on RepoVet CSVs")
    parser.add_argument("sql", nargs="?", help="SQL query to run")
    parser.add_argument("--file", "-f", help="Read SQL from file")
    parser.add_argument("--commits", default=None, help="Path to commits.csv")
    parser.add_argument("--prs", default=None, help="Path to prs.csv")
    parser.add_argument("--issues", default=None, help="Path to issues.csv")
    parser.add_argument("--schema", action="store_true", help="Show table schemas")
    parser.add_argument("--csv", action="store_true", help="Output as CSV")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    # Auto-detect CSVs in common locations
    import os
    if not args.commits:
        for candidate in ["commits.csv", "~/.repovet/cache/*/commits.csv"]:
            import glob
            matches = glob.glob(os.path.expanduser(candidate))
            if matches:
                args.commits = matches[0]
                break

    db = load_db(args.commits, args.prs, args.issues)

    if args.schema:
        show_schema(db)
        return

    sql = args.sql
    if args.file:
        with open(args.file) as f:
            sql = f.read()

    if not sql:
        parser.error("Provide a SQL query or --file or --schema")

    try:
        result = db.execute(sql)
        if args.csv:
            result.write_csv(sys.stdout)
        elif args.json:
            import json
            cols = [desc[0] for desc in result.description]
            rows = [dict(zip(cols, row)) for row in result.fetchall()]
            json.dump(rows, sys.stdout, indent=2, default=str)
            print()
        else:
            print(result.fetch_df().to_string() if hasattr(result, 'fetch_df') else result.fetchall())
    except Exception as e:
        print(f"Query error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
