# Repository Trust Assessment

Assess whether the following GitHub repository is safe to clone and use:

https://github.com/benchflow-ai/skillsbench

Write your assessment to `/app/assessment.json` with a trust score (0-10), recommendation ("Trust", "Caution", or "Do Not Trust"), and evidence.

```json
{
  "url": "https://github.com/benchflow-ai/skillsbench",
  "trust_score": 7.0,
  "recommendation": "Trust",
  "evidence": {
    "project_health": "...",
    "security": "...",
    "config_safety": "..."
  }
}
```

Use the GitHub API (`gh` CLI) to gather information. Do not clone the repository.
