"""Tests for fcontext req."""
from pathlib import Path
from fcontext.requirements import (
    req_init, req_add, req_list, req_show, req_set,
    req_board, req_tree, req_comment, req_backlog_md,
    req_link, req_trace,
    _load_items, _find_item, _parse_links,
)


class TestReqInit:
    def test_creates_csv(self, workspace: Path):
        csv = workspace / ".fcontext" / "_requirements" / "items.csv"
        assert csv.exists()
        content = csv.read_text()
        assert "id,type,title" in content


class TestReqAdd:
    """TASK-006: 测试 req — CRUD"""

    def test_add_requirement(self, workspace: Path):
        rc = req_add(workspace, "requirement", "Test requirement")
        assert rc == 0
        items = _load_items(workspace)
        assert len(items) == 1
        assert items[0]["id"] == "REQ-001"
        assert items[0]["title"] == "Test requirement"
        assert items[0]["status"] == "draft"

    def test_add_generates_doc(self, workspace: Path):
        req_add(workspace, "requirement", "Test requirement")
        doc = workspace / ".fcontext" / "_requirements" / "docs" / "REQ-001.md"
        assert doc.exists()
        assert "REQ-001" in doc.read_text()

    def test_add_all_types(self, workspace: Path):
        for t in ("roadmap", "epic", "requirement", "story", "task", "bug"):
            rc = req_add(workspace, t, f"Test {t}")
            assert rc == 0
        items = _load_items(workspace)
        assert len(items) == 6

    def test_add_with_parent(self, workspace: Path):
        req_add(workspace, "epic", "Parent Epic")
        rc = req_add(workspace, "requirement", "Child Req", parent="EPIC-001")
        assert rc == 0
        items = _load_items(workspace)
        child = _find_item(items, "REQ-001")
        assert child["parent"] == "EPIC-001"

    def test_add_invalid_parent(self, workspace: Path):
        rc = req_add(workspace, "requirement", "Orphan", parent="EPIC-999")
        assert rc == 1

    def test_add_invalid_hierarchy(self, workspace: Path):
        req_add(workspace, "task", "A task")
        rc = req_add(workspace, "epic", "Epic under task", parent="TASK-001")
        assert rc == 1

    def test_add_story_under_requirement(self, workspace: Path):
        req_add(workspace, "requirement", "Parent Req")
        rc = req_add(workspace, "story", "User Story", parent="REQ-001")
        assert rc == 0
        items = _load_items(workspace)
        story = _find_item(items, "STORY-001")
        assert story["parent"] == "REQ-001"

    def test_add_task_under_story(self, workspace: Path):
        req_add(workspace, "story", "A Story")
        rc = req_add(workspace, "task", "Sub task", parent="STORY-001")
        assert rc == 0
        items = _load_items(workspace)
        task = _find_item(items, "TASK-001")
        assert task["parent"] == "STORY-001"

    def test_add_invalid_type(self, workspace: Path):
        rc = req_add(workspace, "invalid_type", "Bad type")
        assert rc == 1

    def test_add_invalid_priority(self, workspace: Path):
        rc = req_add(workspace, "requirement", "Bad pri", priority="P9")
        assert rc == 1

    def test_add_increments_id(self, workspace: Path):
        req_add(workspace, "requirement", "First")
        req_add(workspace, "requirement", "Second")
        items = _load_items(workspace)
        assert items[0]["id"] == "REQ-001"
        assert items[1]["id"] == "REQ-002"


class TestReqList:
    def test_list_empty(self, workspace: Path, capsys):
        rc = req_list(workspace)
        assert rc == 0
        assert "no items" in capsys.readouterr().out

    def test_list_all(self, workspace: Path, capsys):
        req_add(workspace, "requirement", "R1")
        req_add(workspace, "task", "T1")
        req_list(workspace)
        out = capsys.readouterr().out
        assert "REQ-001" in out
        assert "TASK-001" in out

    def test_list_filter_type(self, workspace: Path, capsys):
        req_add(workspace, "requirement", "R1")
        req_add(workspace, "task", "T1")
        capsys.readouterr()  # flush previous output
        req_list(workspace, filter_type="task")
        out = capsys.readouterr().out
        assert "TASK-001" in out
        assert "REQ-001" not in out

    def test_list_filter_status(self, workspace: Path, capsys):
        req_add(workspace, "requirement", "R1")
        req_set(workspace, "REQ-001", "status", "active")
        req_add(workspace, "requirement", "R2")
        capsys.readouterr()  # flush previous output
        req_list(workspace, filter_status="active")
        out = capsys.readouterr().out
        assert "REQ-001" in out
        assert "REQ-002" not in out


class TestReqShow:
    def test_show_existing(self, workspace: Path, capsys):
        req_add(workspace, "requirement", "My Req")
        rc = req_show(workspace, "REQ-001")
        assert rc == 0
        out = capsys.readouterr().out
        assert "My Req" in out
        assert "requirement" in out

    def test_show_not_found(self, workspace: Path):
        rc = req_show(workspace, "REQ-999")
        assert rc == 1

    def test_show_children(self, workspace: Path, capsys):
        req_add(workspace, "epic", "Parent")
        req_add(workspace, "requirement", "Child", parent="EPIC-001")
        req_show(workspace, "EPIC-001")
        out = capsys.readouterr().out
        assert "Children" in out
        assert "REQ-001" in out


class TestReqSet:
    def test_set_status(self, workspace: Path):
        req_add(workspace, "requirement", "R1")
        rc = req_set(workspace, "REQ-001", "status", "active")
        assert rc == 0
        items = _load_items(workspace)
        assert items[0]["status"] == "active"

    def test_set_title(self, workspace: Path):
        req_add(workspace, "requirement", "Old Title")
        req_set(workspace, "REQ-001", "title", "New Title")
        items = _load_items(workspace)
        assert items[0]["title"] == "New Title"

    def test_set_invalid_field(self, workspace: Path):
        req_add(workspace, "requirement", "R1")
        rc = req_set(workspace, "REQ-001", "id", "REQ-999")
        assert rc == 1

    def test_set_invalid_status(self, workspace: Path):
        req_add(workspace, "requirement", "R1")
        rc = req_set(workspace, "REQ-001", "status", "invalid_status")
        assert rc == 1

    def test_set_not_found(self, workspace: Path):
        rc = req_set(workspace, "REQ-999", "status", "active")
        assert rc == 1

    def test_set_updates_timestamp(self, workspace: Path):
        req_add(workspace, "requirement", "R1")
        items = _load_items(workspace)
        old_updated = items[0]["updated"]
        req_set(workspace, "REQ-001", "status", "active")
        items = _load_items(workspace)
        # updated should be set (at least same day)
        assert items[0]["updated"] >= old_updated


class TestReqBoard:
    def test_board_empty(self, workspace: Path, capsys):
        rc = req_board(workspace)
        assert rc == 0

    def test_board_groups_by_status(self, workspace: Path, capsys):
        req_add(workspace, "requirement", "R1")
        req_set(workspace, "REQ-001", "status", "active")
        req_add(workspace, "requirement", "R2")
        req_board(workspace)
        out = capsys.readouterr().out
        assert "DRAFT" in out
        assert "ACTIVE" in out


class TestReqTree:
    def test_tree_empty(self, workspace: Path, capsys):
        rc = req_tree(workspace)
        assert rc == 0

    def test_tree_hierarchy(self, workspace: Path, capsys):
        req_add(workspace, "roadmap", "Road")
        req_add(workspace, "epic", "Ep", parent="ROAD-001")
        req_add(workspace, "requirement", "Req", parent="EPIC-001")
        req_tree(workspace)
        out = capsys.readouterr().out
        assert "ROAD-001" in out
        assert "EPIC-001" in out
        assert "REQ-001" in out


class TestReqComment:
    def test_comment_appends(self, workspace: Path):
        req_add(workspace, "requirement", "R1")
        rc = req_comment(workspace, "REQ-001", "This is a comment")
        assert rc == 0
        doc = workspace / ".fcontext" / "_requirements" / "docs" / "REQ-001.md"
        content = doc.read_text()
        assert "This is a comment" in content

    def test_comment_not_found(self, workspace: Path):
        rc = req_comment(workspace, "REQ-999", "Nope")
        assert rc == 1


class TestBacklogMd:
    def test_generates_backlog(self, workspace: Path):
        req_add(workspace, "requirement", "R1")
        rc = req_backlog_md(workspace)
        assert rc == 0
        bl = workspace / ".fcontext" / "_requirements" / "_backlog.md"
        assert bl.exists()
        assert "REQ-001" in bl.read_text()


# ── Provenance (author, source) ───────────────────────────────────────────────

class TestProvenance:
    def test_add_with_author(self, workspace: Path):
        rc = req_add(workspace, "requirement", "Login", author="客户张总")
        assert rc == 0
        items = _load_items(workspace)
        assert items[0]["author"] == "客户张总"

    def test_add_with_source(self, workspace: Path):
        rc = req_add(workspace, "requirement", "Login",
                     source="meeting/2026-02-10.md")
        assert rc == 0
        items = _load_items(workspace)
        assert items[0]["source"] == "meeting/2026-02-10.md"

    def test_add_with_all_provenance(self, workspace: Path):
        rc = req_add(workspace, "requirement", "Login",
                     author="张总", source="meeting/note.md")
        assert rc == 0
        items = _load_items(workspace)
        assert items[0]["author"] == "张总"
        assert items[0]["source"] == "meeting/note.md"

    def test_show_displays_author_source(self, workspace: Path, capsys):
        req_add(workspace, "requirement", "Login",
                author="张总", source="meeting/note.md")
        capsys.readouterr()  # flush
        req_show(workspace, "REQ-001")
        out = capsys.readouterr().out
        assert "张总" in out
        assert "meeting/note.md" in out

    def test_set_author(self, workspace: Path):
        req_add(workspace, "requirement", "R1")
        rc = req_set(workspace, "REQ-001", "author", "李总")
        assert rc == 0
        items = _load_items(workspace)
        assert items[0]["author"] == "李总"

    def test_set_source(self, workspace: Path):
        req_add(workspace, "requirement", "R1")
        rc = req_set(workspace, "REQ-001", "source", "email/feedback.md")
        assert rc == 0
        items = _load_items(workspace)
        assert items[0]["source"] == "email/feedback.md"


# ── Links on add ──────────────────────────────────────────────────────────────

class TestAddWithLinks:
    def test_add_with_link(self, workspace: Path):
        req_add(workspace, "requirement", "Old login")
        rc = req_add(workspace, "requirement", "New login",
                     links="supersedes:REQ-001")
        assert rc == 0
        items = _load_items(workspace)
        new = _find_item(items, "REQ-002")
        assert "supersedes:REQ-001" in new["links"]

    def test_add_with_invalid_link_type(self, workspace: Path):
        req_add(workspace, "requirement", "Old")
        rc = req_add(workspace, "requirement", "New",
                     links="invalid:REQ-001")
        assert rc == 1

    def test_add_with_nonexistent_target(self, workspace: Path):
        rc = req_add(workspace, "requirement", "New",
                     links="supersedes:REQ-999")
        assert rc == 1

    def test_add_with_bad_format(self, workspace: Path):
        rc = req_add(workspace, "requirement", "New",
                     links="no-colon-here")
        assert rc == 1


# ── req link command ──────────────────────────────────────────────────────────

class TestReqLink:
    def test_link_basic(self, workspace: Path):
        req_add(workspace, "requirement", "V1 Login")
        req_add(workspace, "requirement", "V2 Login")
        rc = req_link(workspace, "REQ-002", "supersedes", "REQ-001")
        assert rc == 0
        items = _load_items(workspace)
        r2 = _find_item(items, "REQ-002")
        assert "supersedes:REQ-001" in r2["links"]

    def test_link_multiple(self, workspace: Path):
        req_add(workspace, "requirement", "R1")
        req_add(workspace, "requirement", "R2")
        req_add(workspace, "requirement", "R3")
        req_link(workspace, "REQ-003", "supersedes", "REQ-002")
        req_link(workspace, "REQ-003", "relates", "REQ-001")
        items = _load_items(workspace)
        r3 = _find_item(items, "REQ-003")
        parsed = _parse_links(r3["links"])
        assert ("supersedes", "REQ-002") in parsed
        assert ("relates", "REQ-001") in parsed

    def test_link_duplicate_idempotent(self, workspace: Path, capsys):
        req_add(workspace, "requirement", "R1")
        req_add(workspace, "requirement", "R2")
        req_link(workspace, "REQ-002", "evolves", "REQ-001")
        rc = req_link(workspace, "REQ-002", "evolves", "REQ-001")
        assert rc == 0
        out = capsys.readouterr().out
        assert "already exists" in out

    def test_link_invalid_type(self, workspace: Path):
        req_add(workspace, "requirement", "R1")
        req_add(workspace, "requirement", "R2")
        rc = req_link(workspace, "REQ-002", "invalid", "REQ-001")
        assert rc == 1

    def test_link_source_not_found(self, workspace: Path):
        req_add(workspace, "requirement", "R1")
        rc = req_link(workspace, "REQ-999", "relates", "REQ-001")
        assert rc == 1

    def test_link_target_not_found(self, workspace: Path):
        req_add(workspace, "requirement", "R1")
        rc = req_link(workspace, "REQ-001", "relates", "REQ-999")
        assert rc == 1

    def test_link_logs_changelog(self, workspace: Path):
        req_add(workspace, "requirement", "R1")
        req_add(workspace, "requirement", "R2")
        req_link(workspace, "REQ-002", "supersedes", "REQ-001")
        doc = workspace / ".fcontext" / "_requirements" / "docs" / "REQ-002.md"
        content = doc.read_text()
        assert "Change" in content
        assert "supersedes:REQ-001" in content


# ── req trace command ─────────────────────────────────────────────────────────

class TestReqTrace:
    def test_trace_single(self, workspace: Path, capsys):
        req_add(workspace, "requirement", "Standalone")
        rc = req_trace(workspace, "REQ-001")
        assert rc == 0
        out = capsys.readouterr().out
        assert "REQ-001" in out

    def test_trace_chain(self, workspace: Path, capsys):
        req_add(workspace, "requirement", "V1 Login")
        req_add(workspace, "requirement", "V2 Login")
        req_add(workspace, "requirement", "V3 Login")
        req_link(workspace, "REQ-002", "supersedes", "REQ-001")
        req_link(workspace, "REQ-003", "supersedes", "REQ-002")
        capsys.readouterr()  # flush
        req_trace(workspace, "REQ-003")
        out = capsys.readouterr().out
        assert "REQ-001" in out
        assert "REQ-002" in out
        assert "REQ-003" in out

    def test_trace_from_middle(self, workspace: Path, capsys):
        """Tracing from middle should still show full chain."""
        req_add(workspace, "requirement", "V1")
        req_add(workspace, "requirement", "V2")
        req_add(workspace, "requirement", "V3")
        req_link(workspace, "REQ-002", "evolves", "REQ-001")
        req_link(workspace, "REQ-003", "evolves", "REQ-002")
        capsys.readouterr()  # flush
        req_trace(workspace, "REQ-002")
        out = capsys.readouterr().out
        # Should show the origin REQ-001 too
        assert "REQ-001" in out
        assert "REQ-002" in out

    def test_trace_not_found(self, workspace: Path):
        rc = req_trace(workspace, "REQ-999")
        assert rc == 1

    def test_trace_shows_provenance(self, workspace: Path, capsys):
        req_add(workspace, "requirement", "V1", author="张总",
                source="meeting/note.md")
        capsys.readouterr()  # flush
        req_trace(workspace, "REQ-001")
        out = capsys.readouterr().out
        assert "张总" in out
        assert "meeting/note.md" in out


# ── Changelog ─────────────────────────────────────────────────────────────────

class TestChangelog:
    def test_set_logs_change(self, workspace: Path):
        req_add(workspace, "requirement", "R1")
        req_set(workspace, "REQ-001", "status", "active")
        doc = workspace / ".fcontext" / "_requirements" / "docs" / "REQ-001.md"
        content = doc.read_text()
        assert "Change" in content
        assert "draft" in content
        assert "active" in content

    def test_multiple_changes_logged(self, workspace: Path):
        req_add(workspace, "requirement", "R1")
        req_set(workspace, "REQ-001", "status", "active")
        req_set(workspace, "REQ-001", "priority", "P0")
        doc = workspace / ".fcontext" / "_requirements" / "docs" / "REQ-001.md"
        content = doc.read_text()
        assert content.count("**Change**") == 2


# ── _parse_links helper ──────────────────────────────────────────────────────

class TestParseLinks:
    def test_empty(self):
        assert _parse_links("") == []

    def test_single(self):
        result = _parse_links("supersedes:REQ-001")
        assert result == [("supersedes", "REQ-001")]

    def test_multiple(self):
        result = _parse_links("supersedes:REQ-001,relates:REQ-002")
        assert len(result) == 2
        assert ("supersedes", "REQ-001") in result
        assert ("relates", "REQ-002") in result

    def test_whitespace(self):
        result = _parse_links(" evolves : REQ-001 , blocks : REQ-002 ")
        assert ("evolves", "REQ-001") in result
        assert ("blocks", "REQ-002") in result
