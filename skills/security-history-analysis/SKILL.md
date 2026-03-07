---
name: security-history-analysis
description: |
  Scans git history from commits.csv for security-related patterns, committed
  secrets, force-push indicators, and vulnerable dependency signals. Use when
  the user asks about security posture, CVE history, secret leaks, or
  vulnerability exposure. Do NOT use for live code scanning or agent config
  threats — those belong to the threat-* skills.
---

# Security History Analysis

## When to use this

- User asks "does this repo have security issues?" or "any CVEs?"
- User wants to know if secrets were ever committed
- User asks about force-push history or hidden commits
- You have `commits.csv` at `~/.repovet/cache/{repo}/commits.csv`

## Input

CSV file with columns: `repo_name`, `commit_hash`, `author_name`, `author_email`, `author_date`, `committer_name`, `committer_email`, `commit_date`, `subject`, `body`, `parent_hashes`, `refs`, `is_merge`, `files_changed`, `insertions`, `deletions`, `changed_files`, `lang_stats`, `dir_stats`

Location: `~/.repovet/cache/{repo}/commits.csv`

The `changed_files` column contains a semicolon-separated list of file paths modified in each commit. The `subject` and `body` columns contain the commit message.

## Workflow

### 1. Security keyword scan in commit messages

Search `subject` and `body` for these patterns (case-insensitive):

**Critical severity** (score impact: -2 each):
- `CVE-\d{4}-\d+` (specific CVE references)
- `SQL injection`, `XSS`, `cross-site scripting`
- `remote code execution`, `RCE`
- `exploit`, `zero-day`, `0day`

**High severity** (score impact: -1 each):
- `vulnerability`, `vulnerable`
- `security fix`, `security patch`, `security update`
- `authentication bypass`, `auth bypass`
- `privilege escalation`
- `buffer overflow`, `heap overflow`, `stack overflow`
- `denial of service`, `DoS`

**Medium severity** (score impact: -0.5 each):
- `security`, `hardening`
- `sanitize`, `sanitization`, `escape`, `escaping`
- `CSRF`, `SSRF`, `XXE`, `IDOR`
- `timing attack`, `side channel`

**Positive indicators** (score impact: +0.5 each, max +2):
- `security audit`, `pen test`, `penetration test`
- `SECURITY.md`, `security policy`
- `bug bounty`
- `2FA`, `MFA`, `two-factor`

```python
import re

critical = [
    re.compile(r'CVE-\d{4}-\d+', re.I),
    re.compile(r'SQL\s*injection', re.I),
    re.compile(r'\bXSS\b', re.I),
    re.compile(r'remote\s+code\s+execution|\bRCE\b', re.I),
    re.compile(r'\bexploit\b', re.I),
    re.compile(r'zero[\s-]?day|0[\s-]?day', re.I),
]

# Apply each pattern to subject + body, collect findings
findings = []
for row in commits:
    text = f"{row['subject']} {row['body']}"
    for pattern in critical:
        if pattern.search(text):
            findings.append({
                'commit': row['commit_hash'],
                'date': row['author_date'],
                'severity': 'critical',
                'match': pattern.pattern,
                'subject': row['subject'],
            })
```

### 2. Force-push and rebase indicators

Check for signs of rewritten history:

- **Ref anomalies**: look in `refs` column for unusual patterns
- **Committer vs author mismatch**: when `committer_date` is significantly later than `author_date` (> 7 days), the commit may have been rebased
- **Gap detection**: sort by `author_date`, look for missing sequence where commit hashes in `parent_hashes` reference unknown parents (parent not in dataset)
- **Commit message patterns**: `force push`, `rebase`, `squash`, `amend`, `rewrite history`

Report each finding with the commit hash and date.

### 3. Committed secrets scan

Examine the `changed_files` column for filenames that suggest secrets:

**High risk filenames** (should never be committed):
- `.env`, `.env.local`, `.env.production`, `.env.staging`
- `credentials.json`, `credentials.yml`, `credentials.xml`
- `secrets.json`, `secrets.yml`, `secrets.yaml`
- `*.pem`, `*.key`, `*.p12`, `*.pfx`, `*.keystore`
- `id_rsa`, `id_dsa`, `id_ecdsa`, `id_ed25519`
- `.htpasswd`, `.pgpass`, `.netrc`
- `token.json`, `tokens.json`
- `service-account*.json`
- `aws-credentials`, `.aws/credentials`

**Medium risk filenames**: `config.json`, `config.yml`, `docker-compose*.yml`, `application.properties`, `application.yml`, `.npmrc`, `.pypirc`

Match filenames from `changed_files` (semicolon-separated) against these patterns using regex. Split, strip, and test each file path. Collect findings with commit hash, date, severity, and matched file.

### 4. Vulnerable dependency signals

Check `changed_files` for dependency file modifications and cross-reference with commit messages:

**Dependency files to watch**:
- `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml` (Node.js)
- `requirements.txt`, `Pipfile.lock`, `poetry.lock` (Python)
- `Gemfile.lock` (Ruby)
- `go.sum` (Go)
- `Cargo.lock` (Rust)
- `pom.xml`, `build.gradle` (Java)
- `composer.lock` (PHP)

When a dependency file is changed AND the commit message mentions security-related keywords (from step 1), flag it as a security-related dependency update.

Count:
- Total dependency file updates
- Security-motivated dependency updates
- Ratio of security to total dependency updates

A high ratio of security updates suggests exposure to dependency vulnerabilities.

## Calculating the security score

Start at 10.0 and apply deductions:

```python
score = 10.0

# Critical findings: -2 each (min 0 from this category)
score -= min(len(critical_findings) * 2, 6)

# High findings: -1 each
score -= min(len(high_findings) * 1, 4)

# Medium findings: -0.5 each
score -= min(len(medium_findings) * 0.5, 2)

# Committed secrets: -1.5 each (this is serious)
score -= min(len(secret_findings) * 1.5, 5)

# Force-push indicators: -0.5 each
score -= min(len(forcepush_findings) * 0.5, 2)

# Positive indicators: +0.5 each (max +2)
score += min(len(positive_findings) * 0.5, 2)

# Clamp to 0-10
score = max(0, min(10, score))
```

## Output format

Produce a markdown report with these sections:

- **Security Score: X.X / 10**
- **Summary**: counts of security commits, CVEs, secret leaks, force-push indicators, positive signals
- **Critical Findings**: table with commit, date, type, details
- **High Severity Findings**: table of findings
- **Committed Secrets**: table with commit, date, file, risk level
- **History Integrity**: force-push / rebase findings
- **Dependency Security**: total updates, security-motivated updates, affected ecosystems
- **Positive Signals**: audit references, security policy, etc.
- **Recommendations**: actionable items based on findings

## Common Pitfalls

- **Do NOT assume all security keywords mean vulnerabilities.** A commit saying "add security documentation" is positive, not negative. Check context.
- **Do NOT flag .env.example or .env.template as secret leaks.** These are template files. Only flag actual secret files.
- **Do NOT double-count.** If a single commit matches both "CVE" and "vulnerability", count it once at the highest severity.
- **Handle missing changed_files gracefully.** Some commits (especially merges) may have empty `changed_files`.
- **Normalize file paths.** The `changed_files` field may contain paths with leading slashes or varied separators. Strip and normalize before matching.
- **Recency matters.** A CVE fix from 5 years ago is less concerning than one from last month. Weight recent findings more heavily in the narrative, even if the score formula treats them equally.
