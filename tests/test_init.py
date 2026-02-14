"""Tests for fcontext init."""
from pathlib import Path
from fcontext.init import init_workspace


class TestInit:
    """TASK-002: 测试 init — 目录创建"""

    def test_creates_directory_structure(self, empty_dir: Path):
        init_workspace(empty_dir)
        ctx = empty_dir / ".fcontext"
        assert ctx.is_dir()
        assert (ctx / "_cache").is_dir()
        assert (ctx / "_topics").is_dir()
        assert (ctx / "_requirements").is_dir()
        assert (ctx / "_requirements" / "docs").is_dir()

    def test_creates_gitignore(self, empty_dir: Path):
        init_workspace(empty_dir)
        gi = empty_dir / ".fcontext" / ".gitignore"
        assert gi.exists()
        content = gi.read_text()
        assert "_workspace.map" in content
        assert "_index.json" in content
        assert "ex.csv" not in content
        assert "Git-imported" in content

    def test_creates_readme(self, empty_dir: Path):
        init_workspace(empty_dir)
        readme = empty_dir / ".fcontext" / "_README.md"
        assert readme.exists()
        content = readme.read_text()
        assert empty_dir.name in content
        assert "Key Concepts" in content

    def test_readme_not_overwritten(self, empty_dir: Path):
        init_workspace(empty_dir)
        readme = empty_dir / ".fcontext" / "_README.md"
        readme.write_text("# Custom knowledge\nMy notes")
        init_workspace(empty_dir)  # second init
        assert readme.read_text() == "# Custom knowledge\nMy notes"

    def test_creates_index_json(self, empty_dir: Path):
        init_workspace(empty_dir)
        idx = empty_dir / ".fcontext" / "_index.json"
        assert idx.exists()
        assert idx.read_text() == "{}"

    def test_creates_workspace_map(self, empty_dir: Path):
        init_workspace(empty_dir)
        ws = empty_dir / ".fcontext" / "_workspace.map"
        assert ws.exists()
        assert "Workspace Map" in ws.read_text()

    def test_creates_items_csv(self, empty_dir: Path):
        init_workspace(empty_dir)
        csv = empty_dir / ".fcontext" / "_requirements" / "items.csv"
        assert csv.exists()
        assert "id,type,title" in csv.read_text()

    def test_idempotent(self, empty_dir: Path):
        init_workspace(empty_dir)
        init_workspace(empty_dir)  # should not crash
        assert (empty_dir / ".fcontext").is_dir()
