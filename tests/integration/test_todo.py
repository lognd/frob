"""
Integration tests for frob todo: sequential calls in the same cwd,
verifying ID monotonicity, done/hidden lifecycle, and clear-done behavior.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

FROB = [sys.executable, "-m", "frob"]


def _frob(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        FROB + args,
        capture_output=True,
        text=True,
        cwd=str(cwd),
    )


def _output(r: subprocess.CompletedProcess) -> str:
    return r.stdout + r.stderr


class TestTodoPersistence:
    def test_items_persist_across_calls(self, tmp_path):
        _frob(["todo", "add", "first item"], tmp_path)
        r = _frob(["todo", "list"], tmp_path)
        assert "first item" in _output(r)

    def test_multiple_adds_all_visible(self, tmp_path):
        _frob(["todo", "add", "alpha"], tmp_path)
        _frob(["todo", "add", "beta"], tmp_path)
        _frob(["todo", "add", "gamma"], tmp_path)
        r = _frob(["todo", "list"], tmp_path)
        out = _output(r)
        assert "alpha" in out
        assert "beta" in out
        assert "gamma" in out

    def test_stored_in_frob_dir(self, tmp_path):
        _frob(["todo", "add", "check storage"], tmp_path)
        todo_md = tmp_path / ".frob" / "todo.md"
        assert todo_md.exists()
        assert "check storage" in todo_md.read_text()


class TestTodoIdMonotonicity:
    def test_ids_are_1_2_3(self, tmp_path):
        r1 = _frob(["todo", "add", "first"], tmp_path)
        r2 = _frob(["todo", "add", "second"], tmp_path)
        r3 = _frob(["todo", "add", "third"], tmp_path)
        assert "#1" in _output(r1) or "1" in _output(r1)
        assert "#2" in _output(r2) or "2" in _output(r2)
        assert "#3" in _output(r3) or "3" in _output(r3)

    def test_id_not_reused_after_remove(self, tmp_path):
        _frob(["todo", "add", "a"], tmp_path)
        _frob(["todo", "add", "b"], tmp_path)
        _frob(["todo", "remove", "1"], tmp_path)
        r = _frob(["todo", "add", "c"], tmp_path)
        out = _output(r)
        # new item should be #3, not #1
        assert "#3" in out or "3" in out

    def test_id_not_reused_after_done_clear(self, tmp_path):
        _frob(["todo", "add", "a"], tmp_path)
        _frob(["todo", "add", "b"], tmp_path)
        _frob(["todo", "done", "1"], tmp_path)
        _frob(["todo", "done", "2"], tmp_path)
        _frob(["todo", "clear-done"], tmp_path)
        r = _frob(["todo", "add", "new item"], tmp_path)
        out = _output(r)
        assert "#3" in out or "3" in out


class TestTodoDoneLifecycle:
    def test_done_hides_from_list(self, tmp_path):
        _frob(["todo", "add", "pending"], tmp_path)
        _frob(["todo", "add", "finished"], tmp_path)
        _frob(["todo", "done", "2"], tmp_path)

        r = _frob(["todo", "list"], tmp_path)
        out = _output(r)
        assert "pending" in out
        assert "finished" not in out

    def test_done_visible_with_all_flag(self, tmp_path):
        _frob(["todo", "add", "pending"], tmp_path)
        _frob(["todo", "add", "finished"], tmp_path)
        _frob(["todo", "done", "2"], tmp_path)

        r = _frob(["todo", "list", "--all"], tmp_path)
        out = _output(r)
        assert "pending" in out
        assert "finished" in out

    def test_done_marked_in_file(self, tmp_path):
        _frob(["todo", "add", "mark me"], tmp_path)
        _frob(["todo", "done", "1"], tmp_path)
        content = (tmp_path / ".frob" / "todo.md").read_text()
        assert "[x]" in content

    def test_middle_item_done_others_unaffected(self, tmp_path):
        _frob(["todo", "add", "one"], tmp_path)
        _frob(["todo", "add", "two"], tmp_path)
        _frob(["todo", "add", "three"], tmp_path)
        _frob(["todo", "done", "2"], tmp_path)

        r = _frob(["todo", "list"], tmp_path)
        out = _output(r)
        assert "one" in out
        assert "two" not in out
        assert "three" in out


class TestTodoClearDone:
    def test_clear_done_removes_completed_items(self, tmp_path):
        _frob(["todo", "add", "keep"], tmp_path)
        _frob(["todo", "add", "discard"], tmp_path)
        _frob(["todo", "done", "2"], tmp_path)
        _frob(["todo", "clear-done"], tmp_path)

        r = _frob(["todo", "list", "--all"], tmp_path)
        out = _output(r)
        assert "keep" in out
        assert "discard" not in out

    def test_clear_done_preserves_pending(self, tmp_path):
        _frob(["todo", "add", "keep1"], tmp_path)
        _frob(["todo", "add", "keep2"], tmp_path)
        _frob(["todo", "add", "gone"], tmp_path)
        _frob(["todo", "done", "3"], tmp_path)
        _frob(["todo", "clear-done"], tmp_path)

        r = _frob(["todo", "list"], tmp_path)
        out = _output(r)
        assert "keep1" in out
        assert "keep2" in out

    def test_clear_done_on_empty_is_idempotent(self, tmp_path):
        r = _frob(["todo", "clear-done"], tmp_path)
        assert r.returncode == 0
        r2 = _frob(["todo", "clear-done"], tmp_path)
        assert r2.returncode == 0


class TestTodoRemove:
    def test_remove_deletes_permanently(self, tmp_path):
        _frob(["todo", "add", "delete me"], tmp_path)
        _frob(["todo", "remove", "1"], tmp_path)
        r = _frob(["todo", "list", "--all"], tmp_path)
        assert "delete me" not in _output(r)

    def test_remove_does_not_affect_siblings(self, tmp_path):
        _frob(["todo", "add", "alpha"], tmp_path)
        _frob(["todo", "add", "beta"], tmp_path)
        _frob(["todo", "add", "gamma"], tmp_path)
        _frob(["todo", "remove", "2"], tmp_path)
        r = _frob(["todo", "list"], tmp_path)
        out = _output(r)
        assert "alpha" in out
        assert "beta" not in out
        assert "gamma" in out
