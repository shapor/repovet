# AI Coding Agent Configuration Files — Complete Inventory

## Purpose
Comprehensive list of ALL configuration files that AI coding agents read, so RepoVet can scan for malicious config across all popular tools.

---

## Claude Code

### Config Files
- `.claude/settings.json` — Main settings (permissions, MCP servers)
- `.claude/hooks/*.sh` — Pre/post command hooks
- `.claude/commands/` — Custom slash commands (JSON files)
- `CLAUDE.md` / `.claude.md` — Instructions for the agent
- `.claudeignore` — Files to exclude from context (?)

### Skills
- `skills/*/SKILL.md` — Skill definitions
- `skills/*/scripts/` — Executable scripts referenced by skills

### Unknown / To Verify
- **Does Claude Code read nested `.claude/` directories?** ❓
- **Does it read nested `CLAUDE.md` files?** ❓
- **Search depth: root only vs recursive?** ❓

### Where to Confirm
- [ ] Check `/help` in Claude Code CLI
- [ ] Look at `.claude-plugin/` in anthropics/claude-code repo
- [ ] Test: Create nested `.claude/` and see if it's recognized
- [ ] File GitHub issue asking for clarification

---

## Cursor

### Config Files
- `.cursorrules` — Instructions/rules for Cursor
- `.cursor/` — Directory for Cursor config (exact contents unknown)

### Unknown / To Verify
- **File format of `.cursorrules`** ❓ (plain text? markdown? JSON?)
- **Does Cursor read nested `.cursorrules`?** ❓
- **What's in `.cursor/` directory?** ❓
- **Any executable hooks or scripts?** ❓

### Where to Confirm
- [ ] Check cursor.com/docs
- [ ] Search GitHub for `.cursorrules` examples
- [ ] Test: Create example and see what Cursor reads
- [ ] Ask in forum.cursor.com

---

## GitHub Copilot

### Config Files
- `.github/copilot-instructions.md` — Custom instructions for Copilot
- `.github/copilot.yml` or `.github/copilot.yaml` (?) — Config file
- Workspace settings in `.vscode/settings.json` (Copilot sections)

### Unknown / To Verify
- **Does it read `.github/copilot-instructions.md` from nested dirs?** ❓
- **Other config file locations?** ❓
- **Any executable components?** ❓

### Where to Confirm
- [ ] Check GitHub Copilot docs
- [ ] Search for "copilot custom instructions" documentation
- [ ] Review VS Code extension docs

---

## Windsurf (Codeium)

### Config Files
- `.windsurfrules` (?) — Similar to `.cursorrules`
- `.codeium/` directory (?)

### Unknown / To Verify
- **What config files does Windsurf actually use?** ❓
- **Format and scanning behavior?** ❓

### Where to Confirm
- [ ] Check codeium.com documentation
- [ ] Search for Windsurf config examples

---

## Aider

### Config Files
- `.aider.conf.yml` — Main configuration
- `.aiderignore` — Files to ignore
- `.aider/` directory (?)

### Unknown / To Verify
- **Does it execute any code from config?** ❓
- **Nested config support?** ❓

### Where to Confirm
- [ ] Check aider.chat documentation
- [ ] Review github.com/paul-gauthier/aider

---

## Cody (Sourcegraph)

### Config Files
- `.cody/` directory (?)
- `.codyignore` — Files to exclude
- Workspace settings in IDE config

### Unknown / To Verify
- **Config file locations?** ❓
- **Any executable components?** ❓

### Where to Confirm
- [ ] Check sourcegraph.com/cody documentation
- [ ] Review Cody extension docs

---

## Zed AI

### Config Files
- Settings in `~/.config/zed/settings.json` (user-level)
- Project-level settings (?)
- `.zedignore` (?)

### Unknown / To Verify
- **Does Zed have project-level config files?** ❓
- **Any repo-specific instructions?** ❓

### Where to Confirm
- [ ] Check zed.dev documentation
- [ ] Review Zed editor settings docs

---

## Continue.dev

### Config Files
- `.continuerc.json` — Main configuration
- `.continue/` directory — Config and context
- `continue-config.json` (?)

### Unknown / To Verify
- **Exact config file names and locations?** ❓
- **Any executable components?** ❓

### Where to Confirm
- [ ] Check continue.dev documentation
- [ ] Review github.com/continuedev/continue

---

## Codex / OpenAI API Clients

### Config Files
Varies by client, but commonly:
- `.openai-config` (?)
- API keys in `.env` files
- System prompts in various locations

### Unknown / To Verify
- **Are there standard Codex config files?** ❓
- **What do popular Codex clients read?** ❓

### Where to Confirm
- [ ] Check OpenAI Codex documentation (deprecated?)
- [ ] Review popular Codex wrapper tools

---

## Gemini Code Assist / Duet AI

### Config Files
- Google Cloud workspace settings
- `.gcloudignore` (?)
- Project-level config (?)

### Unknown / To Verify
- **Does Gemini Code Assist read local config files?** ❓
- **Any repo-level instructions?** ❓

### Where to Confirm
- [ ] Check Google Cloud documentation
- [ ] Review Gemini Code Assist docs

---

## Tabnine

### Config Files
- `.tabnine` directory (?)
- Workspace settings in IDE config
- `tabnine.yml` (?)

### Unknown / To Verify
- **Config file locations?** ❓
- **Any project-level settings?** ❓

### Where to Confirm
- [ ] Check tabnine.com documentation
- [ ] Review Tabnine extension docs

---

## Amazon CodeWhisperer

### Config Files
- AWS config (`.aws/`)
- IDE-specific settings
- Project-level config (?)

### Unknown / To Verify
- **Does CodeWhisperer read local config files?** ❓
- **Any custom instructions support?** ❓

### Where to Confirm
- [ ] Check AWS documentation
- [ ] Review CodeWhisperer docs

---

## Priority for RepoVet v1

### Must Scan (High Priority)
1. **Claude Code** — `.claude/`, `CLAUDE.md`, skills
2. **Cursor** — `.cursorrules`, `.cursor/`
3. **GitHub Copilot** — `.github/copilot-instructions.md`

**Rationale**: These are the most popular and have clear repo-level config files.

### Should Scan (Medium Priority)
4. **Aider** — `.aider.conf.yml`
5. **Continue** — `.continue/`
6. **Windsurf/Codeium** — `.windsurfrules`, `.codeium/`

**Rationale**: Growing popularity, may have executable config.

### Nice to Have (Low Priority)
7. **Cody** — `.cody/`, `.codyignore`
8. **Tabnine** — `.tabnine/`
9. Other tools with less clear config patterns

---

## Common Patterns Across Tools

### Likely Config Locations
1. **Root directory** — Most tools read config from repo root
2. **`.github/` directory** — GitHub-specific integrations
3. **Hidden directories** — `.toolname/` pattern is common
4. **Dotfiles** — `.toolnamerules`, `.toolnamerc`, `.toolname.config`

### Common Features to Scan For
1. **Custom instructions** — Text that influences agent behavior
2. **Ignore patterns** — Could hide malicious files from scanning
3. **Hooks/scripts** — Executable code run by the agent
4. **API keys** — Credentials embedded in config
5. **Permission overrides** — Bypassing safety features

---

## Research Action Items

### Immediate (Before Implementing RepoVet)
- [ ] Test Claude Code with nested `.claude/` directories
- [ ] Search GitHub for `.cursorrules` examples and patterns
- [ ] Find Copilot custom instructions documentation
- [ ] Check if any tools execute scripts from config files

### Post-Hackathon (Complete Inventory)
- [ ] Create test repos for each tool
- [ ] Document exact scanning behavior
- [ ] Build comprehensive config file database
- [ ] Create threat model per tool

---

## Default Scanning Strategy for RepoVet v1

We **MUST scan recursively** — not optional:

### Scan Recursively
```python
# Scan entire repo tree, not just root
patterns = [
    ".claude/**/*",
    "CLAUDE.md",
    "**/.claude.md",
    ".cursorrules",
    "**/.cursorrules",
    ".cursor/**/*",
    ".github/copilot-instructions.md",
    ".aider.conf.yml",
    ".continue/**/*",
    ".windsurfrules",
    ".codeium/**/*",
    "skills/**/SKILL.md",
]
```

### Rationale: Launch Directory Attack Vector

**Even if agents only read config from their launch directory, users can be social-engineered to launch from subdirectories:**

```bash
# Attack scenario
cd ~/victim-repo
git clone https://github.com/attacker/malicious-repo

# Repo structure:
malicious-repo/
├── README.md                    # "Looks normal at root"
└── src/
    └── backend/
        └── .claude/
            └── hooks/
                └── pre-command.sh  # Malicious hook

# Social engineering:
"Hey can you help debug the backend module?
 Just cd into src/backend and run your agent"

cd malicious-repo/src/backend
claude-code                      # Now reads ./. claude/ from here!
                                 # Malicious hook executes
```

**The threat model isn't just "does the agent walk the tree?" — it's "where might a user launch the agent?"**

Therefore:
1. **Must scan recursively** — Every subdirectory is a potential launch point
2. **Nested config = red flag** — Legitimate repos rarely have nested agent config
3. **Report all findings** — Even if tool doesn't read it, it's suspicious
4. **User education** — "This repo has Claude config in subdirectories — only launch from root"

### Report Nested Config Separately
```
⚠️ Warning: Found nested configuration files
  - src/suspicious/.claude/hooks/evil.sh
  - vendor/lib/.cursorrules

Note: Some tools may not read these nested configs, but their presence is suspicious.
```

---

## Next Steps

1. **Start with what we know** — Scan Claude, Cursor, Copilot config files
2. **Test nested behavior** — Create test repos and verify
3. **Document as we go** — Update this inventory with findings
4. **Expand post-hackathon** — Add more tools as we confirm their config patterns

This inventory should be a living document that grows over time.
