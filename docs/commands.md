# Commands

## Core

### `fcontext init`

Initialize `.fcontext/` in current directory. Creates `_README.md` and `_workspace.map`.

```bash
fcontext init
```

### `fcontext enable <agent>`

Generate agent-specific instruction files pointing to `.fcontext/`.

```bash
fcontext enable copilot    # .github/instructions/fcontext.instructions.md
fcontext enable claude     # .claude/rules/fcontext.md
fcontext enable cursor     # .cursor/rules/fcontext.md
fcontext enable trae       # .trae/rules/fcontext.md
fcontext enable opencode   # Claude format
fcontext enable openclaw   # skills/ only
```

### `fcontext status`

Show initialization state, enabled agents, indexed files, and experience packs.

```bash
fcontext status
```

### `fcontext version`

Print version number.

```bash
fcontext version
```

---

## Indexing

### `fcontext index <path>`

Convert files or directories to Markdown. Supports PDF, DOCX, XLSX, PPTX, and more. Text files (`.md`, `.txt`, `.rst`) are copied directly.

```bash
fcontext index report.pdf              # Single file
fcontext index docs/                   # Entire directory
fcontext index specs/ --force          # Re-convert even if cached
```

---

## Requirements

### `fcontext req add <title>`

Create a new requirement.

```bash
fcontext req add "User login" -t story
fcontext req add "Fix crash on submit" -t bug
fcontext req add "OAuth support" -t task --parent STORY-001
```

**Types:** `roadmap`, `epic`, `story`, `task`, `bug`

### `fcontext req list`

List all requirements.

```bash
fcontext req list
fcontext req list --type story
fcontext req list --status in-progress
```

### `fcontext req show <id>`

Show full details of a requirement.

```bash
fcontext req show STORY-001
```

### `fcontext req set <id> <field> <value>`

Update a requirement field.

```bash
fcontext req set STORY-001 status in-progress
fcontext req set STORY-001 status done
fcontext req set STORY-001 priority high
```

### `fcontext req link <id> <relation> <target>`

Link two requirements with an evolution relationship.

```bash
fcontext req link STORY-002 supersedes STORY-001
fcontext req link STORY-003 evolves STORY-002
```

### `fcontext req trace <id>`

Show the full evolution chain of a requirement.

```bash
fcontext req trace STORY-003
```

### `fcontext req tree`

Display requirements as a hierarchy tree.

```bash
fcontext req tree
```

### `fcontext req board`

Display requirements as a Kanban board.

```bash
fcontext req board
```

---

## Topics

### `fcontext topic list`

List all topic files with timestamps.

```bash
fcontext topic list
```

Topics are plain Markdown files in `.fcontext/_topics/`. AI agents create them during sessions to persist knowledge. You can also create them manually.

---

## Experience Packs

### `fcontext experience list`

List imported experience packs.

```bash
fcontext experience list
```

### `fcontext experience import <source>`

Import a knowledge pack from zip, directory, URL, or Git repository.

```bash
fcontext experience import knowledge.zip
fcontext experience import /path/to/pack/
fcontext experience import git@github.com:org/pack.git
fcontext experience import https://example.com/pack.zip
```

### `fcontext experience update`

Update all Git-sourced experience packs to latest.

```bash
fcontext experience update
```

### `fcontext experience remove <name>`

Remove an imported experience pack.

```bash
fcontext experience remove domain-knowledge
```

---

## Export

### `fcontext export <destination>`

Export `.fcontext/` data as a shareable package.

```bash
fcontext export backup.zip              # Export to zip
fcontext export git@github.com:org/knowledge.git   # Export to Git repo
```
