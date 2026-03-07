---
name: judge-panel
description: >
  Evaluate a hackathon submission through the full Skillathon judge panel. Use when
  you want a comprehensive multi-perspective evaluation of an idea, task, or skill.
  Trigger on "evaluate this idea", "judge panel review", "would this win", or
  "hackathon submission review". Loads all 7 judge personas and produces a combined
  scorecard with actionable feedback.
---

# Skillathon Judge Panel Evaluation

## How to Use This Skill

Present any hackathon idea, task, or skill and evaluate it from all 7 perspectives.

## The Panel

| Judge | Org | Lens | Key Question |
|-------|-----|------|-------------|
| Furqan Rydhan | Founders Inc / AppLovin / Nebula | Product potential & agent autonomy | "Would I plug this into my stack?" |
| Bence Nagy | Anthropic | Skill architecture & developer utility | "Would I install this?" |
| Ryan Marten | Harbor | Task difficulty & benchmark quality | "Does this stump models?" |
| Xiangyi Li | BenchFlow | Skill delta & domain impact | "Show me the numbers" |
| Belinda Mo | Sundial | Reusability & community value | "Would anyone else use this?" |
| Roey Ben Chaim | Zenity | Security & governance | "What could go wrong?" |
| Grace Zhang | World Intelligence | Physical world & data infrastructure | "Is this grounded in reality?" |

## Evaluation Workflow

### Step 1: Summarize the Submission
- What domain? What task? What skills?
- What's the claimed difficulty and skill delta?

### Step 2: Score Each Judge (1-5, use their individual rubrics)
Read each judge's SKILL.md in the `skills/judge-*` directories for detailed rubrics.

### Step 3: Identify Consensus and Disagreements
- Where do 4+ judges agree? (strong signal)
- Where do judges disagree? (reveals tradeoffs)

### Step 4: Weighted Final Score
The judges' priorities overlap in predictable ways:

| Theme | Judges Who Care | Combined Weight |
|-------|----------------|----------------|
| Product potential / scale | Furqan, Belinda | HIGH |
| Task difficulty / realism | Ryan, Xiangyi | HIGH |
| Skill quality / architecture | Bence, Xiangyi, Belinda | HIGH |
| Domain impact / novelty | Xiangyi, Grace, Furqan | HIGH |
| Verification / anti-cheating | Ryan, Bence, Roey | MEDIUM |
| Security / governance | Roey | MEDIUM |
| Community / ecosystem value | Belinda, Xiangyi | MEDIUM |
| Agent autonomy / persistence | Furqan, Bence | MEDIUM |
| Physical world relevance | Grace | LOWER (unless in that track) |

### Step 5: Output Format

```
## Panel Scorecard

| Judge | Score | Top Praise | Top Concern |
|-------|-------|-----------|-------------|
| Furqan | X/5 | ... | ... |
| Bence | X/5 | ... | ... |
| Ryan  | X/5 | ... | ... |
| Xiangyi | X/5 | ... | ... |
| Belinda | X/5 | ... | ... |
| Roey  | X/5 | ... | ... |
| Grace | X/5 | ... | ... |

**Panel Average**: X.X/5
**Consensus Strengths**: ...
**Consensus Risks**: ...
**Top 3 Improvements**: ...
**Win Probability**: Low / Medium / High / Very High
```

## What Wins This Hackathon (Cross-Judge Synthesis)

The intersection of all judges' preferences points to:

1. **Underrepresented domain** (Healthcare +51.9pp, Manufacturing +41.9pp)
2. **Genuinely hard task** (<39% without skills, SOTA struggles)
3. **2-3 focused, curated skills** (not comprehensive, not self-generated)
4. **Deterministic verification** (pytest, not LLM-as-judge)
5. **Publishable to Sundial** (reusable beyond the hackathon)
6. **Security-aware** (handles sensitive data correctly)
7. **Clean Harbor format** (instruction.md + task.toml + Dockerfile + tests)
8. **Measurable skill delta** (with/without comparison, >15pp improvement)
