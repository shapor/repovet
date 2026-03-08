#!/bin/bash
set -e

# This is the oracle solution that uses RepoVet skills
# In a real Harbor evaluation, the agent would have access to RepoVet skills
# This solution demonstrates the expected approach

# For this demo, we'll simulate the RepoVet assessment
# In practice, the agent would call: /repo-trust-assessment on each URL
# The agent should use gh CLI to fetch repo metadata without cloning

cat > /app/assessment.json << 'EOF'
{
  "repositories": [
    {
      "url": "https://github.com/anthropics/anthropic-sdk-python",
      "trust_score": 9.0,
      "recommendation": "Trust",
      "evidence": {
        "project_health": "Well-maintained by Anthropic, active development, good contributor base",
        "security": "No security issues detected, official Anthropic repository",
        "config_safety": "Clean repository structure, no malicious configurations"
      },
      "reason": "Official Anthropic SDK with strong maintenance and no security concerns"
    },
    {
      "url": "https://github.com/test-org/suspicious-hooks-repo",
      "trust_score": 2.5,
      "recommendation": "Do Not Trust",
      "evidence": {
        "project_health": "Unknown repository",
        "security": "Contains suspicious git hooks",
        "config_safety": "Git hooks that execute on clone detected - HIGH RISK"
      },
      "reason": "Contains malicious git hooks that would execute during clone"
    },
    {
      "url": "https://github.com/test-org/malicious-agent-config",
      "trust_score": 1.5,
      "recommendation": "Do Not Trust",
      "evidence": {
        "project_health": "Unknown repository",
        "security": "Agent configuration files with auto-execution detected",
        "config_safety": "Contains .claude/hooks with automatic execution - CRITICAL THREAT"
      },
      "reason": "Agent config files contain auto-execution code that runs without user approval"
    },
    {
      "url": "https://github.com/test-org/borderline-permissions",
      "trust_score": 5.5,
      "recommendation": "Caution",
      "evidence": {
        "project_health": "Limited activity",
        "security": "No critical issues",
        "config_safety": "Overly permissive configurations but not actively malicious"
      },
      "reason": "Borderline repository with loose permissions - use with caution"
    },
    {
      "url": "https://github.com/test-org/clearly-malicious",
      "trust_score": 0.5,
      "recommendation": "Do Not Trust",
      "evidence": {
        "project_health": "Suspicious repository structure",
        "security": "Multiple threat indicators: credential theft, network exfiltration, obfuscation",
        "config_safety": "CRITICAL: Contains credential access, data exfiltration, and remote code execution"
      },
      "reason": "Multiple critical security threats detected - do not use under any circumstances"
    }
  ]
}
EOF

echo "Repository trust assessment complete. Results written to /app/assessment.json"
