"""End-to-end tests for `frob mission`."""

from tests.system.conftest import run


class TestMissionNew:
    def test_creates_file(self, tmp_path):
        r = run("mission", "new", "fix", cwd=str(tmp_path))
        assert r.returncode == 0
        r.stdout.strip() or r.stderr.strip()
        # Should print the path to the mission file
        mission_files = list((tmp_path / ".frob" / "missions").glob("*.md"))
        assert len(mission_files) == 1

    def test_invalid_type(self, tmp_path):
        r = run("mission", "new", "bogus", cwd=str(tmp_path))
        assert r.returncode != 0

    def test_with_error_flag(self, tmp_path):
        r = run(
            "mission", "new", "fix", "--error", "TypeError: oops", cwd=str(tmp_path)
        )
        assert r.returncode == 0
        files = list((tmp_path / ".frob" / "missions").glob("*.md"))
        assert "TypeError: oops" in files[0].read_text()


class TestMissionList:
    def test_empty(self, tmp_path):
        r = run("mission", "list", cwd=str(tmp_path))
        assert r.returncode == 0
        assert "no pending" in (r.stdout + r.stderr).lower()

    def test_lists_created(self, tmp_path):
        run("mission", "new", "fix", cwd=str(tmp_path))
        run("mission", "new", "test", cwd=str(tmp_path))
        r = run("mission", "list", cwd=str(tmp_path))
        assert r.returncode == 0
        output = r.stdout + r.stderr
        assert "fix" in output
        assert "test" in output


class TestMissionDone:
    def _make_mission(self, tmp_path):
        run("mission", "new", "fix", cwd=str(tmp_path))
        files = list((tmp_path / ".frob" / "missions").glob("*.md"))
        assert files
        return files[0].stem

    def test_done_removes_file(self, tmp_path):
        mid = self._make_mission(tmp_path)
        r = run("mission", "done", mid, cwd=str(tmp_path))
        assert r.returncode == 0
        assert not (tmp_path / ".frob" / "missions" / f"{mid}.md").exists()

    def test_done_not_found(self, tmp_path):
        r = run("mission", "done", "deadbeef", cwd=str(tmp_path))
        assert r.returncode != 0


class TestMissionStuck:
    def _make_mission(self, tmp_path):
        run("mission", "new", "fix", cwd=str(tmp_path))
        files = list((tmp_path / ".frob" / "missions").glob("*.md"))
        return files[0].stem

    def test_stuck_moves_file(self, tmp_path):
        mid = self._make_mission(tmp_path)
        r = run("mission", "stuck", mid, "cannot find symbol", cwd=str(tmp_path))
        assert r.returncode == 0
        assert not (tmp_path / ".frob" / "missions" / f"{mid}.md").exists()
        stuck = tmp_path / ".frob" / "missions" / "stuck" / f"{mid}.md"
        assert stuck.exists()
        assert "cannot find symbol" in stuck.read_text()

    def test_stuck_not_in_list(self, tmp_path):
        mid = self._make_mission(tmp_path)
        run("mission", "stuck", mid, "reason", cwd=str(tmp_path))
        r = run("mission", "list", cwd=str(tmp_path))
        assert mid not in (r.stdout + r.stderr)
