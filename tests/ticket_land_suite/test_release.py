from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest
from typani.result import Err, Ok

import frob.tickets._land_release as _land_release_mod
from frob.gitio import ProcResult, run_argv
from frob.tickets import (
    new_ticket,
)
from frob.tickets._land import land
from frob.tickets._models import (
    LandError,
)
from tests.ticket_land_suite.conftest import (
    _commit_all,
    _make_closeable,
    _run,
    _spec,
    _status_ignoring_frob,
)

pytestmark = pytest.mark.heavy_subprocess



# frob:ticket T-0338
class TestReleaseBump:
    """T-0338: `land`'s optional `bump_version` callback -- the REL001
    version-bump/stamp coordinator step folded into `land` itself."""

    def test_bump_applied_and_reported(self, repo: Path) -> None:
        # frob:tests \
        # tests/test_ticket_land.py::TestReleaseBump.test_bump_applied_and_reported
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-bump", str(wt)], repo)
        created = new_ticket(wt, _spec("Bump me", scope=("src/bumped.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "bumped.py").write_text("# bumped\n")
        _commit_all(wt, "add bumped.py")

        def bump_version(root: Path, ticket: Any, final_id: str) -> Any:
            (root / "VERSION_BUMPED").write_text(final_id)
            _run(["git", "add", "VERSION_BUMPED"], root)
            return Ok("1.2.3")

        result = land(repo, tid, wt, dry_run=False, bump_version=bump_version)
        assert result.is_ok, result.err
        report = result.danger_ok
        assert report.release_bumped_to == "1.2.3"
        assert (repo / "VERSION_BUMPED").exists()
        # The bump's own write must have landed in the SAME commit as the
        # squash-apply, not a separate uncommitted change.
        assert _status_ignoring_frob(repo) == ""

    def test_no_bump_needed_reports_none(self, repo: Path) -> None:
        # frob:tests \
        # tests/test_ticket_land.py::TestReleaseBump.test_no_bump_needed_reports_none
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-nobump", str(wt)], repo)
        created = new_ticket(wt, _spec("No bump needed", scope=("src/quiet.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "quiet.py").write_text("# quiet\n")
        _commit_all(wt, "add quiet.py")

        result = land(
            repo,
            tid,
            wt,
            dry_run=False,
            bump_version=lambda root, ticket, fid: Ok(None),
        )
        assert result.is_ok, result.err
        assert result.danger_ok.release_bumped_to is None

    def test_bump_failure_unwinds_squash(self, repo: Path) -> None:
        # frob:tests \
        # tests/test_ticket_land.py::TestReleaseBump.test_bump_failure_unwinds_squash
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-badbump", str(wt)], repo)
        created = new_ticket(wt, _spec("Bad bump", scope=("src/badbump.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "badbump.py").write_text("# bad bump\n")
        _commit_all(wt, "add badbump.py")

        before_main_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()

        result = land(
            repo,
            tid,
            wt,
            dry_run=False,
            bump_version=lambda root, ticket, fid: Err(LandError.ReleaseBumpFailed),
        )
        assert result.is_err
        assert result.danger_err == LandError.ReleaseBumpFailed
        assert (
            _run(["git", "rev-parse", "HEAD"], repo).stdout.strip() == before_main_sha
        )
        assert _run(["git", "status", "--porcelain"], repo).stdout.strip() == ""

    def test_no_callback_is_noop(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestReleaseBump.test_no_callback_is_noop
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-nocallback", str(wt)], repo)
        created = new_ticket(wt, _spec("No callback", scope=("src/nc.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "nc.py").write_text("# no callback\n")
        _commit_all(wt, "add nc.py")

        result = land(repo, tid, wt, dry_run=False)
        assert result.is_ok, result.err
        assert result.danger_ok.release_bumped_to is None

    # frob:ticket T-0992
    def test_stale_worktree_version_bump_yields_main_plus_one(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestReleaseBump.test_stale_worktree_version_bump_yields_main_plus_one  # noqa: E501
        """T-0992 acceptance criterion: a worktree whose own pyproject.toml
        carries an OLDER version than main (it forked before some other
        land already bumped main) must still land at main-plus-one, never
        at a version recomputed from the worktree's stale carried value --
        the T-0976/T-0989 incident class. The `bump_version` callback here
        deliberately reads `root`'s (main's) CURRENT on-disk version, not
        the worktree's, modeling the fixed input-selection contract."""
        (repo / "pyproject.toml").write_text(
            '[project]\nname = "frob"\nversion = "0.183.0"\n'
        )
        _commit_all(repo, "main is ahead at 0.183.0")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-stale-version", str(wt)], repo)
        # The worktree's own pyproject still carries the OLDER version it
        # forked from main with -- never touched as part of this ticket's
        # scope, so it rides through the squash unchanged.
        (wt / "pyproject.toml").write_text(
            '[project]\nname = "frob"\nversion = "0.181.0"\n'
        )
        _commit_all(wt, "worktree still carries stale 0.181.0")

        created = new_ticket(wt, _spec("Stale worktree version", scope=("src/sv.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "sv.py").write_text("# stale version test\n")
        _commit_all(wt, "add sv.py")

        def bump_version(root: Path, ticket: Any, final_id: str) -> Any:
            # A correctly-implemented callback computes main+1 (0.184.0)
            # regardless of what the squash-apply did to the working
            # tree's pyproject.toml in between -- the T-0992 guard verifies
            # this independently against main's true pre-land committed
            # version, not the worktree's carried value.
            next_version = "0.184.0"
            (root / "pyproject.toml").write_text(
                f'[project]\nname = "frob"\nversion = "{next_version}"\n'
            )
            _run(["git", "add", "pyproject.toml"], root)
            return Ok(next_version)

        result = land(repo, tid, wt, dry_run=False, bump_version=bump_version)
        assert result.is_ok, result.err
        assert result.danger_ok.release_bumped_to == "0.184.0"
        assert (repo / "pyproject.toml").read_text().count('version = "0.184.0"') == 1

    # frob:ticket T-0992
    def test_downgrade_bump_is_refused(self, repo: Path) -> None:
        # frob:tests \
        # tests/test_ticket_land.py::TestReleaseBump.test_downgrade_bump_is_refused
        """T-0992 hard monotonicity refusal: a `bump_version` callback that
        computes a version no greater than main's CURRENT pre-land version
        (the T-0976/T-0989 failure mode -- a stale worktree-carried input
        winning over main's real version) must be refused loudly, and the
        staged squash unwound, rather than silently clobbering main."""
        (repo / "pyproject.toml").write_text(
            '[project]\nname = "frob"\nversion = "0.183.0"\n'
        )
        _commit_all(repo, "main is ahead at 0.183.0")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-downgrade", str(wt)], repo)
        created = new_ticket(wt, _spec("Downgrade bump", scope=("src/dg.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "dg.py").write_text("# downgrade test\n")
        _commit_all(wt, "add dg.py")

        before_main_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()

        def bump_version(root: Path, ticket: Any, final_id: str) -> Any:
            # Simulates the incident: recomputed from a stale (worktree-
            # carried) input, landing on a version <= main's current one.
            (root / "pyproject.toml").write_text(
                '[project]\nname = "frob"\nversion = "0.182.0"\n'
            )
            _run(["git", "add", "pyproject.toml"], root)
            return Ok("0.182.0")

        result = land(repo, tid, wt, dry_run=False, bump_version=bump_version)
        assert result.is_err
        assert result.danger_err == LandError.ReleaseBumpFailed
        assert (
            _run(["git", "rev-parse", "HEAD"], repo).stdout.strip() == before_main_sha
        )
        assert _run(["git", "status", "--porcelain"], repo).stdout.strip() == ""
        # Main's pyproject.toml must still read its pre-land version, not
        # the callback's would-be downgrade -- the unwind must be complete.
        assert (repo / "pyproject.toml").read_text().count('version = "0.183.0"') == 1



# frob:ticket T-1078
# frob:ticket T-2220
class TestReleaseBumpQuartetAtomicity:
    """T-1078: land's REL001 bump used to update pyproject.toml/
    CHANGELOG.md while leaving `.frob-release.json` on its old version
    whenever a `bump_version` callback forgot (or failed silently) to
    write the manifest itself -- the desync then made every later land
    compute an already-taken version and refuse on the T-0992
    monotonicity guard. `land` now force-resyncs the manifest to the
    callback's reported version in the SAME step, and its refusal
    diagnostic names an incoherent quartet explicitly when that is the
    actual cause of a monotonicity refusal."""

    # frob:ticket T-2220
    def test_manifest_version_written_same_step_as_pyproject(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestReleaseBumpQuartetAtomicity.test_manifest_version_written_same_step_as_pyproject  # noqa: E501
        (repo / ".frob-release.json").write_text(
            '{"version": "0.183.0", "api": {"a": "digest"}}\n'
        )
        _commit_all(repo, "seed release manifest at 0.183.0")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-quartet", str(wt)], repo)
        created = new_ticket(wt, _spec("Quartet atomicity", scope=("src/qa.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "qa.py").write_text("# quartet atomicity\n")
        _commit_all(wt, "add qa.py")

        def bump_version(root: Path, ticket: Any, final_id: str) -> Any:
            # Models the incident's root cause: the callback bumps
            # pyproject.toml/CHANGELOG.md but never touches (or fails to
            # write) `.frob-release.json` at all -- land itself must be
            # the thing that keeps the manifest coherent.
            (root / "pyproject.toml").write_text(
                '[project]\nname = "frob"\nversion = "0.184.0"\n'
            )
            _run(["git", "add", "pyproject.toml"], root)
            return Ok("0.184.0")

        result = land(repo, tid, wt, dry_run=False, bump_version=bump_version)
        assert result.is_ok, result.err
        assert result.danger_ok.release_bumped_to == "0.184.0"

        manifest_text = (repo / ".frob-release.json").read_text()
        assert '"version": "0.184.0"' in manifest_text
        # The pre-existing api map must survive the resync untouched.
        assert '"a": "digest"' in manifest_text
        # Landed in the SAME commit as pyproject.toml -- no leftover diff.
        assert _status_ignoring_frob(repo) == ""
        # T-2220: `result.danger_ok.commit_sha` is the squash-apply commit
        # itself -- root's actual HEAD is now one commit further, a
        # separate `land_commit`-recording follow-up `_record_land_commit`
        # makes right after it (structurally required: a commit cannot
        # embed its own hash). The release quartet's own atomicity claim
        # is about THAT commit, not whatever root's tip happens to be.
        landed_sha = result.danger_ok.commit_sha
        assert landed_sha is not None
        head_files = _run(
            ["git", "show", "--stat", "--format=", landed_sha], repo
        ).stdout
        assert ".frob-release.json" in head_files
        assert "pyproject.toml" in head_files

    def test_incoherent_quartet_refusal_names_desync(
        self, repo: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestReleaseBumpQuartetAtomicity.test_incoherent_quartet_refusal_names_desync  # noqa: E501
        # Main's own quartet is ALREADY desynced before this land even
        # starts (mirrors the real incident: a prior land bumped
        # pyproject.toml but left the manifest stale).
        (repo / "pyproject.toml").write_text(
            '[project]\nname = "frob"\nversion = "0.211.0"\n'
        )
        (repo / ".frob-release.json").write_text('{"version": "0.210.0", "api": {}}\n')
        _commit_all(repo, "main quartet desynced: pyproject 0.211.0, manifest 0.210.0")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-desync", str(wt)], repo)
        created = new_ticket(wt, _spec("Desync refusal", scope=("src/dr.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "dr.py").write_text("# desync refusal\n")
        _commit_all(wt, "add dr.py")

        before_main_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()

        def bump_version(root: Path, ticket: Any, final_id: str) -> Any:
            # Derived from the stale manifest (0.210.0 -> 0.211.0), which
            # collides with pyproject's already-bumped 0.211.0 -- exactly
            # the incident's monotonicity trip.
            (root / "pyproject.toml").write_text(
                '[project]\nname = "frob"\nversion = "0.211.0"\n'
            )
            _run(["git", "add", "pyproject.toml"], root)
            return Ok("0.211.0")

        with caplog.at_level("ERROR", logger="frob.tickets._land"):
            result = land(repo, tid, wt, dry_run=False, bump_version=bump_version)

        assert result.is_err
        assert result.danger_err == LandError.ReleaseBumpFailed
        assert (
            _run(["git", "rev-parse", "HEAD"], repo).stdout.strip() == before_main_sha
        )
        assert _run(["git", "status", "--porcelain"], repo).stdout.strip() == ""
        assert "INCOHERENT" in caplog.text
        assert "frob release sync" in caplog.text
        assert "0.210.0" in caplog.text
        assert "0.211.0" in caplog.text




# frob:ticket T-1349
class TestLandReleaseMonotonicityHelpers:
    """T-1349: T-1334's move of the REL001 monotonicity family into
    `_land_release.py` was landed with `--skip-mutation-evidence` on the
    claim that pre-existing structural coverage (via the full `land()`
    end-to-end tests elsewhere in this file) already proves these
    functions correct. These tests exercise each leaf function directly to
    kill the specific surviving mutants T-1349's mutation run found
    (boolop/compare swaps on the error-guard and monotonicity checks) --
    the exact claim mutation testing exists to falsify, not re-assert."""

    def test_read_root_pyproject_version_ok_but_nonzero_returncode_is_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestLandReleaseMonotonicityHelpers.test_read_root_pyproject_version_ok_but_nonzero_returncode_is_none  # noqa: E501
        """Kills the `or` -> `and` mutant on `_read_root_pyproject_version`'s
        error guard: `run_argv` succeeding (is_err=False) with a nonzero
        `returncode` (e.g. `git show` reporting a bad revision/path) must
        still read as "nothing to report" -- an `and` mutant would only
        treat `is_err` alone as the guard and fall through here."""

        def _fake_run_argv(argv: Sequence[str], **kwargs: Any) -> Any:
            return Ok(
                ProcResult(
                    argv=tuple(argv),
                    returncode=128,
                    stdout='version = "9.9.9"\n',
                    stderr="fatal: bad revision",
                )
            )

        monkeypatch.setattr(_land_release_mod, "run_argv", _fake_run_argv)
        result = _land_release_mod._read_root_pyproject_version(tmp_path, "deadbeef")
        assert result is None

    def test_read_root_manifest_version_ok_but_nonzero_returncode_is_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestLandReleaseMonotonicityHelpers.test_read_root_manifest_version_ok_but_nonzero_returncode_is_none  # noqa: E501
        """Same `or` -> `and` mutant, on `_read_root_manifest_version`'s
        identical guard shape."""

        def _fake_run_argv(argv: Sequence[str], **kwargs: Any) -> Any:
            return Ok(
                ProcResult(
                    argv=tuple(argv),
                    returncode=128,
                    stdout='{"version": "9.9.9"}',
                    stderr="fatal: bad revision",
                )
            )

        monkeypatch.setattr(_land_release_mod, "run_argv", _fake_run_argv)
        result = _land_release_mod._read_root_manifest_version(tmp_path, "deadbeef")
        assert result is None

    def test_monotonic_when_no_prior_version(self) -> None:
        # frob:tests tests/test_ticket_land.py::TestLandReleaseMonotonicityHelpers.test_monotonic_when_no_prior_version  # noqa: E501
        """`pre_bump_version=None` is vacuously monotonic."""
        assert _land_release_mod._release_bump_is_monotonic(None, "0.1.0") is True

    def test_fallback_path_equal_versions_not_monotonic(self) -> None:
        # frob:tests tests/test_ticket_land.py::TestLandReleaseMonotonicityHelpers.test_fallback_path_equal_versions_not_monotonic  # noqa: E501
        """Kills the `!=` -> `==` and `and` -> `or` mutants on the PEP-440
        parse-failure fallback: two EQUAL non-numeric versions must not be
        treated as monotonic (an `==` mutant would flip this, and an `or`
        mutant would treat equal-but-not-greater as monotonic since the
        left side of the fallback and-clause would already be enough)."""
        assert (
            _land_release_mod._release_bump_is_monotonic("nonnumeric", "nonnumeric")
            is False
        )

    def test_fallback_path_lesser_version_not_monotonic(self) -> None:
        # frob:tests tests/test_ticket_land.py::TestLandReleaseMonotonicityHelpers.test_fallback_path_lesser_version_not_monotonic  # noqa: E501
        """Kills the `>` -> other-comparator mutant on the same fallback:
        a strictly LESSER non-numeric string must not be monotonic."""
        assert (
            _land_release_mod._release_bump_is_monotonic(
                "zzz-nonnumeric", "aaa-nonnumeric"
            )
            is False
        )

    def test_fallback_path_greater_version_is_monotonic(self) -> None:
        # frob:tests tests/test_ticket_land.py::TestLandReleaseMonotonicityHelpers.test_fallback_path_greater_version_is_monotonic  # noqa: E501
        """Positive complement of the two fallback tests above: a
        genuinely greater non-numeric string IS monotonic."""
        assert (
            _land_release_mod._release_bump_is_monotonic(
                "aaa-nonnumeric", "zzz-nonnumeric"
            )
            is True
        )

    def test_log_monotonicity_refusal_quartet_desync_requires_all_three_legs(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestLandReleaseMonotonicityHelpers.test_log_monotonicity_refusal_quartet_desync_requires_all_three_legs  # noqa: E501
        """Kills the `and` -> `or` mutant on `quartet_desynced`'s three-leg
        check: a `pre_manifest_version` that is `None` (never observed at
        `pre_land_tip`) must NOT be treated as desynced even though the
        other two legs alone would satisfy an `or`-mutated check."""
        with caplog.at_level("ERROR", logger="frob.tickets._land_release"):
            _land_release_mod._log_monotonicity_refusal(
                "T-9999", "0.2.0", "0.2.0", None
            )
        assert "INCOHERENT" not in caplog.text

    def test_log_monotonicity_refusal_fires_on_genuine_desync(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestLandReleaseMonotonicityHelpers.test_log_monotonicity_refusal_fires_on_genuine_desync  # noqa: E501
        """Positive complement: all three legs present and manifest !=
        pre-bump DOES fire the INCOHERENT message."""
        with caplog.at_level("ERROR", logger="frob.tickets._land_release"):
            _land_release_mod._log_monotonicity_refusal(
                "T-9999", "0.3.0", "0.2.0", "0.1.0"
            )
        assert "INCOHERENT" in caplog.text

    def test_sync_uv_lock_ok_but_nonzero_returncode_on_git_add_is_failed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestLandReleaseMonotonicityHelpers.test_sync_uv_lock_ok_but_nonzero_returncode_on_git_add_is_failed  # noqa: E501
        """Kills the `or` -> `and` mutant on `_sync_uv_lock_for_land`'s
        `git add uv.lock` guard: `uv lock` itself succeeds, but the
        subsequent `git add` returns `Ok` with a nonzero returncode (e.g.
        `uv.lock` outside the repo's pathspec) -- must still refuse as
        `GitFailed`, not fall through to the success-log path an `and`
        mutant would take here."""
        (tmp_path / "pyproject.toml").write_text('[project]\nversion = "0.1.0"\n')

        def _fake_run_argv(argv: Sequence[str], **kwargs: Any) -> Any:
            if tuple(argv) == ("uv", "lock"):
                return Ok(
                    ProcResult(argv=tuple(argv), returncode=0, stdout="", stderr="")
                )
            return Ok(
                ProcResult(
                    argv=tuple(argv),
                    returncode=128,
                    stdout="",
                    stderr="fatal: pathspec did not match",
                )
            )

        monkeypatch.setattr(_land_release_mod, "run_argv", _fake_run_argv)
        result = _land_release_mod._sync_uv_lock_for_land(tmp_path, "T-9999")
        assert result.is_err
        assert result.danger_err == LandError.GitFailed

    def test_resync_release_manifest_ok_but_nonzero_returncode_on_git_add_is_failed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestLandReleaseMonotonicityHelpers.test_resync_release_manifest_ok_but_nonzero_returncode_on_git_add_is_failed  # noqa: E501
        """Kills the `or` -> `and` mutant on `_resync_release_manifest`'s
        `git add .frob-release.json` guard: the manifest write itself
        succeeds, but the subsequent `git add` returns `Ok` with a nonzero
        returncode -- must still refuse as `ReleaseBumpFailed`, not fall
        through to `Ok(None)` the way an `and` mutant would here."""
        (tmp_path / ".frob-release.json").write_text(
            '{"version": "0.1.0", "api": {}}\n'
        )

        def _fake_run_argv(argv: Sequence[str], **kwargs: Any) -> Any:
            return Ok(
                ProcResult(
                    argv=tuple(argv),
                    returncode=128,
                    stdout="",
                    stderr="fatal: pathspec did not match",
                )
            )

        monkeypatch.setattr(_land_release_mod, "run_argv", _fake_run_argv)
        result = _land_release_mod._resync_release_manifest(tmp_path, "T-9999", "0.2.0")
        assert result.is_err
        assert result.danger_err == LandError.ReleaseBumpFailed


# frob:ticket T-1007
# frob:ticket T-2462
class TestRealCallbackStaleWorktreeManifest:
    """T-1007: the SAME T-0992 acceptance criterion (a stale worktree-
    carried value must never win over root's own state), now proven
    through the REAL `ticket_runner._apply_release_bump_for_land` callback
    instead of a fake `bump_version` closure that hardcodes the correct
    answer. Before T-1007's fix, this callback derived its baseline from
    whatever `.frob-release.json` ended up on root's WORKING TREE after
    the squash-apply -- which a stale, out-of-scope worktree copy can
    silently corrupt -- so this scenario tripped the T-0992 monotonicity
    guard's REFUSAL on the first land attempt every time (guard fires,
    but never prevents the retry churn). After the fix, the callback reads
    `.frob-release.json` from root's own git HEAD (never the working-tree
    copy the squash just wrote), computes main-plus-one correctly, and
    lands clean on the FIRST attempt -- the guard becomes a never-fires
    invariant for this callback, exactly as T-1007 required.

    T-2462: the bump itself is now DEFERRED -- `pyproject.toml`/`.frob-
    release.json` are no longer rewritten by this callback at all, so the
    T-1007 correctness claim now shows up in the `changelog.d/T-####.md`
    fragment's `bump:` label and CHANGELOG.md's regenerated pending
    section instead of in a rewritten `pyproject.toml`/`.frob-release.
    json`: main-plus-one (0.184.0), computed from ROOT's committed
    manifest (0.183.0) -- never the worktree's stale 0.181.0 copy, which
    would have under-computed 0.182.0."""

    def test_stale_worktree_manifest_still_lands_main_plus_one(
        self, repo: Path
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestRealCallbackStaleWorktreeManifest.test_stale_worktree_manifest_still_lands_main_plus_one  # noqa: E501
        from frob.app import ticket_runner

        (repo / "pyproject.toml").write_text(
            '[project]\nname = "frob"\nversion = "0.183.0"\n'
        )
        (repo / "CHANGELOG.md").write_text("# Changelog\n\n## [0.183.0] - unreleased\n")
        (repo / ".frob-release.json").write_text('{"version": "0.183.0", "api": {}}\n')
        _commit_all(repo, "main is ahead at 0.183.0, manifest stamped to match")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-stale-manifest", str(wt)], repo)
        # Simulates the T-1007 incident directly: the worktree's OWN copy
        # of the manifest is stale (out of ticket scope, untouched by the
        # ticket itself, but present as a real diff against the fork
        # point) -- exactly the class of file that rides straight through
        # `git merge --squash` into root's working tree.
        (wt / ".frob-release.json").write_text('{"version": "0.181.0", "api": {}}\n')
        _commit_all(wt, "worktree still carries a stale manifest")

        created = new_ticket(wt, _spec("Stale worktree manifest", scope=("src/sm.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        # A new PUBLIC function -- a real MINOR-class API addition, so the
        # real `diff_class`/`required_version` machinery has something
        # genuine to compute against.
        (wt / "src" / "sm.py").write_text("def added():\n    pass\n")
        _commit_all(wt, "add sm.py (new public function)")

        result = land(
            repo,
            tid,
            wt,
            dry_run=False,
            bump_version=ticket_runner._land_bump_version_fn(),
        )
        assert result.is_ok, result.err
        # T-2462: the bump is deferred -- this callback ALWAYS reports
        # `None`, even though a fragment was written (see its own
        # docstring for why reporting a version here is incompatible with
        # leaving pyproject.toml unwritten).
        assert result.danger_ok.release_bumped_to is None
        # pyproject.toml/.frob-release.json stay EXACTLY at main's own
        # pre-land values -- never touched by this land at all.
        assert (repo / "pyproject.toml").read_text().count('version = "0.183.0"') == 1
        assert (repo / "pyproject.toml").read_text().count('version = "0.184.0"') == 0
        manifest_text = (repo / ".frob-release.json").read_text()
        assert '"version": "0.183.0"' in manifest_text
        assert '"version": "0.184.0"' not in manifest_text
        # The T-1007 correctness claim now lives in the fragment: computed
        # from ROOT's own committed 0.183.0 manifest (never the
        # worktree's stale 0.181.0 copy), the real target is 0.184.0/
        # minor -- CHANGELOG.md's regenerated pending section names it.
        changelog_text = (repo / "CHANGELOG.md").read_text()
        assert "## [0.184.0] - unreleased" in changelog_text
        # T-2462: the fragment is filed under the RENUMBERED final id
        # (T-0001 in this fixture's fresh ledger), not the draft id `tid`
        # was allocated as -- same id `_write_release_bump` receives as
        # `final_id`.
        fragment_path = repo / "changelog.d" / "T-0001.md"
        assert fragment_path.is_file()
        assert "bump: minor" in fragment_path.read_text()



# frob:ticket T-0793
# frob:ticket T-2220
class TestUvLockSync:
    """T-0793: land's release-bump step re-syncs `uv.lock` in the SAME
    commit as a real version bump, and the DirtyMain check tolerates (and
    auto-restores) a `uv.lock` whose only drift is the frob-version line
    flapping from a prior `uv run`/`uv lock` against an already-bumped
    pyproject.toml."""

    # frob:ticket T-2220
    def test_bump_then_lock_synced_in_commit(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests \
        # tests/test_ticket_land.py::TestUvLockSync.test_bump_then_lock_synced_in_commit
        (repo / "pyproject.toml").write_text(
            '[project]\nname = "frob"\nversion = "0.1.0"\n'
        )
        _commit_all(repo, "add pyproject")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-lock", str(wt)], repo)
        created = new_ticket(wt, _spec("Bump with lock", scope=("src/locked.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "locked.py").write_text("# locked\n")
        _commit_all(wt, "add locked.py")

        def _fake_run_argv(argv: Sequence[str], **kwargs: Any) -> Any:
            if tuple(argv) == ("uv", "lock"):
                (kwargs["cwd"] / "uv.lock").write_text(
                    '[[package]]\nname = "frob"\nversion = "1.2.3"\n'
                )
                return Ok(
                    ProcResult(argv=tuple(argv), returncode=0, stdout="", stderr="")
                )
            return run_argv(argv, **kwargs)

        monkeypatch.setattr(_land_release_mod, "run_argv", _fake_run_argv)

        def bump_version(root: Path, ticket: Any, final_id: str) -> Any:
            (root / "pyproject.toml").write_text(
                '[project]\nname = "frob"\nversion = "1.2.3"\n'
            )
            _run(["git", "add", "pyproject.toml"], root)
            return Ok("1.2.3")

        result = land(repo, tid, wt, dry_run=False, bump_version=bump_version)
        assert result.is_ok, result.err
        assert result.danger_ok.release_bumped_to == "1.2.3"
        assert (repo / "uv.lock").read_text().count('version = "1.2.3"') == 1
        # uv.lock landed in the SAME commit as the bump, not left dirty.
        assert _status_ignoring_frob(repo) == ""
        # T-2220: check the SQUASH-APPLY commit itself (`commit_sha`), not
        # bare HEAD -- root's tip is now one commit further, a follow-up
        # `_record_land_commit` write made right after it.
        landed_sha = result.danger_ok.commit_sha
        assert landed_sha is not None
        committed_files = _run(
            ["git", "show", "--name-only", "--pretty=format:", landed_sha], repo
        ).stdout.split()
        assert "uv.lock" in committed_files

    def test_dirty_lock_version_line_only_does_not_refuse(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestUvLockSync.test_dirty_lock_version_line_only_does_not_refuse  # noqa: E501
        (repo / "uv.lock").write_text(
            '[[package]]\nname = "frob"\nversion = "0.1.0"\nsource = { editable = "." }\n'
        )
        _commit_all(repo, "add uv.lock")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-lockdirty", str(wt)], repo)
        created = new_ticket(wt, _spec("Tolerate lock drift"))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        _commit_all(wt, "wip")

        # Simulate the flap: only the frob version line in uv.lock changed,
        # nothing else in the tree is dirty.
        (repo / "uv.lock").write_text(
            '[[package]]\nname = "frob"\nversion = "0.2.0"\nsource = { editable = "." }\n'
        )

        result = land(repo, tid, wt, dry_run=True)
        assert result.is_ok, result.err
        # The drift was auto-restored back to the committed content.
        assert 'version = "0.1.0"' in (repo / "uv.lock").read_text()
        assert _status_ignoring_frob(repo) == ""

    def test_worktree_side_lock_flap_auto_restored_before_wip_commit(
        self, repo: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestUvLockSync.test_worktree_side_lock_flap_auto_restored_before_wip_commit  # noqa: E501
        # frob:tests src/frob/tickets/_land_git_ops.py::_wip_commit kind="unit"
        """T-1003 (churn item 4): the T-0793 frob-version-only auto-restore
        applies to the WORKTREE's own `uv.lock` too, before the wip-commit
        dirty check -- not just `root`'s, as `test_dirty_lock_version_
        line_only_does_not_refuse` above already locks. Without this, the
        flap would get silently wip-committed as noise and squash-applied
        into the landing commit, needing the same manual `git checkout --
        uv.lock` ritual on the OTHER side of the land."""
        (repo / "uv.lock").write_text(
            '[[package]]\nname = "frob"\nversion = "0.1.0"\nsource = { editable = "." }\n'
        )
        _commit_all(repo, "add uv.lock")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-wtlockdirty", str(wt)], repo)
        created = new_ticket(wt, _spec("Tolerate worktree-side lock drift"))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        _commit_all(wt, "wip")

        # Simulate the flap IN THE WORKTREE (not root): only the frob
        # version line changed, uncommitted, nothing else dirty.
        (wt / "uv.lock").write_text(
            '[[package]]\nname = "frob"\nversion = "0.2.0"\nsource = { editable = "." }\n'
        )

        with caplog.at_level("INFO", logger="frob.tickets._land"):
            result = land(repo, tid, wt, dry_run=False)

        assert result.is_ok, result.err
        assert "wip-commit dirty check" in caplog.text
        # Restored back to the committed content in the worktree, never
        # wip-committed as noise nor squash-applied into the landing
        # commit -- root's own uv.lock still reads its one committed line.
        assert 'version = "0.1.0"' in (wt / "uv.lock").read_text()
        assert (repo / "uv.lock").read_text().count('version = "0.1.0"') == 1

    def test_dirty_lock_with_other_change_still_refuses(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestUvLockSync.test_dirty_lock_with_other_change_still_refuses  # noqa: E501
        (repo / "uv.lock").write_text(
            '[[package]]\nname = "frob"\nversion = "0.1.0"\nsource = { editable = "." }\n'
        )
        _commit_all(repo, "add uv.lock")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-lockplus", str(wt)], repo)
        created = new_ticket(wt, _spec("Real dirt"))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        _commit_all(wt, "wip")

        (repo / "uv.lock").write_text(
            '[[package]]\nname = "frob"\nversion = "0.2.0"\nsource = { editable = "." }\n'
        )
        (repo / "other.txt").write_text("real uncommitted change\n")

        result = land(repo, tid, wt, dry_run=True)
        assert result.is_err
        assert result.danger_err == LandError.DirtyMain

    def test_dirty_lock_version_plus_other_line_still_refuses(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestUvLockSync.test_dirty_lock_version_plus_other_line_still_refuses  # noqa: E501
        (repo / "uv.lock").write_text(
            "[[package]]\n"
            'name = "frob"\n'
            'version = "0.1.0"\n'
            'source = { editable = "." }\n'
        )
        _commit_all(repo, "add uv.lock")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-lockmixed", str(wt)], repo)
        created = new_ticket(wt, _spec("Mixed lock drift"))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        _commit_all(wt, "wip")

        # uv.lock is the SOLE dirty path, but its diff touches BOTH the
        # frob version line AND another line (a dependency hash flip,
        # here a changed `source` value) -- `_diff_is_frob_version_line_
        # only` must reject this shape (len(changed) != 2) so the
        # destructive auto-restore never fires on real lock content.
        dirty_content = (
            "[[package]]\n"
            'name = "frob"\n'
            'version = "0.2.0"\n'
            'source = { editable = "./elsewhere" }\n'
        )
        (repo / "uv.lock").write_text(dirty_content)

        result = land(repo, tid, wt, dry_run=True)
        assert result.is_err
        assert result.danger_err == LandError.DirtyMain
        # Not auto-restored: the dirty content is left exactly as written.
        assert (repo / "uv.lock").read_text() == dirty_content

    def test_lock_sync_spawn_failure_unwinds_squash(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestUvLockSync.test_lock_sync_spawn_failure_unwinds_squash  # noqa: E501
        (repo / "pyproject.toml").write_text(
            '[project]\nname = "frob"\nversion = "0.1.0"\n'
        )
        _commit_all(repo, "add pyproject")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-lockfail", str(wt)], repo)
        created = new_ticket(
            wt, _spec("Bump with failing lock", scope=("src/failedlock.py",))
        )
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "failedlock.py").write_text("# failed lock\n")
        _commit_all(wt, "add failedlock.py")

        before_main_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()

        def _fake_run_argv(argv: Sequence[str], **kwargs: Any) -> Any:
            if tuple(argv) == ("uv", "lock"):
                return Ok(
                    ProcResult(
                        argv=tuple(argv),
                        returncode=1,
                        stdout="",
                        stderr="simulated uv lock failure",
                    )
                )
            return run_argv(argv, **kwargs)

        monkeypatch.setattr(_land_release_mod, "run_argv", _fake_run_argv)

        def bump_version(root: Path, ticket: Any, final_id: str) -> Any:
            (root / "pyproject.toml").write_text(
                '[project]\nname = "frob"\nversion = "1.2.3"\n'
            )
            _run(["git", "add", "pyproject.toml"], root)
            return Ok("1.2.3")

        result = land(repo, tid, wt, dry_run=False, bump_version=bump_version)
        assert result.is_err
        assert result.danger_err == LandError.ReleaseBumpFailed
        assert (
            _run(["git", "rev-parse", "HEAD"], repo).stdout.strip() == before_main_sha
        )
        assert _run(["git", "status", "--porcelain"], repo).stdout.strip() == ""


# frob:ticket T-1699
class TestRapidDebtOnlyDriftAutoCommit:
    """T-1699: `_commit_rapid_debt_only_drift` -- the second DirtyMain
    auto-heal `_refuse_if_main_dirty` tries, alongside T-0793's uv.lock
    precedent. Unlike that precedent (which DISCARDS a benign flap),
    this one COMMITS: a `rapid-debt.jsonl` append is real, land-owned
    content a concurrent land's own two-step append-then-commit
    (deliberately outside the land lock, T-1684) can leave dirty for a
    second agent's land to observe mid-window."""

    def test_sole_rapid_debt_dirt_is_committed(self, repo: Path) -> None:
        # frob:tests \
        # tests/test_ticket_land.py::TestRapidDebtOnlyDriftAutoCommit.test_sole_rapid_d\
        # ebt_dirt_is_committed
        from frob.tickets._land_git_ops import _commit_rapid_debt_only_drift

        (repo / "rapid-debt.jsonl").write_text(
            '{"commit": "abc123", "skipped": "post-land-unscoped-sweep-deferred", '
            '"ticket": "T-0001"}\n'
        )
        _run(["git", "add", "rapid-debt.jsonl"], repo)
        _run(["git", "commit", "-q", "-m", "seed rapid-debt.jsonl"], repo)
        (repo / "rapid-debt.jsonl").write_text(
            '{"commit": "abc123", "skipped": "post-land-unscoped-sweep-deferred", '
            '"ticket": "T-0001"}\n'
            '{"commit": "def456", "skipped": "post-land-unscoped-sweep-deferred", '
            '"ticket": "T-0002"}\n'
        )

        assert _commit_rapid_debt_only_drift(repo) is True
        assert _run(["git", "status", "--porcelain"], repo).stdout.strip() == ""

    def test_a_second_dirty_file_blocks_the_auto_commit(self, repo: Path) -> None:
        # frob:tests \
        # tests/test_ticket_land.py::TestRapidDebtOnlyDriftAutoCommit.test_a_second_dir\
        # ty_file_blocks_the_auto_commit
        from frob.tickets._land_git_ops import _commit_rapid_debt_only_drift

        (repo / "rapid-debt.jsonl").write_text(
            '{"commit": "abc123", "skipped": "x", "ticket": "T-0001"}\n'
        )
        (repo / "other.py").write_text("# unrelated dirt\n")

        assert _commit_rapid_debt_only_drift(repo) is False
        status = _run(["git", "status", "--porcelain"], repo).stdout
        assert "rapid-debt.jsonl" in status
        assert "other.py" in status

    def test_no_dirt_at_all_is_a_noop(self, repo: Path) -> None:
        # frob:tests \
        # tests/test_ticket_land.py::TestRapidDebtOnlyDriftAutoCommit.test_no_dirt_at_a\
        # ll_is_a_noop
        from frob.tickets._land_git_ops import _commit_rapid_debt_only_drift

        assert _commit_rapid_debt_only_drift(repo) is False


# frob:ticket T-0338
class TestRebuildNatives:
    """T-0338: `land`'s optional `rebuild_natives` callback -- invoked only
    when the landed changeset touches a native source tree."""

    def test_invoked_when_native_source_touched(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestRebuildNatives.test_invoked_when_native_source_touched  # noqa: E501
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-native-src", str(wt)], repo)
        created = new_ticket(
            wt, _spec("Native change", scope=("frob-core/src/lib.rs",))
        )
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "frob-core").mkdir()
        (wt / "frob-core" / "src").mkdir()
        (wt / "frob-core" / "src" / "lib.rs").write_text("// native change\n")
        _commit_all(wt, "touch frob-core")

        calls: list[Path] = []

        def rebuild_natives(root: Path) -> bool:
            calls.append(root)
            return True

        result = land(repo, tid, wt, dry_run=False, rebuild_natives=rebuild_natives)
        assert result.is_ok, result.err
        assert result.danger_ok.natives_rebuilt is True
        assert calls == [repo]

    def test_skipped_when_no_native_source_touched(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestRebuildNatives.test_skipped_when_no_native_source_touched  # noqa: E501
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-not-native", str(wt)], repo)
        created = new_ticket(wt, _spec("Regular change", scope=("src/regular.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "regular.py").write_text("# regular\n")
        _commit_all(wt, "add regular.py")

        calls: list[Path] = []

        def rebuild_natives(root: Path) -> bool:
            calls.append(root)
            return True

        result = land(repo, tid, wt, dry_run=False, rebuild_natives=rebuild_natives)
        assert result.is_ok, result.err
        assert result.danger_ok.natives_rebuilt is False
        assert calls == []

    def test_rebuild_runs_after_the_landing_commit_is_durable(self, repo: Path) -> None:
        """T-3111 must-fire: the callback must observe a root whose HEAD is
        ALREADY the landing commit with a clean working tree -- before this
        fix it ran while root held the whole squash staged and
        uncommitted, so every second of a minutes-long native build was a
        second every sibling agent saw DirtyMain."""
        # frob:tests tests/test_ticket_land.py::TestRebuildNatives.test_rebuild_runs_after_the_landing_commit_is_durable  # noqa: E501
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-native-order", str(wt)], repo)
        created = new_ticket(
            wt, _spec("Native change ordering", scope=("frob-core/src/lib.rs",))
        )
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "frob-core" / "src").mkdir(parents=True)
        (wt / "frob-core" / "src" / "lib.rs").write_text("// native change\n")
        _commit_all(wt, "touch frob-core")

        observed: list[tuple[str, str]] = []

        def rebuild_natives(root: Path) -> bool:
            observed.append(
                (
                    _run(["git", "status", "--porcelain"], root).stdout.strip(),
                    _run(["git", "rev-parse", "HEAD"], root).stdout.strip(),
                )
            )
            return True

        result = land(repo, tid, wt, dry_run=False, rebuild_natives=rebuild_natives)
        assert result.is_ok, result.err
        assert len(observed) == 1
        porcelain, head_at_rebuild = observed[0]
        assert porcelain == "", (
            "the rebuild ran while root still held staged, uncommitted "
            f"land content: {porcelain!r}"
        )
        assert head_at_rebuild == result.danger_ok.commit_sha, (
            "the rebuild ran before the landing commit existed; root's tip "
            f"was {head_at_rebuild!r}, the landing commit is "
            f"{result.danger_ok.commit_sha!r}"
        )

    def test_rebuild_failure_does_not_block_land(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestRebuildNatives.test_rebuild_failure_does_not_block_land  # noqa: E501
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-native-fail", str(wt)], repo)
        created = new_ticket(
            wt, _spec("Native change fails rebuild", scope=("strata-core/src/lib.rs",))
        )
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "strata-core").mkdir()
        (wt / "strata-core" / "src").mkdir()
        (wt / "strata-core" / "src" / "lib.rs").write_text("// native change\n")
        _commit_all(wt, "touch strata-core")

        result = land(repo, tid, wt, dry_run=False, rebuild_natives=lambda root: False)
        assert result.is_ok, result.err
        assert result.danger_ok.natives_rebuilt is False
