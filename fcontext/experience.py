"""fcontext experience — import, export, and list experience packs.

Experience packs are read-only knowledge snapshots from other projects.
They live in .fcontext/_experiences/<name>/ and contain _cache/, _topics/,
and _requirements/ subdirectories, plus a _README.md describing the pack.
"""
from __future__ import annotations

import csv
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

# Only these subdirectories are included in experience packs.
KNOWLEDGE_DIRS = ("_cache", "_topics", "_requirements")

# Also included in export/import (not a knowledge dir but metadata)
README_NAME = "_README.md"

# ── Experience registry (ex.csv) ──────────────────────────────────────────────

EX_CSV_COLUMNS = ("name", "source_type", "source", "branch", "imported_at", "file_count")


def _experiences_dir(root: Path) -> Path:
    return root / ".fcontext" / "_experiences"


def _ex_csv_path(root: Path) -> Path:
    return _experiences_dir(root) / "ex.csv"


def _load_ex(root: Path) -> list[dict[str, str]]:
    """Load experience registry from ex.csv."""
    path = _ex_csv_path(root)
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _save_ex(root: Path, rows: list[dict[str, str]]) -> None:
    """Save experience registry to ex.csv."""
    path = _ex_csv_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=EX_CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def _record_import(root: Path, name: str, source_type: str, source: str,
                   branch: str, file_count: int) -> None:
    """Add or update a row in ex.csv for an imported experience."""
    rows = _load_ex(root)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    new_row = {
        "name": name,
        "source_type": source_type,
        "source": source,
        "branch": branch,
        "imported_at": now,
        "file_count": str(file_count),
    }
    # Replace existing row with same name (force-overwrite case)
    rows = [r for r in rows if r.get("name") != name]
    rows.append(new_row)
    _save_ex(root, rows)


def _unrecord(root: Path, name: str) -> None:
    """Remove a row from ex.csv."""
    rows = _load_ex(root)
    filtered = [r for r in rows if r.get("name") != name]
    if len(filtered) != len(rows):
        _save_ex(root, filtered)


# ── .gitignore management for git-imported experiences ────────────────────

def _gitignore_path(root: Path) -> Path:
    return root / ".fcontext" / ".gitignore"


def _gitignore_add(root: Path, name: str) -> None:
    """Add _experiences/<name>/ to .fcontext/.gitignore for git-imported packs."""
    gi = _gitignore_path(root)
    entry = f"_experiences/{name}/\n"
    if gi.exists():
        content = gi.read_text(encoding="utf-8")
        if entry in content:
            return  # already present
        if not content.endswith("\n"):
            content += "\n"
        content += entry
    else:
        content = entry
    gi.write_text(content, encoding="utf-8")


def _gitignore_remove(root: Path, name: str) -> None:
    """Remove _experiences/<name>/ from .fcontext/.gitignore."""
    gi = _gitignore_path(root)
    if not gi.exists():
        return
    entry = f"_experiences/{name}/\n"
    content = gi.read_text(encoding="utf-8")
    if entry in content:
        content = content.replace(entry, "")
        gi.write_text(content, encoding="utf-8")


def list_experiences(root: Path) -> int:
    """List all imported experience packs."""
    exp_dir = _experiences_dir(root)
    if not exp_dir.is_dir():
        print("  (no experience packs)")
        return 0

    packs = sorted(d for d in exp_dir.iterdir() if d.is_dir())
    if not packs:
        print("  (no experience packs)")
        return 0

    # Load registry for source info
    registry = {r["name"]: r for r in _load_ex(root)}

    for pack in packs:
        readme = pack / README_NAME
        desc = ""
        if readme.exists():
            # First non-heading, non-empty line is the description
            for line in readme.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if stripped and not stripped.startswith("#"):
                    desc = stripped
                    break

        dirs_present = [d.name for d in pack.iterdir() if d.is_dir() and d.name in KNOWLEDGE_DIRS]
        file_count = sum(1 for _ in pack.rglob("*") if _.is_file())
        total_size = sum(f.stat().st_size for f in pack.rglob("*") if f.is_file())
        size_str = _human_size(total_size)

        print(f"  {pack.name}")
        if desc:
            print(f"    {desc}")
        print(f"    dirs: {', '.join(dirs_present)}  files: {file_count}  size: {size_str}")

        # Source info from registry
        rec = registry.get(pack.name)
        if rec:
            src_type = rec.get("source_type", "")
            src = rec.get("source", "")
            branch = rec.get("branch", "")
            imported_at = rec.get("imported_at", "")
            source_line = f"    source: {src_type}"
            if src:
                source_line += f"  {src}"
            if branch:
                source_line += f"  branch={branch}"
            if imported_at:
                source_line += f"  imported={imported_at}"
            print(source_line)

        print()

    return 0


def remove_experience(root: Path, name: str) -> int:
    """Remove an imported experience pack."""
    target = _experiences_dir(root) / name
    if not target.is_dir():
        print(f"error: experience '{name}' not found", file=sys.stderr)
        return 1
    shutil.rmtree(target)
    _gitignore_remove(root, name)
    _unrecord(root, name)
    print(f"  ✓ removed experience '{name}'")
    return 0


def update_experience(root: Path, name: str | None = None) -> int:
    """Update experience packs by re-importing from their original source.

    Reads ex.csv and for each updatable entry:
    - source_type='git' or 'local-git' → re-clone with force
    - source_type='url' → re-download with force
    - source_type='zip' → skip (local file, cannot auto-update)

    If *name* is given, only that single experience is updated.
    Returns 0 if all updates succeeded, 1 if any failed.
    """
    rows = _load_ex(root)

    if name:
        rows = [r for r in rows if r["name"] == name]
        if not rows:
            print(f"error: experience '{name}' not found in registry", file=sys.stderr)
            return 1

    if not rows:
        print("no experience packs to update")
        return 0

    updatable = [r for r in rows if r.get("source_type") in ("git", "local-git", "url")]
    skipped = [r for r in rows if r.get("source_type") not in ("git", "local-git", "url")]

    for r in skipped:
        print(f"  skip '{r['name']}' (source_type={r.get('source_type', '?')}, cannot auto-update)")

    if not updatable:
        print("no updatable experience packs (only git/url sources can be updated)")
        return 0

    failed = 0
    for r in updatable:
        src_type = r["source_type"]
        source = r["source"]
        exp_name = r["name"]
        branch = r.get("branch") or None

        print(f"  updating '{exp_name}' ({src_type}) ...")
        if src_type in ("git", "local-git"):
            rc = import_experience_git(root, source, name=exp_name,
                                       force=True, branch=branch)
        else:  # url
            rc = _import_from_url(root, source, name=exp_name, force=True)

        if rc != 0:
            print(f"  ✗ failed to update '{exp_name}'", file=sys.stderr)
            failed += 1

    return 1 if failed else 0


def _is_git_url(source: str) -> bool:
    """Detect if source looks like a git URL.

    Matches:
      https://github.com/org/repo.git
      https://github.com/org/repo
      git@github.com:org/repo.git
      ssh://git@host/repo.git
    """
    # ssh-style: git@host:org/repo
    if re.match(r'^[\w.-]+@[\w.-]+:', source):
        return True
    # URL-style: https://, ssh://, git://
    if re.match(r'^(https?|ssh|git)://', source):
        return True
    return False


def _is_local_git_repo(source: str) -> bool:
    """Return True if *source* is a path to a local directory containing .git."""
    p = Path(source)
    return p.is_dir() and (p / ".git").exists()


def _is_download_url(source: str) -> bool:
    """Detect if source is an HTTP(S) URL pointing to a downloadable file.

    Matches URLs ending with .zip (case-insensitive), possibly with query params.
    These should be downloaded rather than git-cloned.
    """
    if not re.match(r'^https?://', source):
        return False
    # Strip query string / fragment for extension check
    path_part = source.split('?')[0].split('#')[0]
    return path_part.lower().endswith('.zip')


def import_experience(root: Path, source: str, name: str | None = None,
                      force: bool = False, branch: str | None = None) -> int:
    """Import an experience pack from a zip file, git repo, or URL.

    Auto-detects source type:
    - Download URL (https://.../*.zip) → download and import as zip
    - Git URL (https://, git@, ssh://) → clone and extract .fcontext/
    - Local git repo (directory with .git/) → clone and extract .fcontext/
    - Local file → treat as zip
    """
    if _is_download_url(source):
        return _import_from_url(root, source, name=name, force=force)
    if _is_git_url(source) or _is_local_git_repo(source):
        return import_experience_git(root, source, name=name, force=force, branch=branch)
    return _import_from_zip(root, source, name=name, force=force)


def _import_from_url(root: Path, url: str, name: str | None = None,
                     force: bool = False) -> int:
    """Download a zip from an HTTP(S) URL and import it."""
    # Derive name from URL filename if not provided
    if not name:
        path_part = url.split('?')[0].split('#')[0]
        name = Path(path_part).stem  # e.g. "knowledge.zip" → "knowledge"

    print(f"  downloading {url} ...")
    try:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_zip = Path(tmp) / "download.zip"
            with urlopen(url, timeout=60) as resp:
                tmp_zip.write_bytes(resp.read())

            if not zipfile.is_zipfile(tmp_zip):
                print("error: downloaded file is not a valid zip", file=sys.stderr)
                return 1

            rc = _import_from_zip(root, str(tmp_zip), name=name, force=force)
            if rc == 0:
                # Re-record with correct source_type and URL
                _record_import(root, name, source_type="url", source=url,
                               branch="", file_count=int(
                                   next((r["file_count"] for r in _load_ex(root)
                                         if r["name"] == name), "0")))
            return rc
    except (URLError, OSError) as exc:
        print(f"error: download failed: {exc}", file=sys.stderr)
        return 1


def import_experience_git(root: Path, url: str, name: str | None = None,
                          force: bool = False, branch: str | None = None) -> int:
    """Import an experience pack from a git repository.

    Clones the repo (shallow), locates .fcontext/ knowledge dirs,
    and copies them into _experiences/<name>/.
    """
    # Derive name from URL if not provided
    if not name:
        # https://github.com/org/repo.git → repo
        # git@github.com:org/repo.git → repo
        basename = url.rstrip('/').rsplit('/', 1)[-1].rsplit(':', 1)[-1]
        name = basename.removesuffix('.git') or 'experience'

    target = _experiences_dir(root) / name
    if target.exists() and not force:
        print(f"error: experience '{name}' already exists (use -f to overwrite)",
              file=sys.stderr)
        return 1

    # Clone to temp directory
    with tempfile.TemporaryDirectory() as tmp:
        clone_dir = Path(tmp) / "repo"
        cmd = ["git", "clone", "--depth", "1"]
        if branch:
            cmd += ["--branch", branch]
        cmd += [url, str(clone_dir)]

        print(f"  cloning {url} ...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            err = result.stderr.strip()
            print(f"error: git clone failed: {err}", file=sys.stderr)
            return 1

        # Locate .fcontext/ in cloned repo
        fcontext_dir = clone_dir / ".fcontext"
        if not fcontext_dir.is_dir():
            print("error: cloned repo has no .fcontext/ directory",
                  file=sys.stderr)
            return 1

        # Check for knowledge content
        has_knowledge = any((fcontext_dir / kd).is_dir() and
                            any((fcontext_dir / kd).iterdir())
                            for kd in KNOWLEDGE_DIRS)
        if not has_knowledge:
            print(f"error: .fcontext/ contains no knowledge directories "
                  f"({', '.join(KNOWLEDGE_DIRS)})",
                  file=sys.stderr)
            return 1

        # Prepare target
        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True, exist_ok=True)

        # Copy knowledge dirs and _README.md
        extracted = 0
        for kd in KNOWLEDGE_DIRS:
            src = fcontext_dir / kd
            if src.is_dir():
                shutil.copytree(src, target / kd)
                extracted += sum(1 for _ in (target / kd).rglob("*") if _.is_file())

        readme_src = fcontext_dir / README_NAME
        if readme_src.exists():
            shutil.copy2(readme_src, target / README_NAME)
            extracted += 1

    # Determine source type
    source_type = "local-git" if _is_local_git_repo(url) else "git"
    _record_import(root, name, source_type=source_type, source=url,
                   branch=branch or "", file_count=extracted)

    # Remote git imports can be re-cloned — ignore in git
    if source_type == "git":
        _gitignore_add(root, name)

    print(f"  ✓ imported experience '{name}' from git ({extracted} files)")
    return 0


def _import_from_zip(root: Path, source: str, name: str | None = None,
                     force: bool = False) -> int:
    """Import an experience pack from a zip file.

    The zip should contain _cache/, _topics/, _requirements/ at its root
    (or inside a single top-level folder).
    """
    source_path = Path(source).resolve()
    if not source_path.exists():
        print(f"error: file not found: {source}", file=sys.stderr)
        return 1

    if not zipfile.is_zipfile(source_path):
        print(f"error: not a valid zip file: {source}", file=sys.stderr)
        return 1

    # Derive name from zip filename if not provided
    if not name:
        name = source_path.stem  # e.g. "ipmi_app_ba.zip" → "ipmi_app_ba"

    target = _experiences_dir(root) / name
    if target.exists() and not force:
        print(f"error: experience '{name}' already exists (use -f to overwrite)", file=sys.stderr)
        return 1

    if target.exists():
        shutil.rmtree(target)

    target.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(source_path, "r") as zf:
        # Detect if zip has a single top-level directory wrapper
        top_dirs = {n.split("/")[0] for n in zf.namelist() if "/" in n}
        prefix = ""
        if len(top_dirs) == 1:
            candidate = top_dirs.pop()
            # Check if knowledge dirs are inside this wrapper
            has_knowledge_inside = any(
                n.startswith(f"{candidate}/{kd}/") for n in zf.namelist() for kd in KNOWLEDGE_DIRS
            )
            if has_knowledge_inside:
                prefix = candidate + "/"

        extracted = 0
        for member in zf.infolist():
            if member.is_dir():
                continue

            rel = member.filename
            if prefix and rel.startswith(prefix):
                rel = rel[len(prefix):]

            # Only extract files under knowledge directories or _README.md
            top = rel.split("/")[0] if "/" in rel else rel
            if top not in KNOWLEDGE_DIRS and rel != README_NAME:
                continue

            dest = target / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(member) as src, open(dest, "wb") as dst:
                dst.write(src.read())
            extracted += 1

    if extracted == 0:
        shutil.rmtree(target)
        print(f"error: zip contains no knowledge directories ({', '.join(KNOWLEDGE_DIRS)})", file=sys.stderr)
        return 1

    _record_import(root, name, source_type="zip", source=source,
                   branch="", file_count=extracted)

    print(f"  ✓ imported experience '{name}' ({extracted} files)")
    return 0


def _collect_knowledge(root: Path) -> list[tuple[Path, str]]:
    """Collect all exportable files from knowledge directories.

    Includes:
    - Workspace's own _cache/, _topics/, _requirements/
    - Locally-sourced experiences (source_type=zip or local-git) that cannot
      be re-fetched remotely.  Remote experiences (git/url) are excluded
      because they can be re-cloned / re-downloaded.
    """
    ctx = root / ".fcontext"
    files: list[tuple[Path, str]] = []

    # 1. Workspace's own knowledge dirs
    for kd in KNOWLEDGE_DIRS:
        kd_path = ctx / kd
        if not kd_path.is_dir():
            continue
        for f in kd_path.rglob("*"):
            if f.is_file():
                rel = str(f.relative_to(ctx))
                files.append((f, rel))

    # 2. Local-source experiences (zip, local-git) — cannot be re-fetched
    registry = {r["name"]: r for r in _load_ex(root)}
    exp_dir = _experiences_dir(root)
    if exp_dir.is_dir():
        for pack in sorted(exp_dir.iterdir()):
            if not pack.is_dir():
                continue
            rec = registry.get(pack.name, {})
            src_type = rec.get("source_type", "")
            # Only include local sources that can't be re-obtained remotely
            if src_type not in ("zip", "local-git"):
                continue
            for f in pack.rglob("*"):
                if f.is_file():
                    rel = str(f.relative_to(ctx))
                    files.append((f, rel))

        # Include ex.csv itself so the registry survives round-trip
        csv_path = _ex_csv_path(root)
        if csv_path.exists():
            files.append((csv_path, str(csv_path.relative_to(ctx))))

    return files


def export_experience(root: Path, output: str, name: str | None = None,
                      branch: str | None = None, message: str | None = None) -> int:
    """Export current project knowledge to a zip file or git remote.

    Auto-detects output type:
    - Git URL (https://, git@, ssh://) → push .fcontext/ knowledge to remote
    - Local path → create zip file
    """
    if _is_git_url(output):
        return _export_to_git(root, output, name=name, branch=branch, message=message)
    return _export_to_zip(root, output, name=name)


def _export_to_zip(root: Path, output: str, name: str | None = None) -> int:
    """Export current project knowledge as a zip file."""
    output_path = Path(output).resolve()

    # Determine if output is meant to be a directory
    is_dir_target = output_path.is_dir() or output.endswith("/") or output_path.suffix == ""
    if is_dir_target:
        pack_name = name or root.name
        output_path.mkdir(parents=True, exist_ok=True)
        output_path = output_path / f"{pack_name}.zip"
    elif output_path.suffix != ".zip":
        output_path = output_path.with_suffix(output_path.suffix + ".zip")

    files = _collect_knowledge(root)
    if not files:
        print("error: nothing to export (no files in _cache/, _topics/, _requirements/)", file=sys.stderr)
        return 1

    output_path.parent.mkdir(parents=True, exist_ok=True)

    readme_content = _generate_readme(root, files)

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(README_NAME, readme_content)
        for abs_path, rel_path in files:
            zf.write(abs_path, rel_path)

    print(f"  ✓ exported {len(files)} files → {output_path}")
    return 0


def _export_to_git(root: Path, url: str, name: str | None = None,
                   branch: str | None = None, message: str | None = None) -> int:
    """Export current project knowledge by pushing to a git remote.

    Clones the existing remote (if any) to preserve history, updates
    .fcontext/ knowledge content, commits the changes, and pushes.
    If the remote is empty or doesn't exist, initialises a new repo.
    """
    import os

    files = _collect_knowledge(root)
    if not files:
        print("error: nothing to export (no files in _cache/, _topics/, _requirements/)", file=sys.stderr)
        return 1

    pack_name = name or root.name
    branch = branch or "main"
    commit_msg = message or f"Export knowledge from {pack_name}"

    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "fcontext",
        "GIT_AUTHOR_EMAIL": "fcontext@export",
        "GIT_COMMITTER_NAME": "fcontext",
        "GIT_COMMITTER_EMAIL": "fcontext@export",
    }

    with tempfile.TemporaryDirectory() as tmp:
        repo_dir = Path(tmp) / "export"

        # Try cloning existing remote to preserve history
        clone_cmd = ["git", "clone", "--branch", branch, url, str(repo_dir)]
        clone_result = subprocess.run(clone_cmd, capture_output=True, text=True, env=env)

        if clone_result.returncode == 0:
            # Successfully cloned — remove old .fcontext/ content to sync
            old_ctx = repo_dir / ".fcontext"
            if old_ctx.exists():
                shutil.rmtree(old_ctx)
        else:
            # Remote is empty or branch doesn't exist — init fresh
            repo_dir.mkdir(parents=True)
            init_result = subprocess.run(
                ["git", "init", "-b", branch], cwd=repo_dir,
                capture_output=True, text=True, env=env)
            if init_result.returncode != 0:
                print(f"error: git init failed: {init_result.stderr.strip()}",
                      file=sys.stderr)
                return 1
            add_remote = subprocess.run(
                ["git", "remote", "add", "origin", url], cwd=repo_dir,
                capture_output=True, text=True, env=env)
            if add_remote.returncode != 0:
                print(f"error: git remote add failed: {add_remote.stderr.strip()}",
                      file=sys.stderr)
                return 1

        # Write knowledge files into .fcontext/
        ctx_dir = repo_dir / ".fcontext"
        ctx_dir.mkdir(parents=True, exist_ok=True)

        for abs_path, rel_path in files:
            dest = ctx_dir / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(abs_path, dest)

        # Generate _README.md
        readme_content = _generate_readme(root, files)
        (ctx_dir / README_NAME).write_text(readme_content, encoding="utf-8")

        # Use project _README.md as top-level README
        project_readme = root / ".fcontext" / README_NAME
        if project_readme.exists():
            shutil.copy2(project_readme, repo_dir / "README.md")
        else:
            (repo_dir / "README.md").write_text(readme_content, encoding="utf-8")

        # Stage, commit, push
        subprocess.run(["git", "add", "."], cwd=repo_dir,
                       capture_output=True, text=True, env=env)

        # Check if there are actual changes to commit
        diff_result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"], cwd=repo_dir,
            capture_output=True, text=True, env=env)
        if diff_result.returncode == 0:
            # No changes — nothing new to push
            print(f"  ✓ no changes to export (remote is up-to-date)")
            return 0

        commit_result = subprocess.run(
            ["git", "commit", "-m", commit_msg], cwd=repo_dir,
            capture_output=True, text=True, env=env)
        if commit_result.returncode != 0:
            print(f"error: git commit failed: {commit_result.stderr.strip()}",
                  file=sys.stderr)
            return 1

        print(f"  pushing to {url} (branch={branch}) ...")
        push_cmd = ["git", "push", "-u", "origin", branch]
        push_result = subprocess.run(push_cmd, cwd=repo_dir,
                                     capture_output=True, text=True, env=env)
        if push_result.returncode != 0:
            print(f"error: git push failed: {push_result.stderr.strip()}",
                  file=sys.stderr)
            return 1

    print(f"  ✓ exported {len(files)} files → {url} (branch={branch})")
    return 0


def _generate_readme(root: Path, files: list[tuple[Path, str]]) -> str:
    """Generate a _README.md summarizing the experience pack."""
    ctx = root / ".fcontext"
    pack_name = root.name
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Count files per knowledge dir
    counts: dict[str, int] = {}
    for _, rel in files:
        top = rel.split("/")[0]
        counts[top] = counts.get(top, 0) + 1

    # Collect topic names
    topics: list[str] = []
    topics_dir = ctx / "_topics"
    if topics_dir.is_dir():
        topics = sorted(f.stem for f in topics_dir.iterdir() if f.is_file() and f.suffix == ".md")

    lines = [
        f"# {pack_name}",
        f"",
        f"Knowledge exported from project **{pack_name}** on {now}.",
        f"",
        f"## Contents",
        f"",
    ]
    for kd in KNOWLEDGE_DIRS:
        if kd in counts:
            lines.append(f"- `{kd}/` — {counts[kd]} files")
    lines.append("")

    if topics:
        lines.append("## Topics")
        lines.append("")
        for t in topics:
            lines.append(f"- {t}")
        lines.append("")

    lines.append("---")
    lines.append("*This file is auto-generated by `fcontext export`. Read-only.*")
    lines.append("")
    return "\n".join(lines)


def _human_size(nbytes: int) -> str:
    """Format byte count as human-readable string."""
    for unit in ("B", "KB", "MB", "GB"):
        if nbytes < 1024:
            return f"{nbytes:.0f} {unit}" if unit == "B" else f"{nbytes:.1f} {unit}"
        nbytes /= 1024
    return f"{nbytes:.1f} TB"
