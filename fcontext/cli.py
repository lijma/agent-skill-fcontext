#!/usr/bin/env python3
"""fcontext CLI — Make any workspace AI-ready.

Usage:
    fcontext init              Initialize .fcontext/ in current workspace
    fcontext enable <agent>    Activate an AI agent (copilot/claude/cursor/trae/opencode/openclaw)
    fcontext index             Scan & convert binary files to Markdown
    fcontext status            Show index statistics
    fcontext clean             Clear all cached files and reset index
    fcontext reset             Reset all .fcontext/ data (requires confirmation)
    fcontext export            Export knowledge to zip file or git remote
    fcontext req               Requirements management (roadmap/epic/req/task/bug)
    fcontext topic             Manage accumulated knowledge topics
    fcontext experience        Manage experience packs (import/list/remove)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__


def cmd_init(args: argparse.Namespace) -> int:
    """Initialize .fcontext/ in the workspace."""
    from .init import init_workspace

    root = Path(args.dir).resolve()
    return init_workspace(root, force=args.force)


def cmd_enable(args: argparse.Namespace) -> int:
    """Enable an AI agent."""
    from .init import enable_agent, list_agents

    root = _find_root(".")
    if root is None:
        print("fatal: not an fcontext workspace (run 'fcontext init' first)", file=sys.stderr)
        return 1

    if args.agent == "list":
        return list_agents(root)

    return enable_agent(root, args.agent, force=args.force)


def cmd_index(args: argparse.Namespace) -> int:
    """Scan workspace and convert binary files to Markdown."""
    from .indexer import run_index, run_index_file, run_index_dir

    # If a specific target (file or dir) is given
    target = Path(args.target).resolve() if args.target else None
    start = str(target.parent if target and target.is_file() else target or args.dir)

    root = _find_root(start)
    if root is None:
        print("fatal: not an fcontext workspace (run 'fcontext init' first)", file=sys.stderr)
        return 1

    if target:
        if target.is_dir():
            return run_index_dir(root, target, force=args.force)
        return run_index_file(root, target, force=args.force)
    return run_index(root, force=args.force)


def cmd_status(args: argparse.Namespace) -> int:
    """Show index statistics."""
    from .indexer import run_status

    root = _find_root(args.dir)
    if root is None:
        print("fatal: not an fcontext workspace (run 'fcontext init' first)", file=sys.stderr)
        return 1
    return run_status(root)


def cmd_clean(args: argparse.Namespace) -> int:
    """Clear all cached files and reset index."""
    from .indexer import run_clean

    root = _find_root(args.dir)
    if root is None:
        print("fatal: not an fcontext workspace (run 'fcontext init' first)", file=sys.stderr)
        return 1
    return run_clean(root)


def cmd_reset(args: argparse.Namespace) -> int:
    """Reset all .fcontext/ data with double confirmation."""
    import shutil

    root = _find_root(args.dir)
    if root is None:
        print("fatal: not an fcontext workspace (run 'fcontext init' first)", file=sys.stderr)
        return 1

    ctx = root / ".fcontext"
    print(f"⚠️  This will DELETE all data in {ctx}/")
    print("   Including: _cache, _topics, _requirements, workspace map")
    print()

    confirm1 = input("Are you sure? (yes/no): ").strip().lower()
    if confirm1 != "yes":
        print("Aborted.")
        return 1

    confirm2 = input("Type 'reset' to confirm: ").strip().lower()
    if confirm2 != "reset":
        print("Aborted.")
        return 1

    # Remove .fcontext/ entirely
    shutil.rmtree(ctx)
    print(f"\n  ✓ removed {ctx}/")

    # Also remove agent files
    from .init import AGENT_CONFIGS, get_all_agent_paths
    for agent in AGENT_CONFIGS:
        for rel_path in get_all_agent_paths(agent):
            agent_file = root / rel_path
            if agent_file.exists():
                agent_file.unlink()
                print(f"  ✓ removed {rel_path}")

    # Remove .gitignore entries added by fcontext (if only fcontext content)
    gitignore = root / ".gitignore"
    if gitignore.exists():
        lines = gitignore.read_text().splitlines()
        fcontext_lines = {".fcontext/_cache/", "__pycache__/", "*.pyc", "*.egg-info/"}
        remaining = [l for l in lines if l.strip() not in fcontext_lines]
        if any(l.strip() for l in remaining):
            gitignore.write_text("\n".join(remaining) + "\n")
        else:
            gitignore.unlink()
            print("  ✓ removed .gitignore")

    print("\n  Reset complete. Run 'fcontext init' to start fresh.")
    return 0


# ── experience subcommands ────────────────────────────────────────────────────

def cmd_experience(args: argparse.Namespace) -> int:
    """Dispatch experience subcommands."""
    from .experience import list_experiences, import_experience, remove_experience, update_experience

    root = _find_root(args.dir if hasattr(args, 'dir') else '.')
    if root is None:
        print("fatal: not an fcontext workspace (run 'fcontext init' first)", file=sys.stderr)
        return 1

    action = args.exp_action

    if action == 'list':
        return list_experiences(root)
    elif action == 'import':
        return import_experience(root, source=args.source, name=args.name,
                                 force=args.force,
                                 branch=getattr(args, 'branch', None))
    elif action == 'remove':
        return remove_experience(root, name=args.name)
    elif action == 'update':
        return update_experience(root, name=getattr(args, 'name', None))
    else:
        print(f"unknown experience action: {action}", file=sys.stderr)
        return 1


# ── export command ────────────────────────────────────────────────────────────

def cmd_export(args: argparse.Namespace) -> int:
    """Export knowledge to zip file or git remote."""
    from .experience import export_experience

    root = _find_root(args.dir if hasattr(args, 'dir') else '.')
    if root is None:
        print("fatal: not an fcontext workspace (run 'fcontext init' first)", file=sys.stderr)
        return 1

    return export_experience(root, output=args.output, name=args.name,
                             branch=getattr(args, 'branch', None),
                             message=getattr(args, 'message', None))


# ── topic subcommands ─────────────────────────────────────────────────────────

def cmd_topic(args: argparse.Namespace) -> int:
    """Dispatch topic subcommands."""
    from .topics import topic_list, topic_show, topic_clean

    root = _find_root(args.dir if hasattr(args, 'dir') else '.')
    if root is None:
        print("fatal: not an fcontext workspace (run 'fcontext init' first)", file=sys.stderr)
        return 1

    action = args.topic_action

    if action == 'list':
        return topic_list(root)
    elif action == 'show':
        return topic_show(root, name=args.name)
    elif action == 'clean':
        return topic_clean(root)
    else:
        print(f"unknown topic action: {action}", file=sys.stderr)
        return 1


# ── req subcommands ───────────────────────────────────────────────────────────

def cmd_req(args: argparse.Namespace) -> int:
    """Dispatch requirement subcommands."""
    from .requirements import (
        req_add, req_list, req_show, req_set,
        req_board, req_tree, req_comment, req_backlog_md,
        req_link, req_trace,
    )

    root = _find_root(args.dir if hasattr(args, "dir") else ".")
    if root is None:
        print("fatal: not an fcontext workspace (run 'fcontext init' first)", file=sys.stderr)
        return 1

    action = args.req_action

    if action == "add":
        return req_add(root, item_type=args.type, title=args.title,
                       priority=args.priority, parent=args.parent,
                       assignee=args.assignee, tags=args.tags,
                       author=args.author, source=args.source,
                       links=args.link)
    elif action == "list":
        return req_list(root, filter_type=args.type,
                        filter_status=args.status,
                        filter_parent=args.parent)
    elif action == "show":
        return req_show(root, item_id=args.id)
    elif action == "set":
        return req_set(root, item_id=args.id, field=args.field, value=args.value)
    elif action == "board":
        rc = req_board(root)
        req_backlog_md(root)  # also generate _backlog.md
        return rc
    elif action == "tree":
        return req_tree(root)
    elif action == "comment":
        return req_comment(root, item_id=args.id, comment_text=args.message)
    elif action == "link":
        return req_link(root, item_id=args.id, link_type=args.type, target_id=args.target)
    elif action == "trace":
        return req_trace(root, item_id=args.id)
    else:
        print(f"unknown req action: {action}", file=sys.stderr)
        return 1


def _find_root(start: str) -> Path | None:
    """Walk up to find a directory containing .fcontext/."""
    current = Path(start).resolve()
    for parent in [current, *current.parents]:
        if (parent / ".fcontext").is_dir():
            return parent
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="fcontext",
        description="Make any workspace AI-ready. Like 'git init', but for AI context.",
    )
    parser.add_argument("--version", action="version", version=f"fcontext {__version__}")

    sub = parser.add_subparsers(dest="command")

    # --- init ---
    p_init = sub.add_parser("init", help="Initialize .fcontext/ in workspace")
    p_init.add_argument("dir", nargs="?", default=".", help="Workspace root (default: .)")
    p_init.add_argument("-f", "--force", action="store_true", help="Overwrite existing instruction files")
    p_init.set_defaults(func=cmd_init)

    # --- enable ---
    p_enable = sub.add_parser("enable", help="Activate an AI agent (copilot/claude/cursor/trae/opencode/openclaw)")
    p_enable.add_argument("agent", help="Agent name: copilot, claude, cursor, trae, opencode, openclaw (or 'list' to show status)")
    p_enable.add_argument("-f", "--force", action="store_true", help="Overwrite existing agent config")
    p_enable.set_defaults(func=cmd_enable)

    # --- index ---
    p_index = sub.add_parser("index", help="Scan & convert binary files to Markdown")
    p_index.add_argument("target", nargs="?", default=None, help="File or directory to convert (or omit to scan entire workspace)")
    p_index.add_argument("--dir", "-d", default=".", help="Workspace root (default: .)")
    p_index.add_argument("-f", "--force", action="store_true", help="Re-convert even if up-to-date")
    p_index.set_defaults(func=cmd_index)

    # --- status ---
    p_status = sub.add_parser("status", help="Show index statistics")
    p_status.add_argument("dir", nargs="?", default=".", help="Workspace root (default: .)")
    p_status.set_defaults(func=cmd_status)

    # --- clean ---
    p_clean = sub.add_parser("clean", help="Clear all cached files and reset index")
    p_clean.add_argument("dir", nargs="?", default=".", help="Workspace root (default: .)")
    p_clean.set_defaults(func=cmd_clean)

    # --- reset ---
    p_reset = sub.add_parser("reset", help="Reset all .fcontext/ data (requires confirmation)")
    p_reset.add_argument("dir", nargs="?", default=".", help="Workspace root (default: .)")
    p_reset.set_defaults(func=cmd_reset)

    # --- topic (knowledge management) ---
    p_topic = sub.add_parser("topic", help="Manage accumulated knowledge topics")
    p_topic.add_argument("--dir", "-d", default=".", help="Workspace root (default: .)")
    topic_sub = p_topic.add_subparsers(dest="topic_action")
    p_topic.set_defaults(func=cmd_topic)

    # topic list
    topic_sub.add_parser("list", help="List all topics")

    # topic show
    p_topic_show = topic_sub.add_parser("show", help="Show a topic's content")
    p_topic_show.add_argument("name", help="Topic name (or partial match)")

    # topic clean
    topic_sub.add_parser("clean", help="Remove empty topic files")

    # --- export (knowledge export) ---
    p_export = sub.add_parser("export", help="Export knowledge to zip file or git remote")
    p_export.add_argument("output", help="Output path (file/directory) or git URL (https/ssh)")
    p_export.add_argument("--dir", "-d", default=".", help="Workspace root (default: .)")
    p_export.add_argument("--name", default=None, help="Pack name (default: project directory name)")
    p_export.add_argument("--branch", "-b", default=None, help="Git branch to push (default: main)")
    p_export.add_argument("--message", "-m", default=None, help="Git commit message")
    p_export.set_defaults(func=cmd_export)

    # --- experience (experience packs) ---
    p_exp = sub.add_parser("experience", help="Manage experience packs")
    p_exp.add_argument("--dir", "-d", default=".", help="Workspace root (default: .)")
    exp_sub = p_exp.add_subparsers(dest="exp_action")
    p_exp.set_defaults(func=cmd_experience)

    # experience list
    exp_sub.add_parser("list", help="List imported experience packs")

    # experience import
    p_exp_import = exp_sub.add_parser("import", help="Import experience pack from zip or git URL")
    p_exp_import.add_argument("source", help="Path to zip file or git URL (https/ssh)")
    p_exp_import.add_argument("--name", default=None, help="Name for the experience (default: derived from source)")
    p_exp_import.add_argument("--branch", "-b", default=None, help="Git branch or tag to clone (default: default branch)")
    p_exp_import.add_argument("-f", "--force", action="store_true", help="Overwrite existing experience")

    # experience remove
    p_exp_remove = exp_sub.add_parser("remove", help="Remove an imported experience pack")
    p_exp_remove.add_argument("name", help="Name of the experience to remove")

    # experience update
    p_exp_update = exp_sub.add_parser("update", help="Update experience packs from their original source (git/url)")
    p_exp_update.add_argument("name", nargs="?", default=None, help="Name of specific experience to update (default: all)")

    # --- req (requirements management) ---
    p_req = sub.add_parser("req", help="Requirements management")
    p_req.add_argument("--dir", "-d", default=".", help="Workspace root (default: .)")
    req_sub = p_req.add_subparsers(dest="req_action")
    p_req.set_defaults(func=cmd_req)

    # req add
    p_req_add = req_sub.add_parser("add", help="Add a new item")
    p_req_add.add_argument("title", help="Title of the item")
    p_req_add.add_argument("-t", "--type", default="requirement",
                           choices=("roadmap", "epic", "requirement", "story", "task", "bug"),
                           help="Item type (default: requirement)")
    p_req_add.add_argument("-p", "--priority", default="P2",
                           choices=("P0", "P1", "P2", "P3"),
                           help="Priority (default: P2)")
    p_req_add.add_argument("--parent", default="", help="Parent item ID (e.g. EPIC-001)")
    p_req_add.add_argument("--assignee", default="", help="Assignee name")
    p_req_add.add_argument("--tags", default="", help="Comma-separated tags")
    p_req_add.add_argument("--author", default="", help="Who proposed this requirement")
    p_req_add.add_argument("--source", default="", help="Source file path (e.g. meeting-notes/2026-02-10.md)")
    p_req_add.add_argument("--link", default="", help="Links to other items (e.g. supersedes:REQ-001,evolves:REQ-002)")

    # req list
    p_req_list = req_sub.add_parser("list", help="List items")
    p_req_list.add_argument("-t", "--type", default=None,
                            choices=("roadmap", "epic", "requirement", "story", "task", "bug"),
                            help="Filter by type")
    p_req_list.add_argument("-s", "--status", default=None, help="Filter by status")
    p_req_list.add_argument("--parent", default=None, help="Filter by parent ID")

    # req show
    p_req_show = req_sub.add_parser("show", help="Show item details")
    p_req_show.add_argument("id", help="Item ID (e.g. REQ-001)")

    # req set
    p_req_set = req_sub.add_parser("set", help="Update an item field")
    p_req_set.add_argument("id", help="Item ID")
    p_req_set.add_argument("field", help="Field to update (status/priority/title/parent/assignee/tags)")
    p_req_set.add_argument("value", help="New value")

    # req board
    req_sub.add_parser("board", help="Kanban board view by status")

    # req tree
    req_sub.add_parser("tree", help="Hierarchy tree view")

    # req comment
    p_req_comment = req_sub.add_parser("comment", help="Add a comment to an item")
    p_req_comment.add_argument("id", help="Item ID")
    p_req_comment.add_argument("message", help="Comment text")

    # req link
    p_req_link = req_sub.add_parser("link", help="Add a typed link between items")
    p_req_link.add_argument("id", help="Source item ID")
    p_req_link.add_argument("type", choices=("supersedes", "evolves", "relates", "blocks"),
                            help="Link type")
    p_req_link.add_argument("target", help="Target item ID")

    # req trace
    p_req_trace = req_sub.add_parser("trace", help="Trace evolution chain of an item")
    p_req_trace.add_argument("id", help="Item ID to trace")

    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    if args.command == "req" and (not hasattr(args, "req_action") or args.req_action is None):
        p_req.print_help()
        return 0

    if args.command == "topic" and (not hasattr(args, "topic_action") or args.topic_action is None):
        p_topic.print_help()
        return 0

    if args.command == "experience" and (not hasattr(args, "exp_action") or args.exp_action is None):
        p_exp.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
