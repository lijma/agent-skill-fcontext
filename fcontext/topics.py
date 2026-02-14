"""fcontext topics — manage accumulated knowledge in _topics/."""
from __future__ import annotations

import sys
import time
from pathlib import Path


def _topics_dir(root: Path) -> Path:
    return root / ".fcontext" / "_topics"


def topic_list(root: Path) -> int:
    """List all topic files with metadata."""
    topics = _topics_dir(root)
    if not topics.is_dir():
        print("  (no _topics/ directory)")
        return 0

    files = sorted(topics.glob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not files:
        print("  (no topics yet — AI will create them during analysis)")
        return 0

    print(f"  {'TOPIC':<35} {'SIZE':>8}  {'UPDATED'}")
    print(f"  {'─'*35} {'─'*8}  {'─'*19}")

    total_size = 0
    for f in files:
        stat = f.stat()
        size = stat.st_size
        total_size += size
        mtime = time.strftime("%Y-%m-%d %H:%M", time.localtime(stat.st_mtime))
        size_str = _human_size(size)
        print(f"  {f.stem:<35} {size_str:>8}  {mtime}")

    print(f"\n  Total: {len(files)} topics, {_human_size(total_size)}")
    return 0


def topic_show(root: Path, name: str) -> int:
    """Show the content of a topic file."""
    topics = _topics_dir(root)

    # Try exact match first, then with .md suffix
    target = topics / name
    if not target.exists():
        target = topics / f"{name}.md"
    if not target.exists():
        # Fuzzy match
        matches = [f for f in topics.glob("*.md") if name.lower() in f.stem.lower()]
        if len(matches) == 1:
            target = matches[0]
        elif len(matches) > 1:
            print(f"  Ambiguous name '{name}', matches:", file=sys.stderr)
            for m in matches:
                print(f"    {m.stem}", file=sys.stderr)
            return 1
        else:
            print(f"  error: topic '{name}' not found", file=sys.stderr)
            return 1

    stat = target.stat()
    mtime = time.strftime("%Y-%m-%d %H:%M", time.localtime(stat.st_mtime))

    print(f"\n  ╔══ {target.stem}")
    print(f"  ║ File:    {target.relative_to(root)}")
    print(f"  ║ Size:    {_human_size(stat.st_size)}")
    print(f"  ║ Updated: {mtime}")
    print(f"  ╠══")

    content = target.read_text(encoding="utf-8")
    for line in content.splitlines():
        print(f"  ║ {line}")

    print(f"  ╚══")
    return 0


def topic_clean(root: Path) -> int:
    """Remove empty or trivial topic files."""
    topics = _topics_dir(root)
    if not topics.is_dir():
        print("  (no _topics/ directory)")
        return 0

    removed = 0
    for f in topics.glob("*.md"):
        content = f.read_text(encoding="utf-8").strip()
        # Remove if empty or only whitespace/headers with no real content
        if len(content) < 10:
            print(f"  ✗ {f.stem} (empty)")
            f.unlink()
            removed += 1

    if removed:
        print(f"\n  Cleaned: {removed} empty topics removed")
    else:
        print("  All topics have content, nothing to clean")
    return 0


def _human_size(size: int) -> str:
    """Format bytes as human-readable."""
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    else:
        return f"{size / (1024 * 1024):.1f} MB"
