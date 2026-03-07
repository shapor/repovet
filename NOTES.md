# Skillathon Notes

## What We're Doing
- Hackathon by BenchFlow at Founders Inc, SF — Mar 7, 2026
- Build skills + tasks to evaluate them
- Tracks: CS, Physical World, Professional, Natural Science, OpenClaw (gaming), Continual Learning
- Prizes: $1k 1st, PS5 2nd

## Key Findings from SkillsBench Paper
- Curated skills raise pass rate +16.2pp average across 7 agent-model configs
- **Self-generated skills provide NO benefit** (-1.3pp avg) — human expertise is the differentiator
- 2-3 focused skills is optimal (+18.6pp); 4+ skills only +5.9pp (diminishing returns)
- Detailed/compact skills > comprehensive (comprehensive actually HURTS at -2.9pp)
- Biggest skill uplift by domain: Healthcare (+51.9pp), Manufacturing (+41.9pp)
- Smallest: Software Engineering (+4.5pp), Mathematics (+6.0pp) — already well-represented in pretraining
- Smaller model + skills can beat larger model without: Haiku 4.5 + skills (27.7%) > Opus 4.5 no skills (22.0%)
- 16 of 84 tasks show NEGATIVE skill deltas — skills can hurt on tasks models already handle well
- Claude Code has highest skill utilization rate; Codex CLI frequently *ignores* provided skills

## Task Format (Harbor)
```
task-name/
├── instruction.md          # Human-written task description (conversational tone)
├── task.toml               # Metadata, timeouts, skills config
├── environment/
│   ├── Dockerfile          # Dependencies
│   └── skills/             # Skill folders with SKILL.md
├── solution/
│   └── solve.sh            # Oracle solution (must pass 100%)
└── tests/
    ├── test.sh
    └── test_outputs.py     # Deterministic pytest verifier
```

## Task Requirements
- SOTA models must score <39% without skills
- Composability: tasks requiring 3-6 skills working together
- Distractor skills: fewer than 10
- Instructions must be human-written (GPTZero checked)
- Deterministic verifiers (pytest assertions, not vibes)
- No task-specific leakage in skills

## Skill Format (SKILL.md)
```
---
name: my-skill
description: When to trigger + what it does. Be specific AND say when NOT to trigger.
---

# Instructions body (<500 lines ideal)
```

### Skill Folder Structure
```
skill-name/
├── SKILL.md              # Required — YAML frontmatter + markdown instructions
├── scripts/              # Optional — executable code for deterministic tasks
├── references/           # Optional — docs loaded into context as needed
└── assets/               # Optional — templates, icons, fonts
```

### What Makes a Good Skill
- Description field is the trigger mechanism — be "pushy" (Anthropic's word)
- Explain WHY, not just WHAT — models are smart, treat them that way
- Show anti-patterns (WRONG vs CORRECT) not just correct patterns
- Progressive disclosure: core in SKILL.md, depth in references/
- Include at least one working example
- Concise stepwise guidance > exhaustive documentation

## Cloned Repos (in src/)
| Repo | What |
|------|------|
| `skillsbench` | The benchmark — 86 tasks, 11 domains, Harbor format |
| `anthropic-skills` | Official Anthropic skills (doc skills, skill-creator, etc.) |
| `knowledge-work-plugins` | Anthropic's role-based plugin collection (finance, legal, engineering, etc.) |
| `sundial-skills` | Sundial's curated skills + CLI |
| `awesome-openclaw-skills` | OpenClaw game dev skills |
| `harbor` | Agent evaluation framework SkillsBench runs on |

## Meta-Skills (skills that create/manage skills)
- `anthropic-skills/skills/skill-creator/` — create, eval, improve, benchmark skills
- `knowledge-work-plugins/cowork-plugin-management/` — create-cowork-plugin, cowork-plugin-customizer

## knowledge-work-plugins Domains
bio-research, customer-support, data, design, engineering, enterprise-search, finance, human-resources, legal, marketing, operations, partner-built (apollo, slack, common-room), product-management, productivity, sales

## Useful Links
- SkillsBench paper: https://arxiv.org/abs/2602.12670
- SkillsBench site: https://www.skillsbench.ai
- Anthropic skills repo: https://github.com/anthropics/skills
- Knowledge work plugins: https://github.com/anthropics/knowledge-work-plugins
- Sundial registry: https://www.sundialhub.com
- Sundial skills repo: https://github.com/sundial-org/skills
- Harbor framework: https://github.com/laude-institute/harbor
- Agent Skills spec: https://agentskills.io
- Skill creator blog post: https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills
