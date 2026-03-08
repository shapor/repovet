# RepoVet Harbor Task

This directory contains the Harbor benchmark task for evaluating RepoVet's repository trust assessment capabilities.

## What's Inside

- **repovet-trust-assessment/** - Complete Harbor task for repository trust assessment

## Task Overview

**Difficulty**: Medium
**Category**: Security
**Expected Delta**: +40-50pp (20-30% baseline → 70-80% with skills)

The task evaluates whether an agent can:
1. Assess GitHub repositories for trustworthiness
2. Detect security threats (hooks, agent configs, exfiltration)
3. Provide evidence-based trust scores
4. Use remote-first scanning (not clone repos prematurely)

## Quick Start

### Test the Solution

```bash
cd repovet-trust-assessment

# Build Docker image
docker build -t repovet-task ./environment

# Run oracle solution
docker run --rm \
  -v $(pwd)/solution:/solution \
  -v $(pwd)/tests:/tests \
  repovet-task bash -c "bash /solution/solve.sh && bash /tests/test.sh"
```

### Run with Harbor

```bash
# Install Harbor
uv tool install harbor

# Run the task
harbor run \
  --task ./repovet-trust-assessment \
  --agent claude-code \
  --model anthropic/claude-opus-4-6
```

## Task Structure

```
repovet-trust-assessment/
├── task.toml              # Task metadata and configuration
├── instruction.md         # Task description for the agent
├── README.md              # Task documentation
├── environment/
│   └── Dockerfile         # Container with gh CLI, Python, git
├── tests/
│   ├── test.sh            # Test runner
│   ├── test_assessment.py # Pytest validation suite
│   └── repos.txt          # Repository list
└── solution/
    └── solve.sh           # Oracle solution
```

## Expected Results

| Setup | Pass Rate | Notes |
|-------|-----------|-------|
| Baseline | 20-30% | Agents clone first, miss threats |
| + RepoVet skills | 70-80% | Remote scanning, threat detection |
| Oracle | 100% | Reference solution |

## Skills Required

This task is designed to work with:
- `repo-trust-assessment` - Main orchestrator
- `threat-*` family (7 skills) - Threat detection
- `git-commit-intel` - Git history analysis
- `github-project-intel` - PR/issue analysis

## Validation

The test suite checks:
- ✅ Assessment file format (JSON with required fields)
- ✅ All 5 repositories assessed
- ✅ Trust scores in valid range (0-10)
- ✅ Safe repo identified correctly (score ≥7)
- ✅ Malicious repos flagged (score ≤4)
- ✅ Evidence provided for each assessment
- ⚠️  Warning if repos cloned directly (security anti-pattern)

## Integration with SkillsBench

This task is ready for inclusion in SkillsBench:
- Follows Harbor task format specification
- Has deterministic verification (pytest)
- Covers underrepresented security domain
- Shows measurable skill delta
- Includes oracle solution for baseline
