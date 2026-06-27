"""End-to-end tests for `frob todo`."""

from tests.system.conftest import run


class TestTodoAdd:
    def test_add_single_item(self, tmp_path):
        r = run("todo", "add", "fix the thing", cwd=tmp_path)
        assert r.returncode == 0
        out = r.stdout + r.stderr
        assert "#1" in out or "added" in out.lower()

    def test_add_creates_frob_dir(self, tmp_path):
        run("todo", "add", "first item", cwd=tmp_path)
        assert (tmp_path / ".frob").is_dir()

    def test_add_creates_todo_md(self, tmp_path):
        run("todo", "add", "first item", cwd=tmp_path)
        assert (tmp_path / ".frob" / "todo.md").exists()

    def test_add_multiple_increments_ids(self, tmp_path):
        run("todo", "add", "item one", cwd=tmp_path)
        run("todo", "add", "item two", cwd=tmp_path)
        r = run("todo", "add", "item three", cwd=tmp_path)
        out = r.stdout + r.stderr
        assert "#3" in out or "3" in out


class TestTodoList:
    def test_list_empty_succeeds(self, tmp_path):
        r = run("todo", "list", cwd=tmp_path)
        assert r.returncode == 0

    def test_list_shows_added_items(self, tmp_path):
        run("todo", "add", "write documentation", cwd=tmp_path)
        r = run("todo", "list", cwd=tmp_path)
        assert r.returncode == 0
        assert "write documentation" in (r.stdout + r.stderr)

    def test_list_shows_all_pending(self, tmp_path):
        run("todo", "add", "alpha task", cwd=tmp_path)
        run("todo", "add", "beta task", cwd=tmp_path)
        r = run("todo", "list", cwd=tmp_path)
        out = r.stdout + r.stderr
        assert "alpha task" in out
        assert "beta task" in out

    def test_list_hides_done_by_default(self, tmp_path):
        run("todo", "add", "pending", cwd=tmp_path)
        run("todo", "add", "finished", cwd=tmp_path)
        run("todo", "done", "2", cwd=tmp_path)
        r = run("todo", "list", cwd=tmp_path)
        out = r.stdout + r.stderr
        assert "pending" in out
        assert "finished" not in out

    def test_list_all_shows_done(self, tmp_path):
        run("todo", "add", "pending", cwd=tmp_path)
        run("todo", "add", "finished", cwd=tmp_path)
        run("todo", "done", "2", cwd=tmp_path)
        r = run("todo", "list", "--all", cwd=tmp_path)
        out = r.stdout + r.stderr
        assert "finished" in out


class TestTodoDone:
    def test_done_marks_item_complete(self, tmp_path):
        run("todo", "add", "task to complete", cwd=tmp_path)
        r = run("todo", "done", "1", cwd=tmp_path)
        assert r.returncode == 0

    def test_done_item_hidden_from_list(self, tmp_path):
        run("todo", "add", "complete me", cwd=tmp_path)
        run("todo", "done", "1", cwd=tmp_path)
        r = run("todo", "list", cwd=tmp_path)
        assert "complete me" not in (r.stdout + r.stderr)

    def test_done_unknown_id_fails(self, tmp_path):
        r = run("todo", "done", "999", cwd=tmp_path)
        assert r.returncode != 0


class TestTodoRemove:
    def test_remove_deletes_item(self, tmp_path):
        run("todo", "add", "to remove", cwd=tmp_path)
        r = run("todo", "remove", "1", cwd=tmp_path)
        assert r.returncode == 0

    def test_remove_item_absent_from_list_all(self, tmp_path):
        run("todo", "add", "to remove", cwd=tmp_path)
        run("todo", "remove", "1", cwd=tmp_path)
        r = run("todo", "list", "--all", cwd=tmp_path)
        assert "to remove" not in (r.stdout + r.stderr)

    def test_remove_unknown_id_fails(self, tmp_path):
        r = run("todo", "remove", "999", cwd=tmp_path)
        assert r.returncode != 0


class TestTodoClearDone:
    def test_clear_done_removes_completed(self, tmp_path):
        run("todo", "add", "keep this", cwd=tmp_path)
        run("todo", "add", "done this", cwd=tmp_path)
        run("todo", "done", "2", cwd=tmp_path)
        r = run("todo", "clear-done", cwd=tmp_path)
        assert r.returncode == 0
        r = run("todo", "list", "--all", cwd=tmp_path)
        out = r.stdout + r.stderr
        assert "keep this" in out
        assert "done this" not in out

    def test_clear_done_empty_is_safe(self, tmp_path):
        r = run("todo", "clear-done", cwd=tmp_path)
        assert r.returncode == 0
