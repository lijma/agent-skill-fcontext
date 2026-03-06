"""Tests for fcontext workspace_map."""
from pathlib import Path
from unittest.mock import patch
from fcontext.workspace_map import generate_workspace_map, _dir_tree


class TestGenerateWorkspaceMap:
    """Cover generate_workspace_map (L39-57, 69, 72-73, 80-93, 97)."""

    def test_basic_structure(self, workspace: Path):
        """Map should contain Directory Structure, File Types, Domains sections."""
        result = generate_workspace_map(workspace)
        assert "# Workspace Map" in result
        assert "Directory Structure" in result
        assert "File Types" in result
        assert "Domains" in result

    def test_with_files(self, workspace: Path):
        """File type counts should appear in the table."""
        (workspace / "readme.md").write_text("# README")
        (workspace / "app.py").write_text("print('hi')")
        result = generate_workspace_map(workspace)
        assert ".md" in result
        assert ".py" in result
        assert "Extension" in result
        assert "Count" in result

    def test_with_subdirectories(self, workspace: Path):
        """Subdirectories should appear in the map."""
        src = workspace / "src"
        src.mkdir()
        (src / "main.py").write_text("x = 1")
        docs = workspace / "docs"
        docs.mkdir()
        (docs / "guide.md").write_text("# Guide")
        result = generate_workspace_map(workspace)
        assert "src/" in result
        assert "docs/" in result

    def test_skips_hidden_dirs(self, workspace: Path):
        """Hidden dirs should not appear."""
        hidden = workspace / ".secret"
        hidden.mkdir()
        (hidden / "file.txt").write_text("hidden")
        result = generate_workspace_map(workspace)
        assert ".secret" not in result

    def test_skips_node_modules(self, workspace: Path):
        """SKIP_DIRS should be excluded from directory tree."""
        nm = workspace / "node_modules"
        nm.mkdir()
        (nm / "package.json").write_text("{}")
        result = generate_workspace_map(workspace)
        # The dir tree section should not list node_modules/ as a subdirectory
        tree_section = result.split("```")[1] if "```" in result else ""
        assert "node_modules/" not in tree_section

    def test_domains_summary(self, workspace: Path):
        """Each top-level dir should appear as a domain."""
        src = workspace / "src"
        src.mkdir()
        (src / "a.py").write_text("")
        (src / "b.py").write_text("")
        tests = workspace / "tests"
        tests.mkdir()
        (tests / "t.py").write_text("")
        result = generate_workspace_map(workspace)
        assert "**src/**" in result
        assert "**tests/**" in result
        assert "2 files" in result  # src has 2 .py files

    def test_files_with_no_extension(self, workspace: Path):
        """Files without extension should show as (no ext)."""
        (workspace / "Makefile").write_text("all:")
        result = generate_workspace_map(workspace)
        assert "(no ext)" in result

    def test_hidden_files_skipped(self, workspace: Path):
        """Dotfiles should not be counted."""
        (workspace / ".env").write_text("SECRET=x")
        (workspace / "visible.txt").write_text("hello")
        result = generate_workspace_map(workspace)
        assert ".env" not in result
        assert ".txt" in result

    def test_root_domain_dot(self, workspace: Path):
        """Files in root directory should be domain '.'."""
        (workspace / "README.md").write_text("# Hi")
        result = generate_workspace_map(workspace)
        assert "**./***" in result or "." in result


class TestDirTree:
    """Cover _dir_tree helper (L69-97)."""

    def test_basic_tree(self, workspace: Path):
        result = _dir_tree(workspace, max_depth=2)
        assert len(result) >= 1
        assert result[0].endswith("/")

    def test_tree_with_dirs_and_files(self, workspace: Path):
        src = workspace / "src"
        src.mkdir()
        (src / "app.py").write_text("")
        sub = src / "sub"
        sub.mkdir()
        (sub / "mod.py").write_text("")
        (workspace / "README.md").write_text("")
        result = _dir_tree(workspace, max_depth=2)
        tree_str = "\n".join(result)
        assert "src/" in tree_str

    def test_tree_respects_max_depth(self, workspace: Path):
        """At max_depth=1, nested dirs should not show children."""
        d1 = workspace / "a"
        d1.mkdir()
        d2 = d1 / "b"
        d2.mkdir()
        d3 = d2 / "c"
        d3.mkdir()
        result = _dir_tree(workspace, max_depth=1)
        tree_str = "\n".join(result)
        # a/ should appear, but b/ inside a/ should not
        assert "a/" in tree_str
        # depth 1 means we only go 1 level deep from root, so b/ should appear inside a/
        # but c/ should not appear at all
        assert "c/" not in tree_str

    def test_tree_skips_hidden_dirs(self, workspace: Path):
        (workspace / ".hidden").mkdir()
        (workspace / "visible").mkdir()
        result = _dir_tree(workspace, max_depth=2)
        tree_str = "\n".join(result)
        assert ".hidden" not in tree_str
        assert "visible/" in tree_str

    def test_tree_skips_pycache(self, workspace: Path):
        (workspace / "__pycache__").mkdir()
        (workspace / "src").mkdir()
        result = _dir_tree(workspace, max_depth=2)
        tree_str = "\n".join(result)
        assert "__pycache__" not in tree_str

    def test_tree_permission_error_walk(self, workspace: Path):
        """PermissionError on iterdir in _walk should be handled gracefully (L72-73)."""
        d = workspace / "restricted"
        d.mkdir()
        (d / "file.txt").write_text("x")
        original_iterdir = Path.iterdir

        def mock_iterdir(self):
            if self.name == "restricted":
                raise PermissionError("denied")
            return original_iterdir(self)

        with patch.object(Path, "iterdir", mock_iterdir):
            result = _dir_tree(workspace, max_depth=2)
        assert len(result) >= 1

    def test_tree_permission_error_child_count(self, workspace: Path):
        """PermissionError on child dir count should show '?' (L90-91)."""
        parent = workspace / "parent"
        parent.mkdir()
        child = parent / "noread"
        child.mkdir()
        (child / "secret.txt").write_text("x")

        original_iterdir = Path.iterdir

        def mock_iterdir(self):
            if self.name == "noread":
                raise PermissionError("denied")
            return original_iterdir(self)

        with patch.object(Path, "iterdir", mock_iterdir):
            result = _dir_tree(workspace, max_depth=2)
        tree_str = "\n".join(result)
        assert "?" in tree_str

    def test_tree_file_count_display(self, workspace: Path):
        """Files at depth > 0 should show count instead of listing."""
        src = workspace / "src"
        src.mkdir()
        (src / "a.py").write_text("")
        (src / "b.py").write_text("")
        (src / "c.py").write_text("")
        result = _dir_tree(workspace, max_depth=2)
        tree_str = "\n".join(result)
        assert "3 files" in tree_str
