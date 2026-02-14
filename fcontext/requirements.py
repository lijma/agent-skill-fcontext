"""fcontext requirements — lightweight project management via CSV + Markdown.

Data model
──────────
  .fcontext/_requirements/
    items.csv              ← single CSV: structured data (relationships, status)
    docs/                  ← one .md per item: detailed description, diagrams
      ROAD-001.md
      EPIC-001.md
      ...

Hierarchy
─────────
  roadmap ─▶ epic ─▶ requirement ─▶ story ─▶ task
                                  ─▶ task      ─▶ bug
                                  ─▶ bug
"""
from __future__ import annotations

import csv
import io
import os
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

# ── Constants ─────────────────────────────────────────────────────────────────

ITEM_TYPES = ("roadmap", "epic", "requirement", "story", "task", "bug")

TYPE_PREFIX = {
    "roadmap": "ROAD",
    "epic": "EPIC",
    "requirement": "REQ",
    "story": "STORY",
    "task": "TASK",
    "bug": "BUG",
}

STATUS_FLOW = ("draft", "planning", "active", "done", "archived", "cancelled")

PRIORITY_LEVELS = ("P0", "P1", "P2", "P3")  # P0=urgent … P3=low

# Typed relationship links between items (beyond parent-child hierarchy)
LINK_TYPES = ("supersedes", "evolves", "relates", "blocks")

CSV_COLUMNS = [
    "id", "type", "title", "status", "priority",
    "parent", "assignee", "tags", "created", "updated",
    "author", "source", "links",
]

# Allowed hierarchy: parent-type → child-types
VALID_PARENT = {
    "epic": {"roadmap"},
    "requirement": {"epic", "roadmap"},
    "story": {"requirement"},
    "task": {"requirement", "story"},
    "bug": {"requirement", "story"},
}

# ── Path helpers ──────────────────────────────────────────────────────────────

def _req_dir(root: Path) -> Path:
    return root / ".fcontext" / "_requirements"


def _csv_path(root: Path) -> Path:
    return _req_dir(root) / "items.csv"


def _docs_dir(root: Path) -> Path:
    return _req_dir(root) / "docs"


# ── CSV I/O ───────────────────────────────────────────────────────────────────

def _load_items(root: Path) -> list[dict[str, str]]:
    """Load all items from CSV."""
    csv_file = _csv_path(root)
    if not csv_file.exists():
        return []
    with open(csv_file, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


def _save_items(root: Path, items: list[dict[str, str]]) -> None:
    """Save all items to CSV."""
    csv_file = _csv_path(root)
    csv_file.parent.mkdir(parents=True, exist_ok=True)
    with open(csv_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(items)


def _next_id(items: list[dict[str, str]], item_type: str) -> str:
    """Generate next ID for a given type, e.g. REQ-003."""
    prefix = TYPE_PREFIX[item_type]
    max_num = 0
    for item in items:
        if item["id"].startswith(prefix + "-"):
            try:
                num = int(item["id"].split("-", 1)[1])
                max_num = max(max_num, num)
            except ValueError:
                pass
    return f"{prefix}-{max_num + 1:03d}"


def _find_item(items: list[dict[str, str]], item_id: str) -> dict[str, str] | None:
    """Find an item by ID (case-insensitive)."""
    item_id_upper = item_id.upper()
    for item in items:
        if item["id"].upper() == item_id_upper:
            return item
    return None


def _now() -> str:
    return time.strftime("%Y-%m-%d", time.localtime())


# ── Markdown doc template ─────────────────────────────────────────────────────

_DEFAULT_SECTION = "## 描述\n\n"


def _doc_template(item_id: str, title: str, item_type: str) -> str:
    """Generate a Markdown doc template for a new item."""
    sections = {
        "roadmap": """\
## 愿景

<!-- 描述这个Roadmap的长期目标和愿景 -->

## 里程碑

<!-- 关键里程碑和时间节点 -->

## 成功指标

<!-- 如何衡量这个Roadmap的成功 -->
""",
        "epic": """\
## 背景

<!-- 为什么需要这个Epic -->

## 目标

<!-- 这个Epic要达成什么 -->

## 范围

<!-- 包含和不包含什么 -->

## 设计

```mermaid
graph TD
    A[开始] --> B[步骤1]
    B --> C[步骤2]
    C --> D[完成]
```
""",
        "requirement": """\
## 描述

<!-- 详细描述这个需求 -->

## 验收条件

- [ ] 条件1
- [ ] 条件2
- [ ] 条件3

## 设计

<!-- 用 mermaid/plantuml 描述流程和设计 -->

```mermaid
sequenceDiagram
    participant User
    participant System
    User->>System: 请求
    System-->>User: 响应
```

## 备注

<!-- 依赖、风险、相关文档 -->
""",
        "story": """\
## 用户故事

<!-- 作为<角色>，我想要<功能>，以便<价值> -->

## 验收条件

- [ ] 条件1
- [ ] 条件2
- [ ] 条件3

## 备注

""",
        "task": """\
## 描述

<!-- 具体要做什么 -->

## 步骤

- [ ] Step 1
- [ ] Step 2
- [ ] Step 3

## 备注

""",
        "bug": """\
## 现象

<!-- 出了什么问题 -->

## 复现步骤

1. 步骤1
2. 步骤2
3. 观察到...

## 期望行为

<!-- 应该是什么样 -->

## 实际行为

<!-- 实际是什么样 -->

## 环境

- OS:
- Version:
""",
    }

    return f"""\
# {item_id}: {title}

> Type: {item_type} | Created: {_now()}

{sections.get(item_type, _DEFAULT_SECTION)}
"""


# ── Commands ──────────────────────────────────────────────────────────────────

def req_init(root: Path) -> int:
    """Initialize _requirements/ directory with empty CSV."""
    req_dir = _req_dir(root)
    docs = _docs_dir(root)
    req_dir.mkdir(parents=True, exist_ok=True)
    docs.mkdir(parents=True, exist_ok=True)

    csv_file = _csv_path(root)
    if not csv_file.exists():
        _save_items(root, [])
        print(f"  create  {csv_file.relative_to(root)}")
    return 0


def req_add(root: Path, item_type: str, title: str,
            priority: str = "P2", parent: str = "",
            assignee: str = "", tags: str = "",
            author: str = "", source: str = "",
            links: str = "") -> int:
    """Add a new item."""
    if item_type not in ITEM_TYPES:
        print(f"error: unknown type '{item_type}'. Must be one of: {', '.join(ITEM_TYPES)}", file=sys.stderr)
        return 1

    if priority not in PRIORITY_LEVELS:
        print(f"error: unknown priority '{priority}'. Must be one of: {', '.join(PRIORITY_LEVELS)}", file=sys.stderr)
        return 1

    items = _load_items(root)

    # Validate parent
    if parent:
        parent = parent.upper()
        parent_item = _find_item(items, parent)
        if parent_item is None:
            print(f"error: parent '{parent}' not found", file=sys.stderr)
            return 1
        allowed = VALID_PARENT.get(item_type, set())
        if parent_item["type"] not in allowed:
            print(f"error: {item_type} cannot be a child of {parent_item['type']}. "
                  f"Allowed parents: {', '.join(allowed) if allowed else 'none'}", file=sys.stderr)
            return 1

    # Validate links format: "type:ID,type:ID"
    if links:
        for link_entry in links.split(","):
            link_entry = link_entry.strip()
            if ":" not in link_entry:
                print(f"error: invalid link format '{link_entry}'. Use 'type:ID' (e.g. supersedes:REQ-001)", file=sys.stderr)
                return 1
            ltype, lid = link_entry.split(":", 1)
            if ltype not in LINK_TYPES:
                print(f"error: unknown link type '{ltype}'. Must be one of: {', '.join(LINK_TYPES)}", file=sys.stderr)
                return 1
            if _find_item(items, lid.strip()) is None:
                print(f"error: link target '{lid.strip()}' not found", file=sys.stderr)
                return 1

    item_id = _next_id(items, item_type)
    now = _now()

    new_item = {
        "id": item_id,
        "type": item_type,
        "title": title,
        "status": "draft",
        "priority": priority,
        "parent": parent,
        "assignee": assignee,
        "tags": tags,
        "created": now,
        "updated": now,
        "author": author,
        "source": source,
        "links": links,
    }
    items.append(new_item)
    _save_items(root, items)

    # Create markdown doc
    docs = _docs_dir(root)
    docs.mkdir(parents=True, exist_ok=True)
    doc_path = docs / f"{item_id}.md"
    doc_path.write_text(_doc_template(item_id, title, item_type), encoding="utf-8")

    print(f"  ✓ created {item_id}: {title}")
    print(f"    type={item_type}  priority={priority}  status=draft")
    if parent:
        print(f"    parent={parent}")
    if author:
        print(f"    author={author}")
    if source:
        print(f"    source={source}")
    if links:
        print(f"    links={links}")
    print(f"    doc: {doc_path.relative_to(root)}")
    return 0


def req_list(root: Path, filter_type: str | None = None,
             filter_status: str | None = None,
             filter_parent: str | None = None) -> int:
    """List items with optional filters."""
    items = _load_items(root)

    if filter_type:
        items = [i for i in items if i["type"] == filter_type]
    if filter_status:
        items = [i for i in items if i["status"] == filter_status]
    if filter_parent:
        fp = filter_parent.upper()
        items = [i for i in items if i["parent"].upper() == fp]

    if not items:
        print("  (no items found)")
        return 0

    # Column widths
    w_id = max(len(i["id"]) for i in items)
    w_type = max(len(i["type"]) for i in items)
    w_status = max(len(i["status"]) for i in items)
    w_pri = 2
    w_title = max(len(i["title"][:50]) for i in items)

    # Header
    hdr = f"  {'ID':<{w_id}}  {'TYPE':<{w_type}}  {'PRI':<{w_pri}}  {'STATUS':<{w_status}}  {'TITLE'}"
    print(hdr)
    print("  " + "─" * (len(hdr) - 2))

    # Status color indicators
    status_icon = {
        "draft": "○", "planning": "◐", "active": "●",
        "done": "✓", "archived": "▪", "cancelled": "✗",
    }

    for item in items:
        icon = status_icon.get(item["status"], " ")
        title = item["title"][:50]
        parent_hint = f"  ↑{item['parent']}" if item["parent"] else ""
        print(f"  {item['id']:<{w_id}}  {item['type']:<{w_type}}  {item['priority']:<{w_pri}}  "
              f"{icon} {item['status']:<{w_status}}  {title}{parent_hint}")

    print(f"\n  Total: {len(items)} items")
    return 0


def req_show(root: Path, item_id: str) -> int:
    """Show detailed info for a single item."""
    items = _load_items(root)
    item = _find_item(items, item_id)
    if item is None:
        print(f"error: '{item_id}' not found", file=sys.stderr)
        return 1

    # CSV fields
    print(f"\n  ╔══ {item['id']}: {item['title']}")
    print(f"  ║ Type:     {item['type']}")
    print(f"  ║ Status:   {item['status']}")
    print(f"  ║ Priority: {item['priority']}")
    if item["parent"]:
        print(f"  ║ Parent:   {item['parent']}")
    if item["assignee"]:
        print(f"  ║ Assignee: {item['assignee']}")
    if item["tags"]:
        print(f"  ║ Tags:     {item['tags']}")
    if item.get("author"):
        print(f"  ║ Author:   {item['author']}")
    if item.get("source"):
        print(f"  ║ Source:   {item['source']}")
    print(f"  ║ Created:  {item['created']}")
    print(f"  ║ Updated:  {item['updated']}")

    # Links
    if item.get("links"):
        print(f"  ║")
        print(f"  ║ Links:")
        for link_entry in item["links"].split(","):
            link_entry = link_entry.strip()
            if ":" in link_entry:
                ltype, lid = link_entry.split(":", 1)
                target = _find_item(items, lid.strip())
                label = f"{target['title']}" if target else "(not found)"
                print(f"  ║   {ltype} → {lid.strip()} {label}")

    # Reverse links (items that link TO this one)
    reverse_links = []
    for other in items:
        for link_entry in other.get("links", "").split(","):
            link_entry = link_entry.strip()
            if ":" in link_entry:
                ltype, lid = link_entry.split(":", 1)
                if lid.strip().upper() == item["id"].upper():
                    reverse_links.append((ltype, other["id"], other["title"]))
    if reverse_links:
        if not item.get("links"):
            print(f"  ║")
            print(f"  ║ Links:")
        for ltype, oid, otitle in reverse_links:
            print(f"  ║   {oid} {ltype} → this  {otitle}")

    # Children
    children = [i for i in items if i["parent"].upper() == item["id"].upper()]
    if children:
        print(f"  ║")
        print(f"  ║ Children ({len(children)}):")
        for c in children:
            print(f"  ║   {c['id']} [{c['status']}] {c['title']}")

    # Markdown doc
    doc_path = _docs_dir(root) / f"{item['id']}.md"
    if doc_path.exists():
        print(f"  ║")
        print(f"  ║ Doc: {doc_path.relative_to(root)}")
        content = doc_path.read_text(encoding="utf-8").strip()
        # Show first few lines
        preview_lines = content.split("\n")[:8]
        for line in preview_lines:
            print(f"  ║   {line}")
        if len(content.split("\n")) > 8:
            print(f"  ║   ...")
    else:
        print(f"  ║ Doc: (not found — run 'fcontext req edit {item['id']}')")

    print(f"  ╚══")
    return 0


def req_set(root: Path, item_id: str, field: str, value: str) -> int:
    """Update a field on an item."""
    allowed_fields = {"title", "status", "priority", "parent", "assignee", "tags", "author", "source"}
    if field not in allowed_fields:
        print(f"error: cannot set '{field}'. Allowed: {', '.join(sorted(allowed_fields))}", file=sys.stderr)
        return 1

    if field == "status" and value not in STATUS_FLOW:
        print(f"error: unknown status '{value}'. Must be one of: {', '.join(STATUS_FLOW)}", file=sys.stderr)
        return 1

    if field == "priority" and value not in PRIORITY_LEVELS:
        print(f"error: unknown priority '{value}'. Must be one of: {', '.join(PRIORITY_LEVELS)}", file=sys.stderr)
        return 1

    items = _load_items(root)
    item = _find_item(items, item_id)
    if item is None:
        print(f"error: '{item_id}' not found", file=sys.stderr)
        return 1

    old_value = item.get(field, "")
    item[field] = value
    item["updated"] = _now()
    _save_items(root, items)

    # Append changelog to markdown doc
    _append_changelog(root, item["id"], field, old_value, value)

    print(f"  ✓ {item['id']}: {field} '{old_value}' → '{value}'")
    return 0


def _parse_links(links_str: str) -> list[tuple[str, str]]:
    """Parse 'type:ID,type:ID' into [(type, ID), ...]."""
    if not links_str:
        return []
    result = []
    for entry in links_str.split(","):
        entry = entry.strip()
        if ":" in entry:
            ltype, lid = entry.split(":", 1)
            result.append((ltype.strip(), lid.strip().upper()))
    return result


def _serialize_links(link_pairs: list[tuple[str, str]]) -> str:
    """Serialize [(type, ID), ...] back to CSV string."""
    return ",".join(f"{t}:{i}" for t, i in link_pairs)


def _append_changelog(root: Path, item_id: str, field: str,
                      old_value: str, new_value: str) -> None:
    """Append a changelog entry to the item's markdown doc."""
    doc_path = _docs_dir(root) / f"{item_id}.md"
    if not doc_path.exists():
        return
    now = time.strftime("%Y-%m-%d %H:%M", time.localtime())
    entry = f"\n\n---\n\n**Change** ({now}): {field} `{old_value}` → `{new_value}`\n"
    with open(doc_path, "a", encoding="utf-8") as f:
        f.write(entry)


def req_link(root: Path, item_id: str, link_type: str, target_id: str) -> int:
    """Add a typed link between two items."""
    if link_type not in LINK_TYPES:
        print(f"error: unknown link type '{link_type}'. "
              f"Must be one of: {', '.join(LINK_TYPES)}", file=sys.stderr)
        return 1

    items = _load_items(root)
    item = _find_item(items, item_id)
    if item is None:
        print(f"error: '{item_id}' not found", file=sys.stderr)
        return 1

    target = _find_item(items, target_id)
    if target is None:
        print(f"error: target '{target_id}' not found", file=sys.stderr)
        return 1

    # Parse existing links
    existing = _parse_links(item.get("links", ""))
    tid_upper = target_id.upper()

    # Check for duplicate
    if (link_type, tid_upper) in existing:
        print(f"  (link already exists: {item['id']} {link_type} → {tid_upper})")
        return 0

    existing.append((link_type, tid_upper))
    item["links"] = _serialize_links(existing)
    item["updated"] = _now()
    _save_items(root, items)

    # Log to markdown
    _append_changelog(root, item["id"], "link",
                      "", f"{link_type}:{tid_upper}")

    print(f"  ✓ {item['id']} ──{link_type}──▶ {target['id']} ({target['title']})")
    return 0


def req_trace(root: Path, item_id: str) -> int:
    """Trace the evolution chain of a requirement."""
    items = _load_items(root)
    item = _find_item(items, item_id)
    if item is None:
        print(f"error: '{item_id}' not found", file=sys.stderr)
        return 1

    by_id = {i["id"].upper(): i for i in items}

    # Build full graph: forward and reverse links
    # Forward: item has links field pointing to targets
    # Reverse: other items' links point to this item
    graph: dict[str, list[tuple[str, str]]] = defaultdict(list)  # id -> [(type, target_id)]
    reverse: dict[str, list[tuple[str, str]]] = defaultdict(list)  # id -> [(type, source_id)]

    for i in items:
        iid = i["id"].upper()
        for ltype, lid in _parse_links(i.get("links", "")):
            graph[iid].append((ltype, lid))
            reverse[lid].append((ltype, iid))

    # Walk backward to find the origin
    origin = item["id"].upper()
    visited = {origin}
    while True:
        preds = reverse.get(origin, [])
        found_prev = None
        for ltype, src in preds:
            if ltype in ("supersedes", "evolves") and src not in visited:
                found_prev = src
                break
        if found_prev is None:
            break
        visited.add(found_prev)
        origin = found_prev

    # Walk forward from origin to build the chain
    chain: list[tuple[str | None, str]] = []  # [(link_type, item_id)]
    current = origin
    visited_fwd = {current}
    chain.append((None, current))

    while True:
        succs = graph.get(current, [])
        found_next = None
        for ltype, tgt in succs:
            if ltype in ("supersedes", "evolves") and tgt not in visited_fwd:
                found_next = (ltype, tgt)
                break
        # Also check reverse: someone supersedes/evolves current
        if found_next is None:
            for other_id, links in graph.items():
                for ltype, tgt in links:
                    if tgt == current and ltype in ("supersedes", "evolves") and other_id not in visited_fwd:
                        found_next = (ltype, other_id)
                        break
                if found_next:
                    break
        if found_next is None:
            break
        ltype, nid = found_next
        visited_fwd.add(nid)
        chain.append((ltype, nid))
        current = nid

    # Status indicators
    status_icon = {
        "draft": "○", "planning": "◐", "active": "●",
        "done": "✓", "archived": "▪", "cancelled": "✗",
    }

    # Print chain
    print(f"\n  Evolution Trace for {item['id']}")
    print(f"  {'=' * 40}")
    for i, (ltype, iid) in enumerate(chain):
        node = by_id.get(iid)
        if node is None:
            continue
        icon = status_icon.get(node["status"], " ")
        marker = "  ▸ " if iid == item["id"].upper() else "    "
        prefix = ""
        if ltype:
            prefix = f"  └─ {ltype} ──▶ "
        else:
            prefix = "  "
        print(f"{marker}{prefix}{icon} {node['id']} [{node['status']}] {node['title']}")
        if node.get("author"):
            print(f"      author: {node['author']}")
        if node.get("source"):
            print(f"      source: {node['source']}")

    # Also show non-evolution links (relates, blocks)
    all_links = _parse_links(item.get("links", ""))
    other_links = [(t, i) for t, i in all_links if t not in ("supersedes", "evolves")]
    if other_links:
        print(f"\n  Other Links:")
        for ltype, lid in other_links:
            target = by_id.get(lid)
            label = target["title"] if target else "(not found)"
            print(f"    {ltype} → {lid} {label}")

    return 0


def req_board(root: Path) -> int:
    """Show a Kanban-style board grouped by status."""
    items = _load_items(root)
    if not items:
        print("  (no items)")
        return 0

    # Group by status
    by_status: dict[str, list[dict]] = defaultdict(list)
    for item in items:
        by_status[item["status"]].append(item)

    # Print columns
    active_statuses = [s for s in STATUS_FLOW if s in by_status]

    for status in active_statuses:
        group = by_status[status]
        print(f"\n  ┌─ {status.upper()} ({len(group)}) ─────────────────")
        for item in group:
            parent_hint = f" ↑{item['parent']}" if item["parent"] else ""
            print(f"  │ [{item['priority']}] {item['id']} {item['title'][:40]}{parent_hint}")
        print(f"  └────────────────────────────────────")

    # Summary
    total = len(items)
    done = len(by_status.get("done", []))
    active = len(by_status.get("active", []))
    print(f"\n  Summary: {total} total, {active} active, {done} done"
          f" ({done * 100 // total}% complete)" if total > 0 else "")
    return 0


def req_tree(root: Path) -> int:
    """Show hierarchy as a tree."""
    items = _load_items(root)
    if not items:
        print("  (no items)")
        return 0

    # Build lookup
    by_id = {item["id"].upper(): item for item in items}
    children_of: dict[str, list[dict]] = defaultdict(list)
    roots = []

    for item in items:
        parent = item["parent"].upper() if item["parent"] else ""
        if parent and parent in by_id:
            children_of[parent].append(item)
        else:
            roots.append(item)

    # Status indicators
    status_icon = {
        "draft": "○", "planning": "◐", "active": "●",
        "done": "✓", "archived": "▪", "cancelled": "✗",
    }

    def _print_tree(item: dict, prefix: str, is_last: bool):
        connector = "└── " if is_last else "├── "
        icon = status_icon.get(item["status"], " ")
        print(f"  {prefix}{connector}{icon} {item['id']} [{item['priority']}] {item['title'][:45]}")

        kids = children_of.get(item["id"].upper(), [])
        child_prefix = prefix + ("    " if is_last else "│   ")
        for i, child in enumerate(kids):
            _print_tree(child, child_prefix, i == len(kids) - 1)

    print(f"\n  Requirement Tree")
    print(f"  ================")
    for i, r in enumerate(roots):
        _print_tree(r, "", i == len(roots) - 1)

    return 0


def req_comment(root: Path, item_id: str, comment_text: str) -> int:
    """Append a comment to an item's markdown doc."""
    items = _load_items(root)
    item = _find_item(items, item_id)
    if item is None:
        print(f"error: '{item_id}' not found", file=sys.stderr)
        return 1

    doc_path = _docs_dir(root) / f"{item['id']}.md"
    if not doc_path.exists():
        # Create it first
        doc_path.parent.mkdir(parents=True, exist_ok=True)
        doc_path.write_text(_doc_template(item["id"], item["title"], item["type"]), encoding="utf-8")

    now = time.strftime("%Y-%m-%d %H:%M", time.localtime())
    comment_block = f"\n\n---\n\n**Comment** ({now}):\n\n{comment_text}\n"

    with open(doc_path, "a", encoding="utf-8") as f:
        f.write(comment_block)

    # Update timestamp
    item["updated"] = _now()
    _save_items(root, items)

    print(f"  ✓ comment added to {item['id']}")
    print(f"    doc: {doc_path.relative_to(root)}")
    return 0


def req_backlog_md(root: Path) -> int:
    """Generate a _backlog.md summary view (auto-generated, for AI reading)."""
    items = _load_items(root)
    lines = [
        "# Requirements Backlog",
        "",
        f"> Auto-generated by `fcontext req board` — {_now()}",
        "> Do NOT edit manually. Use `fcontext req` commands.",
        "",
    ]

    # Group by type
    by_type: dict[str, list[dict]] = defaultdict(list)
    for item in items:
        by_type[item["type"]].append(item)

    # Status summary table
    lines.append("## Summary")
    lines.append("")
    lines.append("| Status | Count |")
    lines.append("|--------|-------|")
    status_counts = defaultdict(int)
    for item in items:
        status_counts[item["status"]] += 1
    for status in STATUS_FLOW:
        if status in status_counts:
            lines.append(f"| {status} | {status_counts[status]} |")
    lines.append(f"| **Total** | **{len(items)}** |")
    lines.append("")

    # Items table
    lines.append("## All Items")
    lines.append("")
    lines.append("| ID | Type | Priority | Status | Title | Parent | Author | Source | Links |")
    lines.append("|----|------|----------|--------|-------|--------|--------|--------|-------|")
    for item in items:
        lines.append(f"| {item['id']} | {item['type']} | {item['priority']} | "
                      f"{item['status']} | {item['title']} | {item['parent']} | "
                      f"{item.get('author', '')} | {item.get('source', '')} | "
                      f"{item.get('links', '')} |")
    lines.append("")

    backlog_path = _req_dir(root) / "_backlog.md"
    backlog_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  ✓ generated {backlog_path.relative_to(root)}")
    return 0
