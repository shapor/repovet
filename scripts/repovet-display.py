#!/usr/bin/env python3
"""Rich terminal analytics display for RepoVet.

Produces a colorful, GitHub-style contribution profile in the terminal
using only ANSI escape codes and Unicode box-drawing characters.

Usage:
    python repovet-display.py commits.csv
    python repovet-display.py commits.csv --prs prs.csv --issues issues.csv
"""

import argparse
import importlib.util
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import duckdb

# Import analysis functions from repovet-analyze.py (hyphen in name requires
# importlib.util to load by file path rather than normal import).
_script_dir = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("repovet_analyze", os.path.join(_script_dir, "repovet-analyze.py"))
_analyze = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_analyze)

connect = _analyze.connect
repo_overview = _analyze.repo_overview
top_contributors = _analyze.top_contributors
bus_factor = _analyze.bus_factor
commit_velocity = _analyze.commit_velocity
language_breakdown = _analyze.language_breakdown
calculate_health_score = _analyze.calculate_health_score
bot_analysis = _analyze.bot_analysis

# ---------------------------------------------------------------------------
# ANSI helpers
# ---------------------------------------------------------------------------

def fg(r, g, b):
    return f"\033[38;2;{r};{g};{b}m"

def bg(r, g, b):
    return f"\033[48;2;{r};{g};{b}m"

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
ITALIC = "\033[3m"
UNDERLINE = "\033[4m"

# GitHub-style greens for heatmaps
BG_EMPTY  = bg(22, 27, 34)
BG_LOW    = bg(14, 68, 41)
BG_MED    = bg(0, 109, 50)
BG_HIGH   = bg(38, 166, 65)
BG_VHIGH  = bg(57, 211, 83)

FG_EMPTY  = fg(48, 54, 61)
FG_LOW    = fg(14, 68, 41)
FG_MED    = fg(0, 109, 50)
FG_HIGH   = fg(38, 166, 65)
FG_VHIGH  = fg(57, 211, 83)

GREEN_BGS = [BG_EMPTY, BG_LOW, BG_MED, BG_HIGH, BG_VHIGH]
GREEN_FGS = [FG_EMPTY, FG_LOW, FG_MED, FG_HIGH, FG_VHIGH]

# Accent colors for charts
ACCENT_COLORS = [
    (88, 166, 255),   # blue
    (255, 123, 114),  # red/coral
    (62, 218, 149),   # green
    (210, 153, 255),  # purple
    (255, 208, 115),  # yellow
    (121, 192, 255),  # light blue
    (255, 159, 164),  # pink
    (126, 231, 135),  # light green
    (190, 132, 255),  # violet
    (255, 220, 150),  # light yellow
]

TITLE_COLOR   = fg(136, 198, 255)
HEADER_COLOR  = fg(88, 166, 255)
MUTED_COLOR   = fg(125, 133, 144)
TEXT_COLOR     = fg(201, 209, 217)
WHITE         = fg(240, 246, 252)
GREEN_TEXT    = fg(62, 218, 149)
RED_TEXT      = fg(255, 123, 114)
YELLOW_TEXT   = fg(255, 208, 115)
CYAN_TEXT     = fg(121, 192, 255)

SPARKLINE_CHARS = " \u2581\u2582\u2583\u2584\u2585\u2586\u2587\u2588"

# Terminal width
try:
    TERM_WIDTH = os.get_terminal_size().columns
except OSError:
    TERM_WIDTH = 100


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def fmt_num(n):
    """Format number with commas."""
    if n is None:
        return "0"
    return f"{int(n):,}"


def section_header(title, width=None):
    """Print a styled section header."""
    w = width or min(TERM_WIDTH, 80)
    line = "\u2500" * w
    print()
    print(f"  {HEADER_COLOR}{BOLD}{title}{RESET}")
    print(f"  {MUTED_COLOR}{line}{RESET}")


def quantile_index(value, thresholds):
    """Map value to 0-4 bucket based on thresholds."""
    if value == 0:
        return 0
    for i, t in enumerate(thresholds):
        if value <= t:
            return i + 1
    return 4


# ---------------------------------------------------------------------------
# Section: Key Stats Box
# ---------------------------------------------------------------------------

def render_stats_box(overview, bf_data, health, bots):
    """Render the key stats summary box."""
    repo_name = overview.get("repo_name", "unknown")
    age = overview["age_days"]
    days_since = overview["days_since_last_commit"]
    contributors = overview["unique_authors"]
    bf_val = bf_data["bus_factor"]
    commits = overview["total_commits"]
    merges = overview["merge_commits"]
    ins = overview["total_insertions"]
    dels = overview["total_deletions"]
    score = health["score"]

    if days_since == 0:
        last_str = "today"
    elif days_since == 1:
        last_str = "yesterday"
    elif days_since < 30:
        last_str = f"{days_since}d ago"
    elif days_since < 365:
        last_str = f"{days_since // 30}mo ago"
    else:
        last_str = f"{days_since // 365}y ago"

    # Score color
    if score >= 7:
        sc_color = GREEN_TEXT
    elif score >= 4:
        sc_color = YELLOW_TEXT
    else:
        sc_color = RED_TEXT

    bot_pct = bots["bot_percentage"]

    # Build the box content
    inner_w = 56
    border_color = MUTED_COLOR

    def pad_line(content, visible_len):
        padding = inner_w - visible_len
        return f"  {border_color}\u2502{RESET}  {content}{' ' * max(0, padding)}  {border_color}\u2502{RESET}"

    print()
    print(f"  {border_color}\u250c{'─' * (inner_w + 4)}\u2510{RESET}")

    # Repo name
    label = f"Repo: {repo_name}"
    print(pad_line(f"{TITLE_COLOR}{BOLD}\u2728 {label}{RESET}", len(label) + 2))

    # Age + last commit
    label = f"Age: {age} days   Last commit: {last_str}"
    print(pad_line(f"{TEXT_COLOR}\u23f1  {label}{RESET}", len(label) + 3))

    # Contributors + bus factor
    label = f"Contributors: {contributors}   Bus factor: {bf_val}"
    print(pad_line(f"{TEXT_COLOR}\u2630  {label}{RESET}", len(label) + 3))

    # Commits + merges
    label = f"Commits: {fmt_num(commits)}   Merges: {fmt_num(merges)}   Bots: {bot_pct}%"
    print(pad_line(f"{TEXT_COLOR}\u270e  {label}{RESET}", len(label) + 3))

    # Lines added/deleted
    add_str = fmt_num(ins)
    del_str = fmt_num(dels)
    line_content = f"{GREEN_TEXT}+{add_str}{RESET}  {RED_TEXT}-{del_str}{RESET}"
    visible_len = len(f"+{add_str}  -{del_str}") + 3
    print(pad_line(f"\u00b1  {line_content}", visible_len))

    # Health score
    label = f"Health Score: {score}/10"
    print(pad_line(f"{sc_color}\u2665  {label}{RESET}", len(label) + 3))

    print(f"  {border_color}\u2514{'─' * (inner_w + 4)}\u2518{RESET}")


# ---------------------------------------------------------------------------
# Section: Contribution Heatmap
# ---------------------------------------------------------------------------

def render_heatmap(db):
    """Render a GitHub-style contribution heatmap for the last 52 weeks."""
    section_header("Contribution Heatmap (last 52 weeks)")

    now = datetime.now(timezone.utc)
    start = now - timedelta(weeks=52)

    rows = db.execute("""
        SELECT
            CAST(author_ts AS DATE) AS day,
            COUNT(*) AS commits
        FROM commits
        WHERE author_ts >= ?
        GROUP BY day
        ORDER BY day
    """, [start]).fetchall()

    day_counts = {}
    for r in rows:
        if r[0] is not None:
            # DuckDB may return datetime.date or other date-like objects
            d = r[0]
            if hasattr(d, 'date'):
                d = d.date()
            elif not hasattr(d, 'weekday'):
                from datetime import date as _date
                d = _date.fromisoformat(str(d))
            day_counts[d] = r[1]

    # Build the 7x52 grid (rows = weekday, cols = week)
    # Find the Monday of the start week
    start_date = start.date()
    # Go back to the most recent Monday at or before start_date
    days_since_mon = start_date.weekday()  # 0=Mon
    grid_start = start_date - timedelta(days=days_since_mon)

    # Compute thresholds from actual data
    all_counts = [v for v in day_counts.values() if v > 0]
    if all_counts:
        sorted_c = sorted(all_counts)
        n = len(sorted_c)
        thresholds = [
            sorted_c[min(n - 1, n // 4)],
            sorted_c[min(n - 1, n // 2)],
            sorted_c[min(n - 1, 3 * n // 4)],
        ]
    else:
        thresholds = [1, 3, 7]

    # Build grid
    grid = [[0] * 53 for _ in range(7)]
    for week in range(53):
        for dow in range(7):
            d = grid_start + timedelta(days=week * 7 + dow)
            if d <= now.date():
                grid[dow][week] = day_counts.get(d, 0)
            else:
                grid[dow][week] = -1  # future

    # Month labels
    month_labels = [""] * 53
    for week in range(53):
        d = grid_start + timedelta(days=week * 7)
        if d.day <= 7:
            month_labels[week] = d.strftime("%b")

    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    # Print month header
    header = "       "
    for week in range(53):
        lbl = month_labels[week]
        if lbl:
            header += lbl + " "
        else:
            header += "   "
    print(f"  {MUTED_COLOR}{header.rstrip()}{RESET}")

    # Print each row
    for dow in range(7):
        if dow % 2 == 0:
            label = f"  {MUTED_COLOR}{day_names[dow]:>3}{RESET}  "
        else:
            label = f"       "
        row = label
        for week in range(53):
            val = grid[dow][week]
            if val < 0:
                row += "   "
            elif val == 0:
                row += f"{BG_EMPTY}   {RESET}"
            else:
                idx = quantile_index(val, thresholds)
                row += f"{GREEN_BGS[idx]}   {RESET}"
        print(row)

    # Legend
    legend = f"  {MUTED_COLOR}      Less {RESET}"
    for i in range(5):
        legend += f"{GREEN_BGS[i]}   {RESET}"
    legend += f" {MUTED_COLOR}More{RESET}"
    print(legend)


# ---------------------------------------------------------------------------
# Section: Top Contributors Bar Chart
# ---------------------------------------------------------------------------

def render_contributors(contributors_data, total_commits):
    """Render horizontal bar chart of top contributors."""
    section_header("Top Contributors")

    if not contributors_data:
        print(f"  {MUTED_COLOR}No contributor data available{RESET}")
        return

    top = contributors_data[:10]
    max_commits = max(c["commits"] for c in top) if top else 1
    name_width = max(len(c["name"]) for c in top)
    bar_max = min(TERM_WIDTH - name_width - 30, 40)

    for i, c in enumerate(top):
        color = ACCENT_COLORS[i % len(ACCENT_COLORS)]
        fg_c = fg(*color)
        pct = 100 * c["commits"] / max(total_commits, 1)
        bar_len = max(1, int(bar_max * c["commits"] / max_commits))
        bar = "\u2588" * bar_len
        name = c["name"][:20]
        commits_str = fmt_num(c["commits"])
        print(f"  {WHITE}{name:<{name_width}}{RESET}  {fg_c}{bar}{RESET}  "
              f"{TEXT_COLOR}{commits_str:>6} commits{RESET} "
              f"{MUTED_COLOR}({pct:.0f}%){RESET}")


# ---------------------------------------------------------------------------
# Section: Language Breakdown
# ---------------------------------------------------------------------------

def render_languages(langs_data):
    """Render language breakdown as stacked bar + individual bars."""
    section_header("Languages")

    if not langs_data:
        print(f"  {MUTED_COLOR}No language data available{RESET}")
        return

    # Top languages
    total_churn = sum(l["total_churn"] for l in langs_data) or 1
    top = langs_data[:8]

    # Stacked bar
    stacked_width = min(TERM_WIDTH - 10, 60)
    stacked = "  "
    for i, l in enumerate(top):
        color = ACCENT_COLORS[i % len(ACCENT_COLORS)]
        width = max(1, int(stacked_width * l["total_churn"] / total_churn))
        stacked += f"{bg(*color)} {fg(0, 0, 0)}{l['language'][:width]:<{width}}{RESET}"
    print(stacked)
    print()

    # Individual bars
    name_width = max(len(l["language"]) for l in top)
    bar_max = min(TERM_WIDTH - name_width - 22, 35)

    for i, l in enumerate(top):
        color = ACCENT_COLORS[i % len(ACCENT_COLORS)]
        fg_c = fg(*color)
        pct = 100 * l["total_churn"] / total_churn
        bar_len = max(1, int(bar_max * l["total_churn"] / (top[0]["total_churn"] or 1)))
        bar = "\u2588" * bar_len
        dim_bar = "\u2591" * (bar_max - bar_len)
        name = l["language"]
        print(f"  {TEXT_COLOR}{name:<{name_width}}{RESET}  "
              f"{fg_c}{bar}{MUTED_COLOR}{dim_bar}{RESET}  "
              f"{TEXT_COLOR}{pct:>5.1f}%{RESET}")


# ---------------------------------------------------------------------------
# Section: Velocity Sparkline
# ---------------------------------------------------------------------------

def render_velocity(velocity_data):
    """Render commit velocity as sparklines per year."""
    section_header("Commit Velocity (monthly)")

    if not velocity_data:
        print(f"  {MUTED_COLOR}No velocity data available{RESET}")
        return

    # Group by year
    by_year = defaultdict(list)
    for v in velocity_data:
        if v["month"]:
            year = v["month"][:4]
            by_year[year].append(v["commits"])

    max_commits = max(c for vals in by_year.values() for c in vals) if by_year else 1

    for year in sorted(by_year.keys()):
        months = by_year[year]
        spark = ""
        for c in months:
            idx = int(8 * c / max(max_commits, 1))
            idx = min(idx, len(SPARKLINE_CHARS) - 1)
            # Color based on intensity
            if idx <= 2:
                color = FG_LOW
            elif idx <= 4:
                color = FG_MED
            elif idx <= 6:
                color = FG_HIGH
            else:
                color = FG_VHIGH
            spark += f"{color}{SPARKLINE_CHARS[idx]}{RESET}"

        total = sum(months)
        avg = total / len(months)
        # Month labels
        month_names = ["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"]
        labels = " ".join(month_names[:len(months)])
        print(f"  {WHITE}{year}:{RESET}  {spark}  {MUTED_COLOR}{fmt_num(total)} total, "
              f"avg {avg:.0f}/mo{RESET}")
        print(f"  {MUTED_COLOR}        {labels}{RESET}")


# ---------------------------------------------------------------------------
# Section: Activity by Hour/Day Heatmap
# ---------------------------------------------------------------------------

def render_activity_heatmap(db):
    """Render commit activity heatmap by hour and day of week."""
    section_header("Commit Activity by Day & Hour (UTC)")

    rows = db.execute("""
        SELECT
            EXTRACT(DOW FROM author_ts) AS dow,
            EXTRACT(HOUR FROM author_ts) AS hour,
            COUNT(*) AS commits
        FROM commits
        WHERE author_ts IS NOT NULL
        GROUP BY dow, hour
    """).fetchall()

    # Build 7x24 grid (dow 0=Sun in DuckDB, we'll remap to Mon=0)
    grid = [[0] * 24 for _ in range(7)]
    for r in rows:
        if r[0] is not None and r[1] is not None:
            # DuckDB DOW: 0=Sun, 1=Mon, ... 6=Sat -> remap to Mon=0..Sun=6
            dow = (int(r[0]) - 1) % 7
            hour = int(r[1])
            grid[dow][hour] = r[2]

    # Compute thresholds
    all_vals = [grid[d][h] for d in range(7) for h in range(24) if grid[d][h] > 0]
    if all_vals:
        sv = sorted(all_vals)
        n = len(sv)
        thresholds = [sv[min(n - 1, n // 4)], sv[min(n - 1, n // 2)], sv[min(n - 1, 3 * n // 4)]]
    else:
        thresholds = [1, 3, 7]

    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    # Hour header (show every 3 hours)
    header = "         "
    for h in range(0, 24, 3):
        header += f"{h:02d}    "
    print(f"  {MUTED_COLOR}{header.rstrip()}{RESET}")

    for dow in range(7):
        row = f"  {MUTED_COLOR}{day_names[dow]:>3}{RESET}  "
        for h in range(24):
            val = grid[dow][h]
            if val == 0:
                row += f"{BG_EMPTY}  {RESET}"
            else:
                idx = quantile_index(val, thresholds)
                row += f"{GREEN_BGS[idx]}  {RESET}"
        print(row)


# ---------------------------------------------------------------------------
# Section: Health Score Breakdown
# ---------------------------------------------------------------------------

def render_health_details(health):
    """Render health score with visual breakdown."""
    section_header("Health Score Breakdown")

    score = health["score"]
    max_score = 10

    # Big score display
    if score >= 7:
        sc_color = GREEN_TEXT
        grade = "Healthy"
    elif score >= 4:
        sc_color = YELLOW_TEXT
        grade = "Fair"
    else:
        sc_color = RED_TEXT
        grade = "Needs Attention"

    # Score bar
    bar_width = 30
    filled = int(bar_width * score / max_score)
    bar = "\u2588" * filled + "\u2591" * (bar_width - filled)
    print(f"  {sc_color}{BOLD}{score}/10{RESET}  {sc_color}{bar}{RESET}  "
          f"{MUTED_COLOR}{grade}{RESET}")
    print()

    # Reasons
    for reason in health["reasons"]:
        if "(+" in reason:
            icon = f"{GREEN_TEXT}\u2713{RESET}"
        elif "(-" in reason:
            icon = f"{RED_TEXT}\u2717{RESET}"
        else:
            icon = f"{YELLOW_TEXT}\u25cb{RESET}"
        print(f"  {icon} {TEXT_COLOR}{reason}{RESET}")


# ---------------------------------------------------------------------------
# Section: PR Analysis (optional)
# ---------------------------------------------------------------------------

def render_pr_analysis(db):
    """Render PR analysis if data is available."""
    try:
        pr_data = _analyze.pr_analysis(db)
    except Exception:
        return None

    if not pr_data or pr_data["total_prs"] == 0:
        return None

    section_header("Pull Request Analysis")

    total = pr_data["total_prs"]
    merged = pr_data["merged"]
    open_prs = pr_data["open"]
    closed = pr_data["closed_unmerged"]

    # Stacked bar showing PR states
    bar_width = min(TERM_WIDTH - 10, 50)
    merged_w = max(1, int(bar_width * merged / max(total, 1)))
    open_w = max(1, int(bar_width * open_prs / max(total, 1))) if open_prs else 0
    closed_w = max(bar_width - merged_w - open_w, 0)

    bar = (f"{bg(62, 218, 149)}{' ' * merged_w}{RESET}"
           f"{bg(88, 166, 255)}{' ' * open_w}{RESET}"
           f"{bg(255, 123, 114)}{' ' * closed_w}{RESET}")
    print(f"  {bar}")
    print(f"  {GREEN_TEXT}\u25cf Merged: {merged}{RESET}  "
          f"{CYAN_TEXT}\u25cf Open: {open_prs}{RESET}  "
          f"{RED_TEXT}\u25cf Closed: {closed}{RESET}  "
          f"{MUTED_COLOR}Total: {total}{RESET}")

    if pr_data["median_merge_hours"] is not None:
        print(f"  {TEXT_COLOR}Median merge time: {pr_data['median_merge_hours']}h   "
              f"Avg first review: {pr_data.get('avg_first_review_hours', 'N/A')}h{RESET}")

    return pr_data


# ---------------------------------------------------------------------------
# Section: Issue Analysis (optional)
# ---------------------------------------------------------------------------

def render_issue_analysis(db):
    """Render issue analysis if data is available."""
    try:
        iss_data = _analyze.issue_analysis(db)
    except Exception:
        return None

    if not iss_data or iss_data["total_issues"] == 0:
        return None

    section_header("Issue Tracker")

    total = iss_data["total_issues"]
    open_iss = iss_data["open"]
    closed = iss_data["closed"]

    bar_width = min(TERM_WIDTH - 10, 50)
    closed_w = max(1, int(bar_width * closed / max(total, 1)))
    open_w = bar_width - closed_w

    bar = (f"{bg(62, 218, 149)}{' ' * closed_w}{RESET}"
           f"{bg(255, 123, 114)}{' ' * open_w}{RESET}")
    print(f"  {bar}")
    print(f"  {GREEN_TEXT}\u25cf Closed: {closed}{RESET}  "
          f"{RED_TEXT}\u25cf Open: {open_iss}{RESET}  "
          f"{MUTED_COLOR}Total: {total}{RESET}")

    if iss_data["median_close_hours"] is not None:
        print(f"  {TEXT_COLOR}Median close time: {iss_data['median_close_hours']}h{RESET}")

    return iss_data


# ---------------------------------------------------------------------------
# Section: Top active files (bonus)
# ---------------------------------------------------------------------------

def render_recent_focus(db):
    """Show most active directories in recent commits."""
    section_header("Recent Focus Areas (last 90 days)")

    try:
        rows = db.execute("""
            WITH parsed AS (
                SELECT
                    key AS directory,
                    CAST(value->>'ins' AS INTEGER) AS ins,
                    CAST(value->>'dels' AS INTEGER) AS dels
                FROM commits,
                LATERAL (SELECT UNNEST(from_json(dir_stats, '{"a":{"ins":0,"dels":0}}')) )
                WHERE dir_stats IS NOT NULL AND dir_stats != '{}'
                  AND author_ts >= NOW() - INTERVAL '90 days'
            )
            SELECT
                directory,
                SUM(ins) + SUM(dels) AS churn
            FROM parsed
            GROUP BY directory
            ORDER BY churn DESC
            LIMIT 6
        """).fetchall()
    except Exception:
        print(f"  {MUTED_COLOR}No directory data available{RESET}")
        return

    if not rows:
        print(f"  {MUTED_COLOR}No recent activity{RESET}")
        return

    max_churn = rows[0][1] if rows else 1
    name_width = max(len(r[0]) for r in rows)
    bar_max = min(TERM_WIDTH - name_width - 20, 30)

    for i, r in enumerate(rows):
        color = ACCENT_COLORS[i % len(ACCENT_COLORS)]
        fg_c = fg(*color)
        bar_len = max(1, int(bar_max * r[1] / max(max_churn, 1)))
        bar = "\u2588" * bar_len
        print(f"  {TEXT_COLOR}{r[0]:<{name_width}}{RESET}  "
              f"{fg_c}{bar}{RESET}  {MUTED_COLOR}{fmt_num(r[1])} lines{RESET}")


# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------

def render_banner():
    """Print the RepoVet banner."""
    banner_color = fg(88, 166, 255)
    print()
    print(f"{banner_color}{BOLD}"
          f"  ╦═╗┌─┐┌─┐┌─┐╦  ╦┌─┐┌┬┐  ╔╦╗┬┌─┐┌─┐┬  ┌─┐┬ ┬\n"
          f"  ╠╦╝├┤ ├─┘│ │╚╗╔╝├┤  │   ║║│└─┐├─┘│  ├─┤└┬┘\n"
          f"  ╩╚═└─┘┴  └─┘ ╚╝ └─┘ ┴   ═╩╝┴└─┘┴  ┴─┘┴ ┴ ┴{RESET}")
    print(f"  {MUTED_COLOR}Terminal-based repository analytics{RESET}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Rich terminal analytics display for RepoVet"
    )
    parser.add_argument("commits", help="Path to commits.csv")
    parser.add_argument("--prs", help="Path to prs.csv")
    parser.add_argument("--issues", help="Path to issues.csv")
    args = parser.parse_args()

    # Connect to DuckDB and load data
    db = connect(args.commits, args.prs, args.issues)

    # Gather all data
    overview = repo_overview(db)

    # Try to get repo name from the data, fall back to filename
    try:
        rn = db.execute("SELECT repo_name FROM commits WHERE repo_name IS NOT NULL LIMIT 1").fetchone()
        overview["repo_name"] = rn[0] if rn else None
    except Exception:
        overview["repo_name"] = None
    if not overview.get("repo_name"):
        fname = args.commits.split("/")[-1] if "/" in args.commits else args.commits
        overview["repo_name"] = fname.replace("-commits.csv", "").replace(".csv", "")
    contributors_data = top_contributors(db)
    bf_data = bus_factor(db)
    velocity_data = commit_velocity(db)
    bots = bot_analysis(db)

    langs_data = []
    try:
        langs_data = language_breakdown(db)
    except Exception:
        pass

    pr_data = None
    issue_data = None
    if args.prs:
        try:
            pr_data = _analyze.pr_analysis(db)
        except Exception:
            pass
    if args.issues:
        try:
            issue_data = _analyze.issue_analysis(db)
        except Exception:
            pass

    health = calculate_health_score(overview, bf_data, pr_data, issue_data)

    # ---- Render everything ----

    render_banner()

    # 1. Key Stats Box
    render_stats_box(overview, bf_data, health, bots)

    # 2. Health Score
    render_health_details(health)

    # 3. Contribution Heatmap
    render_heatmap(db)

    # 4. Top Contributors
    render_contributors(contributors_data, overview["total_commits"])

    # 5. Languages
    render_languages(langs_data)

    # 6. Velocity Sparkline
    render_velocity(velocity_data)

    # 7. Activity Heatmap
    render_activity_heatmap(db)

    # 8. Recent Focus
    render_recent_focus(db)

    # 9. PR Analysis (optional)
    if args.prs:
        render_pr_analysis(db)

    # 10. Issue Analysis (optional)
    if args.issues:
        render_issue_analysis(db)

    # Footer
    print()
    print(f"  {MUTED_COLOR}{'─' * min(TERM_WIDTH, 80)}{RESET}")
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"  {MUTED_COLOR}Generated by RepoVet Display at {ts}{RESET}")
    print()


if __name__ == "__main__":
    main()
