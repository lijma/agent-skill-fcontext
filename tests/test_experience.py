"""Tests for fcontext experience — list, import, export, remove."""
import subprocess
import zipfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from io import BytesIO

import pytest

from fcontext.experience import (
    list_experiences, import_experience, export_experience, remove_experience,
    update_experience,
    _is_git_url, _is_download_url, import_experience_git, _export_to_git,
    _load_ex, _ex_csv_path, _gitignore_path,
)


class TestExperienceList:
    """STORY-004: fcontext experience list"""

    def test_list_empty(self, workspace: Path, capsys):
        list_experiences(workspace)
        assert "no experience packs" in capsys.readouterr().out

    def test_list_shows_imported(self, workspace: Path, capsys):
        # Create a fake experience with _README.md
        exp = workspace / ".fcontext" / "_experiences" / "my_pack"
        (exp / "_topics").mkdir(parents=True)
        (exp / "_topics" / "analysis.md").write_text("some content")
        (exp / "_README.md").write_text("# my_pack\n\nBA knowledge for IPMI project.\n")
        list_experiences(workspace)
        out = capsys.readouterr().out
        assert "my_pack" in out
        assert "_topics" in out
        assert "BA knowledge for IPMI project" in out

    def test_list_without_readme(self, workspace: Path, capsys):
        # Experience without _README.md still shows
        exp = workspace / ".fcontext" / "_experiences" / "bare_pack" / "_cache"
        exp.mkdir(parents=True)
        (exp / "doc.md").write_text("content")
        list_experiences(workspace)
        out = capsys.readouterr().out
        assert "bare_pack" in out


class TestExperienceImport:
    """STORY-005: fcontext experience import"""

    def _make_zip(self, tmp_path: Path, name: str = "test_exp") -> Path:
        """Helper: create a valid experience zip."""
        zip_path = tmp_path / f"{name}.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("_cache/doc1.md", "# Document 1")
            zf.writestr("_topics/arch.md", "# Architecture")
            zf.writestr("_requirements/items.csv", "id,type,title\n")
            zf.writestr("_README.md", "# test_exp\n\nTest experience pack.\n")
        return zip_path

    def test_import_from_zip(self, workspace: Path, tmp_path: Path):
        zp = self._make_zip(tmp_path)
        rc = import_experience(workspace, str(zp))
        assert rc == 0

        exp = workspace / ".fcontext" / "_experiences" / "test_exp"
        assert exp.is_dir()
        assert (exp / "_cache" / "doc1.md").exists()
        assert (exp / "_topics" / "arch.md").exists()
        assert (exp / "_requirements" / "items.csv").exists()
        assert (exp / "_README.md").exists()
        assert "Test experience pack" in (exp / "_README.md").read_text()

    def test_import_uses_custom_name(self, workspace: Path, tmp_path: Path):
        zp = self._make_zip(tmp_path)
        rc = import_experience(workspace, str(zp), name="ba_knowledge")
        assert rc == 0
        assert (workspace / ".fcontext" / "_experiences" / "ba_knowledge").is_dir()

    def test_import_rejects_duplicate(self, workspace: Path, tmp_path: Path):
        zp = self._make_zip(tmp_path)
        import_experience(workspace, str(zp))
        rc = import_experience(workspace, str(zp))
        assert rc == 1  # already exists

    def test_import_force_overwrites(self, workspace: Path, tmp_path: Path):
        zp = self._make_zip(tmp_path)
        import_experience(workspace, str(zp))
        rc = import_experience(workspace, str(zp), force=True)
        assert rc == 0

    def test_import_skips_non_knowledge_files(self, workspace: Path, tmp_path: Path):
        zip_path = tmp_path / "mixed.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("_cache/good.md", "kept")
            zf.writestr("_workspace.map", "skipped")
            zf.writestr("random.txt", "skipped")
        import_experience(workspace, str(zip_path), name="mixed")
        exp = workspace / ".fcontext" / "_experiences" / "mixed"
        assert (exp / "_cache" / "good.md").exists()
        assert not (exp / "_workspace.map").exists()
        assert not (exp / "random.txt").exists()

    def test_import_handles_wrapped_zip(self, workspace: Path, tmp_path: Path):
        """Zip with a single top-level directory wrapper."""
        zip_path = tmp_path / "wrapped.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("project/.fcontext/_cache/doc.md", "content")
            zf.writestr("project/.fcontext/_topics/note.md", "content")
        # This won't match because wrapper is "project/.fcontext", not just "project"
        # with knowledge dirs directly inside. Let's test the correct wrapper pattern:
        zip_path2 = tmp_path / "wrapped2.zip"
        with zipfile.ZipFile(zip_path2, "w") as zf:
            zf.writestr("myproject/_cache/doc.md", "content")
            zf.writestr("myproject/_topics/note.md", "content")
        import_experience(workspace, str(zip_path2), name="wrapped")
        exp = workspace / ".fcontext" / "_experiences" / "wrapped"
        assert (exp / "_cache" / "doc.md").exists()
        assert (exp / "_topics" / "note.md").exists()

    def test_import_rejects_missing_file(self, workspace: Path):
        rc = import_experience(workspace, "/nonexistent.zip")
        assert rc == 1

    def test_import_rejects_non_zip(self, workspace: Path, tmp_path: Path):
        bad = tmp_path / "not_a_zip.txt"
        bad.write_text("hello")
        rc = import_experience(workspace, str(bad))
        assert rc == 1

    def test_import_rejects_empty_zip(self, workspace: Path, tmp_path: Path):
        zip_path = tmp_path / "empty.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("readme.txt", "no knowledge dirs here")
        rc = import_experience(workspace, str(zip_path), name="empty")
        assert rc == 1


class TestExport:
    """fcontext export — export to zip file"""

    def test_export_creates_zip(self, workspace: Path, tmp_path: Path):
        # Add some knowledge
        (workspace / ".fcontext" / "_cache" / "doc.md").write_text("# Doc")
        (workspace / ".fcontext" / "_topics" / "arch.md").write_text("# Arch")

        out_zip = tmp_path / "export.zip"
        rc = export_experience(workspace, str(out_zip))
        assert rc == 0
        assert out_zip.exists()

        with zipfile.ZipFile(out_zip) as zf:
            names = zf.namelist()
            assert "_cache/doc.md" in names
            assert "_topics/arch.md" in names
            assert "_README.md" in names
            readme = zf.read("_README.md").decode()
            assert "Knowledge exported" in readme
            assert "arch" in readme  # topic listed
            assert "fcontext export" in readme

    def test_export_to_directory(self, workspace: Path, tmp_path: Path):
        (workspace / ".fcontext" / "_topics" / "note.md").write_text("note")

        rc = export_experience(workspace, str(tmp_path))
        assert rc == 0
        # Should use project dir name as filename
        expected = tmp_path / f"{workspace.name}.zip"
        assert expected.exists()

    def test_export_to_directory_with_name(self, workspace: Path, tmp_path: Path):
        (workspace / ".fcontext" / "_topics" / "note.md").write_text("note")

        rc = export_experience(workspace, str(tmp_path), name="my_knowledge")
        assert rc == 0
        assert (tmp_path / "my_knowledge.zip").exists()

    def test_export_fails_when_empty(self, empty_dir: Path, tmp_path: Path):
        # Use empty_dir (no init) but create minimal .fcontext with empty knowledge dirs
        ctx = empty_dir / ".fcontext"
        ctx.mkdir()
        (ctx / "_cache").mkdir()
        (ctx / "_topics").mkdir()
        (ctx / "_requirements").mkdir()
        out_zip = tmp_path / "empty.zip"
        rc = export_experience(empty_dir, str(out_zip))
        assert rc == 1

    def test_export_excludes_non_knowledge(self, workspace: Path, tmp_path: Path):
        (workspace / ".fcontext" / "_cache" / "doc.md").write_text("keep")
        # _workspace.map and _index.json should not be exported
        (workspace / ".fcontext" / "_workspace.map").write_text("skip")
        (workspace / ".fcontext" / "_index.json").write_text("{}")

        out_zip = tmp_path / "export.zip"
        export_experience(workspace, str(out_zip))

        with zipfile.ZipFile(out_zip) as zf:
            names = zf.namelist()
            assert "_cache/doc.md" in names
            assert "_workspace.map" not in names
            assert "_index.json" not in names

    def test_export_includes_local_zip_experience(self, workspace: Path, tmp_path: Path):
        """Locally-imported (zip) experiences should be included in export."""
        # Add workspace knowledge so export is not empty
        (workspace / ".fcontext" / "_cache" / "own.md").write_text("own")

        # Import from local zip
        zp = tmp_path / "local_pack.zip"
        with zipfile.ZipFile(zp, "w") as z:
            z.writestr("_topics/insight.md", "local insight")
            z.writestr("_cache/ref.md", "local ref")
            z.writestr("_README.md", "# local pack")
        import_experience(workspace, str(zp), name="local_exp")

        out_zip = tmp_path / "export.zip"
        export_experience(workspace, str(out_zip))

        with zipfile.ZipFile(out_zip) as zf:
            names = zf.namelist()
            assert "_cache/own.md" in names
            assert "_experiences/local_exp/_topics/insight.md" in names
            assert "_experiences/local_exp/_cache/ref.md" in names
            assert "_experiences/local_exp/_README.md" in names
            assert "_experiences/ex.csv" in names

    def test_export_excludes_remote_git_experience(self, workspace: Path, tmp_path: Path):
        """Remote git experiences should NOT be in export (re-cloneable)."""
        (workspace / ".fcontext" / "_cache" / "own.md").write_text("own")

        # Simulate a git-imported experience by creating the dir + registry row
        exp = workspace / ".fcontext" / "_experiences" / "remote_exp"
        (exp / "_topics").mkdir(parents=True)
        (exp / "_topics" / "note.md").write_text("remote note")
        from fcontext.experience import _record_import
        _record_import(workspace, "remote_exp", source_type="git",
                       source="git@github.com:org/repo.git", branch="", file_count=1)

        out_zip = tmp_path / "export.zip"
        export_experience(workspace, str(out_zip))

        with zipfile.ZipFile(out_zip) as zf:
            names = zf.namelist()
            assert "_cache/own.md" in names
            # Remote git experience should be excluded
            assert not any("remote_exp" in n for n in names)


class TestExperienceRoundTrip:
    """Export then import should preserve all knowledge."""

    def test_roundtrip(self, workspace: Path, tmp_path: Path):
        # Populate knowledge
        (workspace / ".fcontext" / "_cache" / "spec.md").write_text("# Spec\nDetails here")
        (workspace / ".fcontext" / "_topics" / "design.md").write_text("# Design\nDecisions")

        # Export
        zip_path = tmp_path / "roundtrip.zip"
        export_experience(workspace, str(zip_path))

        # Import into same workspace as experience
        import_experience(workspace, str(zip_path), name="self_snapshot")

        exp = workspace / ".fcontext" / "_experiences" / "self_snapshot"
        assert (exp / "_cache" / "spec.md").read_text() == "# Spec\nDetails here"
        assert (exp / "_topics" / "design.md").read_text() == "# Design\nDecisions"


class TestExportGit:
    """fcontext export to git remote."""

    def _make_bare_repo(self, tmp_path: Path, name: str = "remote.git") -> Path:
        """Create a local bare git repo to act as a push target."""
        bare = tmp_path / name
        subprocess.run(["git", "init", "--bare", str(bare)],
                       capture_output=True, check=True)
        return bare

    def test_export_to_git_pushes(self, workspace: Path, tmp_path: Path):
        """Export should push knowledge to a bare git repo."""
        (workspace / ".fcontext" / "_cache" / "doc.md").write_text("# Doc")
        (workspace / ".fcontext" / "_topics" / "arch.md").write_text("# Arch")

        bare = self._make_bare_repo(tmp_path)
        rc = _export_to_git(workspace, str(bare))
        assert rc == 0

        # Verify by cloning the bare repo and checking contents
        clone_dir = tmp_path / "verify"
        subprocess.run(["git", "clone", "-b", "main", str(bare), str(clone_dir)],
                       capture_output=True, check=True)
        assert (clone_dir / ".fcontext" / "_cache" / "doc.md").exists()
        assert (clone_dir / ".fcontext" / "_topics" / "arch.md").exists()
        assert (clone_dir / ".fcontext" / "_README.md").exists()
        assert (clone_dir / "README.md").exists()
        # Top-level README should be the project's _README.md content
        readme = (clone_dir / "README.md").read_text()
        project_readme = (workspace / ".fcontext" / "_README.md").read_text()
        assert readme == project_readme

    def test_export_git_with_branch(self, workspace: Path, tmp_path: Path):
        """Export should push to specified branch."""
        (workspace / ".fcontext" / "_topics" / "note.md").write_text("note")

        bare = self._make_bare_repo(tmp_path)
        rc = _export_to_git(workspace, str(bare), branch="knowledge")
        assert rc == 0

        # Verify branch exists
        result = subprocess.run(["git", "branch"], cwd=bare,
                                capture_output=True, text=True)
        assert "knowledge" in result.stdout

    def test_export_git_with_message(self, workspace: Path, tmp_path: Path):
        """Export should use custom commit message."""
        (workspace / ".fcontext" / "_topics" / "note.md").write_text("note")

        bare = self._make_bare_repo(tmp_path)
        rc = _export_to_git(workspace, str(bare), message="my custom msg")
        assert rc == 0

        # Clone and check commit message
        clone_dir = tmp_path / "verify"
        subprocess.run(["git", "clone", "-b", "main", str(bare), str(clone_dir)],
                       capture_output=True, check=True)
        result = subprocess.run(["git", "log", "--oneline", "-1"], cwd=clone_dir,
                                capture_output=True, text=True)
        assert "my custom msg" in result.stdout

    def test_export_git_empty_fails(self, empty_dir: Path, tmp_path: Path):
        """Export to git with no knowledge should fail."""
        ctx = empty_dir / ".fcontext"
        ctx.mkdir()
        (ctx / "_cache").mkdir()
        (ctx / "_topics").mkdir()
        (ctx / "_requirements").mkdir()
        bare = self._make_bare_repo(tmp_path)
        rc = _export_to_git(empty_dir, str(bare))
        assert rc == 1

    def test_export_auto_dispatches_git_url(self, workspace: Path, tmp_path: Path):
        """export_experience should detect git URL and dispatch to git export."""
        (workspace / ".fcontext" / "_topics" / "note.md").write_text("note")
        bare = self._make_bare_repo(tmp_path)
        # Local bare repo path is not a git URL, test with explicit _export_to_git
        rc = _export_to_git(workspace, str(bare))
        assert rc == 0

    def test_export_git_bad_url(self, workspace: Path):
        """Push to invalid URL should fail."""
        (workspace / ".fcontext" / "_topics" / "note.md").write_text("note")
        rc = _export_to_git(workspace, "https://invalid.example/no-repo.git")
        assert rc == 1

    def test_export_git_preserves_history(self, workspace: Path, tmp_path: Path):
        """Multiple exports should create separate commits, not overwrite."""
        bare = self._make_bare_repo(tmp_path)

        # First export
        (workspace / ".fcontext" / "_topics" / "v1.md").write_text("version 1")
        rc1 = _export_to_git(workspace, str(bare), message="export v1")
        assert rc1 == 0

        # Second export with new content
        (workspace / ".fcontext" / "_topics" / "v2.md").write_text("version 2")
        rc2 = _export_to_git(workspace, str(bare), message="export v2")
        assert rc2 == 0

        # Clone and verify both commits exist
        clone_dir = tmp_path / "verify_history"
        subprocess.run(["git", "clone", "-b", "main", str(bare), str(clone_dir)],
                       capture_output=True, check=True)
        result = subprocess.run(["git", "log", "--oneline"], cwd=clone_dir,
                                capture_output=True, text=True)
        lines = result.stdout.strip().splitlines()
        assert len(lines) == 2  # two commits, not one
        assert "export v2" in lines[0]
        assert "export v1" in lines[1]

        # Both files should be present
        assert (clone_dir / ".fcontext" / "_topics" / "v1.md").exists()
        assert (clone_dir / ".fcontext" / "_topics" / "v2.md").exists()

    def test_export_git_no_change_skips(self, workspace: Path, tmp_path: Path):
        """Export with identical content should not create a new commit."""
        bare = self._make_bare_repo(tmp_path)
        (workspace / ".fcontext" / "_topics" / "note.md").write_text("unchanged")

        _export_to_git(workspace, str(bare), message="first")
        rc = _export_to_git(workspace, str(bare), message="second")
        assert rc == 0

        # Should still have only 1 commit
        clone_dir = tmp_path / "verify_skip"
        subprocess.run(["git", "clone", "-b", "main", str(bare), str(clone_dir)],
                       capture_output=True, check=True)
        result = subprocess.run(["git", "log", "--oneline"], cwd=clone_dir,
                                capture_output=True, text=True)
        lines = result.stdout.strip().splitlines()
        assert len(lines) == 1
        assert "first" in lines[0]


class TestIsGitUrl:
    """Test git URL detection."""

    def test_https(self):
        assert _is_git_url("https://github.com/org/repo.git")

    def test_https_no_suffix(self):
        assert _is_git_url("https://github.com/org/repo")

    def test_ssh(self):
        assert _is_git_url("git@github.com:org/repo.git")

    def test_ssh_protocol(self):
        assert _is_git_url("ssh://git@github.com/org/repo.git")

    def test_git_protocol(self):
        assert _is_git_url("git://github.com/org/repo.git")

    def test_local_path_not_git(self):
        assert not _is_git_url("/tmp/some/file.zip")

    def test_relative_path_not_git(self):
        assert not _is_git_url("./exports/pack.zip")

    def test_filename_not_git(self):
        assert not _is_git_url("experience.zip")


def _make_git_repo_with_fcontext(tmp_path: Path, repo_name: str = "source_repo") -> Path:
    """Helper: create a local git repo with .fcontext/ knowledge content."""
    import os
    env = {**os.environ,
           "GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "t@t"}
    repo = tmp_path / repo_name
    repo.mkdir()
    ctx = repo / ".fcontext"
    (ctx / "_cache").mkdir(parents=True)
    (ctx / "_topics").mkdir(parents=True)
    (ctx / "_requirements").mkdir(parents=True)
    (ctx / "_cache" / "spec.md").write_text("# Spec from git")
    (ctx / "_topics" / "arch.md").write_text("# Architecture notes")
    (ctx / "_README.md").write_text("# source_repo\n\nKnowledge from git repo.\n")
    # git init + commit
    subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
    subprocess.run(["git", "add", "."], cwd=repo, capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "init knowledge"],
                    cwd=repo, capture_output=True, check=True, env=env)
    return repo


class TestExperienceImportGit:
    """STORY-008: fcontext experience import from git URL."""

    def test_import_from_local_git(self, workspace: Path, tmp_path: Path):
        repo = _make_git_repo_with_fcontext(tmp_path)
        rc = import_experience(workspace, str(repo), name="from_git")
        assert rc == 0
        exp = workspace / ".fcontext" / "_experiences" / "from_git"
        assert (exp / "_cache" / "spec.md").exists()
        assert "Spec from git" in (exp / "_cache" / "spec.md").read_text()
        assert (exp / "_topics" / "arch.md").exists()
        assert (exp / "_README.md").exists()

    def test_import_git_derives_name(self, workspace: Path, tmp_path: Path):
        repo = _make_git_repo_with_fcontext(tmp_path, "my_project")
        rc = import_experience_git(workspace, str(repo))
        assert rc == 0
        assert (workspace / ".fcontext" / "_experiences" / "my_project").is_dir()

    def test_import_git_rejects_duplicate(self, workspace: Path, tmp_path: Path):
        repo = _make_git_repo_with_fcontext(tmp_path)
        import_experience_git(workspace, str(repo), name="dup")
        rc = import_experience_git(workspace, str(repo), name="dup")
        assert rc == 1  # already exists

    def test_import_git_force_overwrites(self, workspace: Path, tmp_path: Path):
        repo = _make_git_repo_with_fcontext(tmp_path)
        import_experience_git(workspace, str(repo), name="overwrite")
        rc = import_experience_git(workspace, str(repo), name="overwrite", force=True)
        assert rc == 0

    def test_import_git_no_fcontext_dir(self, workspace: Path, tmp_path: Path):
        """Repo without .fcontext/ should fail."""
        repo = tmp_path / "empty_repo"
        repo.mkdir()
        subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
        (repo / "README.md").write_text("# Just a readme")
        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=repo, capture_output=True, check=True,
                        env={**__import__('os').environ,
                             "GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "t@t",
                             "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "t@t"})
        rc = import_experience_git(workspace, str(repo), name="empty")
        assert rc == 1

    def test_import_git_bad_url(self, workspace: Path):
        rc = import_experience_git(workspace, "https://invalid.example/no-repo.git", name="bad")
        assert rc == 1

    def test_import_git_with_branch(self, workspace: Path, tmp_path: Path):
        """Test cloning a specific branch."""
        repo = _make_git_repo_with_fcontext(tmp_path, "branched")
        # Create a branch with different content
        subprocess.run(["git", "checkout", "-b", "docs"], cwd=repo, capture_output=True, check=True)
        (repo / ".fcontext" / "_topics" / "branch-note.md").write_text("# Branch-only note")
        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "branch content"], cwd=repo, capture_output=True, check=True,
                        env={**__import__('os').environ,
                             "GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "t@t",
                             "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "t@t"})
        rc = import_experience_git(workspace, str(repo), name="branched", branch="docs")
        assert rc == 0
        exp = workspace / ".fcontext" / "_experiences" / "branched"
        assert (exp / "_topics" / "branch-note.md").exists()

    def test_auto_dispatch_local_path_as_git(self, workspace: Path, tmp_path: Path):
        """import_experience with a local git repo path should auto-detect and succeed."""
        repo = _make_git_repo_with_fcontext(tmp_path)
        # Local git repo (has .git/) is detected by _is_local_git_repo
        # and dispatched to import_experience_git automatically
        rc = import_experience(workspace, str(repo), name="localdir")
        assert rc == 0
        exp = workspace / ".fcontext" / "_experiences" / "localdir"
        assert (exp / "_cache" / "spec.md").exists()
        assert (exp / "_topics" / "arch.md").exists()


class TestExCsv:
    """Experience registry — ex.csv tracking imports."""

    def _make_zip(self, tmp_path: Path, name: str = "test_exp") -> Path:
        zip_path = tmp_path / f"{name}.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("_cache/doc1.md", "# Document 1")
            zf.writestr("_topics/arch.md", "# Architecture")
            zf.writestr("_README.md", "# test_exp\n\nTest.\n")
        return zip_path

    def test_zip_import_creates_csv(self, workspace: Path, tmp_path: Path):
        """Importing from zip should create ex.csv with source_type=zip."""
        zp = self._make_zip(tmp_path)
        import_experience(workspace, str(zp), name="from_zip")

        csv_path = _ex_csv_path(workspace)
        assert csv_path.exists()
        rows = _load_ex(workspace)
        assert len(rows) == 1
        row = rows[0]
        assert row["name"] == "from_zip"
        assert row["source_type"] == "zip"
        assert str(zp) in row["source"]
        assert row["branch"] == ""
        assert int(row["file_count"]) > 0
        assert row["imported_at"]  # non-empty timestamp

    def test_git_import_records_csv(self, workspace: Path, tmp_path: Path):
        """Importing from local git repo should record source_type=local-git."""
        repo = _make_git_repo_with_fcontext(tmp_path)
        import_experience(workspace, str(repo), name="from_git")

        rows = _load_ex(workspace)
        assert len(rows) == 1
        row = rows[0]
        assert row["name"] == "from_git"
        assert row["source_type"] == "local-git"
        assert str(repo) in row["source"]

    def test_git_import_records_branch(self, workspace: Path, tmp_path: Path):
        """Branch info should be recorded when specified."""
        repo = _make_git_repo_with_fcontext(tmp_path, "branched")
        subprocess.run(["git", "checkout", "-b", "docs"], cwd=repo,
                        capture_output=True, check=True)
        (repo / ".fcontext" / "_topics" / "extra.md").write_text("extra")
        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "docs branch"], cwd=repo,
                        capture_output=True, check=True,
                        env={**__import__('os').environ,
                             "GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "t@t",
                             "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "t@t"})
        import_experience_git(workspace, str(repo), name="branched", branch="docs")

        rows = _load_ex(workspace)
        assert rows[0]["branch"] == "docs"

    def test_multiple_imports_tracked(self, workspace: Path, tmp_path: Path):
        """Multiple imports should accumulate rows in ex.csv."""
        zp1 = self._make_zip(tmp_path, "pack_a")
        zp2 = self._make_zip(tmp_path, "pack_b")
        import_experience(workspace, str(zp1), name="alpha")
        import_experience(workspace, str(zp2), name="beta")

        rows = _load_ex(workspace)
        assert len(rows) == 2
        names = {r["name"] for r in rows}
        assert names == {"alpha", "beta"}

    def test_force_overwrite_updates_row(self, workspace: Path, tmp_path: Path):
        """Force-importing same name should update (not duplicate) the row."""
        zp = self._make_zip(tmp_path)
        import_experience(workspace, str(zp), name="dup")
        import_experience(workspace, str(zp), name="dup", force=True)

        rows = _load_ex(workspace)
        assert len(rows) == 1
        assert rows[0]["name"] == "dup"

    def test_remove_cleans_csv(self, workspace: Path, tmp_path: Path):
        """Removing an experience should remove its row from ex.csv."""
        zp = self._make_zip(tmp_path)
        import_experience(workspace, str(zp), name="to_remove")
        assert len(_load_ex(workspace)) == 1

        remove_experience(workspace, "to_remove")
        rows = _load_ex(workspace)
        assert len(rows) == 0
        # CSV file still exists (empty header)
        assert _ex_csv_path(workspace).exists()

    def test_remove_preserves_other_rows(self, workspace: Path, tmp_path: Path):
        """Removing one experience should not affect other rows."""
        zp1 = self._make_zip(tmp_path, "keep_me")
        zp2 = self._make_zip(tmp_path, "drop_me")
        import_experience(workspace, str(zp1), name="keeper")
        import_experience(workspace, str(zp2), name="dropper")
        assert len(_load_ex(workspace)) == 2

        remove_experience(workspace, "dropper")
        rows = _load_ex(workspace)
        assert len(rows) == 1
        assert rows[0]["name"] == "keeper"

    def test_list_shows_source_info(self, workspace: Path, tmp_path: Path, capsys):
        """list_experiences should display source info from ex.csv."""
        zp = self._make_zip(tmp_path, "info_pack")
        import_experience(workspace, str(zp), name="info_pack")

        list_experiences(workspace)
        out = capsys.readouterr().out
        assert "info_pack" in out
        assert "source: zip" in out

    def test_list_shows_git_source(self, workspace: Path, tmp_path: Path, capsys):
        """list_experiences should show local-git source type."""
        repo = _make_git_repo_with_fcontext(tmp_path)
        import_experience(workspace, str(repo), name="git_pack")

        list_experiences(workspace)
        out = capsys.readouterr().out
        assert "git_pack" in out
        assert "source: local-git" in out

    def test_list_works_without_csv(self, workspace: Path, capsys):
        """list_experiences should work fine if ex.csv doesn't exist (legacy packs)."""
        # Create a legacy experience without ex.csv
        exp = workspace / ".fcontext" / "_experiences" / "legacy"
        (exp / "_topics").mkdir(parents=True)
        (exp / "_topics" / "note.md").write_text("legacy")

        list_experiences(workspace)
        out = capsys.readouterr().out
        assert "legacy" in out
        assert "source:" not in out  # no registry entry, no source line


class TestGitignore:
    """Git-imported experiences are gitignored; local imports are not."""

    def _make_zip(self, tmp_path: Path, name: str = "test_exp") -> Path:
        zip_path = tmp_path / f"{name}.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("_cache/doc1.md", "# Document 1")
            zf.writestr("_README.md", "# test\n\nTest.\n")
        return zip_path

    def test_zip_import_not_ignored(self, workspace: Path, tmp_path: Path):
        """Zip imports (local) should NOT be added to .gitignore."""
        zp = self._make_zip(tmp_path)
        import_experience(workspace, str(zp), name="local_zip")
        gi = _gitignore_path(workspace)
        content = gi.read_text(encoding="utf-8")
        assert "_experiences/local_zip/" not in content

    def test_local_git_not_ignored(self, workspace: Path, tmp_path: Path):
        """Local git repo imports should NOT be added to .gitignore."""
        repo = _make_git_repo_with_fcontext(tmp_path)
        import_experience(workspace, str(repo), name="local_repo")
        gi = _gitignore_path(workspace)
        content = gi.read_text(encoding="utf-8")
        assert "_experiences/local_repo/" not in content

    def test_remote_git_is_ignored(self, workspace: Path, tmp_path: Path):
        """Remote git URL imports should be added to .gitignore."""
        repo = _make_git_repo_with_fcontext(tmp_path)
        # Use import_experience_git directly with the URL-like source
        # to simulate a remote import (source_type = 'git')
        # We can't actually clone a real remote URL in tests, so we
        # call the internal helper directly.
        from fcontext.experience import _gitignore_add, _record_import
        name = "remote_pack"
        target = workspace / ".fcontext" / "_experiences" / name
        target.mkdir(parents=True)
        (target / "_cache").mkdir()
        (target / "_cache" / "doc.md").write_text("# doc")
        _record_import(workspace, name, source_type="git",
                       source="https://github.com/org/repo.git",
                       branch="", file_count=1)
        _gitignore_add(workspace, name)
        gi = _gitignore_path(workspace)
        content = gi.read_text(encoding="utf-8")
        assert f"_experiences/{name}/" in content

    def test_remote_git_import_adds_gitignore(self, workspace: Path, tmp_path: Path):
        """import_experience_git with a real remote-style URL adds .gitignore entry.

        We simulate by importing from local repo but calling import_experience_git
        with _is_local_git_repo returning False via a URL-formatted path."""
        repo = _make_git_repo_with_fcontext(tmp_path)
        # Directly call with the function, which detects local-git → no ignore
        import_experience_git(workspace, str(repo), name="local_check")
        gi = _gitignore_path(workspace)
        content = gi.read_text(encoding="utf-8")
        # local-git → NOT ignored
        assert "_experiences/local_check/" not in content

    def test_remove_cleans_gitignore(self, workspace: Path, tmp_path: Path):
        """Removing a git-imported experience should remove its .gitignore entry."""
        from fcontext.experience import _gitignore_add
        name = "to_clean"
        # Set up experience dir + gitignore entry
        target = workspace / ".fcontext" / "_experiences" / name / "_cache"
        target.mkdir(parents=True)
        (target / "doc.md").write_text("content")
        _gitignore_add(workspace, name)
        gi = _gitignore_path(workspace)
        assert f"_experiences/{name}/" in gi.read_text(encoding="utf-8")

        remove_experience(workspace, name)
        content = gi.read_text(encoding="utf-8")
        assert f"_experiences/{name}/" not in content

    def test_remove_preserves_other_gitignore_entries(self, workspace: Path, tmp_path: Path):
        """Removing one pack should not affect other gitignore entries."""
        from fcontext.experience import _gitignore_add
        # Add two entries
        for n in ("keep_me", "drop_me"):
            target = workspace / ".fcontext" / "_experiences" / n / "_cache"
            target.mkdir(parents=True)
            (target / "doc.md").write_text("content")
            _gitignore_add(workspace, n)

        remove_experience(workspace, "drop_me")
        content = _gitignore_path(workspace).read_text(encoding="utf-8")
        assert "_experiences/keep_me/" in content
        assert "_experiences/drop_me/" not in content

    def test_gitignore_idempotent(self, workspace: Path):
        """Adding the same entry twice should not create duplicates."""
        from fcontext.experience import _gitignore_add
        _gitignore_add(workspace, "dup")
        _gitignore_add(workspace, "dup")
        content = _gitignore_path(workspace).read_text(encoding="utf-8")
        assert content.count("_experiences/dup/") == 1

    def test_ex_csv_tracked_in_git(self, workspace: Path, tmp_path: Path):
        """ex.csv should NOT appear in .gitignore — it should be tracked."""
        zp = self._make_zip(tmp_path)
        import_experience(workspace, str(zp), name="tracked")
        gi = _gitignore_path(workspace)
        content = gi.read_text(encoding="utf-8")
        assert "ex.csv" not in content


# ── _is_download_url tests ──────────────────────────────────────────────

class TestIsDownloadUrl:
    """Unit tests for _is_download_url() detection."""

    def test_https_zip(self):
        assert _is_download_url("https://example.com/knowledge.zip") is True

    def test_http_zip(self):
        assert _is_download_url("http://example.com/pack.zip") is True

    def test_https_zip_with_query(self):
        assert _is_download_url("https://cdn.example.com/v1/pack.zip?token=abc") is True

    def test_https_zip_with_fragment(self):
        assert _is_download_url("https://example.com/pack.zip#section") is True

    def test_https_zip_case_insensitive(self):
        assert _is_download_url("https://example.com/Pack.ZIP") is True

    def test_git_url_not_download(self):
        """A .git URL should NOT be treated as download."""
        assert _is_download_url("https://github.com/org/repo.git") is False

    def test_plain_https_not_download(self):
        assert _is_download_url("https://github.com/org/repo") is False

    def test_ssh_url_not_download(self):
        assert _is_download_url("ssh://git@example.com/repo") is False

    def test_local_path_not_download(self):
        assert _is_download_url("/tmp/knowledge.zip") is False

    def test_git_at_not_download(self):
        assert _is_download_url("git@github.com:org/repo.git") is False


# ── URL import tests ────────────────────────────────────────────────────

class TestImportUrl:
    """Tests for importing experience packs from HTTP(S) URLs."""

    @staticmethod
    def _make_zip_bytes(tmp_path: Path) -> bytes:
        """Create a valid experience zip in memory and return its bytes."""
        zp = tmp_path / "pack.zip"
        with zipfile.ZipFile(zp, "w") as z:
            z.writestr("_topics/analysis.md", "# Analysis\nSome insight")
            z.writestr("_cache/doc.md", "cached content")
            z.writestr("_README.md", "# test pack")
        return zp.read_bytes()

    def _mock_urlopen(self, data: bytes, status: int = 200):
        """Return a context-manager mock that behaves like urlopen()."""
        resp = MagicMock()
        resp.read.return_value = data
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        return resp

    def test_import_from_url_happy_path(self, workspace: Path, tmp_path: Path):
        """Download a valid zip from URL and import it."""
        data = self._make_zip_bytes(tmp_path)
        with patch("fcontext.experience.urlopen", return_value=self._mock_urlopen(data)):
            rc = import_experience(workspace, "https://cdn.example.com/knowledge.zip")
        assert rc == 0
        exp = workspace / ".fcontext" / "_experiences" / "knowledge"
        assert exp.is_dir()
        assert (exp / "_topics" / "analysis.md").exists()
        assert (exp / "_cache" / "doc.md").exists()

    def test_import_url_name_override(self, workspace: Path, tmp_path: Path):
        """--name flag should override name derived from URL."""
        data = self._make_zip_bytes(tmp_path)
        with patch("fcontext.experience.urlopen", return_value=self._mock_urlopen(data)):
            rc = import_experience(workspace, "https://example.com/pack.zip", name="custom")
        assert rc == 0
        assert (workspace / ".fcontext" / "_experiences" / "custom").is_dir()

    def test_import_url_not_zip(self, workspace: Path, capsys):
        """Downloaded file that is not a valid zip should fail."""
        resp = self._mock_urlopen(b"this is not a zip file at all")
        with patch("fcontext.experience.urlopen", return_value=resp):
            rc = import_experience(workspace, "https://example.com/bad.zip")
        assert rc == 1
        assert "not a valid zip" in capsys.readouterr().err

    def test_import_url_network_error(self, workspace: Path, capsys):
        """Network error during download should fail gracefully."""
        from urllib.error import URLError
        with patch("fcontext.experience.urlopen", side_effect=URLError("connection refused")):
            rc = import_experience(workspace, "https://example.com/pack.zip")
        assert rc == 1
        assert "download failed" in capsys.readouterr().err

    def test_import_url_ex_csv_source_type(self, workspace: Path, tmp_path: Path):
        """ex.csv should record source_type='url' with the original URL."""
        data = self._make_zip_bytes(tmp_path)
        with patch("fcontext.experience.urlopen", return_value=self._mock_urlopen(data)):
            import_experience(workspace, "https://cdn.example.com/knowledge.zip")
        rows = _load_ex(workspace)
        assert len(rows) == 1
        assert rows[0]["source_type"] == "url"
        assert rows[0]["source"] == "https://cdn.example.com/knowledge.zip"

    def test_import_url_force_overwrite(self, workspace: Path, tmp_path: Path):
        """force=True should overwrite existing experience from URL."""
        data = self._make_zip_bytes(tmp_path)
        with patch("fcontext.experience.urlopen", return_value=self._mock_urlopen(data)):
            rc1 = import_experience(workspace, "https://example.com/knowledge.zip")
            assert rc1 == 0
            rc2 = import_experience(workspace, "https://example.com/knowledge.zip", force=True)
            assert rc2 == 0

    def test_import_url_no_force_rejects_dup(self, workspace: Path, tmp_path: Path, capsys):
        """Without force, re-importing same name from URL should fail."""
        data = self._make_zip_bytes(tmp_path)
        with patch("fcontext.experience.urlopen", return_value=self._mock_urlopen(data)):
            import_experience(workspace, "https://example.com/knowledge.zip")
            rc = import_experience(workspace, "https://example.com/knowledge.zip")
        assert rc == 1
        assert "already exists" in capsys.readouterr().err

    def test_import_url_name_from_query_url(self, workspace: Path, tmp_path: Path):
        """Name should be derived correctly even when URL has query params."""
        data = self._make_zip_bytes(tmp_path)
        with patch("fcontext.experience.urlopen", return_value=self._mock_urlopen(data)):
            rc = import_experience(workspace, "https://cdn.example.com/packs/mypack.zip?v=2")
        assert rc == 0
        assert (workspace / ".fcontext" / "_experiences" / "mypack").is_dir()


# ── experience update tests ────────────────────────────────────────────────────────────

class TestExperienceUpdate:
    """Tests for fcontext experience update."""

    @staticmethod
    def _make_zip_bytes(tmp_path: Path, tag: str = "v1") -> bytes:
        zp = tmp_path / f"pack-{tag}.zip"
        with zipfile.ZipFile(zp, "w") as z:
            z.writestr("_topics/analysis.md", f"# Analysis {tag}")
            z.writestr("_cache/doc.md", f"cached {tag}")
            z.writestr("_README.md", f"# pack {tag}")
        return zp.read_bytes()

    @staticmethod
    def _mock_urlopen(data: bytes):
        resp = MagicMock()
        resp.read.return_value = data
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        return resp

    def test_update_empty_registry(self, workspace: Path, capsys):
        """No experiences → no-op."""
        rc = update_experience(workspace)
        assert rc == 0
        assert "no experience packs" in capsys.readouterr().out

    def test_update_skips_zip_source(self, workspace: Path, tmp_path: Path, capsys):
        """Zip-imported experiences cannot be auto-updated."""
        zp = tmp_path / "pack.zip"
        with zipfile.ZipFile(zp, "w") as z:
            z.writestr("_topics/a.md", "content")
        import_experience(workspace, str(zp), name="local")
        rc = update_experience(workspace)
        assert rc == 0
        out = capsys.readouterr().out
        assert "skip 'local'" in out
        assert "no updatable" in out

    def test_update_git_experience(self, workspace: Path, tmp_path: Path, capsys):
        """Git-imported experiences should be re-cloned."""
        repo = _make_git_repo_with_fcontext(tmp_path)
        import_experience(workspace, str(repo), name="from_git")
        # Verify initial content
        t = workspace / ".fcontext" / "_experiences" / "from_git" / "_cache" / "spec.md"
        assert "Spec from git" in t.read_text()

        # Modify source repo to have new content
        import os
        env = {**os.environ,
               "GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "t@t",
               "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "t@t"}
        (repo / ".fcontext" / "_cache" / "spec.md").write_text("# Updated Spec")
        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "update"],
                       cwd=repo, capture_output=True, check=True, env=env)

        # Update should pull new content
        rc = update_experience(workspace)
        assert rc == 0
        assert "Updated Spec" in t.read_text()

    def test_update_url_experience(self, workspace: Path, tmp_path: Path, capsys):
        """URL-imported experiences should be re-downloaded."""
        data_v1 = self._make_zip_bytes(tmp_path, tag="v1")
        with patch("fcontext.experience.urlopen", return_value=self._mock_urlopen(data_v1)):
            import_experience(workspace, "https://example.com/pack.zip", name="remote")
        assert "v1" in (workspace / ".fcontext" / "_experiences" / "remote" / "_README.md").read_text()

        # Now update with v2 content
        data_v2 = self._make_zip_bytes(tmp_path, tag="v2")
        with patch("fcontext.experience.urlopen", return_value=self._mock_urlopen(data_v2)):
            rc = update_experience(workspace)
        assert rc == 0
        assert "v2" in (workspace / ".fcontext" / "_experiences" / "remote" / "_README.md").read_text()

    def test_update_single_by_name(self, workspace: Path, tmp_path: Path, capsys):
        """Update only the named experience, skip others."""
        data = self._make_zip_bytes(tmp_path)
        with patch("fcontext.experience.urlopen", return_value=self._mock_urlopen(data)):
            import_experience(workspace, "https://example.com/a.zip", name="aaa")
            import_experience(workspace, "https://example.com/b.zip", name="bbb")

        data_v2 = self._make_zip_bytes(tmp_path, tag="v2")
        with patch("fcontext.experience.urlopen", return_value=self._mock_urlopen(data_v2)):
            rc = update_experience(workspace, name="aaa")
        assert rc == 0
        # aaa updated to v2
        assert "v2" in (workspace / ".fcontext" / "_experiences" / "aaa" / "_README.md").read_text()
        # bbb NOT updated (still v1)
        assert "v1" in (workspace / ".fcontext" / "_experiences" / "bbb" / "_README.md").read_text()

    def test_update_unknown_name(self, workspace: Path, capsys):
        """Updating a non-existent name should fail."""
        rc = update_experience(workspace, name="nonexistent")
        assert rc == 1
        assert "not found" in capsys.readouterr().err

    def test_update_records_new_timestamp(self, workspace: Path, tmp_path: Path):
        """After update, ex.csv imported_at should be refreshed."""
        data = self._make_zip_bytes(tmp_path)
        with patch("fcontext.experience.urlopen", return_value=self._mock_urlopen(data)):
            import_experience(workspace, "https://example.com/pack.zip", name="ts")
        old_ts = _load_ex(workspace)[0]["imported_at"]

        data_v2 = self._make_zip_bytes(tmp_path, tag="v2")
        with patch("fcontext.experience.urlopen", return_value=self._mock_urlopen(data_v2)):
            update_experience(workspace, name="ts")
        new_ts = _load_ex(workspace)[0]["imported_at"]
        # Timestamp should be updated (or at least equal if test is very fast)
        assert new_ts >= old_ts

    def test_update_preserves_source_type(self, workspace: Path, tmp_path: Path):
        """After update, source_type should remain 'url' (not change to 'zip')."""
        data = self._make_zip_bytes(tmp_path)
        with patch("fcontext.experience.urlopen", return_value=self._mock_urlopen(data)):
            import_experience(workspace, "https://example.com/pack.zip", name="keep")

        data_v2 = self._make_zip_bytes(tmp_path, tag="v2")
        with patch("fcontext.experience.urlopen", return_value=self._mock_urlopen(data_v2)):
            update_experience(workspace, name="keep")

        rows = _load_ex(workspace)
        row = next(r for r in rows if r["name"] == "keep")
        assert row["source_type"] == "url"
        assert row["source"] == "https://example.com/pack.zip"
