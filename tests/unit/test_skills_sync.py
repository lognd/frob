"""Tests for `frob sync-skills` (T-2241): `frob.scaffold._skills_sync`'s
bidirectional agents/skills -> ~/.claude sync, replacing Makefile's old
bash for-loop recipe. Every test uses a temp directory as the "claude
dir" target -- never the real `~/.claude` (per the ticket's own
MUST-STILL-PASS instruction)."""

from __future__ import annotations

import re
from pathlib import Path

from frob.scaffold._skills_sync import run, sync_skills

#: T-2241 acceptance[2]: repo root, resolved the same way every other
#: Makefile-adjacent test in this repo does.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_MAKEFILE = (_REPO_ROOT / "Makefile").read_text(encoding="utf-8")


def _make_entry(root: Path, *parts: str, content: str = "x") -> Path:
    """Create `root/<parts...>/` with one file inside, return the dir."""
    d = root.joinpath(*parts)
    d.mkdir(parents=True, exist_ok=True)
    (d / "content.txt").write_text(content, encoding="utf-8")
    return d


class TestSyncSkills:
    """`sync_skills(repo_root, claude_dir)` -- the pure sync function."""

    def test_syncs_new_repo_entries(self, tmp_path: Path) -> None:
        """A repo-side agents/skills entry appears under claude_dir after
        one call (T-2241 acceptance[0])."""
        repo = tmp_path / "repo"
        claude_dir = tmp_path / "claude"
        _make_entry(repo, "agents", "foo", content="agent foo")
        _make_entry(repo, "skills", "bar", content="skill bar")

        reports = sync_skills(repo, claude_dir)

        assert reports["agents"].synced == ("foo",)
        assert reports["skills"].synced == ("bar",)
        assert (claude_dir / "agents" / "foo" / "content.txt").read_text() == (
            "agent foo"
        )
        assert (claude_dir / "skills" / "bar" / "content.txt").read_text() == (
            "skill bar"
        )

    def test_updates_existing_entry_in_place(self, tmp_path: Path) -> None:
        """A changed repo-side file overwrites the claude-side copy."""
        repo = tmp_path / "repo"
        claude_dir = tmp_path / "claude"
        _make_entry(repo, "agents", "foo", content="v1")
        sync_skills(repo, claude_dir)
        assert (claude_dir / "agents" / "foo" / "content.txt").read_text() == "v1"

        _make_entry(repo, "agents", "foo", content="v2")
        sync_skills(repo, claude_dir)
        assert (claude_dir / "agents" / "foo" / "content.txt").read_text() == "v2"

    def test_removes_stale_claude_side_entry(self, tmp_path: Path) -> None:
        """T-2241's own MUST-STILL-PASS: an existing ~/.claude entry with no
        repo-side counterpart is removed -- stale-entry cleanup, verified
        against a temp directory rather than the real ~/.claude."""
        repo = tmp_path / "repo"
        claude_dir = tmp_path / "claude"
        _make_entry(claude_dir, "agents", "stale-agent")
        (repo / "agents").mkdir(parents=True)  # repo side now empty

        reports = sync_skills(repo, claude_dir)

        assert reports["agents"].removed == ("stale-agent",)
        assert not (claude_dir / "agents" / "stale-agent").exists()

    def test_missing_repo_directories_are_a_no_op(self, tmp_path: Path) -> None:
        """A repo with neither agents/ nor skills/ still creates both
        target directories (matching the old recipe's unconditional
        `mkdir -p`) but syncs/removes nothing."""
        repo = tmp_path / "repo"
        claude_dir = tmp_path / "claude"
        repo.mkdir()

        reports = sync_skills(repo, claude_dir)

        assert reports["agents"].synced == ()
        assert reports["agents"].removed == ()
        assert reports["skills"].synced == ()
        assert reports["skills"].removed == ()
        assert (claude_dir / "agents").is_dir()
        assert (claude_dir / "skills").is_dir()

    def test_files_directly_under_claude_dir_are_left_alone(
        self, tmp_path: Path
    ) -> None:
        """A stray non-directory entry under claude_dir/<kind> (not a
        `<name>/` directory) is never removed -- mirrors the old recipe's
        `[ -d "$d" ] || continue` guard."""
        repo = tmp_path / "repo"
        claude_dir = tmp_path / "claude"
        (repo / "agents").mkdir(parents=True)
        claude_agents = claude_dir / "agents"
        claude_agents.mkdir(parents=True)
        stray_file = claude_agents / "README.md"
        stray_file.write_text("not a synced entry", encoding="utf-8")

        sync_skills(repo, claude_dir)

        assert stray_file.exists()


class TestMakefileRecipeDelegates:
    """T-2241 acceptance[2]: `sync-skills:`'s recipe body is a single `uv
    run frob sync-skills` line, not the old ~35-line bash for-loop."""

    def test_recipe_body_is_a_single_line(self) -> None:
        match = re.search(r"^sync-skills:[^\n]*\n(?:\t.*\n)*", _MAKEFILE, re.MULTILINE)
        assert match is not None, "sync-skills: recipe not found in Makefile"
        recipe = match.group(0)
        lines = [line for line in recipe.splitlines()[1:] if line.strip()]
        assert lines == ["\tuv run frob sync-skills"], recipe


class TestRun:
    """`run(argv)` -- the CLI entry point `frob.__main__._dispatch` calls
    directly for `frob sync-skills`."""

    def test_run_reports_synced_and_removed_counts(
        self, tmp_path: Path, capsys, monkeypatch
    ) -> None:
        """`run` exits 0 and prints the total synced/removed counts,
        exercising the same `--claude-dir` override tests use to avoid
        ever touching the real `~/.claude` (T-2241's own instruction)."""
        repo = tmp_path / "repo"
        claude_dir = tmp_path / "claude"
        _make_entry(repo, "agents", "foo")
        _make_entry(claude_dir, "skills", "stale-skill")
        (repo / "skills").mkdir(parents=True)

        monkeypatch.setenv("HOME", str(tmp_path / "unused-home"))
        try:
            run([str(repo), "--claude-dir", str(claude_dir)])
        except SystemExit as exc:
            assert exc.code == 0
        else:
            raise AssertionError("run() must call sys.exit(0)")

        out = capsys.readouterr().out
        assert "synced agent: foo" in out
        assert "removed stale skill: stale-skill" in out
        assert "1 synced, 1 removed" in out
        assert (claude_dir / "agents" / "foo").is_dir()
        assert not (claude_dir / "skills" / "stale-skill").exists()

    def test_run_defaults_to_home_claude_when_no_override_given(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """No `--claude-dir` falls back to `~/.claude` -- proven against a
        monkeypatched `HOME` pointed at a temp directory, never the real
        one."""
        repo = tmp_path / "repo"
        fake_home = tmp_path / "fake-home"
        fake_home.mkdir()
        _make_entry(repo, "skills", "baz")
        monkeypatch.setenv("HOME", str(fake_home))

        try:
            run([str(repo)])
        except SystemExit as exc:
            assert exc.code == 0
        else:
            raise AssertionError("run() must call sys.exit(0)")

        assert (fake_home / ".claude" / "skills" / "baz").is_dir()
