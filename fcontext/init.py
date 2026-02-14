"""fcontext init — initialize .fcontext/ in a workspace."""
from __future__ import annotations

import sys
from pathlib import Path

# ── Instruction template (the working protocol) ──────────────────────────────
#
# Design principles (from Anthropic skill-creator):
#   • Claude is already smart — only add what it CANNOT infer
#   • Imperative form — tell Claude what to DO, not what things ARE
#   • "When to use" goes in description, not body (body loads after trigger)
#   • Concise > verbose — every token must justify its cost
#   • Separate Skills for different workflows — they compose better

# Full protocol stored in .fcontext/instructions.md (Single Source of Truth)
INSTRUCTIONS_MD = """\
# fcontext — Working Protocol

This workspace uses `fcontext` CLI to manage structured data in `.fcontext/`.
Always check `.fcontext/` BEFORE searching the codebase.

## Lookup Order

For EVERY question, check these sources first:

1. `.fcontext/_workspace.map` — workspace structure overview
2. `.fcontext/_requirements/items.csv` — requirements, stories, tasks, bugs
3. `.fcontext/_cache/` — converted binary files (PDF/DOCX/XLSX → Markdown)
4. `.fcontext/_topics/` — accumulated analysis from previous sessions

Only search code files AFTER checking these.

## Requirements

Run CLI commands — do NOT parse CSV manually:

```
fcontext req list                     # all items (--type, --status filters)
fcontext req tree                     # hierarchy view
fcontext req board                    # kanban by status
fcontext req show ID                  # details + changelog
fcontext req add "title" -t TYPE      # types: roadmap/epic/requirement/story/task/bug
fcontext req set ID field value       # update (auto-logs changelog)
fcontext req link ID TYPE TARGET      # link types: supersedes/evolves/relates/blocks
fcontext req trace ID                 # follow evolution chain
fcontext req comment ID "msg"         # append comment
```

Add `--author` and `--source` on `req add` to record provenance.

Requirements are immutable. When a requirement changes:
1. Create a new one with `req add`
2. Link: `fcontext req link NEW supersedes OLD` (or `evolves`)

## Binary Files

Read `.fcontext/_cache/` for converted Markdown. If not cached:

```
fcontext index <file>                 # convert one file
fcontext index <dir>                  # convert all in directory
```

Never use other conversion tools — always use `fcontext index` so results are cached and reusable.

## Topics

Save multi-step analysis to `.fcontext/_topics/<name>.md` when findings would be useful in a future session. Skip for single-turn Q&A.

## Other Commands

```
fcontext init                         # initialize .fcontext/
fcontext enable <agent>               # activate agent (copilot/claude/cursor)
fcontext status                       # index statistics
fcontext clean                        # clear cache
fcontext reset                        # delete all .fcontext/ data
fcontext topic list|show|clean        # manage topics
```
"""

# ── Multi-skill architecture ──────────────────────────────────────────────────
#
# Split into focused skills so each has a tight description (≤200 chars)
# and only loads relevant context. Skills compose automatically.
#
#   fcontext       — workspace structure & general commands
#   fcontext-index — binary file conversion & cache
#   fcontext-req   — requirements management (CRUD, evolution, provenance)
#   fcontext-topic — persist & resume multi-step analysis

SKILLS = {
    "fcontext": {
        "description": (
            "Workspace structure overview. Read .fcontext/_workspace.map "
            "to understand project layout, directories, and file types "
            "before answering questions about the project."
        ),
        "body": """\
# Workspace Context

Read `.fcontext/_README.md` for a project knowledge summary, then `_workspace.map` for structure.

This workspace uses `fcontext` CLI. The `.fcontext/` directory contains:

- `_README.md` — project knowledge summary (**AI maintains this**)
- `_workspace.map` — project structure overview (auto-generated)
- `_cache/` — binary files converted to Markdown
- `_topics/` — accumulated analysis from previous sessions
- `_requirements/` — requirements, stories, tasks, bugs
- `_experiences/` — imported domain knowledge packs (read-only)

## Maintaining _README.md

After gaining significant new understanding about the project (domain concepts, architecture, business rules), update `.fcontext/_README.md` to reflect current knowledge. This file is the first thing the next AI session reads.

## General Commands

```
fcontext init                         # initialize .fcontext/
fcontext enable <agent>               # activate agent (copilot/claude/cursor/trae/opencode)
fcontext status                       # index statistics
fcontext clean                        # clear cache
fcontext reset                        # delete all .fcontext/ data
fcontext experience list              # show imported experience packs
fcontext experience import <source>   # import experience (zip/git/url)
fcontext experience remove <name>     # remove an experience pack
fcontext experience update [name]     # update from original source
fcontext export <output>              # export knowledge (zip or git remote)
```
""",
    },
    "fcontext-index": {
        "description": (
            "Convert binary files (PDF, DOCX, XLSX) to Markdown and cache "
            "in .fcontext/_cache/. Use when user references a binary "
            "document or needs to read non-text files."
        ),
        "body": """\
# Binary File Indexing

Binary files are converted to Markdown and cached in `.fcontext/_cache/`.

## Usage

Check `_cache/` first. If the file is not cached:

```
fcontext index <file>                 # convert one file
fcontext index <dir>                  # convert all in directory
```

Do not use other conversion tools — `fcontext index` caches results for reuse across sessions.

The `_index.json` maps each source file to its cached `.md` with mtime tracking.
""",
    },
    "fcontext-req": {
        "description": (
            "Track project requirements, stories, tasks, and bugs. Use when "
            "user asks about requirements, 需求, roadmap, backlog, project "
            "status, or wants to add/update/link items."
        ),
        "body": """\
# Requirements Management

Data lives in `.fcontext/_requirements/`. Run CLI commands — do NOT parse CSV manually.

## Commands

```
fcontext req list                     # all items (--type, --status filters)
fcontext req tree                     # hierarchy view
fcontext req board                    # kanban by status
fcontext req show ID                  # details + changelog
fcontext req add "title" -t TYPE      # types: roadmap/epic/requirement/story/task/bug
fcontext req set ID field value       # update (auto-logs changelog)
fcontext req link ID TYPE TARGET      # link types: supersedes/evolves/relates/blocks
fcontext req trace ID                 # follow evolution chain
fcontext req comment ID "msg"         # append comment
```

## Provenance

Add `--author` and `--source` on `req add` to record who proposed it and from which document.

## Evolution

Requirements are immutable. When a requirement changes:
1. Create a new one with `req add`
2. Link it: `fcontext req link NEW supersedes OLD` (or `evolves`)
3. Trace history: `fcontext req trace ID`

Link types: `supersedes` (replaces), `evolves` (iterates on), `relates`, `blocks`

## What NOT to Track as Requirements

Only create requirement items for **actionable work** (things to build, fix, or decide).

Do NOT create req items for:
- Document version history ("Backlog v1.4 corrections", "v2.0 updates") → use `fcontext index` to cache each version, write diffs to `_topics/`
- Meeting notes or discussion logs → write to `_topics/`
- Changelog entries of external documents → write to `_topics/`

When importing from external backlogs, extract the **actual requirements** (what to build), not the document's revision history.

## Data Structure

```
.fcontext/_requirements/
  items.csv      — id, type, title, status, priority, parent, assignee, tags,
                   created, updated, author, source, links
  _backlog.md    — auto-generated summary (read-only)
  docs/<ID>.md   — detailed description + changelog per item
```
""",
    },
    "fcontext-topic": {
        "description": (
            "Record important conclusions, discoveries, and work logs from "
            "AI sessions into .fcontext/_topics/. Use after completing "
            "non-trivial analysis or multi-step tasks worth preserving."
        ),
        "body": """\
# Topic Knowledge — Recording Guide

Write conclusions and work logs to `.fcontext/_topics/<name>.md` so the next session starts with full context instead of from zero.

## When to Write

- Key conclusions or decisions reached during conversation
- Work log for multi-step tasks (what was done, what remains)
- Cross-document analysis results (comparisons, gap analysis)
- Structural understanding discovered (architecture, module relationships)
- User explicitly asks to save or persist findings

## When NOT to Write

- Simple Q&A (one-turn answers)
- Single-file edits (result lives in the code)
- Content already covered by an existing topic (update it instead)

## Commands

```
fcontext topic list                   # list all topics
fcontext topic show <name>            # show topic content
fcontext topic clean                  # remove empty topic files
```
""",
    },
}

# ── Agent delivery ────────────────────────────────────────────────────────────
#
# Each agent gets rules file + multiple focused SKILL.md files.
# Copilot uses .instructions.md (always-on, applyTo: '**') instead of rules.
#
#   Copilot  →  .instructions.md (always-on) + .github/skills/*/SKILL.md
#   Claude   →  .claude/rules/fcontext.md  + .claude/skills/*/SKILL.md
#   Cursor   →  .cursor/rules/fcontext.md  + .cursor/skills/*/SKILL.md
#   Trae     →  .trae/rules/fcontext.md    + .trae/skills/*/SKILL.md
#   OpenCode →  alias for claude (.claude/)
#   OpenClaw →  skills/ only (no rules, personal AI assistant)

# Minimal always-on instructions for Copilot (just the lookup order)
COPILOT_INSTRUCTIONS = """\
---
name: 'fcontext'
description: 'This workspace uses fcontext CLI. Check .fcontext/ directory before searching the codebase. Manages project structure, binary file conversion (PDF/DOCX/XLSX), requirements tracking (需求/roadmap/backlog), and session knowledge persistence.'
applyTo: '**'
---

# fcontext

This workspace has a `.fcontext/` directory with structured data.
Always check these BEFORE searching source files:

1. `.fcontext/_README.md` — project knowledge summary (AI-maintained)
2. `.fcontext/_workspace.map` — project structure
3. `.fcontext/_requirements/` — requirements, stories, tasks (use `fcontext req` commands)
4. `.fcontext/_cache/` — binary files converted to Markdown (use `fcontext index`)
5. `.fcontext/_topics/` — analysis from previous sessions

## Workflow Rules

### Workspace Context (fcontext)
- **Project structure / architecture / what is this project** → read `.fcontext/_README.md` first, then `_workspace.map`
- **First time in a project** → read `_README.md` to orient, then check `_requirements/` and `_topics/`
- **Before answering any question** → check `.fcontext/` structured data before searching source files
- **Gained significant new understanding** → update `_README.md` to reflect current knowledge

### File Indexing (fcontext index)
- **Need to read binary files (PDF/DOCX/XLSX)** → check `.fcontext/_cache/` first; if not cached, run `fcontext index <file>`
- **User mentions a document / contract / report** → same: check `_cache/`, run `fcontext index` if missing
- **Need to process all documents in a directory** → run `fcontext index <dir>`
- **Not sure which files are cached** → run `fcontext status` to check index state

### Requirements (fcontext req)
- **New requirement / add feature** → first run `fcontext req add "title" -t TYPE` to record it, THEN implement
- **Query requirements / project status / roadmap** → run `fcontext req list` or `fcontext req tree`, do NOT search code
- **Any requirement-related request** → first confirm with user whether this is a requirement change (add/update/link), record it via `fcontext req` commands, THEN proceed to implementation
- **User says "change this feature"** → confirm whether this is a new requirement; if yes, `fcontext req add` + `fcontext req link NEW supersedes/evolves OLD`
- **Need to understand a requirement's history** → run `fcontext req trace ID` to follow evolution chain
- **Finished implementing a requirement** → run `fcontext req set ID status done`
- **Need to see who proposed a requirement** → run `fcontext req show ID`, check author and source fields
- **NEVER create req items for document version history** (e.g. "Backlog v1.4 corrections") → those are NOT requirements; use `fcontext index` to cache document versions and write diffs to `_topics/`

### Topic Knowledge (fcontext topic)
- **Continue / resume / where did we leave off** → run `fcontext topic list` to see topics with timestamps, then read the most relevant/recent topic file
- **Completed multi-step analysis or complex task** → save conclusions and work log to `.fcontext/_topics/<name>.md`
- **Reached important conclusion or decision during conversation** → write to `_topics/` so next session inherits the insight
- **User says "remember this" / "save this"** → persist to `_topics/<name>.md`
- **Discovered structural understanding (architecture, module relationships)** → write to `_topics/` for future reference
- **Mid-task handoff needed** → write work log (what was done, what remains) to `_topics/`

### Experience Knowledge (fcontext experience)
- **First time in a project** → run `fcontext experience list` to discover available domain knowledge
- **业务理解 / 领域问题** → check `_README.md` in each experience to find relevant pack, then read its `_cache/` and `_topics/`
- **Need to share knowledge to another project** → run `fcontext export <output>` (zip file or git URL)
- **Need to import domain knowledge** → run `fcontext experience import <source>` (zip/git/url)
- **Experience pack outdated** → run `fcontext experience update [name]` to pull latest from source
- **NEVER modify** anything under `_experiences/` — it is read-only imported knowledge
"""

# Rules content for agents that use a rules/ directory (claude, cursor, trae).
# Same content as COPILOT_INSTRUCTIONS but without the YAML frontmatter wrapper.
AGENT_RULES_BODY = """# fcontext

This workspace has a `.fcontext/` directory with structured data.
Always check these BEFORE searching source files:

1. `.fcontext/_README.md` — project knowledge summary (AI-maintained)
2. `.fcontext/_workspace.map` — project structure
3. `.fcontext/_requirements/` — requirements, stories, tasks (use `fcontext req` commands)
4. `.fcontext/_cache/` — binary files converted to Markdown (use `fcontext index`)
5. `.fcontext/_topics/` — analysis from previous sessions

## Workflow Rules

### Workspace Context (fcontext)
- **Project structure / architecture / what is this project** → read `.fcontext/_README.md` first, then `_workspace.map`
- **First time in a project** → read `_README.md` to orient, then check `_requirements/` and `_topics/`
- **Before answering any question** → check `.fcontext/` structured data before searching source files
- **Gained significant new understanding** → update `_README.md` to reflect current knowledge

### File Indexing (fcontext index)
- **Need to read binary files (PDF/DOCX/XLSX)** → check `.fcontext/_cache/` first; if not cached, run `fcontext index <file>`
- **User mentions a document / contract / report** → same: check `_cache/`, run `fcontext index` if missing
- **Need to process all documents in a directory** → run `fcontext index <dir>`
- **Not sure which files are cached** → run `fcontext status` to check index state

### Requirements (fcontext req)
- **New requirement / add feature** → first run `fcontext req add "title" -t TYPE` to record it, THEN implement
- **Query requirements / project status / roadmap** → run `fcontext req list` or `fcontext req tree`, do NOT search code
- **Any requirement-related request** → first confirm with user whether this is a requirement change (add/update/link), record it via `fcontext req` commands, THEN proceed to implementation
- **User says "change this feature"** → confirm whether this is a new requirement; if yes, `fcontext req add` + `fcontext req link NEW supersedes/evolves OLD`
- **Need to understand a requirement's history** → run `fcontext req trace ID` to follow evolution chain
- **Finished implementing a requirement** → run `fcontext req set ID status done`
- **Need to see who proposed a requirement** → run `fcontext req show ID`, check author and source fields
- **NEVER create req items for document version history** (e.g. "Backlog v1.4 corrections") → those are NOT requirements; use `fcontext index` to cache document versions and write diffs to `_topics/`

### Topic Knowledge (fcontext topic)
- **Continue / resume / where did we leave off** → run `fcontext topic list` to see topics with timestamps, then read the most relevant/recent topic file
- **Completed multi-step analysis or complex task** → save conclusions and work log to `.fcontext/_topics/<name>.md`
- **Reached important conclusion or decision during conversation** → write to `_topics/` so next session inherits the insight
- **User says "remember this" / "save this"** → persist to `_topics/<name>.md`
- **Discovered structural understanding (architecture, module relationships)** → write to `_topics/` for future reference
- **Mid-task handoff needed** → write work log (what was done, what remains) to `_topics/`

### Experience Knowledge (fcontext experience)
- **First time in a project** → run `fcontext experience list` to discover available domain knowledge
- **业务理解 / 领域问题** → check `_README.md` in each experience to find relevant pack, then read its `_cache/` and `_topics/`
- **Need to share knowledge to another project** → run `fcontext export <output>` (zip file or git URL)
- **Need to import domain knowledge** → run `fcontext experience import <source>` (zip/git/url)
- **Experience pack outdated** → run `fcontext experience update [name]` to pull latest from source
- **NEVER modify** anything under `_experiences/` — it is read-only imported knowledge
"""

AGENT_CONFIGS = {
    "copilot": {
        "instructions_path": ".github/instructions/fcontext.instructions.md",
        "skills_dir": ".github/skills",
        "detect": ".github",
    },
    "claude": {
        "rules_path": ".claude/rules/fcontext.md",
        "skills_dir": ".claude/skills",
        "detect": ".claude",
    },
    "cursor": {
        "rules_path": ".cursor/rules/fcontext.md",
        "skills_dir": ".cursor/skills",
        "detect": ".cursor",
    },
    "trae": {
        "rules_path": ".trae/rules/fcontext.md",
        "skills_dir": ".trae/skills",
        "detect": ".trae",
    },
    "opencode": {
        "alias": "claude",
    },
    "openclaw": {
        "skills_dir": "skills",
        "detect": "skills",
    },
}


def _skill_frontmatter(name: str, description: str) -> str:
    """Generate YAML frontmatter for a SKILL.md file."""
    return f"---\nname: {name}\ndescription: {description}\n---\n\n"


def _write_skills(root: Path, skills_dir: str, force: bool) -> list[str]:
    """Write all SKILL.md files under a skills directory. Returns list of relative paths written."""
    written = []
    for skill_name, skill in SKILLS.items():
        target = root / skills_dir / skill_name / "SKILL.md"
        if target.exists() and not force:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        content = _skill_frontmatter(skill_name, skill["description"]) + skill["body"]
        target.write_text(content, encoding="utf-8")
        written.append(str(target.relative_to(root)))
    return written


def init_workspace(root: Path, force: bool = False) -> int:
    """Initialize .fcontext/ and deliver instructions to agents."""

    ctx = root / ".fcontext"

    # 1. Create directory structure
    for d in [ctx, ctx / "_cache", ctx / "_topics", ctx / "_requirements", ctx / "_requirements" / "docs"]:
        d.mkdir(parents=True, exist_ok=True)

    # 2. Create .gitignore
    gitignore = ctx / ".gitignore"
    gitignore_content = (
        "# Regenerable artifacts (fcontext init)\n"
        "_workspace.map\n"
        "_index.json\n"
        "\n"
        "# Git-imported experiences (re-cloneable, managed by fcontext)\n"
    )
    if not gitignore.exists() or force:
        gitignore.write_text(gitignore_content, encoding="utf-8")
        print(f"  create  {gitignore.relative_to(root)}")

    # 2b. Create _README.md (AI maintains this summary)
    readme = ctx / "_README.md"
    if not readme.exists():
        readme_content = f"""# {root.name}\n\nProject context summary. AI should keep this file up to date.\n\n## Knowledge Available\n\n- `_cache/` — (empty, run `fcontext index` to convert documents)\n- `_topics/` — (empty, AI writes analysis here)\n- `_requirements/` — (initialized, use `fcontext req` commands)\n\n## Key Concepts\n\n(AI: summarize the main domain concepts, business rules, and architecture as you learn them)\n"""
        readme.write_text(readme_content, encoding="utf-8")
        print(f"  create  {readme.relative_to(root)}")

    # 3. Create _index.json
    idx = ctx / "_index.json"
    if not idx.exists():
        idx.write_text("{}", encoding="utf-8")
        print(f"  create  {idx.relative_to(root)}")

    # 3b. Create _requirements/items.csv
    from .requirements import req_init
    req_init(root)

    # 4. Generate workspace map
    from .workspace_map import generate_workspace_map
    ws_map = ctx / "_workspace.map"
    print(f"  scan   workspace structure ...")
    ws_map.write_text(generate_workspace_map(root), encoding="utf-8")
    print(f"  create {ws_map.relative_to(root)}")

    print(f"""
Initialized .fcontext/ in {root}

Next steps:
  fcontext enable copilot   Activate an AI agent
  fcontext enable list      Show all supported agents
  fcontext index            Convert binary files to Markdown
  fcontext status           Check what needs indexing
""")
    return 0


def enable_agent(root: Path, agent_name: str, force: bool = False) -> int:
    """Activate an AI agent by delivering skill files to its config location."""
    agent_name = agent_name.lower()

    if agent_name not in AGENT_CONFIGS:
        available = ", ".join(sorted(AGENT_CONFIGS.keys()))
        print(f"error: unknown agent '{agent_name}'. Available: {available}", file=sys.stderr)
        return 1

    # Resolve alias (e.g. opencode → claude)
    config = AGENT_CONFIGS[agent_name]
    resolved_name = agent_name
    if "alias" in config:
        resolved_name = config["alias"]
        config = AGENT_CONFIGS[resolved_name]
        print(f"  (opencode uses same config as {resolved_name})")

    # Ensure .fcontext exists
    ctx = root / ".fcontext"
    if not ctx.is_dir():
        print("fatal: not an fcontext workspace (run 'fcontext init' first)", file=sys.stderr)
        return 1

    # Copilot: write always-on .instructions.md
    instructions_path = config.get("instructions_path")
    if instructions_path:
        target = root / instructions_path
        if not target.exists() or force:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(COPILOT_INSTRUCTIONS, encoding="utf-8")

    # Claude/Cursor/Trae: write rules file
    rules_path = config.get("rules_path")
    if rules_path:
        target = root / rules_path
        if not target.exists() or force:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(AGENT_RULES_BODY, encoding="utf-8")

    # Write skill files
    written = _write_skills(root, config["skills_dir"], force)

    print(f"  ✓ enabled {agent_name}")
    if instructions_path:
        print(f"    → {instructions_path}")
    if rules_path:
        print(f"    → {rules_path}")
    for p in written:
        print(f"    → {p}")

    return 0


def list_agents(root: Path) -> int:
    """Show which agents are enabled."""
    print(f"  {'AGENT':<10} {'STATUS':<10} SKILLS")
    print(f"  {'─'*10} {'─'*10} {'─'*30}")
    for agent, config in AGENT_CONFIGS.items():
        # Resolve alias
        if "alias" in config:
            target = config["alias"]
            print(f"  {agent:<10} {'→ ' + target:<10}")
            continue
        skills_dir = root / config["skills_dir"]
        skill_count = sum(1 for s in SKILLS if (skills_dir / s / "SKILL.md").exists())
        if skill_count > 0:
            names = ", ".join(s for s in SKILLS if (skills_dir / s / "SKILL.md").exists())
            print(f"  {agent:<10} {'enabled':<10} {names}")
        else:
            print(f"  {agent:<10} {'—':<10}")
    return 0


def get_all_agent_paths(agent_name: str) -> list[str]:
    """Return all file paths an agent might create (for reset cleanup)."""
    config = AGENT_CONFIGS.get(agent_name, {})
    # Resolve alias
    if "alias" in config:
        config = AGENT_CONFIGS.get(config["alias"], {})
    paths = []
    instructions = config.get("instructions_path")
    if instructions:
        paths.append(instructions)
    rules = config.get("rules_path")
    if rules:
        paths.append(rules)
    skills_dir = config.get("skills_dir", "")
    if skills_dir:
        for skill_name in SKILLS:
            paths.append(f"{skills_dir}/{skill_name}/SKILL.md")
    return paths
