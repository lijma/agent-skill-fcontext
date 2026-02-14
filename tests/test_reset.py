"""Tests for fcontext reset."""
from pathlib import Path
from unittest.mock import patch
from fcontext.init import init_workspace, enable_agent


class TestReset:
    """Test the reset command logic (CLI cmd_reset)."""

    def _do_reset(self, root: Path, inputs: list[str]) -> int:
        """Run cmd_reset with mocked input()."""
        import argparse
        from fcontext.cli import cmd_reset
        args = argparse.Namespace(dir=str(root))
        with patch("builtins.input", side_effect=inputs):
            return cmd_reset(args)

    def test_reset_removes_fcontext(self, workspace: Path):
        rc = self._do_reset(workspace, ["yes", "reset"])
        assert rc == 0
        assert not (workspace / ".fcontext").exists()

    def test_reset_removes_agent_files(self, workspace: Path):
        enable_agent(workspace, "copilot")
        instructions = workspace / ".github" / "instructions" / "fcontext.instructions.md"
        assert instructions.exists()
        skills_dir = workspace / ".github" / "skills"
        for name in ("fcontext", "fcontext-index", "fcontext-req", "fcontext-topic"):
            assert (skills_dir / name / "SKILL.md").exists()
        rc = self._do_reset(workspace, ["yes", "reset"])
        assert rc == 0
        assert not instructions.exists()
        for name in ("fcontext", "fcontext-index", "fcontext-req", "fcontext-topic"):
            assert not (skills_dir / name / "SKILL.md").exists()

    def test_reset_abort_on_first_confirm(self, workspace: Path):
        rc = self._do_reset(workspace, ["no"])
        assert rc == 1
        assert (workspace / ".fcontext").exists()

    def test_reset_abort_on_second_confirm(self, workspace: Path):
        rc = self._do_reset(workspace, ["yes", "no"])
        assert rc == 1
        assert (workspace / ".fcontext").exists()

    def test_reset_requires_exact_yes(self, workspace: Path):
        rc = self._do_reset(workspace, ["y"])
        assert rc == 1
        assert (workspace / ".fcontext").exists()

    def test_reset_requires_exact_reset(self, workspace: Path):
        rc = self._do_reset(workspace, ["yes", "confirm"])
        assert rc == 1
        assert (workspace / ".fcontext").exists()

    def test_reset_then_reinit(self, workspace: Path):
        self._do_reset(workspace, ["yes", "reset"])
        assert not (workspace / ".fcontext").exists()
        init_workspace(workspace)
        assert (workspace / ".fcontext").is_dir()
        assert (workspace / ".fcontext" / "_index.json").exists()
