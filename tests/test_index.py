"""Tests for fcontext index."""
import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from fcontext.indexer import (
    run_index, run_index_file, run_index_dir, run_status, run_clean,
    _load_index, _save_index, _convert_file, _copy_text_file, _index_one,
    _cache_dir, _cache_filename, _scan_convertible, _index_path,
)


class TestIndex:
    """TASK-004: 测试 index — 增量转换与mtime跳过"""

    def _create_dummy_pdf(self, workspace: Path, name: str = "test.pdf") -> Path:
        """Create a minimal file with .pdf extension (won't actually convert,
        but tests the scanning and error-handling paths)."""
        f = workspace / name
        f.write_bytes(b"%PDF-1.4 dummy content")
        return f

    def test_scan_finds_convertible(self, workspace: Path):
        self._create_dummy_pdf(workspace)
        from fcontext.indexer import _scan_convertible
        files = _scan_convertible(workspace)
        assert any(f.name == "test.pdf" for f in files)

    def test_scan_skips_hidden_dirs(self, workspace: Path):
        hidden = workspace / ".hidden"
        hidden.mkdir()
        (hidden / "secret.pdf").write_bytes(b"%PDF")
        from fcontext.indexer import _scan_convertible
        files = _scan_convertible(workspace)
        assert not any("secret.pdf" in str(f) for f in files)

    def test_scan_skips_fcontext(self, workspace: Path):
        (workspace / ".fcontext" / "internal.pdf").write_bytes(b"%PDF")
        from fcontext.indexer import _scan_convertible
        files = _scan_convertible(workspace)
        assert not any("internal.pdf" in str(f) for f in files)

    def test_cache_filename_deterministic(self):
        from fcontext.indexer import _cache_filename
        a = _cache_filename("docs/report.pdf")
        b = _cache_filename("docs/report.pdf")
        assert a == b
        assert a.endswith(".md")

    def test_cache_filename_unique(self):
        from fcontext.indexer import _cache_filename
        a = _cache_filename("docs/report.pdf")
        b = _cache_filename("docs/other.pdf")
        assert a != b

    def test_index_json_structure(self, workspace: Path):
        """After index, _index.json has correct structure."""
        idx_path = workspace / ".fcontext" / "_index.json"
        data = json.loads(idx_path.read_text())
        assert isinstance(data, dict)

    def test_run_index_file_not_found(self, workspace: Path):
        fake = workspace / "nonexistent.pdf"
        rc = run_index_file(workspace, fake)
        assert rc == 1

    def test_run_index_file_outside_workspace(self, workspace: Path, tmp_path: Path):
        import tempfile
        with tempfile.TemporaryDirectory() as ext:
            outside = Path(ext) / "file.pdf"
            outside.write_bytes(b"%PDF")
            rc = run_index_file(workspace, outside)
            assert rc == 1


class TestStatus:
    """TASK-005 partial: 测试 status"""

    def test_status_on_empty(self, workspace: Path, capsys):
        rc = run_status(workspace)
        assert rc == 0
        out = capsys.readouterr().out
        assert "Convertible:" in out

    def test_status_counts_pending(self, workspace: Path, capsys):
        (workspace / "doc.pdf").write_bytes(b"%PDF")
        rc = run_status(workspace)
        assert rc == 0
        out = capsys.readouterr().out
        assert "Pending:" in out


class TestClean:
    """TASK-005 partial: 测试 clean"""

    def test_clean_removes_all_cache(self, workspace: Path, capsys):
        # Create some cache files
        cache_dir = workspace / ".fcontext" / "_cache"
        (cache_dir / "file_a.md").write_text("cached a")
        (cache_dir / "file_b.md").write_text("cached b")

        rc = run_clean(workspace)
        assert rc == 0
        # All cache files should be gone
        assert not (cache_dir / "file_a.md").exists()
        assert not (cache_dir / "file_b.md").exists()
        # Index should be reset
        idx = json.loads((workspace / ".fcontext" / "_index.json").read_text())
        assert idx == {}

    def test_clean_resets_index(self, workspace: Path, capsys):
        # Write something into index
        idx_path = workspace / ".fcontext" / "_index.json"
        idx_path.write_text(json.dumps({"some.pdf": {"md": "x.md", "mtime": 0}}))
        rc = run_clean(workspace)
        assert rc == 0
        data = json.loads(idx_path.read_text())
        assert data == {}

    def test_clean_empty_cache(self, workspace: Path, capsys):
        rc = run_clean(workspace)
        assert rc == 0
        out = capsys.readouterr().out
        assert "empty" in out


class TestIndexDir:
    """测试 fcontext index <directory>"""

    def _create_dummy(self, path: Path, name: str) -> Path:
        f = path / name
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(b"%PDF-1.4 dummy")
        return f

    def test_index_dir_scans_only_target(self, workspace: Path, capsys):
        """Only files in the target dir are scanned."""
        docs = workspace / "docs"
        other = workspace / "other"
        self._create_dummy(docs, "a.pdf")
        self._create_dummy(other, "b.pdf")
        capsys.readouterr()

        run_index_dir(workspace, docs)
        out = capsys.readouterr().out
        assert "Found 1 indexable files" in out

    def test_index_dir_not_found(self, workspace: Path):
        fake = workspace / "no_such_dir"
        rc = run_index_dir(workspace, fake)
        assert rc == 1

    def test_index_dir_outside_workspace(self, workspace: Path, tmp_path: Path):
        import tempfile
        with tempfile.TemporaryDirectory() as ext:
            outside = Path(ext)
            rc = run_index_dir(workspace, outside)
            assert rc == 1

    def test_index_dir_recursive(self, workspace: Path, capsys):
        """Subdirectories are included."""
        docs = workspace / "docs"
        self._create_dummy(docs, "top.pdf")
        self._create_dummy(docs / "sub", "nested.pdf")
        capsys.readouterr()

        run_index_dir(workspace, docs)
        out = capsys.readouterr().out
        assert "Found 2 indexable files" in out

    def test_index_dir_skips_hidden(self, workspace: Path, capsys):
        """Hidden dirs inside target are skipped."""
        docs = workspace / "docs"
        self._create_dummy(docs, "visible.pdf")
        self._create_dummy(docs / ".hidden", "secret.pdf")
        capsys.readouterr()

        run_index_dir(workspace, docs)
        out = capsys.readouterr().out
        assert "Found 1 indexable files" in out


class TestIndexText:
    """Text and markdown files should be copied directly to _cache."""

    def test_index_markdown_file(self, workspace: Path):
        """Markdown file should be copied to _cache with source header."""
        md = workspace / "notes.md"
        md.write_text("# My Notes\nSome content here")

        rc = run_index_file(workspace, md)
        assert rc == 0

        # Check cache file exists and has correct content
        cache = workspace / ".fcontext" / "_cache"
        cached = list(cache.glob("notes_*.md"))
        assert len(cached) == 1
        content = cached[0].read_text()
        assert "<!-- source: notes.md -->" in content
        assert "# My Notes" in content
        assert "Some content here" in content

    def test_index_txt_file(self, workspace: Path):
        """Plain text file should be copied to _cache."""
        txt = workspace / "readme.txt"
        txt.write_text("Plain text content")

        rc = run_index_file(workspace, txt)
        assert rc == 0

        cache = workspace / ".fcontext" / "_cache"
        cached = list(cache.glob("readme_*.md"))
        assert len(cached) == 1
        assert "Plain text content" in cached[0].read_text()

    def test_scan_finds_text_files(self, workspace: Path):
        """Scanner should find both binary and text files."""
        (workspace / "doc.pdf").write_bytes(b"%PDF")
        (workspace / "notes.md").write_text("# Notes")
        (workspace / "data.csv").write_text("a,b,c")  # NOT indexable
        (workspace / "code.py").write_text("print(1)")  # NOT indexable

        from fcontext.indexer import _scan_convertible
        files = _scan_convertible(workspace)
        names = {f.name for f in files}
        assert "doc.pdf" in names
        assert "notes.md" in names
        assert "data.csv" not in names
        assert "code.py" not in names

    def test_index_dir_finds_text(self, workspace: Path, capsys):
        """Index dir should find text files alongside binary ones."""
        docs = workspace / "docs"
        docs.mkdir()
        (docs / "spec.pdf").write_bytes(b"%PDF")
        (docs / "notes.md").write_text("# Notes")
        (docs / "data.txt").write_text("data")
        (docs / "config.json").write_text('{}')
        capsys.readouterr()

        run_index_dir(workspace, docs)
        out = capsys.readouterr().out
        assert "Found 3 indexable files" in out  # pdf + md + txt, not json

    def test_text_index_incremental(self, workspace: Path):
        """Second index of unchanged text file should be skipped."""
        md = workspace / "doc.md"
        md.write_text("# Doc")

        rc1 = run_index_file(workspace, md)
        assert rc1 == 0

        rc2 = run_index_file(workspace, md)
        assert rc2 == 0  # up-to-date, not re-copied

    def test_text_index_in_index_json(self, workspace: Path):
        """Text file should appear in _index.json after indexing."""
        md = workspace / "readme.md"
        md.write_text("# README")
        run_index_file(workspace, md)

        idx = json.loads((workspace / ".fcontext" / "_index.json").read_text())
        assert "readme.md" in idx
        assert idx["readme.md"]["md"].startswith(".fcontext/_cache/")

    def test_rst_and_adoc_indexed(self, workspace: Path):
        """RST and AsciiDoc files should be indexable."""
        (workspace / "guide.rst").write_text("Title\n=====\nSome guide")
        (workspace / "manual.adoc").write_text("= Manual\nContent")

        rc1 = run_index_file(workspace, workspace / "guide.rst")
        rc2 = run_index_file(workspace, workspace / "manual.adoc")
        assert rc1 == 0
        assert rc2 == 0

        cache = workspace / ".fcontext" / "_cache"
        assert any("guide" in f.name for f in cache.iterdir())
        assert any("manual" in f.name for f in cache.iterdir())

    def test_json_not_indexed(self, workspace: Path):
        """JSON, YAML, HTML, log etc should NOT be indexable as text."""
        from fcontext.indexer import _scan_convertible
        (workspace / "config.json").write_text('{}')
        (workspace / "config.yaml").write_text("key: value")
        (workspace / "page.html").write_text("<html>")
        (workspace / "app.log").write_text("log line")

        files = _scan_convertible(workspace)
        names = {f.name for f in files}
        assert "config.json" not in names
        assert "config.yaml" not in names
        assert "page.html" not in names
        assert "app.log" not in names


# ── Coverage gap tests for indexer ────────────────────────────────────────────

class TestLoadIndexExisting:
    """Cover _load_index when index file exists — and when it doesn't (L60)."""

    def test_load_existing_index(self, workspace: Path):
        _save_index(workspace, {"test.md": {"md": ".fcontext/_cache/test.md", "mtime": 0}})
        data = _load_index(workspace)
        assert "test.md" in data

    def test_load_index_no_file(self, empty_dir: Path):
        """L60: _load_index returns {} when no _index.json exists."""
        data = _load_index(empty_dir)
        assert data == {}


class TestConvertFileError:
    """Cover _convert_file failure path (L101-103)."""

    def test_convert_file_exception(self, workspace: Path, tmp_path: Path, capsys):
        import sys
        source = tmp_path / "doc.pdf"
        source.write_bytes(b"%PDF-1.4 content")
        cache_path = tmp_path / "output.md"
        # Force ImportError by setting markitdown to None in sys.modules
        real_mod = sys.modules.get("markitdown")
        try:
            sys.modules["markitdown"] = None  # type: ignore
            result = _convert_file(source, cache_path, "doc.pdf")
        finally:
            if real_mod is not None:
                sys.modules["markitdown"] = real_mod
            else:
                sys.modules.pop("markitdown", None)
        assert result is False
        assert "doc.pdf" in capsys.readouterr().err


class TestCopyTextFileError:
    """Cover _copy_text_file error path (L113-115)."""

    def test_copy_text_error(self, workspace: Path, tmp_path: Path, capsys):
        source = tmp_path / "bad.md"
        source.write_text("content")
        cache_path = tmp_path / "output.md"
        with patch("pathlib.Path.read_text", side_effect=PermissionError("denied")):
            result = _copy_text_file(source, cache_path, "bad.md")
        assert result is False
        assert "bad.md" in capsys.readouterr().err


class TestRunIndexFileCachePrint:
    """Cover run_index_file successful caching print (L167: failure path)."""

    def test_index_file_prints_cache_path(self, workspace: Path, capsys):
        md = workspace / "notes.md"
        md.write_text("# Notes")
        capsys.readouterr()
        rc = run_index_file(workspace, md)
        assert rc == 0
        out = capsys.readouterr().out
        assert "cached:" in out

    def test_index_file_returns_1_on_failure(self, workspace: Path, capsys):
        """L167: run_index_file returns 1 when _index_one fails."""
        import sys
        pdf = workspace / "bad.pdf"
        pdf.write_bytes(b"%PDF-1.4 dummy")
        real_mod = sys.modules.get("markitdown")
        try:
            sys.modules["markitdown"] = None  # type: ignore
            rc = run_index_file(workspace, pdf)
        finally:
            if real_mod is not None:
                sys.modules["markitdown"] = real_mod
            else:
                sys.modules.pop("markitdown", None)
        assert rc == 1


class TestRunIndexDirSkipAndFail:
    """Cover index_dir skip-if-up-to-date and failure (L209-212, L227)."""

    def test_index_dir_skips_up_to_date(self, workspace: Path, capsys):
        docs = workspace / "docs"
        docs.mkdir()
        (docs / "notes.md").write_text("# Notes")
        run_index_dir(workspace, docs)
        capsys.readouterr()
        run_index_dir(workspace, docs)
        out = capsys.readouterr().out
        assert "up-to-date" in out

    def test_index_dir_conversion_failure(self, workspace: Path, capsys):
        import sys
        docs = workspace / "docs"
        docs.mkdir()
        (docs / "bad.pdf").write_bytes(b"%PDF-dummy")
        capsys.readouterr()
        real_mod = sys.modules.get("markitdown")
        try:
            sys.modules["markitdown"] = None  # type: ignore
            run_index_dir(workspace, docs)
        finally:
            if real_mod is not None:
                sys.modules["markitdown"] = real_mod
            else:
                sys.modules.pop("markitdown", None)
        out = capsys.readouterr().out
        assert "failed" in out


class TestRunIndexFull:
    """Cover run_index full workspace scan (L238-281)."""

    def test_run_index_with_text_files(self, workspace: Path, capsys):
        (workspace / "notes.md").write_text("# Notes content")
        (workspace / "readme.txt").write_text("Readme content")
        capsys.readouterr()
        rc = run_index(workspace)
        assert rc == 0
        out = capsys.readouterr().out
        assert "Found 2 indexable files" in out
        assert "indexed" in out

    def test_run_index_skips_up_to_date(self, workspace: Path, capsys):
        (workspace / "doc.md").write_text("# Doc")
        run_index(workspace)
        capsys.readouterr()
        run_index(workspace)
        out = capsys.readouterr().out
        assert "up-to-date" in out

    def test_run_index_force_reindexes(self, workspace: Path, capsys):
        (workspace / "doc.md").write_text("# Doc")
        run_index(workspace)
        capsys.readouterr()
        run_index(workspace, force=True)
        out = capsys.readouterr().out
        assert "indexed" in out

    def test_run_index_conversion_failure(self, workspace: Path, capsys):
        import sys
        (workspace / "doc.pdf").write_bytes(b"%PDF-1.4 dummy")
        capsys.readouterr()
        real_mod = sys.modules.get("markitdown")
        try:
            sys.modules["markitdown"] = None  # type: ignore
            rc = run_index(workspace)
        finally:
            if real_mod is not None:
                sys.modules["markitdown"] = real_mod
            else:
                sys.modules.pop("markitdown", None)
        assert rc == 0
        out = capsys.readouterr().out
        assert "failed" in out


class TestRunStatusEdgeCases:
    """Cover run_status stale/orphaned paths (L296-298)."""

    def test_status_shows_stale(self, workspace: Path, capsys):
        md = workspace / "doc.md"
        md.write_text("# Doc")
        run_index_file(workspace, md)
        index = _load_index(workspace)
        for key in index:
            index[key]["mtime"] = 0
        _save_index(workspace, index)
        capsys.readouterr()
        run_status(workspace)
        out = capsys.readouterr().out
        assert "Stale:" in out

    def test_status_shows_orphaned(self, workspace: Path, capsys):
        md = workspace / "doc.md"
        md.write_text("# Doc")
        run_index_file(workspace, md)
        md.unlink()
        capsys.readouterr()
        run_status(workspace)
        out = capsys.readouterr().out
        assert "Orphaned:" in out
        assert "fcontext clean" in out

    def test_status_pending_message(self, workspace: Path, capsys):
        (workspace / "pending.md").write_text("# Pending")
        capsys.readouterr()
        run_status(workspace)
        out = capsys.readouterr().out
        assert "fcontext index" in out


class TestRunCleanWithFiles:
    """Cover run_clean with actual cache files (L310)."""

    def test_clean_with_indexed_files(self, workspace: Path, capsys):
        md = workspace / "doc.md"
        md.write_text("# Doc")
        run_index_file(workspace, md)
        cache = _cache_dir(workspace)
        assert any(cache.iterdir())
        capsys.readouterr()
        rc = run_clean(workspace)
        assert rc == 0
        out = capsys.readouterr().out
        assert "Cleaned:" in out
        assert "1 cached files removed" in out


class TestScanConvertibleSkipsHidden:
    """Cover _scan_convertible hidden file skip (L84)."""

    def test_scan_skips_dotfiles(self, workspace: Path):
        (workspace / ".hidden.md").write_text("secret")
        (workspace / "visible.md").write_text("public")
        files = _scan_convertible(workspace)
        names = {f.name for f in files}
        assert ".hidden.md" not in names
        assert "visible.md" in names


class TestRunIndexDirPrintSummary:
    """Cover run_index_dir print lines (L193: hidden file skip in scan)."""

    def test_index_dir_print_nothing_found(self, workspace: Path, capsys):
        docs = workspace / "docs"
        docs.mkdir()
        (docs / "data.json").write_text('{}')
        capsys.readouterr()
        rc = run_index_dir(workspace, docs)
        assert rc == 0
        out = capsys.readouterr().out
        assert "Found 0 indexable files" in out

    def test_index_dir_skips_dotfiles_in_scan(self, workspace: Path, capsys):
        """L193: Hidden files in index_dir scan loop should be skipped."""
        docs = workspace / "docs"
        docs.mkdir()
        (docs / ".hidden.md").write_text("# Hidden")
        (docs / "visible.md").write_text("# Visible")
        capsys.readouterr()
        rc = run_index_dir(workspace, docs)
        assert rc == 0
        out = capsys.readouterr().out
        assert "Found 1 indexable files" in out
