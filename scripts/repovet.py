#!/usr/bin/env python3
"""
repovet.py — Trust assessment CLI for code repositories.

Scans GitHub repos (remote via API, or local on disk) for agent config threats,
repo health signals, and produces a trust score with detailed report.

Usage:
    python3 repovet.py scan https://github.com/user/repo
    python3 repovet.py scan user/repo
    python3 repovet.py scan /path/to/local/repo
    python3 repovet.py scan user/repo -o report.md
    python3 repovet.py scan user/repo --json
"""

import argparse
import base64
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VERSION = "0.1.0"

AGENT_CONFIG_PATTERNS = [
    ".claude/",
    "CLAUDE.md",
    ".claude.md",
    ".cursorrules",
    ".cursor/",
    ".github/copilot-instructions.md",
    ".aider.conf.yml",
    ".continue/",
    ".windsurfrules",
    "AGENTS.md",
]

# Root-level config directories (not considered "nested" if at repo root)
ROOT_CONFIG_DIRS = {".claude", ".cursor", ".continue", ".github", "skills"}

# Threat detection patterns
THREAT_PATTERNS: dict[str, list[dict[str, Any]]] = {
    "auto_execution": [
        {
            "id": "hook-file",
            "severity": "CRITICAL",
            "pattern": r"\.claude/hooks/",
            "match_type": "path",
            "title": "Auto-execution hook detected",
            "description": "Runs automatically before/after Claude Code commands",
        },
    ],
    "network_exfiltration": [
        {
            "id": "curl-post-data",
            "severity": "CRITICAL",
            "pattern": r"curl\s+.*-[dX].*POST.*https?://|curl\s+.*-s.*-X\s*POST\s+-d\s+@-\s+https?://",
            "match_type": "content",
            "title": "Data exfiltration via curl POST",
            "description": "Sends data to an external server",
        },
        {
            "id": "curl-external",
            "severity": "HIGH",
            "pattern": r"(?:curl|wget|fetch)\s+.*https?://(?!github\.com|pypi\.org|npmjs\.com|registry\.npmjs\.org)",
            "match_type": "content",
            "title": "Network request to external URL",
            "description": "Makes HTTP requests to external servers",
        },
        {
            "id": "pipe-to-curl",
            "severity": "CRITICAL",
            "pattern": r"cat\s+.*\|\s*curl|<\s*\S+\s*curl|\|\s*curl\s+-",
            "match_type": "content",
            "title": "File contents piped to network",
            "description": "Reads file contents and sends them over the network",
        },
    ],
    "remote_code_execution": [
        {
            "id": "curl-pipe-bash",
            "severity": "CRITICAL",
            "pattern": r"curl\s+.*\|\s*(?:ba)?sh|wget\s+.*\|\s*(?:ba)?sh|curl\s+.*-O-\s*\|\s*sh",
            "match_type": "content",
            "title": "Remote code execution (curl | bash)",
            "description": "Downloads and executes remote code without verification",
        },
        {
            "id": "eval-curl",
            "severity": "CRITICAL",
            "pattern": r"eval\s+\"\$\(curl|eval\s+\$\(curl|eval\s+\"\$\(wget",
            "match_type": "content",
            "title": "Remote code execution via eval",
            "description": "Downloads and eval-executes remote code",
        },
    ],
    "credential_access": [
        {
            "id": "aws-creds",
            "severity": "CRITICAL",
            "pattern": r"~/\.aws/credentials|~/.aws/config|\$AWS_SECRET|\.aws/credentials",
            "match_type": "content",
            "title": "AWS credential access",
            "description": "Reads or references AWS credential files",
        },
        {
            "id": "ssh-keys",
            "severity": "CRITICAL",
            "pattern": r"~/\.ssh/id_rsa|~/\.ssh/id_ed25519|\.ssh/id_rsa|\.ssh/id_ed25519|cat\s+.*\.ssh/",
            "match_type": "content",
            "title": "SSH private key access",
            "description": "Reads or references SSH private keys",
        },
        {
            "id": "env-secrets",
            "severity": "HIGH",
            "pattern": r"grep.*(?:TOKEN|KEY|SECRET|PASSWORD|API)|env\s*\|\s*grep.*(?:token|key|secret|password)",
            "match_type": "content",
            "title": "Environment variable secret harvesting",
            "description": "Scans environment for tokens, keys, and secrets",
        },
        {
            "id": "gcloud-creds",
            "severity": "CRITICAL",
            "pattern": r"application_default_credentials\.json|gcloud.*auth.*print-access-token",
            "match_type": "content",
            "title": "GCP credential access",
            "description": "Reads or references Google Cloud credential files",
        },
        {
            "id": "dotenv-read",
            "severity": "HIGH",
            "pattern": r"cat\s+.*\.env\b|source\s+.*\.env\b",
            "match_type": "content",
            "title": ".env file access",
            "description": "Reads .env files which commonly contain secrets",
        },
        {
            "id": "profile-read",
            "severity": "HIGH",
            "pattern": r"cat\s+.*\.bashrc|cat\s+.*\.bash_profile|cat\s+.*\.profile|cat\s+.*\.zshrc",
            "match_type": "content",
            "title": "Shell profile access",
            "description": "Reads shell profile files which may contain secrets and aliases",
        },
    ],
    "obfuscation": [
        {
            "id": "base64-exec",
            "severity": "HIGH",
            "pattern": r"base64\s+-[dD]|base64\s+--decode|\|\s*base64\s+-w0",
            "match_type": "content",
            "title": "Base64 encoding/decoding of data",
            "description": "Uses base64 encoding which can hide malicious content",
        },
        {
            "id": "eval-constructed",
            "severity": "HIGH",
            "pattern": r"eval\s+\"\$|eval\s+\$\(|eval\s+`",
            "match_type": "content",
            "title": "Eval of dynamically constructed string",
            "description": "Executes dynamically built commands, hiding true intent",
        },
    ],
    "prompt_injection": [
        {
            "id": "ignore-instructions",
            "severity": "HIGH",
            "pattern": r"(?i)ignore\s+(?:previous|prior|all|any)\s+instructions",
            "match_type": "content",
            "title": "Instruction override attempt",
            "description": "Attempts to override safety instructions",
        },
        {
            "id": "hide-from-user",
            "severity": "CRITICAL",
            "pattern": r"(?i)(?:do\s+not|don'?t|never)\s+(?:show|display|mention|tell|reveal)\s+.*(?:to\s+the\s+)?user",
            "match_type": "content",
            "title": "Hiding actions from user",
            "description": "Instructs the AI to conceal its actions from the user",
        },
        {
            "id": "always-approve",
            "severity": "HIGH",
            "pattern": r"(?i)always\s+(?:approve|accept|allow|run|execute)|skip\s+(?:safety|security|verification|review)",
            "match_type": "content",
            "title": "Blanket approval instruction",
            "description": "Instructs the AI to bypass approval and safety checks",
        },
        {
            "id": "disregard-instructions",
            "severity": "HIGH",
            "pattern": r"(?i)disregard\s+(?:any|all)?\s*instructions\s+that|override.*(?:safety|security)",
            "match_type": "content",
            "title": "Instruction disregard directive",
            "description": "Tells the AI to disregard conflicting safety instructions",
        },
        {
            "id": "silent-execution",
            "severity": "HIGH",
            "pattern": r"(?i)(?:silently|quietly)\s+(?:run|execute|install)|without\s+(?:asking|prompting|telling)",
            "match_type": "content",
            "title": "Silent execution instruction",
            "description": "Instructs the AI to run commands without user awareness",
        },
    ],
    "destructive_operations": [
        {
            "id": "force-push",
            "severity": "MEDIUM",
            "pattern": r"git\s+push\s+--force|git\s+push\s+-f\b",
            "match_type": "content",
            "title": "Git force push",
            "description": "Force push can destroy commit history",
        },
        {
            "id": "rm-rf",
            "severity": "MEDIUM",
            "pattern": r"rm\s+-rf\s+[/$~]|rm\s+-rf\s+\*",
            "match_type": "content",
            "title": "Recursive force delete",
            "description": "Destructive file deletion with no confirmation",
        },
        {
            "id": "git-reset-hard",
            "severity": "MEDIUM",
            "pattern": r"git\s+reset\s+--hard",
            "match_type": "content",
            "title": "Git hard reset",
            "description": "Hard reset discards all uncommitted changes",
        },
    ],
    "dangerous_permissions": [
        {
            "id": "skip-permissions",
            "severity": "CRITICAL",
            "pattern": r"dangerouslySkipPermissions.*true",
            "match_type": "content",
            "title": "All permissions bypassed",
            "description": "dangerouslySkipPermissions disables all safety prompts",
        },
        {
            "id": "wildcard-bash",
            "severity": "HIGH",
            "pattern": r'"Bash\(\*\)"',
            "match_type": "content",
            "title": "Unrestricted bash execution",
            "description": "Allows any bash command without approval",
        },
    ],
}

SEVERITY_SCORES = {"CRITICAL": 3, "HIGH": 2, "MEDIUM": 1}
SEVERITY_COLORS = {"CRITICAL": "\033[91m", "HIGH": "\033[93m", "MEDIUM": "\033[33m"}
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"


# ---------------------------------------------------------------------------
# GitHub API helpers (via `gh` CLI)
# ---------------------------------------------------------------------------

def gh_api(endpoint: str, paginate: bool = False) -> Any:
    """Call GitHub REST API via `gh` CLI. Returns parsed JSON or None on error."""
    cmd = ["gh", "api", endpoint, "--header", "Accept: application/vnd.github+json"]
    if paginate:
        cmd.append("--paginate")
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False)
    except FileNotFoundError:
        print("Error: `gh` CLI not found. Install from https://cli.github.com/", file=sys.stderr)
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print(f"Warning: API call timed out: {endpoint}", file=sys.stderr)
        return None

    if proc.returncode != 0:
        stderr = proc.stderr.strip()
        if "404" in stderr or "Not Found" in stderr:
            return None
        if "rate limit" in stderr.lower():
            print("Error: GitHub API rate limit exceeded. Try again later.", file=sys.stderr)
            return None
        # For non-critical errors, return None rather than crashing
        print(f"Warning: gh api error for {endpoint}: {stderr}", file=sys.stderr)
        return None

    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None


def parse_repo_spec(spec: str) -> tuple[str | None, str | None]:
    """Parse a repo spec into (owner/repo, local_path).

    Returns (owner_repo, None) for remote repos, (None, path) for local paths.
    """
    # Local path
    if spec.startswith("/") or spec.startswith("./") or spec.startswith("~"):
        return None, os.path.expanduser(spec)
    if os.path.isdir(spec):
        return None, os.path.realpath(spec)

    # GitHub URL: https://github.com/user/repo or https://github.com/user/repo.git
    m = re.match(r"https?://github\.com/([^/]+/[^/]+?)(?:\.git)?/?$", spec)
    if m:
        return m.group(1), None

    # Shorthand: user/repo
    m = re.match(r"^([a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+)$", spec)
    if m:
        return m.group(1), None

    # Could be a local relative path
    if os.path.isdir(spec):
        return None, os.path.realpath(spec)

    # Assume shorthand
    return spec, None


# ---------------------------------------------------------------------------
# Remote scanning (GitHub API)
# ---------------------------------------------------------------------------

def fetch_repo_metadata(owner_repo: str) -> dict | None:
    """Fetch repository metadata via GitHub API."""
    return gh_api(f"repos/{owner_repo}")


def fetch_file_tree(owner_repo: str, branch: str) -> list[dict]:
    """Fetch the full file tree for the default branch."""
    data = gh_api(f"repos/{owner_repo}/git/trees/{branch}?recursive=1")
    if not data or "tree" not in data:
        return []
    return data["tree"]


def find_config_files_in_tree(tree: list[dict]) -> list[dict]:
    """Search the file tree for agent config file patterns."""
    matches = []
    for item in tree:
        path = item.get("path", "")
        item_type = item.get("type", "")  # "blob" or "tree"
        if item_type != "blob":
            continue
        for pattern in AGENT_CONFIG_PATTERNS:
            if pattern.endswith("/"):
                # Directory pattern: match anything under it
                if path.startswith(pattern) or f"/{pattern}" in f"/{path}":
                    matches.append(item)
                    break
            else:
                # Exact file match (at any depth)
                basename = os.path.basename(path)
                if basename == pattern or path == pattern:
                    matches.append(item)
                    break
                # Also check for the pattern at any depth
                if path.endswith(f"/{pattern}"):
                    matches.append(item)
                    break
    return matches


def fetch_file_content(owner_repo: str, path: str) -> str | None:
    """Fetch a single file's content via the GitHub contents API."""
    data = gh_api(f"repos/{owner_repo}/contents/{path}")
    if not data or "content" not in data:
        return None
    try:
        raw = data["content"].replace("\n", "")
        return base64.b64decode(raw).decode("utf-8", errors="replace")
    except Exception:
        return None


def fetch_recent_commits(owner_repo: str, count: int = 100) -> list[dict]:
    """Fetch recent commits via the GitHub API."""
    data = gh_api(f"repos/{owner_repo}/commits?per_page={count}")
    if not data or not isinstance(data, list):
        return []
    return data


def fetch_contributors(owner_repo: str, count: int = 30) -> list[dict]:
    """Fetch top contributors via the GitHub API."""
    data = gh_api(f"repos/{owner_repo}/contributors?per_page={count}")
    if not data or not isinstance(data, list):
        return []
    return data


def classify_nesting(path: str) -> tuple[bool, int]:
    """Determine if a config file is nested and at what depth."""
    parts = path.split("/")
    if len(parts) <= 1:
        return False, 0
    if parts[0] in ROOT_CONFIG_DIRS:
        return False, 0
    # It's nested: depth = number of dirs before the config dir/file
    for i, part in enumerate(parts):
        if part in ROOT_CONFIG_DIRS or any(
            part == p.rstrip("/") for p in AGENT_CONFIG_PATTERNS
        ):
            return True, i
    return True, len(parts) - 1


# ---------------------------------------------------------------------------
# Threat analysis
# ---------------------------------------------------------------------------

class Finding:
    """A single threat finding."""

    def __init__(
        self,
        category: str,
        rule_id: str,
        severity: str,
        title: str,
        description: str,
        file_path: str,
        evidence: str = "",
        line_num: int | None = None,
    ):
        self.category = category
        self.rule_id = rule_id
        self.severity = severity
        self.title = title
        self.description = description
        self.file_path = file_path
        self.evidence = evidence
        self.line_num = line_num


def analyze_content(file_path: str, content: str) -> list[Finding]:
    """Run all threat patterns against a file's content."""
    findings: list[Finding] = []
    seen: set[str] = set()

    for category, rules in THREAT_PATTERNS.items():
        for rule in rules:
            match_type = rule["match_type"]
            key = f"{rule['id']}:{file_path}"

            if match_type == "path":
                if re.search(rule["pattern"], file_path) and key not in seen:
                    seen.add(key)
                    findings.append(Finding(
                        category=category,
                        rule_id=rule["id"],
                        severity=rule["severity"],
                        title=rule["title"],
                        description=rule["description"],
                        file_path=file_path,
                    ))

            elif match_type == "content" and content:
                for line_idx, line in enumerate(content.split("\n"), 1):
                    if re.search(rule["pattern"], line) and key not in seen:
                        seen.add(key)
                        evidence = line.strip()
                        if len(evidence) > 200:
                            evidence = evidence[:200] + "..."
                        findings.append(Finding(
                            category=category,
                            rule_id=rule["id"],
                            severity=rule["severity"],
                            title=rule["title"],
                            description=rule["description"],
                            file_path=file_path,
                            evidence=evidence,
                            line_num=line_idx,
                        ))
                        break  # one finding per rule per file

    return findings


# ---------------------------------------------------------------------------
# Health analysis
# ---------------------------------------------------------------------------

def calculate_health(
    meta: dict | None,
    commits: list[dict],
    contributors: list[dict],
) -> dict:
    """Compute repo health metrics from API data."""
    health: dict[str, Any] = {
        "score": 5.0,
        "age_days": 0,
        "staleness_days": 0,
        "stars": 0,
        "forks": 0,
        "open_issues": 0,
        "contributors_count": len(contributors),
        "bus_factor": 0,
        "commit_velocity_monthly": 0.0,
        "language": "Unknown",
        "description": "",
        "signals": [],
    }

    if not meta:
        health["signals"].append("No repository metadata available")
        return health

    now = datetime.now(timezone.utc)

    # Basic metadata
    health["stars"] = meta.get("stargazers_count", 0)
    health["forks"] = meta.get("forks_count", 0)
    health["open_issues"] = meta.get("open_issues_count", 0)
    health["language"] = meta.get("language") or "Unknown"
    health["description"] = meta.get("description") or ""

    # Age
    created = meta.get("created_at", "")
    if created:
        try:
            created_dt = datetime.strptime(created, "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=timezone.utc
            )
            health["age_days"] = (now - created_dt).days
        except ValueError:
            pass

    # Staleness
    pushed = meta.get("pushed_at", "")
    if pushed:
        try:
            pushed_dt = datetime.strptime(pushed, "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=timezone.utc
            )
            health["staleness_days"] = (now - pushed_dt).days
        except ValueError:
            pass

    # Commit velocity (commits per month from recent data)
    if commits:
        dates = []
        for c in commits:
            cd = (c.get("commit") or {}).get("committer", {}).get("date", "")
            if cd:
                try:
                    dates.append(
                        datetime.strptime(cd, "%Y-%m-%dT%H:%M:%SZ").replace(
                            tzinfo=timezone.utc
                        )
                    )
                except ValueError:
                    pass
        if len(dates) >= 2:
            dates.sort()
            span_days = max((dates[-1] - dates[0]).days, 1)
            health["commit_velocity_monthly"] = round(
                len(dates) / (span_days / 30.0), 1
            )

    # Bus factor from contributors
    if contributors:
        total = sum(c.get("contributions", 0) for c in contributors)
        if total > 0:
            top = contributors[0].get("contributions", 0)
            top_pct = top / total * 100
            bus_factor = 0
            running = 0
            for c in sorted(contributors, key=lambda x: x.get("contributions", 0), reverse=True):
                running += c.get("contributions", 0)
                bus_factor += 1
                if running / total >= 0.5:
                    break
            health["bus_factor"] = bus_factor
            health["top_contributor_pct"] = round(top_pct, 1)
            health["top_contributor"] = contributors[0].get("login", "unknown")

    # Calculate health score (0-10)
    score = 5.0

    # Activity bonus/penalty
    staleness = health["staleness_days"]
    if staleness < 7:
        score += 1.5
        health["signals"].append("Very active (updated this week)")
    elif staleness < 30:
        score += 1.0
        health["signals"].append("Active (updated this month)")
    elif staleness < 90:
        score += 0.0
        health["signals"].append("Moderate activity (updated in last 3 months)")
    elif staleness < 365:
        score -= 1.0
        health["signals"].append(f"Stale ({staleness} days since last push)")
    else:
        score -= 2.0
        health["signals"].append(f"Likely abandoned ({staleness} days since last push)")

    # Popularity bonus
    stars = health["stars"]
    if stars >= 10000:
        score += 1.5
        health["signals"].append(f"Very popular ({stars:,} stars)")
    elif stars >= 1000:
        score += 1.0
        health["signals"].append(f"Popular ({stars:,} stars)")
    elif stars >= 100:
        score += 0.5
        health["signals"].append(f"Moderate following ({stars:,} stars)")
    elif stars < 10:
        score -= 0.5
        health["signals"].append(f"Low visibility ({stars} stars)")

    # Contributors
    n_contributors = health["contributors_count"]
    bus = health["bus_factor"]
    if n_contributors >= 10:
        score += 1.0
        health["signals"].append(f"Healthy contributor base ({n_contributors} contributors)")
    elif n_contributors >= 3:
        score += 0.5
        health["signals"].append(f"Small team ({n_contributors} contributors)")
    elif n_contributors <= 1:
        score -= 1.0
        health["signals"].append("Single maintainer")

    if bus <= 1 and n_contributors > 1:
        score -= 0.5
        top_pct = health.get("top_contributor_pct", 0)
        health["signals"].append(
            f"Bus factor of 1 ({health.get('top_contributor', '?')} owns {top_pct:.0f}% of commits)"
        )

    # Commit velocity
    velocity = health["commit_velocity_monthly"]
    if velocity > 20:
        score += 0.5
        health["signals"].append(f"High commit velocity ({velocity}/month)")
    elif velocity < 1 and health["age_days"] > 90:
        score -= 0.5
        health["signals"].append(f"Low commit velocity ({velocity}/month)")

    # Age
    age = health["age_days"]
    if age < 30:
        score -= 0.5
        health["signals"].append(f"Very new project ({age} days old)")
    elif age > 365:
        score += 0.5
        health["signals"].append(f"Established project ({age // 365} years old)")

    health["score"] = round(max(0.0, min(10.0, score)), 1)
    return health


# ---------------------------------------------------------------------------
# Trust score
# ---------------------------------------------------------------------------

def calculate_trust_score(
    config_safety_score: float, health_score: float
) -> tuple[float, str]:
    """Calculate overall trust score and recommendation."""
    if config_safety_score < 5:
        trust = 0.2 * health_score + 0.8 * config_safety_score
    else:
        trust = 0.5 * health_score + 0.5 * config_safety_score

    trust = round(max(0.0, min(10.0, trust)), 1)

    if trust >= 8.0:
        verdict = "Looks Good"
    elif trust >= 6.0:
        verdict = "Proceed with Caution"
    elif trust >= 4.0:
        verdict = "Review Recommended"
    elif trust >= 2.0:
        verdict = "Significant Risks"
    else:
        verdict = "Do Not Use"

    return trust, verdict


# ---------------------------------------------------------------------------
# Local repo scanning (reuse discovery script logic)
# ---------------------------------------------------------------------------

def scan_local_repo(repo_path: str) -> tuple[dict, list[dict], list[Finding]]:
    """Scan a local repo: return (metadata, config_files_info, findings)."""
    repo_path = os.path.realpath(os.path.expanduser(repo_path))
    if not os.path.isdir(repo_path):
        print(f"Error: {repo_path} is not a directory", file=sys.stderr)
        sys.exit(1)

    # Try to get repo name and remote info
    meta: dict[str, Any] = {
        "name": os.path.basename(repo_path),
        "local_path": repo_path,
        "source": "local",
    }

    # Try to detect GitHub remote for enrichment
    try:
        url_result = subprocess.run(
            ["git", "-C", repo_path, "remote", "get-url", "origin"],
            capture_output=True, text=True, check=False, timeout=5,
        )
        if url_result.returncode == 0:
            remote_url = url_result.stdout.strip()
            meta["remote_url"] = remote_url
            for prefix in ("git@github.com:", "https://github.com/"):
                if remote_url.startswith(prefix):
                    owner_repo = remote_url[len(prefix):].removesuffix(".git")
                    meta["github_repo"] = owner_repo
    except Exception:
        pass

    # Run the discovery script as a library
    script_dir = os.path.dirname(os.path.abspath(__file__))
    discover_script = os.path.join(script_dir, "repovet-config-discover.py")

    config_files_info: list[dict] = []
    findings: list[Finding] = []

    if os.path.exists(discover_script):
        try:
            proc = subprocess.run(
                [sys.executable, discover_script, repo_path, "--compact"],
                capture_output=True, text=True, timeout=30, check=False,
            )
            if proc.returncode == 0:
                discovery = json.loads(proc.stdout)

                # Extract config file info
                for cf in discovery.get("config_files", []):
                    config_files_info.append(cf)

                # Analyze executables for threats
                for exe in discovery.get("executables", []):
                    file_findings = analyze_content(
                        exe.get("source_file", ""),
                        exe.get("content", ""),
                    )
                    findings.extend(file_findings)

                # Analyze instructions for threats
                for instr in discovery.get("instructions", []):
                    file_findings = analyze_content(
                        instr.get("source_file", ""),
                        instr.get("content", ""),
                    )
                    findings.extend(file_findings)

                # Analyze permissions
                for perm in discovery.get("permissions", []):
                    content_str = json.dumps(perm)
                    file_findings = analyze_content(
                        perm.get("source_file", ""),
                        content_str,
                    )
                    findings.extend(file_findings)
        except Exception as e:
            print(f"Warning: discovery script error: {e}", file=sys.stderr)
    else:
        # Fallback: manual file scan
        config_files_info, findings = _manual_local_scan(repo_path)

    return meta, config_files_info, findings


def _manual_local_scan(repo_path: str) -> tuple[list[dict], list[Finding]]:
    """Fallback local scan when discovery script is not available."""
    import glob as globmod

    config_files: list[dict] = []
    findings: list[Finding] = []

    for pattern in AGENT_CONFIG_PATTERNS:
        if pattern.endswith("/"):
            glob_pat = os.path.join(repo_path, "**", pattern + "**", "*")
        else:
            glob_pat = os.path.join(repo_path, "**", pattern)
        for match in globmod.glob(glob_pat, recursive=True):
            if not os.path.isfile(match):
                continue
            rel = os.path.relpath(match, repo_path)
            if rel.startswith(".git" + os.sep):
                continue
            config_files.append({
                "path": rel,
                "size_bytes": os.path.getsize(match),
            })
            content = None
            try:
                with open(match, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
            except Exception:
                pass
            if content:
                findings.extend(analyze_content(rel, content))

    return config_files, findings


# ---------------------------------------------------------------------------
# Remote repo scanning
# ---------------------------------------------------------------------------

def scan_remote_repo(owner_repo: str) -> tuple[dict, list[dict], list[Finding], dict, list[dict], list[dict]]:
    """Scan a remote GitHub repo via API.

    Returns: (metadata, config_files, findings, health_data, commits, contributors)
    """
    print(f"  Fetching repository metadata...", file=sys.stderr)
    meta = fetch_repo_metadata(owner_repo)
    if not meta:
        print(f"Error: Repository '{owner_repo}' not found or not accessible.", file=sys.stderr)
        print("Make sure the repo exists and you have access (run `gh auth status`).", file=sys.stderr)
        sys.exit(1)

    default_branch = meta.get("default_branch", "main")

    print(f"  Fetching file tree ({default_branch})...", file=sys.stderr)
    tree = fetch_file_tree(owner_repo, default_branch)
    if not tree:
        print("Warning: Could not fetch file tree. Report will be limited.", file=sys.stderr)

    # Find config files
    config_entries = find_config_files_in_tree(tree)
    config_files: list[dict] = []
    findings: list[Finding] = []

    if config_entries:
        print(
            f"  Found {len(config_entries)} agent config file(s), fetching contents...",
            file=sys.stderr,
        )
        for entry in config_entries:
            path = entry.get("path", "")
            size = entry.get("size", 0)
            is_nest, nest_depth = classify_nesting(path)
            config_files.append({
                "path": path,
                "size_bytes": size,
                "is_nested": is_nest,
                "nested_depth": nest_depth,
            })

            # Fetch and analyze content
            content = fetch_file_content(owner_repo, path)
            if content:
                file_findings = analyze_content(path, content)
                findings.extend(file_findings)

                # Store content for the report
                config_files[-1]["content"] = content
    else:
        print("  No agent config files found.", file=sys.stderr)

    print(f"  Fetching recent commits...", file=sys.stderr)
    commits = fetch_recent_commits(owner_repo)

    print(f"  Fetching contributors...", file=sys.stderr)
    contributors = fetch_contributors(owner_repo)

    health = calculate_health(meta, commits, contributors)

    return meta, config_files, findings, health, commits, contributors


# ---------------------------------------------------------------------------
# Report formatting
# ---------------------------------------------------------------------------

def format_age(days: int) -> str:
    if days < 1:
        return "today"
    if days == 1:
        return "1 day ago"
    if days < 30:
        return f"{days} days ago"
    if days < 365:
        months = days // 30
        return f"{months} month{'s' if months != 1 else ''} ago"
    years = days // 365
    remaining = (days % 365) // 30
    if remaining > 0:
        return f"{years} year{'s' if years != 1 else ''}, {remaining} month{'s' if remaining != 1 else ''} ago"
    return f"{years} year{'s' if years != 1 else ''} ago"


def format_staleness_label(days: int) -> str:
    if days < 7:
        return "active"
    if days < 30:
        return "recent"
    if days < 90:
        return "aging"
    if days < 365:
        return "stale"
    return "abandoned"


def severity_badge(sev: str, use_color: bool) -> str:
    if use_color:
        color = SEVERITY_COLORS.get(sev, "")
        return f"{color}{BOLD}{sev}{RESET}"
    return sev


def format_finding_md(f: Finding) -> str:
    """Format a single finding as markdown."""
    lines = [f"### {f.severity}: {f.title}"]
    lines.append(f"**File**: `{f.file_path}`")
    if f.line_num:
        lines[-1] += f" (line {f.line_num})"
    lines.append(f"**Risk**: {f.description}")
    if f.evidence:
        lines.append(f"```")
        lines.append(f.evidence)
        lines.append(f"```")
    return "\n".join(lines)


def generate_report(
    repo_name_str: str,
    trust_score: float,
    verdict: str,
    config_safety_score: float,
    health: dict,
    findings: list[Finding],
    config_files: list[dict],
    meta: dict | None = None,
    use_color: bool = False,
) -> str:
    """Generate the full markdown report."""
    lines: list[str] = []

    # Header
    lines.append(f"# RepoVet Assessment: {repo_name_str}")
    lines.append("")

    # Trust score line with color
    score_str = f"{trust_score}/10"
    if use_color:
        if trust_score >= 7:
            score_str = f"\033[92m{BOLD}{trust_score}/10{RESET}"
        elif trust_score >= 4:
            score_str = f"\033[93m{BOLD}{trust_score}/10{RESET}"
        else:
            score_str = f"\033[91m{BOLD}{trust_score}/10{RESET}"
    lines.append(f"**Trust Score: {score_str}** -- {verdict}")
    lines.append("")

    # At a Glance
    lines.append("## At a Glance")

    if meta and meta.get("source") != "local":
        created_days = health.get("age_days", 0)
        stale_days = health.get("staleness_days", 0)
        lines.append(f"- **Created**: {format_age(created_days)}")
        stale_label = format_staleness_label(stale_days)
        lines.append(f"- **Last push**: {format_age(stale_days)} ({stale_label})")
        lines.append(
            f"- **Stars**: {health.get('stars', 0):,} | **Forks**: {health.get('forks', 0):,}"
        )
        lines.append(f"- **Contributors**: {health.get('contributors_count', 0)}")
        lines.append(f"- **Language**: {health.get('language', 'Unknown')}")
        desc = health.get("description", "")
        if desc:
            lines.append(f"- **Description**: {desc}")
    else:
        lines.append(f"- **Path**: `{meta.get('local_path', '?')}`")
        if meta and meta.get("github_repo"):
            lines.append(f"- **Remote**: github.com/{meta['github_repo']}")

    lines.append(f"- **Config files found**: {len(config_files)}")
    lines.append(f"- **Security findings**: {len(findings)}")
    lines.append("")

    # Score breakdown
    lines.append("## Score Breakdown")
    lines.append(f"- **Config Safety**: {config_safety_score}/10")
    lines.append(f"- **Repo Health**: {health.get('score', 5.0)}/10")

    # Explain weighting
    if config_safety_score < 5:
        lines.append(f"- *Config threats dominate scoring (80% config, 20% health)*")
    else:
        lines.append(f"- *Balanced scoring (50% config, 50% health)*")
    lines.append("")

    # Findings
    if findings:
        lines.append("## Agent Configuration Findings")
        lines.append("")

        # Sort by severity
        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2}
        sorted_findings = sorted(findings, key=lambda f: severity_order.get(f.severity, 99))

        # Count by severity
        crit = sum(1 for f in findings if f.severity == "CRITICAL")
        high = sum(1 for f in findings if f.severity == "HIGH")
        med = sum(1 for f in findings if f.severity == "MEDIUM")
        summary_parts = []
        if crit:
            summary_parts.append(f"{crit} critical")
        if high:
            summary_parts.append(f"{high} high")
        if med:
            summary_parts.append(f"{med} medium")
        lines.append(f"**{len(findings)} finding(s)**: {', '.join(summary_parts)}")
        lines.append("")

        for finding in sorted_findings:
            lines.append(format_finding_md(finding))
            lines.append("")
    else:
        lines.append("## Agent Configuration Findings")
        lines.append("")
        lines.append("No security findings detected in agent configuration files.")
        lines.append("")

    # Repo Health
    lines.append("## Repo Health")
    for signal in health.get("signals", []):
        lines.append(f"- {signal}")
    if not health.get("signals"):
        lines.append("- No health signals available (local scan)")
    lines.append("")

    # Nested configs
    nested = [cf for cf in config_files if cf.get("is_nested")]
    if nested:
        lines.append("## Nested Config Warning")
        lines.append("")
        lines.append("Found agent config in subdirectories (potential hiding of malicious configs):")
        for cf in nested:
            depth = cf.get("nested_depth", 0)
            lines.append(f"- `{cf['path']}` (depth: {depth})")
        lines.append("")

    # Config files inventory
    if config_files:
        lines.append("## Config Files Inventory")
        lines.append("")
        for cf in config_files:
            path = cf.get("path", "")
            size = cf.get("size_bytes", 0)
            nested_marker = " [NESTED]" if cf.get("is_nested") else ""
            lines.append(f"- `{path}` ({size:,} bytes){nested_marker}")
        lines.append("")

    # Recommendation
    lines.append("## Recommendation")
    lines.append("")
    lines.append(_generate_recommendation(trust_score, findings, config_files))
    lines.append("")

    return "\n".join(lines)


def _generate_recommendation(
    trust_score: float, findings: list[Finding], config_files: list[dict]
) -> str:
    """Generate a human-readable recommendation based on the assessment."""
    crit = [f for f in findings if f.severity == "CRITICAL"]
    high = [f for f in findings if f.severity == "HIGH"]
    nested = [cf for cf in config_files if cf.get("is_nested")]

    if trust_score >= 8.0:
        return (
            "This repository appears safe to use. No significant risks were "
            "detected in agent configuration files. Standard precautions apply."
        )

    if trust_score >= 6.0:
        parts = ["Proceed with caution."]
        if high:
            parts.append(
                f"Review the {len(high)} high-severity finding(s) before opening in an AI coding tool."
            )
        if nested:
            parts.append(f"Note the {len(nested)} nested config file(s) which may indicate config hiding.")
        return " ".join(parts)

    if trust_score >= 4.0:
        parts = ["Manual review recommended before use."]
        if crit:
            parts.append(
                f"There {'is' if len(crit) == 1 else 'are'} {len(crit)} critical finding(s) "
                "that should be investigated."
            )
        return " ".join(parts)

    # Low trust
    parts = []
    hook_findings = [f for f in crit if f.category == "auto_execution"]
    exfil_findings = [f for f in crit if f.category in ("network_exfiltration", "credential_access")]

    if hook_findings:
        hook_paths = list(set(f.file_path for f in hook_findings))
        parts.append(
            f"Do not open this repo in Claude Code as-is. "
            f"Auto-execution hooks will run automatically. "
            f"If you must use it, delete {', '.join(f'`{p}`' for p in hook_paths)} first."
        )
    elif exfil_findings:
        parts.append(
            "Do not open this repo in an AI coding tool without first removing "
            "the malicious configuration files. Data exfiltration and/or credential "
            "theft patterns were detected."
        )
    else:
        parts.append(
            "This repository has significant security concerns. Review all findings "
            "carefully before use. Consider deleting agent configuration files."
        )

    if nested:
        parts.append(
            f"Also check nested config directories -- {len(nested)} hidden config file(s) found."
        )

    return " ".join(parts)


# ---------------------------------------------------------------------------
# JSON output
# ---------------------------------------------------------------------------

def generate_json_output(
    repo_name_str: str,
    trust_score: float,
    verdict: str,
    config_safety_score: float,
    health: dict,
    findings: list[Finding],
    config_files: list[dict],
    meta: dict | None = None,
) -> dict:
    """Generate structured JSON output."""
    return {
        "repo": repo_name_str,
        "trust_score": trust_score,
        "verdict": verdict,
        "config_safety_score": config_safety_score,
        "health_score": health.get("score", 5.0),
        "health": {k: v for k, v in health.items() if k != "score"},
        "findings": [
            {
                "category": f.category,
                "rule_id": f.rule_id,
                "severity": f.severity,
                "title": f.title,
                "description": f.description,
                "file": f.file_path,
                "evidence": f.evidence,
                "line": f.line_num,
            }
            for f in findings
        ],
        "config_files": [
            {k: v for k, v in cf.items() if k != "content"}
            for cf in config_files
        ],
        "meta": {
            "scanner_version": VERSION,
            "scan_time": datetime.now(timezone.utc).isoformat(),
        },
    }


# ---------------------------------------------------------------------------
# Main scan orchestration
# ---------------------------------------------------------------------------

def cmd_scan(args: argparse.Namespace) -> None:
    """Execute the scan command."""
    spec = args.repo
    use_color = sys.stdout.isatty() and not args.no_color and not args.json
    output_json = args.json

    owner_repo, local_path = parse_repo_spec(spec)

    if use_color:
        print(f"\n{BOLD}RepoVet{RESET} v{VERSION}\n", file=sys.stderr)
    else:
        print(f"\nRepoVet v{VERSION}\n", file=sys.stderr)

    if local_path:
        # --- Local repo scan ---
        print(f"Scanning local repo: {local_path}", file=sys.stderr)
        meta, config_files, findings = scan_local_repo(local_path)

        # Try to enrich with GitHub data if we have a remote
        health: dict[str, Any] = {"score": 5.0, "signals": ["Local scan (limited health data)"]}
        commits: list[dict] = []
        contributors: list[dict] = []

        if meta.get("github_repo"):
            print(f"  Detected GitHub remote: {meta['github_repo']}", file=sys.stderr)
            print(f"  Enriching with GitHub metadata...", file=sys.stderr)
            gh_meta = fetch_repo_metadata(meta["github_repo"])
            if gh_meta:
                commits = fetch_recent_commits(meta["github_repo"])
                contributors = fetch_contributors(meta["github_repo"])
                health = calculate_health(gh_meta, commits, contributors)
                meta.update({
                    "stars": gh_meta.get("stargazers_count", 0),
                    "forks": gh_meta.get("forks_count", 0),
                    "language": gh_meta.get("language"),
                })

        repo_display = meta.get("github_repo", meta.get("name", local_path))

    else:
        # --- Remote repo scan ---
        print(f"Scanning remote repo: {owner_repo}", file=sys.stderr)
        meta_full, config_files, findings, health, commits, contributors = scan_remote_repo(owner_repo)
        meta = meta_full
        repo_display = owner_repo

    # Calculate scores
    config_safety = 10.0
    for f in findings:
        config_safety -= SEVERITY_SCORES.get(f.severity, 0)
    config_safety = max(0.0, min(10.0, config_safety))

    trust_score, verdict = calculate_trust_score(config_safety, health.get("score", 5.0))

    print(f"  Scan complete.\n", file=sys.stderr)

    # Generate output
    if output_json:
        output = generate_json_output(
            repo_display, trust_score, verdict, config_safety,
            health, findings, config_files, meta,
        )
        json_str = json.dumps(output, indent=2, ensure_ascii=False)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as fp:
                fp.write(json_str + "\n")
            print(f"Wrote JSON report to {args.output}", file=sys.stderr)
        else:
            print(json_str)
    else:
        report = generate_report(
            repo_display, trust_score, verdict, config_safety,
            health, findings, config_files, meta, use_color,
        )
        if args.output:
            # Strip ANSI codes for file output
            clean = re.sub(r"\033\[[0-9;]*m", "", report)
            with open(args.output, "w", encoding="utf-8") as fp:
                fp.write(clean + "\n")
            print(f"Wrote report to {args.output}", file=sys.stderr)
        else:
            print(report)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="repovet",
        description="RepoVet -- Trust assessment for code repositories",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python3 repovet.py scan https://github.com/user/repo
  python3 repovet.py scan user/repo
  python3 repovet.py scan /path/to/local/repo
  python3 repovet.py scan user/repo -o report.md
  python3 repovet.py scan user/repo --json
""",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # scan subcommand
    scan_parser = subparsers.add_parser(
        "scan",
        help="Scan a repository for trust assessment",
        description="Scan a GitHub repo (remote or local) and produce a trust report.",
    )
    scan_parser.add_argument(
        "repo",
        help="GitHub URL (https://github.com/user/repo), shorthand (user/repo), or local path",
    )
    scan_parser.add_argument(
        "-o", "--output",
        metavar="FILE",
        help="Write report to FILE instead of stdout",
    )
    scan_parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON instead of markdown",
    )
    scan_parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored output",
    )

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "scan":
        cmd_scan(args)


if __name__ == "__main__":
    main()
