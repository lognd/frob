"""Tests for `frob sync-skills` (T-2241): `frob.scaffold._skills_sync`'s
bidirectional agents/skills -> ~/.claude sync, replacing Makefile's old
bash for-loop recipe. Every test uses a temp directory as the "claude
dir" target -- never the real `~/.claude` (per the ticket's own
MUST-STILL-PASS instruction)."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from frob.gates._render_lint import render_lint_gate
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

    def test_removes_stale_claude_side_entry_this_repo_previously_installed(
        self, tmp_path: Path
    ) -> None:
        """T-2241's own MUST-STILL-PASS, narrowed by T-2386's provenance fix:
        an existing ~/.claude entry THIS REPO installed on a prior sync,
        with no repo-side counterpart left, is removed -- stale-entry
        cleanup still works for entries this repo actually owns, verified
        against a temp directory rather than the real ~/.claude. (The
        pre-T-2386 version of this test synced a claude-side entry with NO
        prior manifest record and asserted removal -- that was the exact
        cross-repo-deletion defect T-2386 fixes; see
        `TestSyncSkillsProvenance.test_hand_maintained_entry_is_never_deleted_or_overwritten`  # noqa: E501
        for the corrected first-run behavior.)"""
        repo = tmp_path / "repo"
        claude_dir = tmp_path / "claude"
        _make_entry(repo, "agents", "temp-agent")
        first = sync_skills(repo, claude_dir)
        assert first["agents"].synced == ("temp-agent",)

        shutil.rmtree(repo / "agents" / "temp-agent")  # repo side now empty

        reports = sync_skills(repo, claude_dir)

        assert reports["agents"].removed == ("temp-agent",)
        assert not (claude_dir / "agents" / "temp-agent").exists()

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


# frob:ticket T-2386
class TestSyncSkillsProvenance:
    """T-2386 (child of T-2384): provenance-manifest-backed cooperation
    between two frob repos syncing agents/skills into the same
    `~/.claude` -- must-now-fire/must-not-delete coverage for the
    epic's acceptance[1]/[2]. Never touches the real `~/.claude`."""

    def test_second_repo_does_not_delete_first_repos_entries(
        self, tmp_path: Path
    ) -> None:
        """T-2384 acceptance[1]: two different repos syncing into the same
        claude_dir never remove each other's entries. Repo A installs
        `agents/alpha`; repo B (no `alpha` of its own) then syncs its own
        `agents/beta` -- repo A's `alpha` must survive repo B's run, even
        though `alpha` has no counterpart in repo B."""
        claude_dir = tmp_path / "claude"
        repo_a = tmp_path / "repo-a"
        repo_b = tmp_path / "repo-b"
        _make_entry(repo_a, "agents", "alpha")
        _make_entry(repo_b, "agents", "beta")

        sync_skills(repo_a, claude_dir)
        sync_skills(repo_b, claude_dir)

        assert (claude_dir / "agents" / "alpha").is_dir()
        assert (claude_dir / "agents" / "beta").is_dir()

        # Alternating a second time must not flap alpha out either.
        sync_skills(repo_a, claude_dir)
        sync_skills(repo_b, claude_dir)
        assert (claude_dir / "agents" / "alpha").is_dir()
        assert (claude_dir / "agents" / "beta").is_dir()

    def test_hand_maintained_entry_is_never_deleted_or_overwritten(
        self, tmp_path: Path
    ) -> None:
        """T-2384 acceptance[2]: a ~/.claude containing a hand-maintained
        agent no frob repo installed survives a repo's first sync
        untouched -- neither deleted (it has no repo-side counterpart)
        nor overwritten (the repo happens to ship a same-named entry)."""
        claude_dir = tmp_path / "claude"
        repo = tmp_path / "repo"
        hand = _make_entry(claude_dir, "agents", "hand-made", content="mine")
        (repo / "agents").mkdir(parents=True)  # repo side has nothing

        reports = sync_skills(repo, claude_dir)

        assert reports["agents"].removed == ()
        assert hand.exists()
        assert (hand / "content.txt").read_text() == "mine"

    def test_hand_maintained_entry_collides_instead_of_being_overwritten(
        self, tmp_path: Path
    ) -> None:
        """Same as above, but the repo DOES ship a same-named entry: the
        collision is reported and the hand-maintained content is left
        alone, not silently overwritten."""
        claude_dir = tmp_path / "claude"
        repo = tmp_path / "repo"
        _make_entry(claude_dir, "agents", "foo", content="hand-made")
        _make_entry(repo, "agents", "foo", content="repo-version")

        reports = sync_skills(repo, claude_dir)

        assert reports["agents"].collisions == ("foo",)
        assert reports["agents"].synced == ()
        assert (
            claude_dir / "agents" / "foo" / "content.txt"
        ).read_text() == "hand-made"

    def test_force_overwrites_collision_and_claims_ownership(
        self, tmp_path: Path
    ) -> None:
        """`force=True` overwrites a collision and this repo now owns the
        entry -- a subsequent unforced sync updates it in place rather
        than colliding again."""
        claude_dir = tmp_path / "claude"
        repo = tmp_path / "repo"
        _make_entry(claude_dir, "agents", "foo", content="hand-made")
        _make_entry(repo, "agents", "foo", content="v1")

        reports = sync_skills(repo, claude_dir, force=True)
        assert reports["agents"].synced == ("foo",)
        assert reports["agents"].collisions == ()
        assert (claude_dir / "agents" / "foo" / "content.txt").read_text() == "v1"

        _make_entry(repo, "agents", "foo", content="v2")
        reports2 = sync_skills(repo, claude_dir)  # no force needed now
        assert reports2["agents"].synced == ("foo",)
        assert reports2["agents"].collisions == ()
        assert (claude_dir / "agents" / "foo" / "content.txt").read_text() == "v2"

    def test_same_repo_sync_twice_is_a_no_op_second_run(self, tmp_path: Path) -> None:
        """T-2384 acceptance[1]: running the same repo's sync twice in a
        row produces no further change on the second run -- no new
        collisions, no removals, and the manifest's ownership set is
        stable."""
        claude_dir = tmp_path / "claude"
        repo = tmp_path / "repo"
        _make_entry(repo, "agents", "foo")
        _make_entry(repo, "skills", "bar")

        sync_skills(repo, claude_dir)
        manifest_after_first = json.loads(
            (claude_dir / ".frob-sync-manifest.json").read_text(encoding="utf-8")
        )

        reports = sync_skills(repo, claude_dir)
        manifest_after_second = json.loads(
            (claude_dir / ".frob-sync-manifest.json").read_text(encoding="utf-8")
        )

        assert reports["agents"].removed == ()
        assert reports["agents"].collisions == ()
        assert reports["skills"].removed == ()
        assert reports["skills"].collisions == ()
        assert manifest_after_first == manifest_after_second

    def test_manifest_records_only_this_repos_owned_entries(
        self, tmp_path: Path
    ) -> None:
        """The on-disk manifest is keyed by resolved repo root and lists
        exactly the `<kind>/<name>` entries that repo installed -- the
        provenance record `sync_skills`'s cross-repo/hand-maintained
        guards read back on every subsequent call."""
        claude_dir = tmp_path / "claude"
        repo = tmp_path / "repo"
        _make_entry(repo, "agents", "foo")

        sync_skills(repo, claude_dir)

        manifest = json.loads(
            (claude_dir / ".frob-sync-manifest.json").read_text(encoding="utf-8")
        )
        assert manifest[str(repo.resolve())]["agents"] == ["foo"]
        assert manifest[str(repo.resolve())]["skills"] == []


# frob:ticket T-2268
class TestSkillsSyncRenderLint:
    """T-2268: `_skills_sync.py::run` used to write through bare `print`
    calls (a RENDER001 regression from T-2241's own land, hours old at the
    time this ticket was filed) instead of routing through
    `frob.render.Renderer` like every other CLI entry point in this repo.
    `render_lint_gate` scans this repo's own git-tracked source directly,
    so this genuinely reproduces against the pre-fix source (RENDER001
    fires) and passes against the fixed source (it does not)."""

    def test_no_render001_violations_for_skills_sync(self) -> None:
        """`render_lint_gate(_REPO_ROOT)` reports zero RENDER001 violations
        for `src/frob/scaffold/_skills_sync.py` (T-2268 acceptance[1])."""
        violations = render_lint_gate(_REPO_ROOT)
        offenders = [
            v
            for v in violations
            if v.rule == "RENDER001" and v.file == "src/frob/scaffold/_skills_sync.py"
        ]
        assert offenders == []


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
        ever touching the real `~/.claude` (T-2241's own instruction).
        The stale entry removed here is one THIS repo installed on a
        prior `run` -- an unowned/hand-maintained entry is never removed
        (T-2386), covered separately by `TestSyncSkillsProvenance`."""
        repo = tmp_path / "repo"
        claude_dir = tmp_path / "claude"
        _make_entry(repo, "agents", "foo")
        _make_entry(repo, "skills", "stale-skill")
        monkeypatch.setenv("HOME", str(tmp_path / "unused-home"))
        try:
            run([str(repo), "--claude-dir", str(claude_dir)])  # first: installs both
        except SystemExit:
            pass
        shutil.rmtree(repo / "skills" / "stale-skill")  # repo side drops it

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
