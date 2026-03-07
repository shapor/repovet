# Skillathon Hackathon Guide

## Event Details
- **Date**: March 7, 2026, 10am-10:30pm
- **Location**: Founders Inc, Building C Floor 3, 2 Marina Blvd, SF
- **Kickoff**: 11am
- **Organizers**: BenchFlow (Xiangyi Li), Sundial (Belinda Mo, Florent Tavernier), Roey Ben Chaim (Zenity), Grace Zhang (World Intelligence)
- **Speakers**: Bence Nagy (Anthropic), Ryan Marten (Harbor/Terminal-Bench), Xiangyi Li (SkillsBench)
- **Credits**: Anthropic API credits + Daytona credits available (upvote pinned Discord message in their Discord)
- **Speakers noted**: Bence Nagy (Anthropic — mentioned knowledge-work-plugins repo), Ryan Marten (Harbor/Terminal-Bench), Xiangyi Li (SkillsBench)
- **Prizes**: $1k 1st place, PS5 2nd place, all demos recorded and featured

## Tracks

### Data Track (main)
Create a realistic task scenario + agent skill(s) that:
- Fails most frontier models without skills
- Requires composing multiple skills together
- Has deterministic verification

**Sub-tracks by domain:**
- **Computer Science**: SWE, ML, cybersecurity
- **Physical World**: Robotics, manufacturing, energy, infra
- **Professional**: Healthcare, finance, office suite, insurance
- **Natural Science**: Physics, math, chemistry, biology
- **OpenClaw**: Game dev — asset generation, character design, world building, dialogue, modding, testing, live ops

### Continual Learning Track
Improve models/prompts via techniques like recursive language models, GEPA (in-context learning), or RL on the model layer.
- Example: [smolclaw.com](https://smolclaw.com) — see [Xiangyi's tweet](https://x.com/xdotli/status/2030219765630071022)
- Can also combine with data track (skill that improves itself based on execution feedback)

## What Wins (Based on SkillsBench Research)

### The Paper's Key Numbers
- Curated skills: **+16.2pp** average pass rate improvement
- Self-generated skills: **-1.3pp** (worse than nothing!)
- Best config: Gemini CLI + Gemini 3 Flash = 48.7% with skills
- Best improvement: Claude Code + Opus 4.5 = **+23.3pp** delta

### Skill Design Sweet Spots
| Factor | Best | Worst |
|--------|------|-------|
| Skill count per task | 2-3 (+18.6pp) | 4+ (+5.9pp) |
| Skill complexity | Detailed (+18.8pp) | Comprehensive (-2.9pp) |
| Skill length | Moderate/focused | Long/exhaustive |

### Domains with Biggest Skill Impact
| Domain | With Skills | No Skills | Delta |
|--------|------------|-----------|-------|
| Healthcare | 86.1% | 34.2% | **+51.9pp** |
| Manufacturing | 42.9% | 1.0% | **+41.9pp** |
| Cybersecurity | 44.0% | 20.8% | +23.2pp |
| Natural Science | 44.9% | 23.1% | +21.9pp |
| Energy | 47.5% | 29.5% | +17.9pp |
| Finance | 27.6% | 12.5% | +15.1pp |
| Software Engineering | 38.9% | 34.4% | +4.5pp (lowest) |

**Takeaway**: Pick a domain that's underrepresented in model pretraining. Healthcare, manufacturing, energy, and finance have the most room for skills to help.

### What Makes Skills Fail
- 16/84 tasks showed negative deltas
- Skills hurt when they introduce conflicting guidance
- Skills hurt when the model already handles the task well
- Overly comprehensive skills consume context without adding actionable guidance
- Skills that are too generic ("use pandas for data processing") don't help

## Task Format (Harbor)

```
task-name/
├── instruction.md          # Human-written, conversational tone
├── task.toml               # Metadata + skill config
├── environment/
│   ├── Dockerfile          # All dependencies
│   └── skills/             # 2-3 curated + some distractors
│       └── skill-name/
│           └── SKILL.md
├── solution/
│   └── solve.sh            # Oracle — must pass 100%
└── tests/
    ├── test.sh
    └── test_outputs.py     # Deterministic pytest assertions
```

### Task Requirements Checklist
- [ ] SOTA models score <39% without skills
- [ ] Requires composing 3-6 skills together
- [ ] Fewer than 10 distractor skills
- [ ] Instructions are human-written (GPTZero verified)
- [ ] Deterministic verifiers (pytest, not LLM-as-judge)
- [ ] Oracle solution passes 100%
- [ ] No task-specific leakage in skills
- [ ] Conversational instruction tone ("I'm trying to...", "Help me...")

### instruction.md Style
Do:
- Conversational, context-rich ("My boss just sent me this file...")
- Numbered sequential steps
- Explicit file paths and output formats
- Explain the WHY

Don't:
- "Objective:" or "Available Skills:" sections
- Robotic/formal tone
- Ambiguous success criteria

## Skill Format (SKILL.md)

### Minimal Structure
```markdown
---
name: my-skill-name
description: What it does AND when to trigger. Be specific. Also say when NOT to trigger.
---

# Skill Title

## When to use this
[Context for when this skill applies]

## Workflow
[Step-by-step procedural guidance]

## Examples
[At least one concrete worked example]

## Common Pitfalls
[What NOT to do — anti-patterns are highly effective]
```

### Folder Structure
```
skill-name/
├── SKILL.md              # Required (<500 lines ideal)
├── scripts/              # Deterministic/repetitive operations
├── references/           # Deeper docs, loaded on demand
└── assets/               # Templates, config files
```

### Writing Effective Skills
1. **Description is king** — it's the trigger mechanism. Be "pushy" (Anthropic's guidance). Include specific scenarios, file types, user phrases
2. **Explain WHY, not just WHAT** — models are smart, reasoning > rigid rules
3. **Show anti-patterns** — WRONG vs CORRECT examples are very effective (see xlsx skill)
4. **Progressive disclosure** — core workflow in SKILL.md, depth in references/
5. **Include working examples** — at least one concrete input/output
6. **Keep it focused** — 2-3 modules per task, not an encyclopedia
7. **Bundle reusable scripts** — if every agent invocation would write the same helper, include it

### Leakage Prevention (Skills Must NOT Contain)
- Task-specific filenames, paths, or identifiers
- Exact command sequences that solve benchmark tasks
- Constants, magic numbers from task specs
- References to specific test cases or expected outputs

## Available Resources

### Cloned Repos (in src/)
| Repo | Contents | Use For |
|------|----------|---------|
| `skillsbench` | 86 tasks, 11 domains | Reference task format, see what exists |
| `anthropic-skills` | 18 official skills | Gold standard skill examples |
| `knowledge-work-plugins` | 91 role-based skills (14 domains) | Professional domain skill patterns |
| `sundial-skills` | 13 curated skills + CLI | Publishing skills |
| `awesome-openclaw-skills` | 939 community skills | Browsing ecosystem, download counts |
| `harbor` | Evaluation framework | Running tasks locally |

### Best Example Skills to Study
| Skill | Why |
|-------|-----|
| `anthropic-skills/skills/skill-creator` | Meta-skill, eval workflow, conversational tone |
| `anthropic-skills/skills/xlsx` | Production quality, anti-patterns, verification checklist |
| `anthropic-skills/skills/pdf` | Clean progressive disclosure, reference files |
| `knowledge-work-plugins/finance/*` | Domain-specific professional workflows |
| `knowledge-work-plugins/data/*` | Data analysis patterns, dashboard building |

### Tools
- **Harbor CLI**: `harbor tasks init`, `harbor tasks check`, `harbor run`
- **Sundial CLI**: `npx sundial-hub add <skill>` to install, explore 50k+ skills
- **Anthropic skill-creator**: Meta-skill for creating/evaluating/iterating on skills (supports evals, A/B testing, description optimization)

## Strategy Notes

### High-Impact Approach
1. Pick an underrepresented domain (healthcare, manufacturing, energy, finance)
2. Identify a realistic multi-step workflow that requires tacit knowledge
3. Write 2-3 focused, detailed skills that encode that knowledge
4. Create a task that's hard without the skills but tractable with them
5. Build deterministic verification
6. Test with and without skills to confirm positive delta

### What Judges Look For
- Task realism (reflects actual professional workflow)
- Task difficulty (SOTA <39% without skills)
- Skill quality (error-free, internally consistent, genuinely useful beyond the benchmark)
- Oracle quality (matches how domain experts would solve it)
- Anti-cheating (no shortcut solutions)
- Skill delta (meaningful improvement with skills vs without)

## Agent Skills Spec (agentskills.io)

The spec is now an open standard adopted by 30+ agent products. Key details:

### YAML Frontmatter Schema
| Field | Required | Constraints |
|-------|----------|-------------|
| `name` | Yes | Max 64 chars, lowercase + hyphens only, must match directory name |
| `description` | Yes | Max 1024 chars, what it does AND when to use it |
| `license` | No | License name or reference to bundled file |
| `compatibility` | No | Max 500 chars, environment requirements |
| `metadata` | No | Arbitrary key-value (author, version, etc.) |
| `allowed-tools` | No | Space-delimited pre-approved tools (experimental) |

### Progressive Disclosure (Token Budget)
1. **Metadata** (~100 tokens): name + description loaded at startup for ALL skills
2. **Instructions** (<5000 tokens recommended): SKILL.md body loaded on activation
3. **Resources** (as needed): scripts/, references/, assets/ loaded only when required

### Validation
```bash
skills-ref validate ./my-skill
```

### Compatible Agents (30+)
Claude Code, Claude.ai, Cursor, GitHub Copilot, VS Code, OpenAI Codex, Gemini CLI, Goose, Roo Code, OpenHands, Junie (JetBrains), Amp, Letta, TRAE (ByteDance), Spring AI, Databricks, Snowflake, Laravel Boost, Mistral Vibe, Factory, and many more.

## Skills Registries & Directories

### skills.sh — The Agent Skills Directory
- 86,622 total skills indexed
- Top skills: find-skills (443K installs), vercel-react-best-practices (182K), web-design-guidelines (142K)
- Install: `npx skillsadd <owner/repo>`
- Sorting: All Time, Trending (24h), Hot
- Works with Claude Code, Cursor, GitHub Copilot, Cline, etc.

### sundialhub.com — Sundial Registry
- 50,000+ community skills
- Install: `npx sundial-hub add <skill-name>`
- Has install counts per skill
- Also has a `skill` meta-skill for finding/improving/publishing skills

### clawhub.com — OpenClaw
- Source for the awesome-openclaw-skills collection
- 939 top skills curated with download counts
- Top: ByteRover (14K), self-improving-agent (9.3K), Agent Browser (4.7K)
- 20 categories from Agent Core & Memory to Utilities

## Anthropic Skill-Creator (March 2026 Update)
The skill-creator now operates in 4 modes:
1. **Create** — interview user, write SKILL.md, generate test prompts
2. **Eval** — spawn parallel with-skill and without-skill runs, grade assertions
3. **Improve** — generalize from feedback, keep prompts lean, explain the why, bundle repeated scripts
4. **Benchmark** — blind A/B comparison, variance analysis, description optimization

Key features:
- Parallel eval runner with grader/comparator/analyzer sub-agents
- HTML eval viewer (generate_review.py) for qualitative review
- Description optimizer: 60/40 train/test split, 3 runs per query, iterates up to 5x
- Works in Claude Code, Cowork, and Claude.ai (with degraded functionality)

## Hackathon Strategy: MCP + Skill Wrapping

### The Thesis
Skills are the **business logic layer** for agents. MCPs give agents raw capabilities (tools), but skills encode the procedural knowledge of *how to use those tools effectively*. The biggest skill uplift comes from domains where powerful tools exist but require expert knowledge to use correctly.

**Formula**: Powerful MCP (raw capability) + Skill (domain expertise) = High-value submission

### High-Potential MCP + Skill Combos

**Healthcare** (biggest uplift at +51.9pp)
- FHIR MCP server + skill for clinical data harmonization workflows
- PubMed/ClinicalTrials.gov MCP + skill for systematic review methodology
- Apple Health MCP + skill for clinical interpretation of wearable data
- Genomics MCPs (UCSC Genome Browser, BioThings) + skill for variant interpretation

**Finance** (+15.1pp, lots of room to grow)
- Financial data MCPs + skill for DCF modeling, ratio analysis, SEC filing interpretation
- Trading/market data MCP + skill for risk assessment workflows
- Database MCP + skill for financial reconciliation procedures

**Manufacturing** (+41.9pp)
- Database/IoT MCPs + skill for quality control statistical process control (SPC)
- Container orchestration MCP + skill for manufacturing execution system workflows

**Energy** (+17.9pp)
- Infrastructure MCPs + skill for power grid analysis, load forecasting
- Database MCP + skill for energy trading and settlement workflows

**Science** (+21.9pp)
- Spatial transcriptomics MCP + skill for single-cell analysis pipelines
- OpenGenes MCP + skill for longevity research methodology
- Data analysis MCPs + skill for experimental design and statistical testing

### Where to Find MCPs
- [awesome-mcp-servers](https://github.com/punkpeye/awesome-mcp-servers) — largest curated list
- [modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers) — official reference implementations
- [mcpservers.org](https://mcpservers.org/) — web directory
- [awesome-devops-mcp-servers](https://github.com/rohitg00/awesome-devops-mcp-servers) — DevOps focused

## Competitive Intel (from lightning pitches)

Most teams are building workflow/preference skills — not the high-delta domain skills the paper shows winning. This is an opportunity.

| Team/Person | Idea | Track | Threat Level |
|-------------|------|-------|-------------|
| Charlie (skillstack.md) | PDF Maestro — OCR skill using Gemini vision to beat Acrobat on complex manuscripts | Data (CS) | Medium — multi-model approach is interesting, but PDF skill already exists in Anthropic's repo |
| Music/creator person | Skills for independent creators to promote brand, integrated with agent platforms | Data (Professional) | Low — vague, more product than benchmark task |
| William | Relationship management skill — auto-loads contacts from LinkedIn/Slack/email, personalizes comms | Data (Professional) | Low-Medium — cool but hard to make deterministic verifier for |
| Sean Wilder (Netherlands) | Cross-agent collaboration skill for 25-person company using OpenClaw in Slack | Continual Learning? | Low — more of a demo than a benchmark submission |
| Security folks | Mentioned but no pitch details | Data (CS/Cyber) | Unknown |
| Robotics folks | Mentioned but no pitch details | Data (Physical World) | Unknown |

### Observations
- Nobody pitched healthcare, manufacturing, energy, or finance — the highest-delta domains
- Most pitches are workflow tools, not hard domain expertise
- Charlie's PDF idea is closest to a strong submission but competes with existing Anthropic PDF skill
- The relationship management idea is clever but subjective outputs are hard to verify deterministically
- Cross-agent collaboration is more continual learning track territory

### Our Advantage
- We have deep research on what actually wins (paper findings, skill design sweet spots)
- MCP-wrapping strategy targets underserved domains with highest uplift potential
- Most competitors seem unaware of the specific benchmark requirements (deterministic verifiers, <39% SOTA, etc.)

## Links
- [SkillsBench Paper](https://arxiv.org/abs/2602.12670)
- [SkillsBench Site](https://www.skillsbench.ai)
- [Contributing Guide](https://www.skillsbench.ai/docs/contributing)
- [Anthropic Skills Repo](https://github.com/anthropics/skills)
- [Knowledge Work Plugins](https://github.com/anthropics/knowledge-work-plugins)
- [Sundial Registry](https://www.sundialhub.com)
- [Harbor Framework](https://github.com/laude-institute/harbor)
- [Agent Skills Spec](https://agentskills.io)
- [Anthropic Blog: Equipping Agents](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
- [Skill Creator Updates](https://www.geeky-gadgets.com/anthropic-skill-creator/)
- [skills.sh Directory](https://skills.sh/) (86K+ skills indexed)
- [OpenClaw / ClawhHub](https://www.clawhub.com/skills)
- [skills-ref Validation Library](https://github.com/agentskills/agentskills/tree/main/skills-ref)
- [Anthropic Skill Creator Course](https://anthropic.skilljar.com/introduction-to-agent-skills)
