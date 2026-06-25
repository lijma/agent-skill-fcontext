"""fcontext indexer — scan, convert, and manage the cache."""
from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


# Binary formats that need conversion via markitdown
CONVERTIBLE_EXTS = {
    ".pdf", ".docx", ".doc", ".xlsx", ".xls", ".xlsm",
    ".pptx", ".ppt", ".key",
    ".excalidraw", ".drawio",
    ".rtf", ".odt", ".ods", ".odp",
    ".epub",
}

# Image formats that need OCR (macOS Vision Framework)
IMAGE_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp",
    ".tiff", ".tif", ".webp", ".heic", ".heif",
}

# Text formats that can be copied directly to _cache
TEXT_EXTS = {
    ".md", ".markdown", ".txt", ".text",
    ".rst", ".adoc", ".asciidoc",
}

# All indexable extensions
INDEXABLE_EXTS = CONVERTIBLE_EXTS | TEXT_EXTS | IMAGE_EXTS


def _is_text_ext(path: Path) -> bool:
    return path.suffix.lower() in TEXT_EXTS


def _is_image_ext(path: Path) -> bool:
    """Check if a file has an image extension that needs OCR."""
    return path.suffix.lower() in IMAGE_EXTS


_OCR_SWIFT_SOURCE = r'''import Vision
import Cocoa

guard CommandLine.arguments.count > 1 else { exit(1) }
let path = CommandLine.arguments[1]
let url = URL(fileURLWithPath: path)
guard let image = NSImage(contentsOf: url) else { exit(2) }
guard let cgImage = image.cgImage(forProposedRect: nil, context: nil, hints: nil) else { exit(2) }
let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.usesLanguageCorrection = true
let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
try handler.perform([request])
guard let results = request.results, !results.isEmpty else { exit(0) }
for result in results {
    if let text = result.topCandidates(1).first?.string {
        print(text)
    }
}
'''


def _ocr_image_file(source: Path, cache_path: Path, rel_path: str) -> bool:
    """OCR an image file via macOS Vision Framework. Returns True on success."""
    if platform.system() != "Darwin":
        print(f"  ✗ {rel_path}: OCR requires macOS", file=sys.stderr)
        return False

    swift_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".swift", delete=False
        ) as f:
            f.write(_OCR_SWIFT_SOURCE)
            swift_path = f.name

        result = subprocess.run(
            ["swift", swift_path, str(source)],
            capture_output=True, text=True, timeout=60,
        )

        if result.returncode == 2:
            print(f"  ✗ {rel_path}: failed to load image", file=sys.stderr)
            return False
        if result.returncode != 0:
            print(
                f"  ✗ {rel_path}: OCR error (exit={result.returncode})",
                file=sys.stderr,
            )
            if result.stderr:
                print(f"    stderr: {result.stderr.strip()}", file=sys.stderr)
            return False

        text = result.stdout.strip()
        header = f"<!-- source: {rel_path} -->\n\n"
        cache_path.write_text(header + text + "\n", encoding="utf-8")
        return True
    except subprocess.TimeoutExpired:
        print(f"  ✗ {rel_path}: OCR timed out", file=sys.stderr)
        return False
    except Exception as e:
        print(f"  ✗ {rel_path}: OCR error — {e}", file=sys.stderr)
        return False
    finally:
        if swift_path is not None and os.path.exists(swift_path):
            os.unlink(swift_path)


# Directories to skip
SKIP_DIRS = {
    ".git", ".hg", ".svn", ".venv", "venv", "__pycache__",
    "node_modules", "dist", "build", "out", ".next",
    ".fcontext",
}


def _ctx_dir(root: Path) -> Path:
    return root / ".fcontext"


def _cache_dir(root: Path) -> Path:
    return _ctx_dir(root) / "_cache"


def _index_path(root: Path) -> Path:
    return _ctx_dir(root) / "_index.json"


def _load_index(root: Path) -> dict[str, Any]:
    idx = _index_path(root)
    if idx.exists():
        return json.loads(idx.read_text(encoding="utf-8"))
    return {}


def _save_index(root: Path, data: dict[str, Any]) -> None:
    idx = _index_path(root)
    idx.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _cache_filename(rel_path: str) -> str:
    """Deterministic cache filename from source relative path."""
    h = hashlib.md5(rel_path.encode()).hexdigest()[:10]
    stem = Path(rel_path).stem[:40]  # truncate long names
    # sanitize stem for filesystem
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in stem)
    return f"{safe}_{h}.md"


def _scan_convertible(root: Path) -> list[Path]:
    """Walk workspace and find all indexable files (binary + text)."""
    results = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for fname in filenames:
            if fname.startswith("."):
                continue
            if Path(fname).suffix.lower() in INDEXABLE_EXTS:
                results.append(Path(dirpath) / fname)
    return results


def _convert_file(source: Path, cache_path: Path, rel_path: str) -> bool:
    """Convert a single file to Markdown. Returns True on success."""
    try:
        from markitdown import MarkItDown
        converter = MarkItDown()
        result = converter.convert(str(source))
        text = getattr(result, "text_content", None) or getattr(result, "text", None) or str(result)

        header = f"<!-- source: {rel_path} -->\n\n"
        cache_path.write_text(header + text, encoding="utf-8")
        return True
    except Exception as e:
        print(f"  ✗ {rel_path}: {e}", file=sys.stderr)
        return False


def _copy_text_file(source: Path, cache_path: Path, rel_path: str) -> bool:
    """Copy a text/markdown file directly to cache. Returns True on success."""
    try:
        content = source.read_text(encoding="utf-8", errors="replace")
        header = f"<!-- source: {rel_path} -->\n\n"
        cache_path.write_text(header + content, encoding="utf-8")
        return True
    except Exception as e:
        print(f"  ✗ {rel_path}: {e}", file=sys.stderr)
        return False


def _index_one(source: Path, cache_path: Path, rel_path: str) -> bool:
    """Index a single file: copy text files, OCR images, convert binaries."""
    if _is_text_ext(source):
        return _copy_text_file(source, cache_path, rel_path)
    if _is_image_ext(source):
        return _ocr_image_file(source, cache_path, rel_path)
    return _convert_file(source, cache_path, rel_path)


def run_index_file(root: Path, target: Path, force: bool = False) -> int:
    """Convert a single file to Markdown and add to cache."""
    cache = _cache_dir(root)
    cache.mkdir(parents=True, exist_ok=True)

    if not target.exists():
        print(f"fatal: file not found: {target}", file=sys.stderr)
        return 1

    try:
        rel = str(target.relative_to(root))
    except ValueError:
        print(f"fatal: {target} is not inside workspace {root}", file=sys.stderr)
        return 1

    index = _load_index(root)
    mtime = target.stat().st_mtime

    # Skip if up-to-date
    if not force and rel in index:
        cached_md = root / index[rel]["md"]
        if cached_md.exists() and index[rel].get("mtime", 0) >= mtime:
            print(f"  ✓ {rel} (up-to-date)")
            md_path = root / index[rel]["md"]
            print(f"  → {md_path}")
            return 0

    cache_name = _cache_filename(rel)
    cache_path = cache / cache_name

    print(f"  → {rel}")
    if _index_one(target, cache_path, rel):
        index[rel] = {
            "md": str(cache_path.relative_to(root)),
            "mtime": mtime,
            "size": target.stat().st_size,
            "indexed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        _save_index(root, index)
        print(f"  ✓ cached: {cache_path.relative_to(root)}")
        return 0
    else:
        return 1


def run_index_dir(root: Path, target_dir: Path, force: bool = False) -> int:
    """Scan a specific directory and convert all convertible files in it."""
    cache = _cache_dir(root)
    cache.mkdir(parents=True, exist_ok=True)

    if not target_dir.exists():
        print(f"fatal: directory not found: {target_dir}", file=sys.stderr)
        return 1

    try:
        rel_dir = str(target_dir.relative_to(root))
    except ValueError:
        print(f"fatal: {target_dir} is not inside workspace {root}", file=sys.stderr)
        return 1

    index = _load_index(root)

    # Scan only within target_dir
    files = []
    for dirpath, dirnames, filenames in os.walk(target_dir):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for fname in filenames:
            if fname.startswith("."):
                continue
            if Path(fname).suffix.lower() in INDEXABLE_EXTS:
                files.append(Path(dirpath) / fname)

    converted = 0
    skipped = 0
    failed = 0

    print(f"Scanning {rel_dir}/ ...")
    print(f"Found {len(files)} indexable files\n")

    for fpath in files:
        rel = str(fpath.relative_to(root))
        mtime = fpath.stat().st_mtime

        if not force and rel in index:
            cached_md = root / index[rel]["md"]
            if cached_md.exists() and index[rel].get("mtime", 0) >= mtime:
                skipped += 1
                continue

        cache_name = _cache_filename(rel)
        cache_path = cache / cache_name

        print(f"  \u2192 {rel}")
        if _index_one(fpath, cache_path, rel):
            index[rel] = {
                "md": str(cache_path.relative_to(root)),
                "mtime": mtime,
                "size": fpath.stat().st_size,
                "indexed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            converted += 1
        else:
            failed += 1

    _save_index(root, index)

    print(f"\nDone: {converted} indexed, {skipped} up-to-date, {failed} failed")
    print(f"Index: {_index_path(root)}")
    return 0


def run_index(root: Path, force: bool = False) -> int:
    """Scan workspace, incrementally convert binary files."""
    cache = _cache_dir(root)
    cache.mkdir(parents=True, exist_ok=True)

    index = _load_index(root)
    files = _scan_convertible(root)

    converted = 0
    skipped = 0
    failed = 0

    print(f"Scanning {root} ...")
    print(f"Found {len(files)} indexable files\n")

    for fpath in files:
        rel = str(fpath.relative_to(root))
        mtime = fpath.stat().st_mtime

        # Skip if already indexed and not stale
        if not force and rel in index:
            cached_md = root / index[rel]["md"]
            if cached_md.exists() and index[rel].get("mtime", 0) >= mtime:
                skipped += 1
                continue

        cache_name = _cache_filename(rel)
        cache_path = cache / cache_name

        print(f"  → {rel}")
        if _index_one(fpath, cache_path, rel):
            index[rel] = {
                "md": str(cache_path.relative_to(root)),
                "mtime": mtime,
                "size": fpath.stat().st_size,
                "indexed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            converted += 1
        else:
            failed += 1

    _save_index(root, index)

    print(f"\nDone: {converted} indexed, {skipped} up-to-date, {failed} failed")
    print(f"Index: {_index_path(root)}")
    return 0


def run_status(root: Path) -> int:
    """Show index statistics."""
    index = _load_index(root)
    files = _scan_convertible(root)
    rel_set = {str(f.relative_to(root)) for f in files}

    indexed = set(index.keys())
    pending = rel_set - indexed
    orphaned = indexed - rel_set

    stale = 0
    for rel in indexed & rel_set:
        fpath = root / rel
        if fpath.exists() and fpath.stat().st_mtime > index[rel].get("mtime", 0):
            stale += 1

    print(f"Workspace:  {root}")
    print(f"Convertible: {len(rel_set)} files")
    print(f"Indexed:     {len(indexed)} files")
    print(f"Pending:     {len(pending)} files")
    print(f"Stale:       {stale} files")
    print(f"Orphaned:    {len(orphaned)} entries")

    if pending:
        print(f"\nRun 'fcontext index' to index {len(pending) + stale} files")
    if orphaned:
        print(f"Run 'fcontext clean' to remove {len(orphaned)} orphaned entries")

    return 0


def run_clean(root: Path) -> int:
    """Clear all cache files and reset index."""
    cache = _cache_dir(root)
    removed = 0

    if cache.exists():
        for f in cache.iterdir():
            if f.is_file():
                f.unlink()
                print(f"  ✗ {f.relative_to(root)}")
                removed += 1

    # Reset index to empty
    _save_index(root, {})

    if removed:
        print(f"\nCleaned: {removed} cached files removed, index reset")
    else:
        print("  cache is already empty")
    return 0
