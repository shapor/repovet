#!/usr/bin/env python3
"""
Gather metadata about all SKILL.md files across repos under src/.
Outputs a JSON file with detailed stats for each skill.
"""

import json
import os
import re
import subprocess
import sys

BASE_DIR = "/home/shapor/src/skillathon/src"
OUTPUT_FILE = "/home/shapor/src/skillathon/skill_stats.json"

# Known repo names for classification
KNOWN_REPOS = [
    "anthropic-skills",
    "knowledge-work-plugins",
    "sundial-skills",
    "awesome-openclaw-skills",
    "harbor",
    "skillsbench",
]


def find_all_skill_md_files():
    """Use find to locate all SKILL.md files."""
    result = subprocess.run(
        ["find", BASE_DIR, "-name", "SKILL.md", "-type", "f"],
        capture_output=True,
        text=True,
    )
    paths = [p.strip() for p in result.stdout.strip().split("\n") if p.strip()]
    return sorted(paths)


def get_file_size(path):
    """Get file size in bytes."""
    try:
        return os.path.getsize(path)
    except OSError:
        return 0


def get_line_count(path):
    """Get line count of a file."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return sum(1 for _ in f)
    except OSError:
        return 0


def get_folder_size(folder_path):
    """Get total size of a folder recursively in bytes."""
    total = 0
    try:
        for dirpath, dirnames, filenames in os.walk(folder_path):
            for fname in filenames:
                fp = os.path.join(dirpath, fname)
                try:
                    total += os.path.getsize(fp)
                except OSError:
                    pass
    except OSError:
        pass
    return total


def count_files_recursive(folder_path):
    """Count files recursively in a folder."""
    count = 0
    try:
        for dirpath, dirnames, filenames in os.walk(folder_path):
            count += len(filenames)
    except OSError:
        pass
    return count


def check_subdirectories(folder_path):
    """Check for scripts/, references/, assets/ subdirectories."""
    result = {}
    for subdir in ["scripts", "references", "assets"]:
        result[f"has_{subdir}"] = os.path.isdir(os.path.join(folder_path, subdir))
    return result


def parse_yaml_frontmatter(path):
    """Parse YAML frontmatter from a markdown file without requiring PyYAML.

    Handles multiline description values (both block scalars and flow scalars
    that wrap across lines).
    """
    name = None
    description = None

    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except OSError:
        return name, description

    # Check for frontmatter delimiters
    if not content.startswith("---"):
        return name, description

    # Find closing ---
    end_match = re.search(r"\n---\s*\n", content[3:])
    if not end_match:
        return name, description

    frontmatter = content[3 : 3 + end_match.start()]

    # Parse the frontmatter line by line to handle multiline values
    lines = frontmatter.split("\n")
    current_key = None
    current_value_lines = []

    def finalize_field():
        nonlocal name, description
        if current_key == "name":
            val = " ".join(current_value_lines).strip()
            # Strip surrounding quotes
            if (val.startswith('"') and val.endswith('"')) or (
                val.startswith("'") and val.endswith("'")
            ):
                val = val[1:-1]
            name = val
        elif current_key == "description":
            val = " ".join(current_value_lines).strip()
            if (val.startswith('"') and val.endswith('"')) or (
                val.startswith("'") and val.endswith("'")
            ):
                val = val[1:-1]
            description = val

    for line in lines:
        # Check if this is a new top-level key (not indented, has colon)
        top_level_match = re.match(r"^([a-zA-Z_][a-zA-Z0-9_-]*)\s*:\s*(.*)", line)
        if top_level_match:
            # Finalize previous key
            if current_key:
                finalize_field()
            current_key = top_level_match.group(1).lower()
            current_value_lines = []
            val_part = top_level_match.group(2).strip()
            if val_part and val_part not in ("|", ">", "|-", ">-"):
                current_value_lines.append(val_part)
        elif current_key and (line.startswith("  ") or line.startswith("\t")):
            # Continuation line for current key
            current_value_lines.append(line.strip())
        elif current_key and line.strip() == "":
            # Blank line might be part of a block scalar
            pass
        else:
            # Something else; finalize
            if current_key:
                finalize_field()
                current_key = None
                current_value_lines = []

    # Finalize last field
    if current_key:
        finalize_field()

    return name, description


def determine_repo(skill_md_path):
    """Determine which repo a SKILL.md belongs to."""
    rel = os.path.relpath(skill_md_path, BASE_DIR)
    parts = rel.split(os.sep)
    if parts:
        repo_name = parts[0]
        if repo_name in KNOWN_REPOS:
            return repo_name
        return repo_name
    return "unknown"


def determine_category(skill_md_path):
    """Determine the domain/category (parent directory path after the repo name).

    For a path like:
      .../src/knowledge-work-plugins/sales/skills/call-prep/SKILL.md
    The category would be: sales/skills/call-prep

    We return everything between the repo name and SKILL.md.
    """
    rel = os.path.relpath(skill_md_path, BASE_DIR)
    parts = rel.split(os.sep)
    # parts[0] = repo name, parts[-1] = SKILL.md
    if len(parts) > 2:
        return os.sep.join(parts[1:-1])
    elif len(parts) == 2:
        return ""
    return ""


def main():
    print("Finding all SKILL.md files...")
    skill_files = find_all_skill_md_files()
    print(f"Found {len(skill_files)} SKILL.md files")

    results = []
    for i, skill_path in enumerate(skill_files):
        if (i + 1) % 100 == 0 or i == 0:
            print(f"Processing {i + 1}/{len(skill_files)}: {skill_path}")

        parent_dir = os.path.dirname(skill_path)

        # Basic file stats
        file_size = get_file_size(skill_path)
        line_count = get_line_count(skill_path)
        folder_size = get_folder_size(parent_dir)
        file_count = count_files_recursive(parent_dir)

        # Frontmatter
        fm_name, fm_description = parse_yaml_frontmatter(skill_path)

        # Repo and category
        repo = determine_repo(skill_path)
        category = determine_category(skill_path)

        # Subdirectories
        subdirs = check_subdirectories(parent_dir)

        entry = {
            "file_path": skill_path,
            "file_size_bytes": file_size,
            "folder_size_bytes": folder_size,
            "line_count": line_count,
            "name": fm_name,
            "description": (fm_description[:200] if fm_description else None),
            "repo": repo,
            "category": category,
            "file_count_in_folder": file_count,
            "has_scripts": subdirs["has_scripts"],
            "has_references": subdirs["has_references"],
            "has_assets": subdirs["has_assets"],
        }
        results.append(entry)

    # Summary stats
    summary = {
        "total_skills": len(results),
        "by_repo": {},
        "skills_with_scripts": sum(1 for r in results if r["has_scripts"]),
        "skills_with_references": sum(1 for r in results if r["has_references"]),
        "skills_with_assets": sum(1 for r in results if r["has_assets"]),
        "total_file_size_bytes": sum(r["file_size_bytes"] for r in results),
        "total_folder_size_bytes": sum(r["folder_size_bytes"] for r in results),
    }
    for r in results:
        repo = r["repo"]
        summary["by_repo"][repo] = summary["by_repo"].get(repo, 0) + 1

    output = {
        "summary": summary,
        "skills": results,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\nDone! Wrote {len(results)} skill entries to {OUTPUT_FILE}")
    print(f"Summary: {json.dumps(summary, indent=2)}")


if __name__ == "__main__":
    main()
