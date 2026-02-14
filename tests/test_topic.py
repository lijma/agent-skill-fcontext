"""Tests for fcontext topic."""
from pathlib import Path
from fcontext.topics import topic_list, topic_show, topic_clean


class TestTopicList:
    """TASK-007: 测试 topic — list/show/clean"""

    def test_list_empty(self, workspace: Path, capsys):
        rc = topic_list(workspace)
        assert rc == 0
        assert "no topics" in capsys.readouterr().out

    def test_list_shows_files(self, workspace: Path, capsys):
        topics = workspace / ".fcontext" / "_topics"
        (topics / "arch-analysis.md").write_text("# Architecture\nSome findings")
        topic_list(workspace)
        out = capsys.readouterr().out
        assert "arch-analysis" in out
        assert "Total: 1" in out

    def test_list_multiple(self, workspace: Path, capsys):
        topics = workspace / ".fcontext" / "_topics"
        (topics / "topic-a.md").write_text("# A\ncontent a")
        (topics / "topic-b.md").write_text("# B\ncontent b")
        topic_list(workspace)
        out = capsys.readouterr().out
        assert "topic-a" in out
        assert "topic-b" in out
        assert "Total: 2" in out


class TestTopicShow:
    def test_show_existing(self, workspace: Path, capsys):
        topics = workspace / ".fcontext" / "_topics"
        (topics / "my-analysis.md").write_text("# My Analysis\n\nKey finding: X")
        rc = topic_show(workspace, "my-analysis")
        assert rc == 0
        out = capsys.readouterr().out
        assert "my-analysis" in out
        assert "Key finding: X" in out

    def test_show_with_md_suffix(self, workspace: Path, capsys):
        topics = workspace / ".fcontext" / "_topics"
        (topics / "report.md").write_text("# Report")
        rc = topic_show(workspace, "report.md")
        assert rc == 0

    def test_show_fuzzy_match(self, workspace: Path, capsys):
        topics = workspace / ".fcontext" / "_topics"
        (topics / "fcontext-architecture.md").write_text("# Arch")
        rc = topic_show(workspace, "architecture")
        assert rc == 0

    def test_show_not_found(self, workspace: Path):
        rc = topic_show(workspace, "nonexistent")
        assert rc == 1

    def test_show_ambiguous(self, workspace: Path):
        topics = workspace / ".fcontext" / "_topics"
        (topics / "analysis-a.md").write_text("# A")
        (topics / "analysis-b.md").write_text("# B")
        rc = topic_show(workspace, "analysis")
        assert rc == 1  # ambiguous


class TestTopicClean:
    def test_clean_removes_empty(self, workspace: Path, capsys):
        topics = workspace / ".fcontext" / "_topics"
        (topics / "empty.md").write_text("")
        (topics / "good.md").write_text("# Good topic\nWith real content")
        rc = topic_clean(workspace)
        assert rc == 0
        assert not (topics / "empty.md").exists()
        assert (topics / "good.md").exists()

    def test_clean_nothing_to_clean(self, workspace: Path, capsys):
        topics = workspace / ".fcontext" / "_topics"
        (topics / "valid.md").write_text("# Valid\nContent here")
        topic_clean(workspace)
        out = capsys.readouterr().out
        assert "nothing to clean" in out
