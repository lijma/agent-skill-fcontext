# fcontext

**Context continuity across AI agents & sessions.**

<a href="https://www.producthunt.com/products/fcontext/reviews/new?utm_source=badge-product_review&utm_medium=badge&utm_source=badge-fcontext" target="_blank"><img src="https://api.producthunt.com/widgets/embed-image/v1/product_review.svg?product_id=1164662&theme=light" alt="fcontext - Context&#0032;continuity&#0032;across&#0032;AI&#0032;coding&#0032;agents&#0032;&#0038;&#0032;sessions | Product Hunt" style="width: 250px; height: 54px;" width="250" height="54" /></a>

---

| | |
|---|---|
| 🔄 **Cross-Agent, Cross-Session** | 👥 **Team Collaboration** |
| Switch between Copilot, Claude, Cursor, Trae — your AI never starts from zero. | Export/import experience packs. Every team member's agent shares the same domain knowledge. |
| 🛡️ **Industrial-Grade Delivery** | 🔒 **Offline & Secure** |
| Structured context + requirements tracking + document indexing = consistent, auditable output. | All data local in `.fcontext/`. No cloud. No API keys. No telemetry. |

---

## The Core Problem

AI coding agents are powerful — but they have three critical blind spots:

1. **Session amnesia** — Every new conversation starts from zero
2. **Agent isolation** — Switch agents, lose all context
3. **Team fragmentation** — Each team member's AI works in a silo

```mermaid
graph TD
    subgraph "Without fcontext"
        U1["Developer"] --> A1["Copilot<br/>Session 1"]
        U1 --> A2["Claude<br/>Session 2"]
        U1 --> A3["Cursor<br/>Session 3"]
        A1 -.-x|"context lost"| A2
        A2 -.-x|"context lost"| A3
    end
```

```mermaid
graph TD
    subgraph "With fcontext"
        FC[".fcontext/<br/>shared context"]
        U2["Developer"] --> B1["Copilot"]
        U2 --> B2["Claude"]
        U2 --> B3["Cursor"]
        B1 <--> FC
        B2 <--> FC
        B3 <--> FC
    end
```

---

## For Individuals

> **AI delivers results, but you deliver process and experience.**

Your expertise — how you approach problems, what patterns you've learned, what pitfalls to avoid — is lost every time a session ends.

fcontext captures and persists that experience:

| What you lose today | What fcontext preserves |
|---------------------|------------------------|
| Debugging conclusions from yesterday | `_topics/debugging-auth-flow.md` |
| Architecture decisions across sessions | `_README.md` (AI-maintained) |
| Document analysis results | `_cache/` (indexed, reusable) |
| Project-specific patterns | `_experiences/` (exportable) |

### Your AI gets smarter over time

```mermaid
graph LR
    S1["Session 1"] -->|saves topics| FC[".fcontext/"]
    FC -->|loads context| S2["Session 2"]
    S2 -->|adds knowledge| FC
    FC -->|richer context| S3["Session 3"]
    S3 -->|even more| FC
```

Each session **builds on** the previous one. Your AI accumulates understanding instead of starting from scratch.

---

## For Teams & Enterprises

> **No single agent has all the context to do the job. Real work is distributed.**

In production environments, context is fragmented across people, documents, and conversations:

```mermaid
graph TD
    subgraph "Reality in Teams"
        D1["Requirements<br/>(PDF/DOCX)"]
        D2["Domain Knowledge<br/>(in people's heads)"]
        D3["Architecture<br/>(past conversations)"]
        D4["Conventions<br/>(tribal knowledge)"]
    end

    subgraph "fcontext unifies"
        FC["_cache/"] --- R["_requirements/"]
        R --- T["_topics/"]
        T --- E["_experiences/"]
    end

    D1 -->|"fcontext index"| FC
    D2 -->|"AI writes"| T
    D3 -->|"AI maintains"| T
    D4 -->|"fcontext export"| E
```

### Key benefits for enterprises

| Concern | How fcontext addresses it |
|---------|--------------------------|
| **Onboarding** | New member imports experience pack → instant project knowledge |
| **Consistency** | All agents read the same structured context → uniform output |
| **Traceability** | Requirements tracked with evolution history → auditable decisions |
| **Compliance** | All data stored locally, no cloud dependency → security-first |
| **Knowledge retention** | Team expertise persists in `_topics/` and `_experiences/` → survives attrition |

### Team knowledge flow

```mermaid
graph LR
    TL["Team Lead"] -->|"fcontext export"| GR["Git Repo<br/>(experience pack)"]
    GR -->|"experience import"| D1["Dev 1's Agent"]
    GR -->|"experience import"| D2["Dev 2's Agent"]
    GR -->|"experience import"| D3["New Hire's Agent"]
    TL -->|"experience update"| GR
```

---

## Quick Start

```bash
pip install fcontext

cd your-project
fcontext init
fcontext enable copilot    # or: claude, cursor, trae, opencode
fcontext index docs/
```

Your AI agent now reads project context automatically on every session.

---

## Supported Agents

| Agent | Command |
|-------|---------|
| GitHub Copilot | `fcontext enable copilot` |
| Claude Code | `fcontext enable claude` |
| Cursor | `fcontext enable cursor` |
| Trae | `fcontext enable trae` |
| OpenCode | `fcontext enable opencode` |
| OpenClaw | `fcontext enable openclaw` |

---

## Links

- [PyPI Package](https://pypi.org/project/fcontext/)
- [GitHub Repository](https://github.com/lijma/agent-skill-fcontext)
