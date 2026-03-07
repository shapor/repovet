#!/usr/bin/env python3
"""
repovet-config-discover.py — Scan a git repo for AI agent configuration files
and extract executable code, instructions, and permission overrides.

Usage:
    python repovet-config-discover.py REPO_PATH [-o output.json]

Output: JSON to stdout (or file with -o)
"""

import argparse
import glob
import json
import os
import re
import sys
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Pattern definitions for each agent tool
# ---------------------------------------------------------------------------

# Map of glob patterns to config type labels
CONFIG_PATTERNS = {
    # Claude Code
    "**/.claude/settings.json": "claude_settings",
    "**/.claude/settings.local.json": "claude_settings_local",
    "**/.claude/hooks/*": "claude_hook",
    "**/.claude/commands/*": "claude_command",
    "**/CLAUDE.md": "claude_instructions",
    "**/.claude.md": "claude_instructions",
    "**/.claudeignore": "claude_ignore",

    # Cursor
    "**/.cursorrules": "cursor_rules",
    "**/.cursor/**/*": "cursor_config",

    # GitHub Copilot
    "**/.github/copilot-instructions.md": "copilot_instructions",

    # Aider
    "**/.aider.conf.yml": "aider_config",
    "**/.aiderignore": "aider_ignore",

    # Continue.dev
    "**/.continue/**/*": "continue_config",
    "**/.continuerc.json": "continue_config",

    # Windsurf / Codeium
    "**/.windsurfrules": "windsurf_rules",

    # Generic agent instructions
    "**/AGENTS.md": "agents_instructions",

    # Skills
    "**/skills/*/SKILL.md": "skill_definition",
    "**/skills/*/scripts/*": "skill_script",
}

# Languages we recognise in fenced code blocks
CODE_BLOCK_LANGUAGES = {
    "bash", "sh", "zsh", "shell",
    "python", "python3", "py",
    "javascript", "js", "node",
    "typescript", "ts",
    "ruby", "rb",
    "perl", "php",
    "powershell", "ps1", "pwsh",
    "cmd", "bat",
}

# Regex for fenced code blocks: ```lang ... ```
CODE_BLOCK_RE = re.compile(
    r"^```(\w+)[ \t]*\n(.*?)^```",
    re.MULTILINE | re.DOTALL,
)

# Settings keys that represent permission overrides / security-relevant config
PERMISSION_KEYS = {
    "dangerouslySkipPermissions",
    "autoApprove",
    "allowedTools",
    "disabledTools",
    "mcpServers",
    "permissions",
    "allow",
    "deny",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def resolve_repo(path: str) -> str:
    """Return absolute, resolved repo path or exit with error."""
    repo = os.path.realpath(os.path.expanduser(path))
    if not os.path.isdir(repo):
        print(f"Error: {path!r} is not a directory", file=sys.stderr)
        sys.exit(1)
    return repo


def relative(repo_root: str, filepath: str) -> str:
    """Return path relative to repo root."""
    return os.path.relpath(filepath, repo_root)


def nested_depth(rel_path: str) -> int:
    """How many parent directories deep from repo root (0 = root level)."""
    parts = rel_path.split(os.sep)
    # The file itself is the last part; parents are everything before it
    return max(0, len(parts) - 1)


def is_nested(rel_path: str) -> bool:
    """True if the config file is NOT at repo root level.

    Root-level means the file (or its immediate config dir) sits directly
    in the repo root.  E.g. `.claude/settings.json` has depth 2 but the
    `.claude` dir is at root, so that's root-level.  `sub/.claude/settings.json`
    is nested.
    """
    parts = rel_path.split(os.sep)
    # Files directly in root (depth 0 or 1 dir like .claude/*)
    # are considered root-level.  Anything deeper where the *first*
    # component is NOT a known config dir is nested.
    if len(parts) <= 1:
        return False
    # Known root-level config dirs
    root_dirs = {".claude", ".cursor", ".continue", ".github", "skills"}
    if parts[0] in root_dirs:
        return False
    return True


def safe_read(filepath: str) -> str | None:
    """Read file content, returning None on error."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except (OSError, PermissionError):
        return None


def safe_json_load(filepath: str) -> dict | None:
    """Parse a JSON file, returning None on error."""
    text = safe_read(filepath)
    if text is None:
        return None
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None


def discover_files(repo_root: str) -> list[tuple[str, str]]:
    """Walk the repo and return (absolute_path, config_type) for every match.

    Uses glob.glob with recursive=True for each pattern.  Deduplicates
    and skips `.git/` internals.
    """
    seen: set[str] = set()
    results: list[tuple[str, str]] = []

    for pattern, config_type in CONFIG_PATTERNS.items():
        full_pattern = os.path.join(repo_root, pattern)
        for match in glob.glob(full_pattern, recursive=True):
            abspath = os.path.realpath(match)
            if abspath in seen:
                continue
            # Skip anything inside .git directory
            rel = relative(repo_root, abspath)
            if rel.startswith(".git" + os.sep) or rel == ".git":
                continue
            # Only include files (not directories)
            if not os.path.isfile(abspath):
                continue
            seen.add(abspath)
            results.append((abspath, config_type))

    # Sort by relative path for deterministic output
    results.sort(key=lambda t: relative(repo_root, t[0]))
    return results


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

def extract_code_blocks(filepath: str, content: str) -> list[dict]:
    """Extract fenced code blocks from a markdown file."""
    blocks = []
    for m in CODE_BLOCK_RE.finditer(content):
        lang = m.group(1).lower()
        code = m.group(2)
        if lang not in CODE_BLOCK_LANGUAGES:
            continue
        # Compute line numbers (1-based)
        start_offset = m.start(2)
        end_offset = m.end(2)
        line_start = content[:start_offset].count("\n") + 1
        line_end = content[:end_offset].count("\n")
        if line_end < line_start:
            line_end = line_start

        rel = relative(repo_root_global, filepath)
        blocks.append({
            "source_file": rel,
            "source_type": "code_block",
            "language": normalise_lang(lang),
            "content": code.rstrip("\n"),
            "line_start": line_start,
            "line_end": line_end,
            "is_nested": is_nested(rel),
            "nested_depth": nested_depth(rel),
        })
    return blocks


def extract_script(filepath: str) -> dict | None:
    """Read a standalone script file (hook, skill script, command)."""
    content = safe_read(filepath)
    if content is None:
        return None
    rel = relative(repo_root_global, filepath)
    lang = detect_script_language(filepath, content)
    lines = content.split("\n")
    return {
        "source_file": rel,
        "source_type": classify_script_type(rel),
        "language": lang,
        "content": content,
        "line_start": 1,
        "line_end": len(lines),
        "is_nested": is_nested(rel),
        "nested_depth": nested_depth(rel),
    }


def extract_permissions(filepath: str, data: dict) -> list[dict]:
    """Pull security-relevant settings from a parsed JSON settings file."""
    perms = []
    rel = relative(repo_root_global, filepath)

    def walk(obj: dict | list, prefix: str = ""):
        if isinstance(obj, dict):
            for key, value in obj.items():
                full_key = f"{prefix}.{key}" if prefix else key
                if key in PERMISSION_KEYS:
                    perms.append({
                        "source_file": rel,
                        "setting": full_key,
                        "value": value,
                    })
                # Recurse into nested dicts / lists
                if isinstance(value, (dict, list)):
                    walk(value, full_key)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                if isinstance(item, (dict, list)):
                    walk(item, f"{prefix}[{i}]")

    walk(data)
    return perms


def extract_instruction(filepath: str, content: str, config_type: str) -> dict:
    """Capture full text of an instruction / rules file."""
    rel = relative(repo_root_global, filepath)
    lines = content.split("\n")
    return {
        "source_file": rel,
        "source_type": config_type,
        "content": content,
        "line_start": 1,
        "line_end": len(lines),
    }


# ---------------------------------------------------------------------------
# Classification helpers
# ---------------------------------------------------------------------------

def normalise_lang(lang: str) -> str:
    mapping = {
        "sh": "bash", "zsh": "bash", "shell": "bash",
        "python3": "python", "py": "python",
        "js": "javascript", "node": "javascript",
        "ts": "typescript",
        "rb": "ruby",
        "ps1": "powershell", "pwsh": "powershell",
        "bat": "cmd",
    }
    return mapping.get(lang, lang)


def detect_script_language(filepath: str, content: str) -> str:
    """Guess language from extension or shebang."""
    ext = os.path.splitext(filepath)[1].lower()
    ext_map = {
        ".sh": "bash", ".bash": "bash", ".zsh": "bash",
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".rb": "ruby",
        ".pl": "perl",
        ".php": "php",
        ".ps1": "powershell",
    }
    if ext in ext_map:
        return ext_map[ext]

    # Check shebang
    first_line = content.split("\n", 1)[0] if content else ""
    if first_line.startswith("#!"):
        if "python" in first_line:
            return "python"
        if "bash" in first_line or "sh" in first_line:
            return "bash"
        if "ruby" in first_line:
            return "ruby"
        if "node" in first_line:
            return "javascript"
        if "perl" in first_line:
            return "perl"

    # JSON files (commands)
    if ext == ".json":
        return "json"
    if ext in (".yml", ".yaml"):
        return "yaml"
    if ext == ".md":
        return "markdown"

    return "unknown"


def classify_script_type(rel_path: str) -> str:
    """Determine source_type based on path."""
    parts = rel_path.replace("\\", "/").split("/")
    if ".claude" in parts:
        idx = parts.index(".claude")
        rest = parts[idx + 1:]
        if rest and rest[0] == "hooks":
            return "hook"
        if rest and rest[0] == "commands":
            return "command"
    if "skills" in parts:
        return "skill_script"
    return "script"


INSTRUCTION_TYPES = {
    "claude_instructions",
    "cursor_rules",
    "copilot_instructions",
    "windsurf_rules",
    "agents_instructions",
    "skill_definition",
}

EXECUTABLE_TYPES = {
    "claude_hook",
    "claude_command",
    "skill_script",
}

MARKDOWN_TYPES = {
    "claude_instructions",
    "copilot_instructions",
    "agents_instructions",
    "skill_definition",
    "windsurf_rules",
    "cursor_rules",
}


# ---------------------------------------------------------------------------
# Main scanning logic
# ---------------------------------------------------------------------------

# Will be set in main() so helpers can use it
repo_root_global: str = ""


def scan_repo(repo_root: str) -> dict:
    """Perform a full scan and return the result dict."""
    global repo_root_global
    repo_root_global = repo_root

    config_files: list[dict] = []
    executables: list[dict] = []
    instructions: list[dict] = []
    permissions: list[dict] = []
    config_type_set: set[str] = set()
    nested_count = 0

    discovered = discover_files(repo_root)

    for filepath, config_type in discovered:
        rel = relative(repo_root, filepath)
        try:
            size = os.path.getsize(filepath)
        except OSError:
            size = 0

        config_files.append({
            "path": rel,
            "type": config_type,
            "size_bytes": size,
            "is_nested": is_nested(rel),
            "nested_depth": nested_depth(rel),
        })

        if is_nested(rel):
            nested_count += 1

        # Determine top-level tool category for summary
        tool = config_type.split("_")[0]  # e.g. "claude", "cursor", ...
        config_type_set.add(tool)

        content = safe_read(filepath)
        if content is None:
            continue

        # --- Extract permissions from JSON settings files ---
        if config_type in ("claude_settings", "claude_settings_local"):
            data = safe_json_load(filepath)
            if data:
                permissions.extend(extract_permissions(filepath, data))

        # --- Extract instruction text ---
        if config_type in INSTRUCTION_TYPES:
            instructions.append(extract_instruction(filepath, content, config_type))

        # --- Extract code blocks from markdown-like files ---
        if config_type in MARKDOWN_TYPES:
            executables.extend(extract_code_blocks(filepath, content))

        # --- Extract executable scripts ---
        if config_type in EXECUTABLE_TYPES:
            exe = extract_script(filepath)
            if exe:
                executables.append(exe)

    # --- Build summary ---
    summary = {
        "total_config_files": len(config_files),
        "total_executables": len(executables),
        "total_instructions": len(instructions),
        "total_permissions": len(permissions),
        "nested_configs_found": nested_count,
        "config_types": sorted(config_type_set),
    }

    return {
        "repo_path": repo_root,
        "repo_name": os.path.basename(repo_root),
        "scan_time": datetime.now(timezone.utc).isoformat(),
        "config_files": config_files,
        "executables": executables,
        "instructions": instructions,
        "permissions": permissions,
        "summary": summary,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Scan a git repo for AI agent config files and extract executable code.",
    )
    parser.add_argument(
        "repo_path",
        help="Path to the local git repository to scan.",
    )
    parser.add_argument(
        "-o", "--output",
        metavar="FILE",
        default=None,
        help="Write JSON output to FILE instead of stdout.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        default=True,
        help="Pretty-print JSON output (default: true).",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        default=False,
        help="Compact JSON output (no indentation).",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    repo_root = resolve_repo(args.repo_path)
    result = scan_repo(repo_root)

    indent = None if args.compact else 2
    json_str = json.dumps(result, indent=indent, ensure_ascii=False)

    if args.output:
        out_dir = os.path.dirname(os.path.abspath(args.output))
        if out_dir and not os.path.isdir(out_dir):
            os.makedirs(out_dir, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(json_str)
            f.write("\n")
        print(f"Wrote {args.output}", file=sys.stderr)
    else:
        print(json_str)


if __name__ == "__main__":
    main()
