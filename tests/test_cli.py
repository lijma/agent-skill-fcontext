"""Tests for fcontext CLI — main() dispatcher and all cmd_* functions."""
import argparse
import os
from pathlib import Path
from unittest.mock import patch

from fcontext.cli import (
    main, _find_root,
    cmd_experience, cmd_topic, cmd_req, cmd_reset,
)


class TestMain:
    """Test main() argument parsing and dispatch."""

    def test_no_args_prints_help(self, workspace: Path, capsys):
        os.chdir(workspace)
        rc = main([])
        assert rc == 0

    def test_version(self, workspace: Path, capsys):
        try:
            main(["--version"])
        except SystemExit as e:
            assert e.code == 0

    def test_req_no_action(self, workspace: Path, capsys):
        os.chdir(workspace)
        rc = main(["req"])
        assert rc == 0

    def test_topic_no_action(self, workspace: Path, capsys):
        os.chdir(workspace)
        rc = main(["topic"])
        assert rc == 0

    def test_experience_no_action(self, workspace: Path, capsys):
        os.chdir(workspace)
        rc = main(["experience"])
        assert rc == 0


class TestCmdInit:
    """Test cmd_init via main()."""

    def test_init_via_cli(self, tmp_path: Path):
        rc = main(["init", str(tmp_path)])
        assert rc == 0
        assert (tmp_path / ".fcontext").is_dir()

    def test_init_force(self, workspace: Path):
        rc = main(["init", str(workspace), "--force"])
        assert rc == 0


class TestCmdEnable:
    """Test cmd_enable via main()."""

    def test_enable_not_workspace(self, tmp_path: Path, capsys):
        os.chdir(tmp_path)
        rc = main(["enable", "copilot"])
        assert rc == 1
        assert "fatal" in capsys.readouterr().err

    def test_enable_copilot(self, workspace: Path):
        os.chdir(workspace)
        rc = main(["enable", "copilot"])
        assert rc == 0

    def test_enable_list(self, workspace: Path, capsys):
        os.chdir(workspace)
        rc = main(["enable", "list"])
        assert rc == 0


class TestCmdIndex:
    """Test cmd_index via main()."""

    def test_index_not_workspace(self, tmp_path: Path, capsys):
        os.chdir(tmp_path)
        rc = main(["index"])
        assert rc == 1
        assert "fatal" in capsys.readouterr().err

    def test_index_whole_workspace(self, workspace: Path, capsys):
        os.chdir(workspace)
        rc = main(["index"])
        assert rc == 0

    def test_index_file(self, workspace: Path, capsys):
        md = workspace / "notes.md"
        md.write_text("# Notes")
        os.chdir(workspace)
        rc = main(["index", str(md)])
        assert rc == 0

    def test_index_dir(self, workspace: Path, capsys):
        docs = workspace / "docs"
        docs.mkdir()
        (docs / "readme.md").write_text("# Hi")
        os.chdir(workspace)
        rc = main(["index", str(docs)])
        assert rc == 0

    def test_index_force(self, workspace: Path, capsys):
        os.chdir(workspace)
        rc = main(["index", "--force"])
        assert rc == 0


class TestCmdStatus:
    """Test cmd_status via main()."""

    def test_status_not_workspace(self, tmp_path: Path, capsys):
        rc = main(["status", str(tmp_path)])
        assert rc == 1
        assert "fatal" in capsys.readouterr().err

    def test_status_ok(self, workspace: Path):
        rc = main(["status", str(workspace)])
        assert rc == 0


class TestCmdClean:
    """Test cmd_clean via main()."""

    def test_clean_not_workspace(self, tmp_path: Path, capsys):
        rc = main(["clean", str(tmp_path)])
        assert rc == 1
        assert "fatal" in capsys.readouterr().err

    def test_clean_ok(self, workspace: Path):
        rc = main(["clean", str(workspace)])
        assert rc == 0


class TestCmdReset:
    """Test cmd_reset via main() — already covered in test_reset.py,
    but we test the not-workspace branch here."""

    def test_reset_not_workspace(self, tmp_path: Path, capsys):
        rc = main(["reset", str(tmp_path)])
        assert rc == 1
        assert "fatal" in capsys.readouterr().err

    def test_reset_abort(self, workspace: Path):
        with patch("builtins.input", side_effect=["no"]):
            rc = main(["reset", str(workspace)])
        assert rc == 1


class TestCmdExport:
    """Test cmd_export via main()."""

    def test_export_not_workspace(self, tmp_path: Path, capsys):
        os.chdir(tmp_path)
        rc = main(["export", "output.zip"])
        assert rc == 1
        assert "fatal" in capsys.readouterr().err

    def test_export_to_zip(self, workspace: Path, tmp_path: Path):
        os.chdir(workspace)
        out = tmp_path / "export.zip"
        rc = main(["export", str(out)])
        assert rc == 0
        assert out.exists()


class TestCmdExperience:
    """Test cmd_experience via main()."""

    def test_experience_not_workspace(self, tmp_path: Path, capsys):
        os.chdir(tmp_path)
        rc = main(["experience", "list"])
        assert rc == 1
        assert "fatal" in capsys.readouterr().err

    def test_experience_list(self, workspace: Path):
        os.chdir(workspace)
        rc = main(["experience", "list"])
        assert rc == 0

    def test_experience_remove_not_found(self, workspace: Path):
        os.chdir(workspace)
        rc = main(["experience", "remove", "nonexistent"])
        assert rc == 1

    def test_experience_import_bad_source(self, workspace: Path):
        os.chdir(workspace)
        rc = main(["experience", "import", "/nonexistent/path.zip"])
        assert rc == 1


class TestCmdTopic:
    """Test cmd_topic via main()."""

    def test_topic_not_workspace(self, tmp_path: Path, capsys):
        os.chdir(tmp_path)
        rc = main(["topic", "list"])
        assert rc == 1
        assert "fatal" in capsys.readouterr().err

    def test_topic_list(self, workspace: Path):
        os.chdir(workspace)
        rc = main(["topic", "list"])
        assert rc == 0

    def test_topic_show(self, workspace: Path, capsys):
        topics = workspace / ".fcontext" / "_topics"
        topics.mkdir(parents=True, exist_ok=True)
        (topics / "my-topic.md").write_text("# Topic\nContent")
        os.chdir(workspace)
        rc = main(["topic", "show", "my-topic"])
        assert rc == 0

    def test_topic_clean(self, workspace: Path):
        os.chdir(workspace)
        rc = main(["topic", "clean"])
        assert rc == 0


class TestCmdReq:
    """Test cmd_req via main()."""

    def test_req_not_workspace(self, tmp_path: Path, capsys):
        os.chdir(tmp_path)
        rc = main(["req", "list"])
        assert rc == 1
        assert "fatal" in capsys.readouterr().err

    def test_req_add(self, workspace: Path):
        os.chdir(workspace)
        rc = main(["req", "add", "My requirement"])
        assert rc == 0

    def test_req_list(self, workspace: Path):
        os.chdir(workspace)
        rc = main(["req", "list"])
        assert rc == 0

    def test_req_show(self, workspace: Path):
        os.chdir(workspace)
        main(["req", "add", "Test req"])
        rc = main(["req", "show", "REQ-001"])
        assert rc == 0

    def test_req_set(self, workspace: Path):
        os.chdir(workspace)
        main(["req", "add", "Test req"])
        rc = main(["req", "set", "REQ-001", "status", "active"])
        assert rc == 0

    def test_req_board(self, workspace: Path):
        os.chdir(workspace)
        rc = main(["req", "board"])
        assert rc == 0

    def test_req_tree(self, workspace: Path):
        os.chdir(workspace)
        rc = main(["req", "tree"])
        assert rc == 0

    def test_req_comment(self, workspace: Path):
        os.chdir(workspace)
        main(["req", "add", "Test req"])
        rc = main(["req", "comment", "REQ-001", "A comment"])
        assert rc == 0

    def test_req_link(self, workspace: Path):
        os.chdir(workspace)
        main(["req", "add", "V1"])
        main(["req", "add", "V2"])
        rc = main(["req", "link", "REQ-002", "supersedes", "REQ-001"])
        assert rc == 0

    def test_req_trace(self, workspace: Path):
        os.chdir(workspace)
        main(["req", "add", "R1"])
        rc = main(["req", "trace", "REQ-001"])
        assert rc == 0

    def test_req_list_with_filters(self, workspace: Path):
        os.chdir(workspace)
        main(["req", "add", "R1", "-t", "task"])
        rc = main(["req", "list", "-t", "task", "-s", "draft"])
        assert rc == 0

    def test_req_add_full_args(self, workspace: Path):
        os.chdir(workspace)
        rc = main(["req", "add", "Full req", "-t", "requirement",
                    "-p", "P0", "--assignee", "Alice", "--tags", "api,auth",
                    "--author", "Bob", "--source", "notes.md"])
        assert rc == 0


class TestFindRoot:
    """Test _find_root helper."""

    def test_finds_from_workspace(self, workspace: Path):
        root = _find_root(str(workspace))
        assert root == workspace

    def test_finds_from_subdir(self, workspace: Path):
        sub = workspace / "a" / "b"
        sub.mkdir(parents=True)
        root = _find_root(str(sub))
        assert root == workspace

    def test_returns_none(self, tmp_path: Path):
        root = _find_root(str(tmp_path))
        assert root is None


# ── cmd_* else-branch coverage (unreachable via argparse, tested directly) ────

class TestCmdExperienceElse:
    """Cover cmd_experience else/update branches (L164-168)."""

    def test_experience_update(self, workspace: Path):
        """L164-165: experience update action."""
        args = argparse.Namespace(
            dir=str(workspace), exp_action="update", name=None
        )
        rc = cmd_experience(args)
        assert rc == 0  # update with no experiences is a no-op

    def test_experience_unknown_action(self, workspace: Path, capsys):
        """L166-168: unknown experience action."""
        args = argparse.Namespace(
            dir=str(workspace), exp_action="bogus"
        )
        rc = cmd_experience(args)
        assert rc == 1
        assert "unknown" in capsys.readouterr().err


class TestCmdTopicElse:
    """Cover cmd_topic else branch (L207-208)."""

    def test_topic_unknown_action(self, workspace: Path, capsys):
        args = argparse.Namespace(
            dir=str(workspace), topic_action="bogus"
        )
        rc = cmd_topic(args)
        assert rc == 1
        assert "unknown" in capsys.readouterr().err


class TestCmdReqElse:
    """Cover cmd_req else branch (L255-256)."""

    def test_req_unknown_action(self, workspace: Path, capsys):
        args = argparse.Namespace(
            dir=str(workspace), req_action="bogus"
        )
        rc = cmd_req(args)
        assert rc == 1
        assert "unknown" in capsys.readouterr().err


class TestCmdResetGitignore:
    """Cover gitignore cleanup in cmd_reset (L130-137)."""

    def _do_reset(self, root: Path, inputs: list[str]) -> int:
        args = argparse.Namespace(dir=str(root))
        with patch("builtins.input", side_effect=inputs):
            return cmd_reset(args)

    def test_reset_removes_gitignore_fcontext_only(self, workspace: Path, capsys):
        """L135-137: gitignore with only fcontext entries → remove file."""
        gitignore = workspace / ".gitignore"
        gitignore.write_text(".fcontext/_cache/\n__pycache__/\n*.pyc\n*.egg-info/\n")
        rc = self._do_reset(workspace, ["yes", "reset"])
        assert rc == 0
        assert not gitignore.exists()

    def test_reset_keeps_gitignore_with_user_entries(self, workspace: Path, capsys):
        """L133-134: gitignore with mixed entries → keep non-fcontext ones."""
        gitignore = workspace / ".gitignore"
        gitignore.write_text(".fcontext/_cache/\n__pycache__/\n*.pyc\n*.egg-info/\nmy-custom-entry/\n")
        rc = self._do_reset(workspace, ["yes", "reset"])
        assert rc == 0
        assert gitignore.exists()
        content = gitignore.read_text()
        assert "my-custom-entry/" in content
        assert ".fcontext/_cache/" not in content
