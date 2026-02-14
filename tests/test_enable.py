"""Tests for fcontext enable."""
from pathlib import Path
from fcontext.init import init_workspace, enable_agent, list_agents


class TestEnable:
    """TASK-003: 测试 enable — Agent指令投递与list"""

    def test_enable_copilot(self, workspace: Path):
        rc = enable_agent(workspace, "copilot")
        assert rc == 0
        # .instructions.md (always-on, minimal lookup order)
        target = workspace / ".github" / "instructions" / "fcontext.instructions.md"
        assert target.exists()
        content = target.read_text()
        assert "name: 'fcontext'" in content
        assert "applyTo: '**'" in content
        assert "_workspace.map" in content
        # Four separate SKILL.md files
        skills_dir = workspace / ".github" / "skills"
        for name in ("fcontext", "fcontext-index", "fcontext-req", "fcontext-topic"):
            skill = skills_dir / name / "SKILL.md"
            assert skill.exists(), f"{name}/SKILL.md missing"
            assert f"name: {name}" in skill.read_text()
        # Spot-check content
        assert "fcontext index" in (skills_dir / "fcontext-index" / "SKILL.md").read_text()
        assert "fcontext req list" in (skills_dir / "fcontext-req" / "SKILL.md").read_text()
        assert "fcontext topic" in (skills_dir / "fcontext-topic" / "SKILL.md").read_text()

    def test_enable_claude(self, workspace: Path):
        rc = enable_agent(workspace, "claude")
        assert rc == 0
        # Rules file
        rules = workspace / ".claude" / "rules" / "fcontext.md"
        assert rules.exists()
        content = rules.read_text()
        assert "_README.md" in content
        assert "Workflow Rules" in content
        # Skills
        skills_dir = workspace / ".claude" / "skills"
        for name in ("fcontext", "fcontext-index", "fcontext-req", "fcontext-topic"):
            skill = skills_dir / name / "SKILL.md"
            assert skill.exists(), f"{name}/SKILL.md missing"
            assert f"name: {name}" in skill.read_text()

    def test_enable_cursor(self, workspace: Path):
        rc = enable_agent(workspace, "cursor")
        assert rc == 0
        # Rules file
        rules = workspace / ".cursor" / "rules" / "fcontext.md"
        assert rules.exists()
        assert "Workflow Rules" in rules.read_text()
        # Skills under .cursor/skills (not .agents/skills)
        skills_dir = workspace / ".cursor" / "skills"
        for name in ("fcontext", "fcontext-index", "fcontext-req", "fcontext-topic"):
            skill = skills_dir / name / "SKILL.md"
            assert skill.exists(), f"{name}/SKILL.md missing"
            assert f"name: {name}" in skill.read_text()

    def test_enable_trae(self, workspace: Path):
        rc = enable_agent(workspace, "trae")
        assert rc == 0
        # Rules file
        rules = workspace / ".trae" / "rules" / "fcontext.md"
        assert rules.exists()
        assert "Workflow Rules" in rules.read_text()
        # Skills
        skills_dir = workspace / ".trae" / "skills"
        for name in ("fcontext", "fcontext-index", "fcontext-req", "fcontext-topic"):
            skill = skills_dir / name / "SKILL.md"
            assert skill.exists(), f"{name}/SKILL.md missing"

    def test_enable_opencode_is_claude_alias(self, workspace: Path):
        rc = enable_agent(workspace, "opencode")
        assert rc == 0
        # Should create files in .claude/ (same as claude)
        rules = workspace / ".claude" / "rules" / "fcontext.md"
        assert rules.exists()
        skills_dir = workspace / ".claude" / "skills"
        for name in ("fcontext", "fcontext-index", "fcontext-req", "fcontext-topic"):
            assert (skills_dir / name / "SKILL.md").exists()

    def test_enable_openclaw_skills_only(self, workspace: Path):
        rc = enable_agent(workspace, "openclaw")
        assert rc == 0
        # Skills in project-root skills/ dir
        skills_dir = workspace / "skills"
        for name in ("fcontext", "fcontext-index", "fcontext-req", "fcontext-topic"):
            skill = skills_dir / name / "SKILL.md"
            assert skill.exists(), f"{name}/SKILL.md missing"
        # No rules file anywhere
        assert not (workspace / "rules").exists()
        assert not (workspace / ".openclaw").exists()

    def test_enable_unknown_agent(self, workspace: Path):
        rc = enable_agent(workspace, "unknown_agent")
        assert rc == 1

    def test_enable_no_overwrite_without_force(self, workspace: Path):
        enable_agent(workspace, "copilot")
        ctx_skill = workspace / ".github" / "skills" / "fcontext" / "SKILL.md"
        ctx_skill.write_text("custom content")
        enable_agent(workspace, "copilot", force=False)
        assert ctx_skill.read_text() == "custom content"

    def test_enable_force_overwrite(self, workspace: Path):
        enable_agent(workspace, "copilot")
        ctx_skill = workspace / ".github" / "skills" / "fcontext" / "SKILL.md"
        ctx_skill.write_text("custom content")
        enable_agent(workspace, "copilot", force=True)
        assert "_workspace.map" in ctx_skill.read_text()

    def test_enable_rules_no_overwrite_without_force(self, workspace: Path):
        enable_agent(workspace, "claude")
        rules = workspace / ".claude" / "rules" / "fcontext.md"
        rules.write_text("custom rules")
        enable_agent(workspace, "claude", force=False)
        assert rules.read_text() == "custom rules"

    def test_enable_rules_force_overwrite(self, workspace: Path):
        enable_agent(workspace, "claude")
        rules = workspace / ".claude" / "rules" / "fcontext.md"
        rules.write_text("custom rules")
        enable_agent(workspace, "claude", force=True)
        assert "Workflow Rules" in rules.read_text()

    def test_enable_without_init_fails(self, empty_dir: Path):
        rc = enable_agent(empty_dir, "copilot")
        assert rc == 1

    def test_list_agents(self, workspace: Path, capsys):
        enable_agent(workspace, "copilot")
        list_agents(workspace)
        out = capsys.readouterr().out
        assert "copilot" in out
        assert "enabled" in out

    def test_list_agents_shows_alias(self, workspace: Path, capsys):
        list_agents(workspace)
        out = capsys.readouterr().out
        assert "opencode" in out
        assert "claude" in out  # shows alias target
