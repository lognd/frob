"""Unit tests for frob.mission."""

from pathlib import Path

import pytest

from frob.mission import (
    MissionError,
    create_mission,
    done_mission,
    list_missions,
    stuck_mission,
)


class TestCreateMission:
    def test_creates_file(self, tmp_path):
        result = create_mission("fix", project_root=tmp_path)
        assert result.is_ok
        path = result.danger_ok
        assert path.exists()
        assert path.suffix == ".md"

    def test_unknown_type(self, tmp_path):
        result = create_mission("bogus", project_root=tmp_path)
        assert result.is_err
        assert result.danger_err == MissionError.InvalidType

    def test_all_types(self, tmp_path):
        for t in ("fix", "test", "implement", "review"):
            r = create_mission(t, project_root=tmp_path)
            assert r.is_ok, f"type={t}"

    def test_content_has_instructions(self, tmp_path):
        result = create_mission("fix", project_root=tmp_path, error="TypeError: oops")
        content = result.danger_ok.read_text()
        assert "STUCK" in content
        assert "TypeError: oops" in content

    def test_gitignore_updated(self, tmp_path):
        create_mission("fix", project_root=tmp_path)
        gi = tmp_path / ".gitignore"
        assert gi.exists()
        assert ".frob/" in gi.read_text()

    def test_gitignore_not_duplicated(self, tmp_path):
        (tmp_path / ".gitignore").write_text(".frob/\n")
        create_mission("fix", project_root=tmp_path)
        text = (tmp_path / ".gitignore").read_text()
        assert text.count(".frob/") == 1

    def test_mission_with_target_and_file(self, tmp_path):
        py_file = tmp_path / "mod.py"
        py_file.write_text("def foo():\n    ...\n")
        result = create_mission(
            "implement",
            project_root=tmp_path,
            file=py_file,
            target="foo",
        )
        assert result.is_ok
        content = result.danger_ok.read_text()
        assert "foo" in content


class TestDoneMission:
    def test_removes_file(self, tmp_path):
        r = create_mission("fix", project_root=tmp_path)
        mission_id = r.danger_ok.stem
        done = done_mission(mission_id, tmp_path)
        assert done.is_ok
        assert not r.danger_ok.exists()

    def test_not_found(self, tmp_path):
        result = done_mission("deadbeef", tmp_path)
        assert result.is_err
        assert result.danger_err == MissionError.NotFound


class TestStuckMission:
    def test_moves_to_stuck(self, tmp_path):
        r = create_mission("fix", project_root=tmp_path)
        path = r.danger_ok
        mission_id = path.stem
        stuck = stuck_mission(mission_id, "can't find the symbol", tmp_path)
        assert stuck.is_ok
        assert not path.exists()
        stuck_path = stuck.danger_ok
        assert stuck_path.exists()
        assert "stuck" in str(stuck_path)
        assert "can't find the symbol" in stuck_path.read_text()

    def test_not_found(self, tmp_path):
        result = stuck_mission("deadbeef", "reason", tmp_path)
        assert result.is_err
        assert result.danger_err == MissionError.NotFound


class TestListMissions:
    def test_empty(self, tmp_path):
        assert list_missions(tmp_path) == []

    def test_lists_pending(self, tmp_path):
        create_mission("fix", project_root=tmp_path)
        create_mission("test", project_root=tmp_path)
        missions = list_missions(tmp_path)
        assert len(missions) == 2
        types = {t for _, t in missions}
        assert "fix" in types
        assert "test" in types

    def test_stuck_not_listed(self, tmp_path):
        r = create_mission("fix", project_root=tmp_path)
        stuck_mission(r.danger_ok.stem, "reason", tmp_path)
        assert list_missions(tmp_path) == []
