# Architecture

## How fcontext Works

fcontext operates on one principle: **structured local files that AI agents already know how to read**.

```mermaid
graph LR
    subgraph "Your Project"
        SRC["Source Code"]
        DOCS["Documents<br/>PDF / DOCX / XLSX"]
    end

    subgraph ".fcontext/"
        README["_README.md<br/>Project Summary"]
        MAP["_workspace.map<br/>Structure"]
        CACHE["_cache/<br/>Converted Docs"]
        TOPICS["_topics/<br/>Session Knowledge"]
        REQ["_requirements/<br/>Stories & Tasks"]
        EXP["_experiences/<br/>Imported Packs"]
    end

    subgraph "Agent Configs"
        GH[".github/instructions/"]
        CL[".claude/rules/"]
        CU[".cursor/rules/"]
        TR[".trae/rules/"]
    end

    SRC --> |fcontext init| README
    SRC --> |fcontext init| MAP
    DOCS --> |fcontext index| CACHE

    README --> |fcontext enable| GH
    README --> |fcontext enable| CL
    README --> |fcontext enable| CU
    README --> |fcontext enable| TR
```

---

## Directory Structure

```
.fcontext/
├── _README.md            # Living project summary (AI-maintained)
├── _workspace.map        # Auto-generated project structure
├── _cache/               # Binary → Markdown conversions
│   ├── specs/
│   │   └── requirements.pdf.md
│   └── docs/
│       └── architecture.docx.md
├── _topics/              # Session-accumulated knowledge
│   ├── auth-analysis.md
│   └── deploy-notes.md
├── _requirements/        # Structured requirement tracking
│   ├── STORY-001.yaml
│   └── TASK-001.yaml
└── _experiences/         # Imported knowledge packs (read-only)
    └── domain-knowledge/
        ├── _README.md
        ├── _cache/
        └── _topics/
```

---

## Data Flow

### Session Lifecycle

```mermaid
sequenceDiagram
    participant Dev as Developer
    participant Agent as AI Agent
    participant FC as .fcontext/

    Dev->>Agent: Start session
    Agent->>FC: Read _README.md
    Agent->>FC: Read _workspace.map
    Agent->>FC: Read _topics/
    Agent->>FC: Read _requirements/
    Agent->>FC: Read _experiences/

    Note over Agent: Full context loaded

    Dev->>Agent: Ask question / Give task
    Agent->>Agent: Work with full context
    Agent->>FC: Write _topics/new-insight.md
    Agent->>FC: Update _README.md

    Note over FC: Knowledge persisted

    Dev->>Agent: Next session (same or different agent)
    Agent->>FC: Read updated context
    Note over Agent: Continuity achieved
```

### Multi-Agent Configuration

When you run `fcontext enable <agent>`, the tool generates agent-specific instruction files that point back to `.fcontext/`:

```mermaid
graph TD
    FC[".fcontext/<br/>Single Source of Truth"]
    
    FC -->|enable copilot| GH[".github/instructions/<br/>fcontext.instructions.md"]
    FC -->|enable claude| CL[".claude/rules/<br/>fcontext.md"]
    FC -->|enable cursor| CU[".cursor/rules/<br/>fcontext.md"]
    FC -->|enable trae| TR[".trae/rules/<br/>fcontext.md"]

    GH --> A1["GitHub Copilot"]
    CL --> A2["Claude Code"]
    CU --> A3["Cursor"]
    TR --> A4["Trae"]
```

Each instruction file contains:

1. **Workflow rules** — when to read/write `.fcontext/` data
2. **Anti-pattern rules** — what NOT to do (e.g., never modify `_experiences/`)
3. **Command reference** — available `fcontext` CLI commands

The instructions are **generated, not copied**. Each agent gets rules formatted for its own instruction system.

---

## Design Principles

| Principle | Implementation |
|-----------|----------------|
| **Files over APIs** | All context is plain Markdown/YAML files |
| **Convention over configuration** | Fixed directory structure, no config needed |
| **Agent-agnostic** | Shared data, agent-specific instruction generation |
| **Additive knowledge** | Topics accumulate, nothing is auto-deleted |
| **Read-only imports** | Experience packs are immutable once imported |
| **Local-first** | No network required for core functionality |
