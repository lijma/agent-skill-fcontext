# fcontext

**Context continuity across AI agents & sessions. Team knowledge collaboration. Industrial-grade AI delivery.**

[![PyPI version](https://img.shields.io/pypi/v/fcontext?style=for-the-badge)](https://pypi.org/project/fcontext/)
[![Python](https://img.shields.io/pypi/pyversions/fcontext?style=for-the-badge)](https://pypi.org/project/fcontext/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue?style=for-the-badge)](LICENSE)
[![Agents](https://img.shields.io/badge/agents-6%20supported-green?style=for-the-badge)](#supported-agents)

---

## The Problem

AI coding agents are powerful, but they forget everything between sessions, lose all context when you switch agents, and have no way to share knowledge across a team. Every conversation starts from zero.

```
WITHOUT fcontext

  Session 1 (Copilot): "Build the auth module"
  Session 2 (Claude):  "What auth module? I don't see any context."
  Session 3 (Cursor):  "Can you explain the project first?"
  Teammate's Agent:    "I have no idea what your team has decided."

  Result: Repeated explanations. Inconsistent output. Wasted tokens.
```

```
WITH fcontext

  Session 1 (Copilot): "Build the auth module" -> saves context
  Session 2 (Claude):  Reads _README.md + _topics/ -> picks up work
  Session 3 (Cursor):  Knows the full project, requirements, history
  Teammate's Agent:    Imports experience pack -> instant onboarding

  Result: Continuous context. Consistent quality. Industrial output.
```

---

## Why fcontext

### For Individuals

> AI delivers results, but **you** deliver process and experience.

Your expertise — how you approach problems, what patterns you've learned, what pitfalls to avoid — is lost every time a session ends. fcontext captures and persists that experience, so your AI gets smarter with every interaction.

- **Cross-session memory** — Topics and conclusions survive between conversations
- **Cross-agent portability** — Switch from Copilot to Claude to Cursor without losing context
- **Experience visualization** — Your accumulated knowledge becomes a structured, reusable asset

### For Teams & Enterprises

> No single agent has all the context to do the job. Real work is distributed.

In production environments, context is fragmented: requirements live in documents, domain knowledge lives in people's heads, architecture decisions live in past conversations. fcontext solves distributed context.

- **Team knowledge sync** — Export/import experience packs so every team member's agent shares the same domain understanding
- **Requirements traceability** — Track stories, tasks, bugs with full evolution history — from document to delivery
- **Compliance-ready** — All data stored locally in `.fcontext/`, no cloud dependency, fully offline capable
- **Industrial-grade delivery** — Structured context + requirements tracking + document indexing = consistent, auditable AI output

---

## Features

| Capability | Description | Data Location |
|------------|-------------|---------------|
| **Multi-Agent Support** | Works with all mainstream AI coding agents | Agent-native config files |
| **Document Indexing** | PDF, DOCX, XLSX, PPTX, Keynote, EPUB to Markdown | `.fcontext/_cache/` |
| **Dynamic Context Building** | AI accumulates knowledge topics across sessions | `.fcontext/_topics/` |
| **Experience Packs** | Import/export domain knowledge across projects and teams | `.fcontext/_experiences/` |
| **Requirements Management** | Stories, tasks, bugs with evolution tracking | `.fcontext/_requirements/` |
| **Workspace Map** | Auto-generated project structure overview | `.fcontext/_workspace.map` |
| **Living Project Summary** | AI-maintained `_README.md`, first thing every session reads | `.fcontext/_README.md` |
| **Offline & Secure** | All data local. No cloud. No API keys. No telemetry. | `.fcontext/` |

### Supported Agents

| Agent | Command | Config Format |
|-------|---------|---------------|
| GitHub Copilot | `fcontext enable copilot` | `.github/instructions/*.instructions.md` |
| Claude Code | `fcontext enable claude` | `.claude/rules/*.md` |
| Cursor | `fcontext enable cursor` | `.cursor/rules/*.md` |
| Trae | `fcontext enable trae` | `.trae/rules/*.md` |
| OpenCode | `fcontext enable opencode` | Uses Claude format |
| OpenClaw | `fcontext enable openclaw` | `skills/` only |

---

## Installation

### Prerequisites

- Python 3.9+
- pip

### Install from PyPI

```bash
pip install fcontext
```

### Verify

```bash
fcontext --version
# fcontext 1.0.0
```

---

## Quick Start

```bash
# 1. Initialize in any project
cd your-project
fcontext init

# 2. Activate your AI agent
fcontext enable copilot    # or: claude, cursor, trae, opencode, openclaw

# 3. Index your documents
fcontext index docs/

# 4. Check status
fcontext status
```

That's it. Your AI agent now reads project context automatically on every session.

---

## Use Cases

### Scenario 1: Picking Up Where You Left Off

**Problem:** You had a deep debugging session yesterday. Today, a new session knows nothing.

```bash
# fcontext automatically persists session knowledge to _topics/
# Next session reads _topics/ and _README.md first

# To see what was saved:
fcontext topic list
fcontext topic show debugging-auth-flow
```

The new session starts with full context of yesterday's findings.

### Scenario 2: Switching Between Agents

**Problem:** You used Cursor for frontend work but need Claude for backend refactoring. Claude has no idea what Cursor did.

```bash
# Enable both agents — they share the same .fcontext/ data
fcontext enable cursor
fcontext enable claude

# Both agents read the same _README.md, _topics/, _requirements/
# Context is agent-agnostic
```

### Scenario 3: Onboarding a New Team Member

**Problem:** A new developer joins. Their AI has zero project knowledge.

```bash
# Team lead exports accumulated knowledge
fcontext export team-knowledge.zip

# New member imports it
fcontext experience import team-knowledge.zip

# Their AI instantly knows: architecture, domain concepts, conventions, pitfalls
fcontext experience list
```

### Scenario 4: Working with Binary Documents

**Problem:** Product specs are in PDF/DOCX. AI cannot read them.

```bash
# Convert to Markdown so any agent can read them
fcontext index specs/product-requirements.pdf
fcontext index contracts/

# AI now references the content directly from _cache/
fcontext status
```

### Scenario 5: Requirements-Driven Development

**Problem:** Requirements are scattered across documents, Slack, and meetings. AI builds the wrong thing.

```bash
# Structure requirements in fcontext
fcontext req add "User authentication via OAuth" -t story
fcontext req add "Support Google and GitHub providers" -t task --parent STORY-001
fcontext req set TASK-001 status in-progress

# AI reads _requirements/ and builds against tracked specs
fcontext req board    # Kanban view
fcontext req tree     # Hierarchy view
```

### Scenario 6: Sharing Domain Expertise Across Projects

**Problem:** You've built deep domain knowledge in Project A. Project B needs the same expertise.

```bash
# In Project A: export to a git repo
fcontext export git@github.com:team/domain-knowledge.git

# In Project B: import as experience pack
fcontext experience import git@github.com:team/domain-knowledge.git

# Keep it updated
fcontext experience update
```

---

## Commands Reference

### Core

| Command | Description |
|---------|-------------|
| `fcontext init` | Initialize `.fcontext/` in workspace |
| `fcontext enable <agent>` | Activate an AI agent |
| `fcontext enable list` | Show all supported agents and status |
| `fcontext status` | Show index statistics |
| `fcontext clean` | Clear cached files |
| `fcontext reset` | Delete all `.fcontext/` data |

### File Indexing

| Command | Description |
|---------|-------------|
| `fcontext index` | Scan and convert all files in workspace |
| `fcontext index <file>` | Convert a specific file |
| `fcontext index <dir>` | Convert all files in a directory |
| `fcontext index -f` | Force re-convert even if up-to-date |

### Requirements

| Command | Description |
|---------|-------------|
| `fcontext req add "title" -t TYPE` | Add item (roadmap/epic/story/task/bug) |
| `fcontext req list` | List all items (supports `--type`, `--status` filters) |
| `fcontext req tree` | Hierarchy view |
| `fcontext req board` | Kanban board by status |
| `fcontext req show ID` | Item details + changelog |
| `fcontext req set ID field value` | Update a field |
| `fcontext req link ID TYPE TARGET` | Link items (supersedes/evolves/relates/blocks) |
| `fcontext req trace ID` | Follow evolution chain |
| `fcontext req comment ID "msg"` | Add a comment |

### Topics

| Command | Description |
|---------|-------------|
| `fcontext topic list` | List accumulated knowledge topics |
| `fcontext topic show <name>` | Show topic content |
| `fcontext topic clean` | Remove empty topic files |

### Experience Packs

| Command | Description |
|---------|-------------|
| `fcontext experience list` | Show imported packs |
| `fcontext experience import <source>` | Import from zip, git URL, or download URL |
| `fcontext experience remove <name>` | Remove a pack |
| `fcontext experience update [name]` | Update from original source |
| `fcontext export <output>` | Export knowledge to zip or git remote |

---

## How It Works

```
your-project/
  .fcontext/                        # All context data (git-tracked)
    _README.md                      # AI-maintained project summary
    _workspace.map                  # Auto-generated structure
    _index.json                     # File index registry
    _cache/                         # Converted documents (Markdown)
    _topics/                        # Session knowledge & conclusions
    _requirements/                  # Stories, tasks, bugs
      items.csv                     # Structured data
      _backlog.md                   # Auto-generated summary
      docs/                         # Per-item details
    _experiences/                   # Imported domain knowledge (read-only)
      <pack-name>/
        _README.md
        _cache/
        _topics/

  .github/instructions/             # Copilot (auto-generated by fcontext enable)
  .claude/rules/                    # Claude (auto-generated)
  .cursor/rules/                    # Cursor (auto-generated)
  .trae/rules/                      # Trae (auto-generated)
```

Each AI agent gets instructions in **its native format**. The instructions teach the agent to:

1. **Read** `.fcontext/_README.md` first to understand the project
2. **Check** `_cache/` before trying to read binary files
3. **Use** `fcontext req` commands for requirements (never parse CSV manually)
4. **Save** important conclusions to `_topics/` for future sessions
5. **Read** `_experiences/` for imported domain knowledge

---

## For Contributors

We welcome contributions! Here's how to get started:

```bash
# 1. Fork and clone the repository
git clone https://github.com/<your-fork>/fcontext.git
cd fcontext

# 2. Install in development mode
pip install -e ".[test]"

# 3. Run the test suite
pytest tests/
# 213 tests should pass

# 4. Understand the structure
# fcontext/
#   cli.py              # CLI entry point & argument parsing
#   init.py             # Workspace initialization & agent configs
#   indexer.py          # File scanning, conversion, text copy
#   experience.py       # Experience pack import/export/update
#   requirements.py     # Requirements CRUD & reporting
#   topics.py           # Topic management
#   workspace_map.py    # Project structure generation

# 5. Make your changes, add tests, verify
pytest tests/ --tb=short

# 6. Create a PR (never push directly to main)
git checkout -b feat/your-feature
git commit -m "feat: description"
git push -u origin feat/your-feature
```

### Guidelines

- Every new feature needs tests
- Keep `from __future__ import annotations` in all modules (Python 3.9 compat)
- CLI commands should give clear error messages when `.fcontext/` is not initialized
- Experience packs under `_experiences/` are always read-only

---

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=anthropic/fcontext&type=Date)](https://star-history.com/#anthropic/fcontext&Date)

---

## License

This project is licensed under the [Apache License 2.0](LICENSE).
