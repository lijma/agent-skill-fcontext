"""Tests for fcontext req."""
import os
from pathlib import Path
from fcontext.requirements import (
    req_init, req_add, req_list, req_show, req_set,
    req_board, req_tree, req_comment, req_backlog_md,
    req_link, req_trace,
    _load_items, _find_item, _parse_links, _next_id,
    _csv_path, _docs_dir, _append_changelog,
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


# ── Coverage gap tests ────────────────────────────────────────────────────────

class TestLoadItemsNoCsv:
    """L84: _load_items when CSV doesn't exist."""

    def test_load_items_no_csv(self, workspace: Path):
        csv = _csv_path(workspace)
        if csv.exists():
            csv.unlink()
        items = _load_items(workspace)
        assert items == []


class TestNextIdValueError:
    """L109-110: _next_id with malformed IDs should handle ValueError."""

    def test_next_id_bad_format(self, workspace: Path):
        # Manually write a CSV with a bad ID
        csv = _csv_path(workspace)
        csv.write_text(
            "id,type,title,status,priority,parent,assignee,tags,created,updated,author,source,links\n"
            "REQ-abc,requirement,Bad ID,draft,P2,,,,2025-01-01,2025-01-01,,,\n"
        )
        items = _load_items(workspace)
        # Should still generate the next valid ID
        next_id = _next_id(items, "requirement")
        assert next_id == "REQ-001"


class TestReqListFilterParent:
    """L372-373: filter_parent in req_list."""

    def test_list_filter_by_parent(self, workspace: Path, capsys):
        req_add(workspace, "epic", "Parent Epic")
        req_add(workspace, "requirement", "Child R1", parent="EPIC-001")
        req_add(workspace, "requirement", "Orphan R2")
        capsys.readouterr()
        req_list(workspace, filter_parent="EPIC-001")
        out = capsys.readouterr().out
        assert "REQ-001" in out
        assert "REQ-002" not in out


class TestReqShowEdgeCases:
    """Cover show display branches."""

    def test_show_with_assignee_and_tags(self, workspace: Path, capsys):
        """L422,424,426: show assignee and tags."""
        req_add(workspace, "requirement", "With fields",
                assignee="Alice", tags="backend,api")
        capsys.readouterr()
        req_show(workspace, "REQ-001")
        out = capsys.readouterr().out
        assert "Alice" in out
        assert "backend,api" in out

    def test_show_with_parent(self, workspace: Path, capsys):
        """L422: show parent."""
        req_add(workspace, "epic", "Epic")
        req_add(workspace, "requirement", "Child", parent="EPIC-001")
        capsys.readouterr()
        req_show(workspace, "REQ-001")
        out = capsys.readouterr().out
        assert "EPIC-001" in out

    def test_show_forward_links(self, workspace: Path, capsys):
        """L436-444: show forward links section."""
        req_add(workspace, "requirement", "V1 Login")
        req_add(workspace, "requirement", "V2 Login",
                links="supersedes:REQ-001")
        capsys.readouterr()
        req_show(workspace, "REQ-002")
        out = capsys.readouterr().out
        assert "Links:" in out
        assert "supersedes" in out
        assert "REQ-001" in out

    def test_show_reverse_links_only(self, workspace: Path, capsys):
        """L456-460: show reverse links when item has no forward links."""
        req_add(workspace, "requirement", "V1 Login")
        req_add(workspace, "requirement", "V2 Login")
        req_link(workspace, "REQ-002", "supersedes", "REQ-001")
        capsys.readouterr()
        # Show REQ-001 which has no forward links but is targeted by REQ-002
        req_show(workspace, "REQ-001")
        out = capsys.readouterr().out
        assert "Links:" in out
        assert "REQ-002" in out
        assert "supersedes" in out

    def test_show_doc_not_found(self, workspace: Path, capsys):
        """L483: doc file missing shows message."""
        req_add(workspace, "requirement", "R1")
        # Delete the doc
        doc = _docs_dir(workspace) / "REQ-001.md"
        if doc.exists():
            doc.unlink()
        capsys.readouterr()
        req_show(workspace, "REQ-001")
        out = capsys.readouterr().out
        assert "not found" in out


class TestReqSetEdgeCases:
    """Cover set edge cases."""

    def test_set_invalid_priority(self, workspace: Path):
        """L501-502: set with invalid priority."""
        req_add(workspace, "requirement", "R1")
        rc = req_set(workspace, "REQ-001", "priority", "P9")
        assert rc == 1


class TestAppendChangelog:
    """L545: _append_changelog when doc doesn't exist."""

    def test_changelog_no_doc(self, workspace: Path):
        # _append_changelog should be a no-op when doc doesn't exist
        _append_changelog(workspace, "REQ-999", "status", "draft", "active")
        # No error, no file created
        assert not (_docs_dir(workspace) / "REQ-999.md").exists()


class TestReqTraceEdgeCases:
    """Cover trace edge cases."""

    def test_trace_with_relates_link(self, workspace: Path, capsys):
        """L670: trace shows non-evolution links (relates, blocks)."""
        req_add(workspace, "requirement", "R1")
        req_add(workspace, "requirement", "R2")
        req_link(workspace, "REQ-001", "relates", "REQ-002")
        capsys.readouterr()
        req_trace(workspace, "REQ-001")
        out = capsys.readouterr().out
        assert "Other Links:" in out
        assert "relates" in out
        assert "REQ-002" in out


class TestReqBoardEdgeCases:
    """Cover board edge cases."""

    def test_board_summary_line(self, workspace: Path, capsys):
        """L688-692: board summary with done and active counts."""
        req_add(workspace, "requirement", "R1")
        req_add(workspace, "requirement", "R2")
        req_set(workspace, "REQ-001", "status", "done")
        req_set(workspace, "REQ-002", "status", "active")
        capsys.readouterr()
        req_board(workspace)
        out = capsys.readouterr().out
        assert "Summary:" in out
        assert "2 total" in out


class TestReqCommentEdgeCases:
    """Cover comment edge cases."""

    def test_comment_creates_doc_if_missing(self, workspace: Path):
        """L783-784: comment creates doc when it doesn't exist."""
        req_add(workspace, "requirement", "R1")
        doc = _docs_dir(workspace) / "REQ-001.md"
        if doc.exists():
            doc.unlink()
        assert not doc.exists()
        rc = req_comment(workspace, "REQ-001", "Comment on missing doc")
        assert rc == 0
        assert doc.exists()
        assert "Comment on missing doc" in doc.read_text()


class TestTraceBranchingEvolution:
    """Cover reverse-walk branch in trace forward loop (L647-650)."""

    def test_trace_branching_evolution(self, workspace: Path, capsys):
        """Two items independently supersede the same item → reverse check fires."""
        req_add(workspace, "requirement", "Original")
        req_add(workspace, "requirement", "Fork A")
        req_add(workspace, "requirement", "Fork B")
        # Both REQ-002 and REQ-003 supersede REQ-001
        req_link(workspace, "REQ-002", "supersedes", "REQ-001")
        req_link(workspace, "REQ-003", "supersedes", "REQ-001")
        capsys.readouterr()
        # Trace REQ-002: forward walk reaches REQ-001, then reverse
        # check should find REQ-003 (not in visited_fwd)
        rc = req_trace(workspace, "REQ-002")
        assert rc == 0
        out = capsys.readouterr().out
        assert "REQ-001" in out
        assert "REQ-002" in out
        assert "REQ-003" in out


class TestTraceStaleReference:
    """Cover node-is-None guard in trace (L670)."""

    def test_trace_with_stale_link(self, workspace: Path, capsys):
        """A link to a deleted item should be handled gracefully."""
        req_add(workspace, "requirement", "R1")
        req_add(workspace, "requirement", "R2")
        req_link(workspace, "REQ-002", "supersedes", "REQ-001")
        # Manually remove REQ-001 from CSV but keep the link on REQ-002
        csv = _csv_path(workspace)
        lines = csv.read_text().splitlines()
        # Keep header + only REQ-002 row
        new_lines = [lines[0]] + [l for l in lines[1:] if "REQ-001" not in l.split(",")[0]]
        csv.write_text("\n".join(new_lines) + "\n")
        capsys.readouterr()
        rc = req_trace(workspace, "REQ-002")
        assert rc == 0
