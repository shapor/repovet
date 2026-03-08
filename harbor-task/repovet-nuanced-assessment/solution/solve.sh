#!/bin/bash
set -e

cat > /app/assessment.json << 'EOF'
{
  "url": "https://github.com/benchflow-ai/skillsbench",
  "trust_score": 5.8,
  "recommendation": "Caution",
  "evidence": {
    "project_health": "48 contributors but bus factor of 1. Intense 4-week sprint in Jan 2026, then activity collapsed. 813 PRs all self-merged with zero review.",
    "security": "No leaked secrets, no CVEs in repo code. CVE references are benchmark tasks, not vulnerabilities. curl|sh patterns are instructional, not auto-executed.",
    "config_safety": "No malicious agent configs. Permissions allow-list for grep/ls/find only. HTTP calls target local containers. Leaked OSU user path is accidental disclosure, not a threat."
  },
  "reason": "Academic benchmark with legitimate research backing (UC Davis, Berkeley, Meta) but severe governance issues. Safe to explore, risky as a dependency."
}
EOF

echo "Assessment written to /app/assessment.json"
