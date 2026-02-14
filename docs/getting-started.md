# Getting Started

## Prerequisites

- Python 3.9+
- An AI coding agent (Copilot, Claude Code, Cursor, Trae, etc.)

## Install

```bash
pip install fcontext
```

Verify:

```bash
fcontext version
# fcontext 1.0.0
```

---

## Step by Step

### 1. Initialize

```bash
cd your-project
fcontext init
```

This creates `.fcontext/` with:

- `_README.md` — project summary (AI will maintain this)
- `_workspace.map` — auto-generated project structure

### 2. Enable your AI agent

```bash
fcontext enable copilot    # or: claude, cursor, trae, opencode, openclaw
```

Your agent now knows to read `.fcontext/` on every session.

### 3. Index documents (optional)

```bash
fcontext index docs/       # Convert PDFs, DOCX, etc. to Markdown
```

### 4. Check status

```bash
fcontext status
```

Shows what's initialized, which agents are enabled, and what's been indexed.

---

## What Happens Next

Start a session with your AI agent. It will:

1. Read `.fcontext/_README.md` for project overview
2. Read `_workspace.map` for structure
3. Check `_topics/` for accumulated knowledge
4. Check `_requirements/` for current work items
5. Check `_experiences/` for domain knowledge

As you work, the AI writes discoveries to `_topics/` and updates `_README.md`. **Each session gets smarter.**

---

## Example Workflow

```bash
# Day 1: Set up
fcontext init
fcontext enable copilot
fcontext index specs/requirements.pdf
fcontext req add "Build user authentication" -t epic

# Day 2: Work with AI
# AI reads everything from Day 1 automatically
fcontext req add "OAuth login flow" -t story --parent EPIC-001

# Day 3: Switch to Claude Code
fcontext enable claude
# Claude reads the same .fcontext/ — full continuity

# Day 5: Share with teammate
git add .fcontext/
git commit -m "add project context"
git push
# Teammate clones → instant context
```
