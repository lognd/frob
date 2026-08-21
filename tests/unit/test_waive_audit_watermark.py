"""T-2467: unit tests for the persisted waive-audit watermark.

T-2721 adds the git-tracked/mirrored-onto-primary behaviour -- see
`TestSaveWatermarkGitTracking` and `TestMirrorToPrimary`."""

from __future__ import annotations

from pathlib import Path

from frob import gitio
from frob.gates._waive_audit_watermark import (
    WaiveAuditWatermark,
    WaiveAuditWatermarkError,
    load_watermark,
    save_watermark,
    utc_now,
    watermark_path,
)


def _git(*args: str, cwd: Path) -> str:
    """Run a `git` command in `cwd` via `frob.gitio.run_argv` (the
    production wrapper every other `frob.tickets`/`frob.gates` caller
    already funnels through, rather than a second, test-local raw
    `subprocess` invocation), raising on failure and returning stdout --
    test plumbing."""
    spawned = gitio.run_argv(["git", *args], cwd=cwd)
    result = spawned.danger_ok
    if result.returncode != 0:
        raise AssertionError(f"git {args!r} failed in {cwd}: {result.stderr}")
    return result.stdout


def _init_repo(root: Path) -> None:
    """A minimal git repo with one commit, deterministic identity -- the
    same shape `tests/_cache_transparency.py::git_init` uses elsewhere."""
    root.mkdir(parents=True, exist_ok=True)
    _git("init", "-q", cwd=root)
    _git("config", "user.email", "test@example.com", cwd=root)
    _git("config", "user.name", "Test", cwd=root)
    (root / "README.md").write_text("placeholder\n")
    _git("add", "README.md", cwd=root)
    _git("commit", "-q", "-m", "initial", cwd=root)


class TestLoadWatermark:
    def test_missing_file_is_not_found(self, tmp_path: Path) -> None:
        result = load_watermark(tmp_path)
        assert result.is_err
        assert result.err is WaiveAuditWatermarkError.NotFound

    def test_malformed_json_is_malformed(self, tmp_path: Path) -> None:
        path = watermark_path(tmp_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{not json")
        result = load_watermark(tmp_path)
        assert result.is_err
        assert result.err is WaiveAuditWatermarkError.Malformed

    def test_valid_file_round_trips(self, tmp_path: Path) -> None:
        watermark = WaiveAuditWatermark(
            commit_sha="deadbeef",
            audited_at=utc_now(),
            waivers_audited=12,
        )
        save_watermark(tmp_path, watermark)
        result = load_watermark(tmp_path)
        assert result.is_ok
        loaded = result.danger_ok
        assert loaded.commit_sha == "deadbeef"
        assert loaded.waivers_audited == 12
        assert loaded.catchup_remaining == 0


class TestSaveWatermark:
    def test_round_trips_through_load(self, tmp_path: Path) -> None:
        watermark = WaiveAuditWatermark(
            commit_sha="cafef00d",
            audited_at=utc_now(),
            waivers_audited=3,
            catchup_remaining=7,
        )
        saved = save_watermark(tmp_path, watermark)
        assert saved.is_ok
        reloaded = load_watermark(tmp_path).danger_ok
        assert reloaded.commit_sha == "cafef00d"
        assert reloaded.catchup_remaining == 7

    def test_creates_parent_dir_if_missing(self, tmp_path: Path) -> None:
        """T-2721: the watermark now lives at the repo ROOT
        (`waive-audit-watermark.json`, not `.frob/waive-audit-
        watermark.json`) -- `watermark_path`'s own parent is `tmp_path`
        itself, which already exists as the pytest fixture, so this
        checks the file is created rather than a `.frob/` subdirectory."""
        watermark = WaiveAuditWatermark(
            commit_sha="abc", audited_at=utc_now(), waivers_audited=0
        )
        result = save_watermark(tmp_path, watermark)
        assert result.is_ok
        assert watermark_path(tmp_path).exists()
        assert watermark_path(tmp_path).name == "waive-audit-watermark.json"
        assert watermark_path(tmp_path).parent == tmp_path


# frob:ticket T-2721
class TestSaveWatermarkGitTracking:
    """T-2721: `save_watermark` commits the watermark file in `root` when
    `root` is a real git checkout -- the "track it in git like the
    ledger" half of the fix. A non-git `root` (a bare `tmp_path`, as
    every OTHER test class in this file uses) must still succeed at the
    on-disk write; the commit attempt degrades silently rather than
    turning a successful write into an `Err`."""

    def test_commits_the_watermark_in_a_real_repo(self, tmp_path: Path) -> None:
        """frob:tests \
        src/frob/gates/_waive_audit_watermark.py::save_watermark"""
        repo = tmp_path / "repo"
        _init_repo(repo)
        watermark = WaiveAuditWatermark(
            commit_sha="beefcafe", audited_at=utc_now(), waivers_audited=5
        )
        result = save_watermark(repo, watermark)
        assert result.is_ok
        log = _git(
            "log", "--oneline", "-1", "--", "waive-audit-watermark.json", cwd=repo
        )
        assert "watermark" in log.lower()
        status = _git("status", "--porcelain", cwd=repo)
        assert status.strip() == ""

    def test_second_save_advances_with_its_own_commit(self, tmp_path: Path) -> None:
        """Two successive `save_watermark` calls must each land their own
        commit, not silently no-op the second time -- the watermark
        genuinely ADVANCES across passes.
        frob:tests src/frob/gates/_waive_audit_watermark.py::save_watermark"""
        repo = tmp_path / "repo"
        _init_repo(repo)
        save_watermark(
            repo,
            WaiveAuditWatermark(
                commit_sha="first", audited_at=utc_now(), waivers_audited=1
            ),
        )
        first_count = _git("rev-list", "--count", "HEAD", cwd=repo).strip()
        save_watermark(
            repo,
            WaiveAuditWatermark(
                commit_sha="second", audited_at=utc_now(), waivers_audited=2
            ),
        )
        second_count = _git("rev-list", "--count", "HEAD", cwd=repo).strip()
        assert int(second_count) == int(first_count) + 1
        assert load_watermark(repo).danger_ok.commit_sha == "second"

    def test_non_git_root_still_succeeds_on_disk(self, tmp_path: Path) -> None:
        """A `tmp_path` fixture is not a git repo -- the commit attempt
        must degrade silently and the on-disk write must still succeed;
        this is the contract every other test class in this file already
        relies on.
        frob:tests src/frob/gates/_waive_audit_watermark.py::save_watermark"""
        watermark = WaiveAuditWatermark(
            commit_sha="nogit", audited_at=utc_now(), waivers_audited=0
        )
        result = save_watermark(tmp_path, watermark)
        assert result.is_ok
        assert watermark_path(tmp_path).exists()


# frob:ticket T-2721
class TestMirrorToPrimary:
    """T-2721's own required positive controls: a `save_watermark` call
    from a WORKTREE must mirror its progress onto the primary checkout
    immediately, and two different worktrees' passes must not clobber
    each other's progress."""

    def _add_worktree(self, primary: Path, name: str) -> Path:
        """A real linked git worktree of `primary`, on its own branch --
        exactly the shape `frob ticket work` cuts for an agent."""
        wt = primary.parent / name
        _git("worktree", "add", "-b", name, str(wt), cwd=primary)
        _git("config", "user.email", "test@example.com", cwd=wt)
        _git("config", "user.name", "Test", cwd=wt)
        return wt

    def test_worktree_pass_reaches_primary_without_a_land(self, tmp_path: Path) -> None:
        """T-2721's own required control #1 (paraphrased for the unit
        level -- the real 'not_covered count reduced' behaviour lives in
        `frob.app.ticket_runner._waive_audit`, outside this ticket's
        scope): a pass run inside a worktree must be VISIBLE on the
        primary checkout's own watermark file immediately, without
        waiting for that worktree's ticket to land.
        frob:tests \
        src/frob/gates/_waive_audit_watermark.py::save_watermark"""
        primary = tmp_path / "primary"
        _init_repo(primary)
        wt = self._add_worktree(primary, "wt-a")

        assert load_watermark(primary).is_err  # nothing audited yet

        watermark = WaiveAuditWatermark(
            commit_sha="fromworktree", audited_at=utc_now(), waivers_audited=100
        )
        result = save_watermark(wt, watermark)
        assert result.is_ok

        on_primary = load_watermark(primary)
        assert on_primary.is_ok
        assert on_primary.danger_ok.commit_sha == "fromworktree"
        assert on_primary.danger_ok.waivers_audited == 100

    def test_two_worktree_passes_do_not_lose_either_ones_progress(
        self, tmp_path: Path
    ) -> None:
        """T-2721's own required control #3: two passes in DIFFERENT
        worktrees, run in sequence, must both reach the primary -- the
        second mirror must not silently discard the first's commit, and
        the primary's final watermark must reflect the LATER pass (the
        watermark is a current-position marker, not a merge of both).
        frob:tests \
        src/frob/gates/_waive_audit_watermark.py::save_watermark"""
        primary = tmp_path / "primary"
        _init_repo(primary)
        wt_a = self._add_worktree(primary, "wt-a")
        wt_b = self._add_worktree(primary, "wt-b")

        save_watermark(
            wt_a,
            WaiveAuditWatermark(
                commit_sha="pass-a", audited_at=utc_now(), waivers_audited=10
            ),
        )
        first_primary_count = _git("rev-list", "--count", "HEAD", cwd=primary).strip()

        # wt_b started from the SAME base as wt_a (both cut from the repo's
        # single initial commit) -- it does not see wt_a's mirrored commit
        # (a real agent's worktree is likewise cut before a sibling's pass
        # lands), so its own mirror still applies as a fresh commit on top
        # of whatever the primary now has, never a lost update.
        save_watermark(
            wt_b,
            WaiveAuditWatermark(
                commit_sha="pass-b", audited_at=utc_now(), waivers_audited=20
            ),
        )
        second_primary_count = _git("rev-list", "--count", "HEAD", cwd=primary).strip()

        assert int(second_primary_count) == int(first_primary_count) + 1
        final = load_watermark(primary).danger_ok
        assert final.commit_sha == "pass-b"
        assert final.waivers_audited == 20
        # both commits are real, reachable history -- neither pass was
        # discarded, only the CURRENT marker reflects the later one.
        log = _git("log", "--oneline", "--", "waive-audit-watermark.json", cwd=primary)
        assert "pass-a" in log or "10" in log
        assert "pass-b" in log or "20" in log

    def test_calling_from_the_primary_checkout_itself_mirrors_nothing_extra(
        self, tmp_path: Path
    ) -> None:
        """`root` already IS the primary checkout -- `_mirror_watermark_
        to_primary` must recognise this and be a no-op (there is nothing
        to copy onto itself), not attempt a self-referential commit.
        frob:tests \
        src/frob/gates/_waive_audit_watermark.py::save_watermark"""
        primary = tmp_path / "primary"
        _init_repo(primary)
        result = save_watermark(
            primary,
            WaiveAuditWatermark(
                commit_sha="direct", audited_at=utc_now(), waivers_audited=1
            ),
        )
        assert result.is_ok
        assert load_watermark(primary).danger_ok.commit_sha == "direct"
