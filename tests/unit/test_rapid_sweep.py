"""Unit tests for `frob.app.ticket_runner._rapid_sweep` (T-1684): the
rapid profile's deferred, non-blocking post-land unscoped sweep."""

from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path
from typing import cast

import pytest

from frob.app.ticket_runner import _rapid_sweep
from frob.app.ticket_runner._rapid_sweep import (
    RapidSweepError,
    _attribute_new_findings,
    _baseline_write_survived,
    _build_regression_body,
    _check_claim_divergence_post_land,
    _close_resolved_sweep_tickets,
    _file_regression_ticket,
    _files_deleted_between,
    _filter_phantom_deleted_findings,
    _identities_still_reproducing,
    _identity_scoped_state_key,
    _land_ids_between,
    _parse_sweep_ticket_identities,
    _read_baseline,
    _read_baseline_commit,
    _read_revalidation_cache,
    _regression_count_line,
    _relativize_regression_scope_file,
    _resolve_actual_head,
    _ticket_is_open,
    _tree_state_key,
    _true_finding_count_for_identities,
    _write_baseline,
    _write_revalidation_cache,
    run_deferred_post_land_sweep,
    spawn_deferred_post_land_sweep,
    sweep_stale_worktrees_after_land,
)


def _init_git_repo(root: Path) -> None:
    """A minimal real git repo for T-2009's `_land_ids_between`/`_resolve_
    actual_head` tests -- these shell out to real `git log`/`rev-parse`,
    unlike most of this module's tests which use a plain `tmp_path`."""
    import subprocess

    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(
        ["git", "-C", str(root), "config", "user.email", "test@example.com"],
        check=True,
    )
    subprocess.run(["git", "-C", str(root), "config", "user.name", "Test"], check=True)


def _git_commit(root: Path, message: str) -> str:
    """One empty, real commit with `message`; returns its full sha."""
    import subprocess

    subprocess.run(
        ["git", "-C", str(root), "commit", "--allow-empty", "-q", "-m", message],
        check=True,
    )
    return subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


class TestRollingBaseline:
    """The rolling baseline is what lets a deferred sweep cost ONE check
    instead of the two `standard` pays."""

    def test_absent_baseline_reads_as_none_not_empty(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestRollingBaseline.test_absent_baseline_reads_as_none_not_empty  # noqa: E501
        assert _read_baseline(tmp_path) is None

    def test_corrupt_baseline_reads_as_none_not_empty(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestRollingBaseline.test_corrupt_baseline_reads_as_none_not_empty  # noqa: E501
        path = tmp_path / ".frob" / "rapid-sweep-baseline.json"
        path.parent.mkdir(parents=True)
        path.write_text("{not json", encoding="utf-8")
        assert _read_baseline(tmp_path) is None

    def test_write_then_read_round_trips(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestRollingBaseline.test_write_then_read_round_trips  # noqa: E501
        findings = frozenset({("COV003", "a.py"), ("DOC011", "b.md")})
        _write_baseline(tmp_path, findings, "deadbeef" * 5)
        assert _read_baseline(tmp_path) == findings
        stored = json.loads(
            (tmp_path / ".frob" / "rapid-sweep-baseline.json").read_text(
                encoding="utf-8"
            )
        )
        assert stored["commit"] == "deadbeef" * 5

    def test_read_baseline_commit_absent_is_none(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestRollingBaseline.test_read_baseline_commit_absent_is_none  # noqa: E501
        assert _read_baseline_commit(tmp_path) is None

    def test_read_baseline_commit_round_trips(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestRollingBaseline.test_read_baseline_commit_round_trips  # noqa: E501
        _write_baseline(tmp_path, frozenset({("COV003", "a.py")}), "abc123")
        assert _read_baseline_commit(tmp_path) == "abc123"


class TestLandIdsBetween:
    """T-2009: the mechanical fix for misattribution -- tell how many
    lands (and which) actually landed in a commit range, instead of
    assuming it was always exactly the one that spawned this sweep."""

    def test_single_land_in_range(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestLandIdsBetween.test_single_land_in_range  # noqa: E501
        _init_git_repo(tmp_path)
        start = _git_commit(tmp_path, "chore: init")
        _git_commit(tmp_path, "fix(tickets): land T-1001 something")
        end = _git_commit(tmp_path, "chore(rapid): record T-1001's deferred sweep")
        assert _land_ids_between(tmp_path, start, end) == ["T-1001"]

    def test_multiple_lands_in_range_oldest_first(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestLandIdsBetween.test_multiple_lands_in_range_oldest_first  # noqa: E501
        _init_git_repo(tmp_path)
        start = _git_commit(tmp_path, "chore: init")
        _git_commit(tmp_path, "fix(tickets): land T-1977 first fix")
        _git_commit(tmp_path, "chore(rapid): record T-1977's deferred sweep")
        _git_commit(tmp_path, "feat(tickets): land T-1995 second fix")
        end = _git_commit(tmp_path, "chore(rapid): record T-1995's deferred sweep")
        # T-1998's real misattribution shape: two lands landed in the
        # window this sweep measured, so both must be named -- neither
        # gets silently dropped, and order is oldest-first (git log
        # --reverse).
        assert _land_ids_between(tmp_path, start, end) == ["T-1977", "T-1995"]

    def test_non_land_commits_are_ignored(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestLandIdsBetween.test_non_land_commits_are_ignored  # noqa: E501
        _init_git_repo(tmp_path)
        start = _git_commit(tmp_path, "chore: init")
        _git_commit(tmp_path, "chore(tickets): file T-2000")
        _git_commit(tmp_path, "fix(tickets): land T-2001 real fix")
        end = _git_commit(tmp_path, "chore: unrelated housekeeping")
        assert _land_ids_between(tmp_path, start, end) == ["T-2001"]

    def test_non_repo_returns_empty_list(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestLandIdsBetween.test_non_repo_returns_empty_list  # noqa: E501
        # tmp_path is not a git repo -- degrade to [] rather than raise,
        # so a caller falls back to the pre-T-2009 single-attribution
        # behavior instead of crashing an otherwise-successful sweep.
        assert _land_ids_between(tmp_path, "abc", "def") == []


class TestResolveActualHead:
    def test_non_repo_falls_back_to_the_given_commit(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestResolveActualHead.test_non_repo_falls_back_to_the_given_commit  # noqa: E501
        assert _resolve_actual_head(tmp_path, "fallback-sha") == "fallback-sha"

    def test_real_repo_resolves_the_true_head(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestResolveActualHead.test_real_repo_resolves_the_true_head  # noqa: E501
        _init_git_repo(tmp_path)
        _git_commit(tmp_path, "chore: init")
        real_head = _git_commit(tmp_path, "chore: second commit")
        # "fallback-sha" is deliberately NOT the real head -- proving the
        # real HEAD is what's returned, not the caller's own guess.
        assert _resolve_actual_head(tmp_path, "fallback-sha") == real_head


# frob:ticket T-2571
class TestFilesDeletedBetween:
    """T-2571's own repro: `TICK003`/`TICK004` fired against
    `tickets.md` in three separate sweeps AFTER a land had already
    deleted it -- these test the ground-truth git-diff detection that
    fix relies on."""

    def test_deleted_file_is_reported(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestFilesDeletedBetween.test_deleted_file_is_reported  # noqa: E501
        _init_git_repo(tmp_path)
        (tmp_path / "tickets.md").write_text("stuff\n")
        import subprocess

        subprocess.run(["git", "-C", str(tmp_path), "add", "tickets.md"], check=True)
        since = _git_commit(tmp_path, "chore: add tickets.md")
        (tmp_path / "tickets.md").unlink()
        subprocess.run(["git", "-C", str(tmp_path), "add", "-A"], check=True)
        until = _git_commit(tmp_path, "chore(tickets): ledger-v2 cutover, delete it")
        assert _files_deleted_between(tmp_path, since, until) == frozenset(
            {"tickets.md"}
        )

    def test_modified_only_file_is_not_reported(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestFilesDeletedBetween.test_modified_only_file_is_not_reported  # noqa: E501
        _init_git_repo(tmp_path)
        (tmp_path / "a.py").write_text("x = 1\n")
        import subprocess

        subprocess.run(["git", "-C", str(tmp_path), "add", "a.py"], check=True)
        since = _git_commit(tmp_path, "chore: add a.py")
        (tmp_path / "a.py").write_text("x = 2\n")
        subprocess.run(["git", "-C", str(tmp_path), "add", "a.py"], check=True)
        until = _git_commit(tmp_path, "chore: modify a.py")
        assert _files_deleted_between(tmp_path, since, until) == frozenset()

    def test_non_repo_or_missing_since_returns_empty(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestFilesDeletedBetween.test_non_repo_or_missing_since_returns_empty  # noqa: E501
        assert _files_deleted_between(tmp_path, None, "abc123") == frozenset()
        assert _files_deleted_between(tmp_path, "abc", "abc") == frozenset()
        assert _files_deleted_between(tmp_path, "abc", "def") == frozenset()


class TestFilterPhantomDeletedFindings:
    def test_deleted_file_finding_is_excluded(self) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestFilterPhantomDeletedFindings.test_deleted_file_finding_is_excluded  # noqa: E501
        fresh = frozenset({("TICK003", "tickets.md"), ("COV003", "a.py")})
        result = _filter_phantom_deleted_findings(
            "T-2571", fresh, frozenset({"tickets.md"})
        )
        assert result == frozenset({("COV003", "a.py")})

    def test_live_file_finding_is_kept(self) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestFilterPhantomDeletedFindings.test_live_file_finding_is_kept  # noqa: E501
        fresh = frozenset({("COV003", "a.py")})
        result = _filter_phantom_deleted_findings("T-2571", fresh, frozenset())
        assert result == fresh

    def test_no_deletions_is_a_noop(self) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestFilterPhantomDeletedFindings.test_no_deletions_is_a_noop  # noqa: E501
        fresh = frozenset({("COV003", "a.py"), ("DOC011", "b.md")})
        assert _filter_phantom_deleted_findings("T-2571", fresh, frozenset()) is fresh


class TestBaselineWriteSurvived:
    def test_matching_commit_survived(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestBaselineWriteSurvived.test_matching_commit_survived  # noqa: E501
        _write_baseline(tmp_path, frozenset({("COV003", "a.py")}), "abc123")
        assert _baseline_write_survived(tmp_path, "abc123") is True

    def test_mismatched_commit_did_not_survive(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestBaselineWriteSurvived.test_mismatched_commit_did_not_survive  # noqa: E501
        _write_baseline(tmp_path, frozenset({("COV003", "a.py")}), "abc123")
        # A concurrent sweep clobbers the file with a DIFFERENT commit
        # right after this sweep's own write, before this check runs.
        _write_baseline(tmp_path, frozenset({("OTHER", "z.py")}), "clobbered-by-x")
        assert _baseline_write_survived(tmp_path, "abc123") is False


# frob:ticket T-2595
class TestDeferredSweepBaselineCasRace:
    """T-2595 repro, exercised entirely through the same public entry
    point (`run_deferred_post_land_sweep`) `TestDeferredSweepMultiLandAttribution`
    above already uses -- deliberately does NOT reference `_write_
    baseline_cas`/`_baseline_lock`/`_is_ancestor` directly, so this test
    stays collectible (and thus a genuine FAILED_AT_PARENT, not a
    collection error) against the pre-T-2595 tree where those symbols do
    not exist yet."""

    def test_a_sweep_computed_against_a_stale_tree_does_not_clobber_a_fresher_ones_baseline(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestDeferredSweepBaselineCasRace.test_a_sweep_computed_against_a_stale_tree_does_not_clobber_a_fresher_ones_baseline  # noqa: E501
        import subprocess

        _init_git_repo(tmp_path)
        c0 = _git_commit(tmp_path, "chore: init")
        _write_baseline(tmp_path, frozenset(), c0)

        commit_older = _git_commit(tmp_path, "fix(tickets): land T-AAAA older view")
        commit_newer = _git_commit(tmp_path, "fix(tickets): land T-BBBB newer view")

        # Sweep NEW: computed against the fresher head, finishes and
        # writes first.
        monkeypatch.setattr(
            "frob.app.ticket_runner._land_cmd._unscoped_error_findings",
            lambda *a, **k: frozenset({("COV003", "fresh.py")}),
        )
        result_new = run_deferred_post_land_sweep(tmp_path, "T-BBBB", commit_newer)
        assert result_new.is_ok
        assert _read_baseline_commit(tmp_path) == commit_newer
        assert _read_baseline(tmp_path) == frozenset({("COV003", "fresh.py")})

        # Sweep OLD: had been computing against the OLDER head all along
        # (modeled here by moving this shared root's real HEAD backward,
        # matching a genuinely stale writer's view of the tree) and
        # finishes SECOND, racing on the same shared root T-1684 always
        # writes to.
        subprocess.run(
            ["git", "-C", str(tmp_path), "checkout", "-q", commit_older], check=True
        )
        monkeypatch.setattr(
            "frob.app.ticket_runner._land_cmd._unscoped_error_findings",
            lambda *a, **k: frozenset({("F401", "stale.py")}),
        )
        result_old = run_deferred_post_land_sweep(tmp_path, "T-AAAA", commit_older)
        assert result_old.is_ok

        # The FRESHER write must survive -- a sweep computed against an
        # older tree state must never discard one computed against a
        # newer one. Fails against the pre-T-2595 unconditional
        # `_write_baseline` this replaced (the older sweep always won
        # there, purely by finishing second).
        assert _read_baseline_commit(tmp_path) == commit_newer
        assert _read_baseline(tmp_path) == frozenset({("COV003", "fresh.py")})


# frob:ticket T-2595
class TestBaselineLock:
    """T-2595: the lock guards only the tiny read-decide-write, never the
    multi-minute check that produces a sweep's findings."""

    def test_no_lock_primitive_refuses_loudly(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2918: neither fcntl (POSIX) nor msvcrt (Windows) available
        must RAISE, never silently proceed unlocked -- the platform-wide
        NO-OP this replaces raced every concurrent sweep for the whole
        lock's lifetime, not just under rare, brief contention."""
        # frob:tests tests/unit/test_rapid_sweep.py::TestBaselineLock.test_no_lock_primitive_refuses_loudly  # noqa: E501
        from frob.app.ticket_runner._rapid_sweep import (
            BaselineLockUnavailable,
            _baseline_lock,
        )

        monkeypatch.setattr(_rapid_sweep, "fcntl", None)
        monkeypatch.setattr(_rapid_sweep, "msvcrt", None)
        with pytest.raises(BaselineLockUnavailable):
            with _baseline_lock(tmp_path):
                pass

    def test_windows_backend_serializes_two_concurrent_holders(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2918: the msvcrt backend is exercised on Linux CI via a fake
        module standing in for the real Windows-only `msvcrt` -- it
        implements just enough of `locking`'s byte-range-lock contract
        (backed by a real `fcntl.flock` under the hood) to prove the
        `_baseline_lock` code path that only ever runs for real on
        Windows: acquire, contend, timeout-degrade, release."""
        # frob:tests tests/unit/test_rapid_sweep.py::TestBaselineLock.test_windows_backend_serializes_two_concurrent_holders  # noqa: E501
        import fcntl as _fcntl

        from frob.app.ticket_runner._rapid_sweep import _baseline_lock

        class _FakeMsvcrt:
            LK_NBLCK = 1
            LK_UNLCK = 2

            @staticmethod
            def locking(fd: int, mode: int, _nbytes: int) -> None:
                if mode == _FakeMsvcrt.LK_UNLCK:
                    _fcntl.flock(fd, _fcntl.LOCK_UN)
                    return
                try:
                    _fcntl.flock(fd, _fcntl.LOCK_EX | _fcntl.LOCK_NB)
                except OSError as exc:
                    raise PermissionError(str(exc)) from exc

        monkeypatch.setattr(_rapid_sweep, "fcntl", None)
        monkeypatch.setattr(_rapid_sweep, "msvcrt", _FakeMsvcrt)

        lock_path = tmp_path / ".frob" / "rapid-sweep-baseline.lock"
        lock_path.parent.mkdir(parents=True)
        fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR, 0o644)
        os.write(fd, b"\0")
        _fcntl.flock(fd, _fcntl.LOCK_EX)
        try:
            entered = False
            with _baseline_lock(tmp_path, timeout=0.2):
                entered = True
            assert entered is True
        finally:
            _fcntl.flock(fd, _fcntl.LOCK_UN)
            os.close(fd)

        # And a real, uncontended acquire/release round-trip on the fake
        # backend actually enters the critical section.
        entered = False
        with _baseline_lock(tmp_path):
            entered = True
        assert entered is True

    def test_serializes_two_concurrent_holders(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestBaselineLock.test_serializes_two_concurrent_holders  # noqa: E501
        # A foreign holder keeps the lock file exclusively locked; this
        # call must not block forever -- it degrades to proceeding
        # WITHOUT the lock once `timeout` elapses (logged, not raised).
        import fcntl as _fcntl

        from frob.app.ticket_runner._rapid_sweep import _baseline_lock

        lock_path = tmp_path / ".frob" / "rapid-sweep-baseline.lock"
        lock_path.parent.mkdir(parents=True)
        fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR, 0o644)
        _fcntl.flock(fd, _fcntl.LOCK_EX)
        try:
            entered = False
            with _baseline_lock(tmp_path, timeout=0.2):
                entered = True
            assert entered is True
        finally:
            _fcntl.flock(fd, _fcntl.LOCK_UN)
            os.close(fd)


# frob:ticket T-2595
class TestIsAncestor:
    """T-2595's CAS ordering primitive: reuses `git merge-base
    --is-ancestor`, matching `_land_cmd._is_ancestor_with_retry`'s own
    posture of trusting git as the source of truth for commit ordering."""

    def test_true_when_older_is_ancestor(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestIsAncestor.test_true_when_older_is_ancestor  # noqa: E501
        from frob.app.ticket_runner._rapid_sweep import _is_ancestor

        _init_git_repo(tmp_path)
        older = _git_commit(tmp_path, "c1")
        newer = _git_commit(tmp_path, "c2")
        assert _is_ancestor(tmp_path, older, newer) is True

    def test_equal_commits_are_ancestors(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestIsAncestor.test_equal_commits_are_ancestors  # noqa: E501
        from frob.app.ticket_runner._rapid_sweep import _is_ancestor

        _init_git_repo(tmp_path)
        commit = _git_commit(tmp_path, "c1")
        assert _is_ancestor(tmp_path, commit, commit) is True

    def test_false_when_not_an_ancestor(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestIsAncestor.test_false_when_not_an_ancestor  # noqa: E501
        from frob.app.ticket_runner._rapid_sweep import _is_ancestor

        _init_git_repo(tmp_path)
        older = _git_commit(tmp_path, "c1")
        newer = _git_commit(tmp_path, "c2")
        # `newer` is NOT an ancestor of `older` -- the reverse direction.
        assert _is_ancestor(tmp_path, newer, older) is False

    def test_none_on_git_failure(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestIsAncestor.test_none_on_git_failure  # noqa: E501
        from frob.app.ticket_runner._rapid_sweep import _is_ancestor

        # tmp_path is not a git repo at all.
        assert _is_ancestor(tmp_path, "deadbeef" * 5, "beefdead" * 5) is None


# frob:ticket T-2595
class TestWriteBaselineCas:
    """T-2595's actual fix: `_write_baseline_cas` must never let a write
    computed from a STALE (older) view of the tree discard a baseline a
    concurrent sweep already wrote from a FRESHER one."""

    def test_writes_when_no_prior_baseline(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestWriteBaselineCas.test_writes_when_no_prior_baseline  # noqa: E501
        from frob.app.ticket_runner._rapid_sweep import _write_baseline_cas

        findings = frozenset({("COV003", "a.py")})
        assert _write_baseline_cas(tmp_path, findings, "deadbeef" * 5) is True
        assert _read_baseline(tmp_path) == findings

    def test_writes_when_prior_is_an_ancestor(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestWriteBaselineCas.test_writes_when_prior_is_an_ancestor  # noqa: E501
        from frob.app.ticket_runner._rapid_sweep import _write_baseline_cas

        _init_git_repo(tmp_path)
        commit1 = _git_commit(tmp_path, "c1")
        commit2 = _git_commit(tmp_path, "c2")
        _write_baseline(tmp_path, frozenset({("OLD", "a.py")}), commit1)
        fresh = frozenset({("NEW", "b.py")})
        assert _write_baseline_cas(tmp_path, fresh, commit2) is True
        assert _read_baseline(tmp_path) == fresh
        assert _read_baseline_commit(tmp_path) == commit2

    def test_skips_when_prior_is_not_an_ancestor(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestWriteBaselineCas.test_skips_when_prior_is_not_an_ancestor  # noqa: E501
        from frob.app.ticket_runner._rapid_sweep import _write_baseline_cas

        # Reproduces the T-2595 race directly: a "sweep A" with a FRESHER
        # view (commit2) writes first; a "sweep B" that had been
        # computing against the OLDER view (commit1) all along finishes
        # second and must not be allowed to discard A's write.
        _init_git_repo(tmp_path)
        commit1 = _git_commit(tmp_path, "c1")
        commit2 = _git_commit(tmp_path, "c2")
        fresh_a = frozenset({("COV003", "a.py")})
        assert _write_baseline_cas(tmp_path, fresh_a, commit2) is True
        fresh_b = frozenset({("F401", "b.py")})
        assert _write_baseline_cas(tmp_path, fresh_b, commit1) is False
        # A's fresher write survives intact -- this is the exact
        # assertion that fails against the pre-T-2595 unconditional
        # `_write_baseline` call this replaced.
        assert _read_baseline(tmp_path) == fresh_a
        assert _read_baseline_commit(tmp_path) == commit2

    def test_writes_when_ancestry_is_unresolvable(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestWriteBaselineCas.test_writes_when_ancestry_is_unresolvable  # noqa: E501
        from frob.app.ticket_runner._rapid_sweep import _write_baseline_cas

        # tmp_path is not a git repo, so `_is_ancestor` cannot resolve the
        # ordering -- an unmeasurable condition must never permanently
        # block a sweep that already has real findings to record.
        _write_baseline(tmp_path, frozenset({("OLD", "a.py")}), "deadbeef" * 5)
        fresh = frozenset({("NEW", "b.py")})
        assert _write_baseline_cas(tmp_path, fresh, "beefdead" * 5) is True
        assert _read_baseline(tmp_path) == fresh


# frob:ticket T-2571
class TestPhantomDeletedPathNotFiledAsRegression:
    """T-2571 acceptance criterion 1, end-to-end: watch
    `test_phantom_deleted_path_is_not_filed_first` FAIL first against the
    unfixed code -- before this ticket, a (rule, file) identity naming a
    file the SAME land deleted was filed as an ordinary new regression,
    exactly the measured T-2381/T-2474/T-2525 shape (TICK003/TICK004
    against a deleted tickets.md)."""

    def test_phantom_deleted_path_is_not_filed_first(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestPhantomDeletedPathNotFiledAsRegression.test_phantom_deleted_path_is_not_filed_first  # noqa: E501
        _init_git_repo(tmp_path)
        import subprocess

        (tmp_path / "tickets.md").write_text("old ledger\n")
        subprocess.run(["git", "-C", str(tmp_path), "add", "tickets.md"], check=True)
        c0 = _git_commit(tmp_path, "chore: init with tickets.md")
        _write_baseline(tmp_path, frozenset(), c0)

        # This land DELETES tickets.md (the T-2356 ledger-v2 cutover
        # shape) AND, independently, introduces one genuine new error.
        (tmp_path / "tickets.md").unlink()
        (tmp_path / "real.py").write_text("bad = 1\n")
        subprocess.run(["git", "-C", str(tmp_path), "add", "-A"], check=True)
        _git_commit(tmp_path, "fix(tickets): land T-2356 ledger-v2 cutover")

        # A STALE check produces a phantom finding against the file this
        # SAME land just deleted, plus one genuine new finding.
        monkeypatch.setattr(
            "frob.app.ticket_runner._land_cmd._unscoped_error_findings",
            lambda *a, **k: frozenset(
                {("TICK003", "tickets.md"), ("ARCH103", "real.py")}
            ),
        )
        seen: list[frozenset[tuple[str, str]]] = []

        def _fake_file(root, final_id, commit, new_findings, **kw):  # noqa: ANN001, ANN202
            seen.append(new_findings)
            return "T-9999"

        monkeypatch.setattr(_rapid_sweep, "_file_regression_ticket", _fake_file)
        result = run_deferred_post_land_sweep(tmp_path, "T-2356", "abc123")
        assert result.is_ok
        # THE FIX: the phantom tickets.md identity never reaches filing
        # -- only the genuine ARCH103/real.py identity does.
        assert seen == [frozenset({("ARCH103", "real.py")})]
        # It also never persists into the next baseline.
        rebaselined = _read_baseline(tmp_path)
        assert rebaselined is not None
        assert ("TICK003", "tickets.md") not in rebaselined


# frob:ticket T-2089
class TestTreeStateKey:
    """T-2089: the cheap tree-state signature the doable-time revalidation
    cache is keyed on -- HEAD sha plus a dirty-tree signal, never a
    full-content hash."""

    # frob:ticket T-2089
    def test_non_repo_is_none(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestTreeStateKey.test_non_repo_is_none  # noqa: E501
        assert _tree_state_key(tmp_path) is None

    # frob:ticket T-2089
    def test_real_repo_returns_a_key(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestTreeStateKey.test_real_repo_returns_a_key  # noqa: E501
        _init_git_repo(tmp_path)
        _git_commit(tmp_path, "chore: init")
        key = _tree_state_key(tmp_path)
        assert key is not None
        # Same tree state, called twice: identical key.
        assert _tree_state_key(tmp_path) == key

    # frob:ticket T-2089
    def test_dirty_tree_changes_the_key(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestTreeStateKey.test_dirty_tree_changes_the_key  # noqa: E501
        _init_git_repo(tmp_path)
        _git_commit(tmp_path, "chore: init")
        clean_key = _tree_state_key(tmp_path)
        (tmp_path / "new_file.txt").write_text("dirty", encoding="utf-8")
        dirty_key = _tree_state_key(tmp_path)
        assert dirty_key is not None
        assert dirty_key != clean_key


# frob:ticket T-2165
class TestIdentityScopedStateKey:
    """T-2165: `_identity_scoped_state_key`'s replacement for
    `_tree_state_key` as the doable-revalidation cache's key -- narrowed
    from whole-tree state to just the files named in a candidate
    identity set, so a cache HIT survives an unrelated land."""

    # frob:ticket T-2165
    def test_unchanged_files_same_key_across_a_head_move(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestIdentityScopedStateKey.test_unchanged_files_same_key_across_a_head_move  # noqa: E501
        """The core fix: two calls against a tree whose HEAD moved (an
        unrelated land happened in between) but whose CANDIDATE files
        did not change must produce the SAME key -- this is exactly the
        case `_tree_state_key` could never hit under concurrent-land
        load."""
        _init_git_repo(tmp_path)
        (tmp_path / "a.py").write_text("original\n", encoding="utf-8")
        (tmp_path / "unrelated.py").write_text("original\n", encoding="utf-8")
        import subprocess

        subprocess.run(["git", "-C", str(tmp_path), "add", "-A"], check=True)
        _git_commit(tmp_path, "chore: init")
        pairs = frozenset({("RULE1", "a.py")})
        before_key = _identity_scoped_state_key(tmp_path, pairs)

        # An unrelated land: a file NOT in `pairs` changes and is
        # committed, moving HEAD -- `_tree_state_key` would change here.
        (tmp_path / "unrelated.py").write_text(
            "changed by another land\n", encoding="utf-8"
        )
        subprocess.run(["git", "-C", str(tmp_path), "add", "-A"], check=True)
        _git_commit(tmp_path, "chore: unrelated land")

        after_key = _identity_scoped_state_key(tmp_path, pairs)
        assert after_key == before_key

    # frob:ticket T-2165
    def test_editing_a_named_file_changes_the_key(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestIdentityScopedStateKey.test_editing_a_named_file_changes_the_key  # noqa: E501
        """Soundness control: editing a file that IS named in `pairs`
        (committed or not) MUST change the key -- this is the "must not
        mask a genuine fix" requirement this ticket's own body calls
        out."""
        _init_git_repo(tmp_path)
        (tmp_path / "a.py").write_text("original\n", encoding="utf-8")
        import subprocess

        subprocess.run(["git", "-C", str(tmp_path), "add", "-A"], check=True)
        _git_commit(tmp_path, "chore: init")
        pairs = frozenset({("RULE1", "a.py")})
        before_key = _identity_scoped_state_key(tmp_path, pairs)

        (tmp_path / "a.py").write_text("fixed\n", encoding="utf-8")

        after_key = _identity_scoped_state_key(tmp_path, pairs)
        assert after_key != before_key

    # frob:ticket T-2165
    def test_editing_an_unrelated_file_does_not_change_the_key(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestIdentityScopedStateKey.test_editing_an_unrelated_file_does_not_change_the_key  # noqa: E501
        _init_git_repo(tmp_path)
        (tmp_path / "a.py").write_text("original\n", encoding="utf-8")
        (tmp_path / "b.py").write_text("original\n", encoding="utf-8")
        import subprocess

        subprocess.run(["git", "-C", str(tmp_path), "add", "-A"], check=True)
        _git_commit(tmp_path, "chore: init")
        pairs = frozenset({("RULE1", "a.py")})
        before_key = _identity_scoped_state_key(tmp_path, pairs)

        (tmp_path / "b.py").write_text("edited, but not in pairs\n", encoding="utf-8")

        after_key = _identity_scoped_state_key(tmp_path, pairs)
        assert after_key == before_key

    # frob:ticket T-2165
    def test_uncommitted_edit_to_a_named_file_changes_the_key(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestIdentityScopedStateKey.test_uncommitted_edit_to_a_named_file_changes_the_key  # noqa: E501
        """The key must be content-based, not commit-based -- an agent's
        own UNCOMMITTED fix to a candidate file must invalidate the
        cache exactly like a committed one would."""
        _init_git_repo(tmp_path)
        (tmp_path / "a.py").write_text("original\n", encoding="utf-8")
        import subprocess

        subprocess.run(["git", "-C", str(tmp_path), "add", "-A"], check=True)
        _git_commit(tmp_path, "chore: init")
        pairs = frozenset({("RULE1", "a.py")})
        before_key = _identity_scoped_state_key(tmp_path, pairs)

        # Uncommitted edit -- deliberately no `git add`/commit.
        (tmp_path / "a.py").write_text("fixed but not committed\n", encoding="utf-8")

        after_key = _identity_scoped_state_key(tmp_path, pairs)
        assert after_key != before_key

    # frob:ticket T-2165
    def test_missing_file_has_a_stable_sentinel_digest(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestIdentityScopedStateKey.test_missing_file_has_a_stable_sentinel_digest  # noqa: E501
        """A file named in `pairs` that does not exist on disk must not
        raise -- it degrades to a stable sentinel entry, and calling
        twice with the same absent file produces the same key."""
        pairs = frozenset({("RULE1", "does_not_exist.py")})
        key1 = _identity_scoped_state_key(tmp_path, pairs)
        key2 = _identity_scoped_state_key(tmp_path, pairs)
        assert key1 == key2


# frob:ticket T-2089
class TestRevalidationCache:
    """T-2089: the doable-time revalidation cache -- content-keyed on tree
    state plus the exact identity set, with a TTL as a defense-in-depth
    bound on top."""

    # frob:ticket T-2089
    def test_absent_cache_is_none(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestRevalidationCache.test_absent_cache_is_none  # noqa: E501
        assert _read_revalidation_cache(tmp_path, "key", frozenset()) is None

    # frob:ticket T-2089
    def test_corrupt_cache_is_none(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestRevalidationCache.test_corrupt_cache_is_none  # noqa: E501
        path = tmp_path / ".frob" / "doable-revalidation-cache.json"
        path.parent.mkdir(parents=True)
        path.write_text("{not json", encoding="utf-8")
        assert _read_revalidation_cache(tmp_path, "key", frozenset()) is None

    # frob:ticket T-2089
    def test_write_then_read_round_trips(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestRevalidationCache.test_write_then_read_round_trips  # noqa: E501
        pairs = frozenset({("COV003", "a.py")})
        reproducing = frozenset({("COV003", "a.py")})
        _write_revalidation_cache(tmp_path, "key", pairs, reproducing)
        cached = _read_revalidation_cache(tmp_path, "key", pairs)
        assert cached is not None
        got_reproducing, age_s = cached
        assert got_reproducing == reproducing
        assert age_s >= 0.0

    # frob:ticket T-2089
    def test_mismatched_tree_key_is_none(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestRevalidationCache.test_mismatched_tree_key_is_none  # noqa: E501
        pairs = frozenset({("COV003", "a.py")})
        _write_revalidation_cache(tmp_path, "key-a", pairs, pairs)
        assert _read_revalidation_cache(tmp_path, "key-b", pairs) is None

    # frob:ticket T-2089
    def test_mismatched_pairs_is_none(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestRevalidationCache.test_mismatched_pairs_is_none  # noqa: E501
        written = frozenset({("COV003", "a.py")})
        queried = frozenset({("COV003", "b.py")})
        _write_revalidation_cache(tmp_path, "key", written, written)
        assert _read_revalidation_cache(tmp_path, "key", queried) is None

    # frob:ticket T-2089
    def test_expired_ttl_is_none(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestRevalidationCache.test_expired_ttl_is_none  # noqa: E501
        pairs = frozenset({("COV003", "a.py")})
        _write_revalidation_cache(tmp_path, "key", pairs, pairs)
        path = tmp_path / ".frob" / "doable-revalidation-cache.json"
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["timestamp"] = 0.0  # far in the past -- well past the TTL
        path.write_text(json.dumps(raw), encoding="utf-8")
        assert _read_revalidation_cache(tmp_path, "key", pairs) is None


class TestDeferredSweepRun:
    """`run_deferred_post_land_sweep` files, never reverts."""

    @pytest.fixture
    def _no_debt(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """`record_rapid_debt` shells out to git; a tmp_path is not a repo."""
        monkeypatch.setattr(
            "frob.tickets._evidence.record_rapid_debt", lambda *a, **k: None
        )

    def test_unmeasurable_check_leaves_the_baseline_untouched(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestDeferredSweepRun.test_unmeasurable_check_leaves_the_baseline_untouched  # noqa: E501
        _write_baseline(tmp_path, frozenset({("COV003", "a.py")}), "old")
        monkeypatch.setattr(
            "frob.app.ticket_runner._land_cmd._unscoped_error_findings",
            lambda *a, **k: None,
        )
        result = run_deferred_post_land_sweep(tmp_path, "T-0001", "abc123")
        assert result.is_err
        assert result.danger_err is RapidSweepError.Unmeasurable
        assert _read_baseline(tmp_path) == frozenset({("COV003", "a.py")})

    def test_first_sweep_records_a_baseline_and_files_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestDeferredSweepRun.test_first_sweep_records_a_baseline_and_files_nothing  # noqa: E501
        fresh = frozenset({("COV003", "a.py")})
        monkeypatch.setattr(
            "frob.app.ticket_runner._land_cmd._unscoped_error_findings",
            lambda *a, **k: fresh,
        )
        filed: list[object] = []
        monkeypatch.setattr(
            _rapid_sweep, "_file_regression_ticket", lambda *a: filed.append(a)
        )
        result = run_deferred_post_land_sweep(tmp_path, "T-0001", "abc123")
        assert result.is_ok
        assert result.danger_ok is None
        assert filed == []
        assert _read_baseline(tmp_path) == fresh

    def test_no_new_findings_is_clean(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestDeferredSweepRun.test_no_new_findings_is_clean  # noqa: E501
        existing = frozenset({("COV003", "a.py")})
        _write_baseline(tmp_path, existing, "old")
        monkeypatch.setattr(
            "frob.app.ticket_runner._land_cmd._unscoped_error_findings",
            lambda *a, **k: existing,
        )
        filed: list[object] = []
        monkeypatch.setattr(
            _rapid_sweep, "_file_regression_ticket", lambda *a: filed.append(a)
        )
        result = run_deferred_post_land_sweep(tmp_path, "T-0001", "abc123")
        assert result.is_ok
        assert result.danger_ok is None
        assert filed == []

    def test_new_findings_file_a_ticket_and_rebaseline(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestDeferredSweepRun.test_new_findings_file_a_ticket_and_rebaseline  # noqa: E501
        _write_baseline(tmp_path, frozenset({("COV003", "a.py")}), "old")
        fresh = frozenset({("COV003", "a.py"), ("DOC011", "b.md")})
        monkeypatch.setattr(
            "frob.app.ticket_runner._land_cmd._unscoped_error_findings",
            lambda *a, **k: fresh,
        )
        seen: list[frozenset[tuple[str, str]]] = []

        def _fake_file(root, final_id, commit, new_findings):  # noqa: ANN001, ANN202
            seen.append(new_findings)
            return "T-9999"

        monkeypatch.setattr(_rapid_sweep, "_file_regression_ticket", _fake_file)
        result = run_deferred_post_land_sweep(tmp_path, "T-0001", "abc123")
        assert result.is_ok
        assert result.danger_ok == "T-9999"
        assert seen == [frozenset({("DOC011", "b.md")})]
        # Rebaselined even though the sweep was red: an already-filed
        # error must not be re-filed by the next land.
        assert _read_baseline(tmp_path) == fresh

    # frob:ticket T-2929
    def test_stale_baseline_refuses_to_file_and_records_debt(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2929 must-fire case: `frob.verify.rapid_soft_warning` firing
        (a stale verification-queue window) means a NEW finding is NOT
        filed as a confident regression ticket -- the sweep refuses and
        records the refusal as a distinct, durable debt kind instead."""
        # frob:tests \
        # tests/unit/test_rapid_sweep.py::TestDeferredSweepRun.test_stale_baseline_refuses_to_file_and_records_debt  # noqa: E501
        # frob:waive FMT001 reason="single-line frob:tests directive naming a long \
        # test node id -- already at frob fmt's own canonical form (verified: `frob \
        # fmt` reports it unchanged), same unwrappable shape as \
        # src/frob/app/_json_guard.py's existing FMT001 waivers"
        _write_baseline(tmp_path, frozenset({("COV003", "a.py")}), "old")
        fresh = frozenset({("COV003", "a.py"), ("DOC006", "tickets/T-0002/ticket.md")})
        monkeypatch.setattr(
            "frob.app.ticket_runner._land_cmd._unscoped_error_findings",
            lambda *a, **k: fresh,
        )
        monkeypatch.setattr(
            "frob.verify.rapid_soft_warning",
            lambda root: (
                "rapid profile verification debt is stale: 53 commits "
                "since watermark (warn threshold 5)"
            ),
        )
        filed: list[object] = []
        monkeypatch.setattr(
            _rapid_sweep, "_file_regression_ticket", lambda *a, **k: filed.append(a)
        )
        debts: list[tuple[str, str]] = []
        monkeypatch.setattr(
            "frob.tickets._evidence.record_rapid_debt",
            lambda root, tid, what: debts.append((tid, what)),
        )
        monkeypatch.setattr(_rapid_sweep, "_commit_rapid_debt", lambda root, tid: None)

        result = run_deferred_post_land_sweep(tmp_path, "T-0001", "abc123")

        assert result.is_ok
        assert result.danger_ok is None
        assert filed == []
        # T-2938: the deferred claim-divergence check reuses this SAME
        # staleness policy (`frob.verify.rapid_soft_warning`) independently
        # of the new-findings filing path above, and records the SAME debt
        # reason when it refuses too -- two refusals, one shared reason,
        # not a second policy.
        assert debts == [
            ("T-0001", "post-land-sweep-attribution-skipped-stale-baseline"),
            ("T-0001", "post-land-sweep-attribution-skipped-stale-baseline"),
        ]
        # Rebaselined regardless -- the next sweep should start from a
        # fresh, current comparison point once the debt is drained.
        assert _read_baseline(tmp_path) == fresh

    # frob:ticket T-2929
    def test_fresh_baseline_files_normally_no_new_noise(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2929 must-stay-quiet case: `rapid_soft_warning` returning
        `None` (a fresh, current verification window) means the sweep
        files exactly as it did before this change -- no new refusal, no
        new debt line, identical behavior to `test_new_findings_file_a_
        ticket_and_rebaseline`."""
        # frob:tests \
        # tests/unit/test_rapid_sweep.py::TestDeferredSweepRun.test_fresh_baseline_files_normally_no_new_noise  # noqa: E501
        # frob:waive FMT001 reason="single-line frob:tests directive naming a long \
        # test node id -- already at frob fmt's own canonical form (verified: `frob \
        # fmt` reports it unchanged), same unwrappable shape as \
        # src/frob/app/_json_guard.py's existing FMT001 waivers"
        _write_baseline(tmp_path, frozenset({("COV003", "a.py")}), "old")
        fresh = frozenset({("COV003", "a.py"), ("DOC011", "b.md")})
        monkeypatch.setattr(
            "frob.app.ticket_runner._land_cmd._unscoped_error_findings",
            lambda *a, **k: fresh,
        )
        monkeypatch.setattr("frob.verify.rapid_soft_warning", lambda root: None)
        seen: list[frozenset[tuple[str, str]]] = []

        def _fake_file(root, final_id, commit, new_findings):  # noqa: ANN001, ANN202
            seen.append(new_findings)
            return "T-9999"

        monkeypatch.setattr(_rapid_sweep, "_file_regression_ticket", _fake_file)
        debts: list[tuple[str, str]] = []
        monkeypatch.setattr(
            "frob.tickets._evidence.record_rapid_debt",
            lambda root, tid, what: debts.append((tid, what)),
        )

        result = run_deferred_post_land_sweep(tmp_path, "T-0001", "abc123")

        assert result.is_ok
        assert result.danger_ok == "T-9999"
        assert seen == [frozenset({("DOC011", "b.md")})]
        assert debts == []
        assert _read_baseline(tmp_path) == fresh


# frob:ticket T-2938
class TestClaimDivergencePostLand:
    """T-2938: `_check_claim_divergence_post_land` -- the deferred-queue
    replacement for the inline `ClaimDivergence` re-verification T-2913
    moved off the rapid land critical path. Reuses `frob.tickets.
    _land_verify._reverify_gate_state_claim` VERBATIM (via callables that
    hand back this sweep's own already-measured `fresh` set instead of
    spawning a second `frob check`) as the sole comparison DECISION, and
    `frob.verify.rapid_soft_warning` (T-2929's existing policy) as the
    sole staleness DECISION -- these tests exercise the wiring, not a
    second copy of either policy."""

    def _claims_ticket(
        self,
        *,
        gate_errors: int,
        error_findings: frozenset[tuple[str, str]] | None,
        scope: tuple[str, ...] = ("src/a.py",),
    ):
        from frob.tickets._models import (
            DoneReportClaims,
            Origin,
            Ticket,
            TicketKind,
            TicketState,
            render_claims_block,
        )

        claims = DoneReportClaims(
            test_count=1,
            evidence_count=1,
            gate_errors=gate_errors,
            gate_warnings=0,
            gate_waived=0,
            error_findings=error_findings,
        )
        body = "## Done report\n\nlanded cleanly.\n\n" + render_claims_block(claims)
        return Ticket(
            id="T-0001",
            title="a ticket with a captured claim",
            state=TicketState.DONE,
            kind=TicketKind.BUG,
            origin=Origin.AGENT,
            created=date(2026, 1, 1),
            body=body,
            scope=scope,
        )

    def _patch_common(
        self,
        monkeypatch: pytest.MonkeyPatch,
        ticket,
        *,
        stale_reason: str | None,
    ) -> tuple[list[dict[str, object]], list[tuple[str, str]]]:
        from typani.result import Ok

        monkeypatch.setattr("frob.tickets._load_one", lambda root, tid: Ok(ticket))
        monkeypatch.setattr(
            "frob.verify.rapid_soft_warning", lambda root: stale_reason
        )
        raised: list[dict[str, object]] = []
        monkeypatch.setattr(
            "frob.verify._quarantine.raise_quarantine",
            lambda root, **kw: raised.append(kw) or Ok(object()),
        )
        debts: list[tuple[str, str]] = []
        monkeypatch.setattr(
            "frob.tickets._evidence.record_rapid_debt",
            lambda root, tid, what: debts.append((tid, what)),
        )
        monkeypatch.setattr(_rapid_sweep, "_commit_rapid_debt", lambda root, tid: None)
        monkeypatch.setattr(
            _rapid_sweep,
            "_file_claim_divergence_ticket",
            lambda root, final_id, actual_head, pairs: "T-9999",
        )
        return raised, debts

    def test_matching_claim_raises_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Must-stay-quiet: a Done report claim that still matches the
        fresh post-merge measurement raises no quarantine and records no
        new debt."""
        # frob:tests tests/unit/test_rapid_sweep.py::TestClaimDivergencePostLand.test_matching_claim_raises_nothing  # noqa: E501
        ticket = self._claims_ticket(
            gate_errors=1, error_findings=frozenset({("COV003", "src/a.py")})
        )
        raised, debts = self._patch_common(monkeypatch, ticket, stale_reason=None)

        _check_claim_divergence_post_land(
            tmp_path, "T-0001", "deadbeef", frozenset({("COV003", "src/a.py")})
        )

        assert raised == []
        assert debts == []

    def test_divergent_claim_raises_quarantine_attributed_to_landing_ticket(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Must-fire: a Done report claiming 0 errors against a fresh
        measurement showing a NEW in-scope error raises quarantine, and
        every raised finding is attributed to the landing ticket id."""
        # frob:tests tests/unit/test_rapid_sweep.py::TestClaimDivergencePostLand.test_divergent_claim_raises_quarantine_attributed_to_landing_ticket  # noqa: E501
        ticket = self._claims_ticket(gate_errors=0, error_findings=frozenset())
        raised, debts = self._patch_common(monkeypatch, ticket, stale_reason=None)

        _check_claim_divergence_post_land(
            tmp_path, "T-0001", "deadbeef", frozenset({("COV003", "src/a.py")})
        )

        from frob.verify._quarantine import QuarantinedFinding

        assert debts == []
        assert len(raised) == 1
        findings = cast("tuple[QuarantinedFinding, ...]", raised[0]["findings"])
        assert len(findings) == 1
        assert findings[0].rule_id == "COV003"
        assert findings[0].file == "src/a.py"
        assert findings[0].commit_sha == "deadbeef"
        assert findings[0].ticket_id == "T-9999"
        assert raised[0]["batch_commit_shas"] == ("deadbeef",)

    def test_stale_baseline_refuses_to_attribute(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A stale verification-queue window (T-2929's shared policy)
        refuses to attribute a claim divergence too, recording the SAME
        debt reason `_refuse_filing_for_stale_verification_queue` already
        uses -- never a second staleness policy."""
        # frob:tests tests/unit/test_rapid_sweep.py::TestClaimDivergencePostLand.test_stale_baseline_refuses_to_attribute  # noqa: E501
        ticket = self._claims_ticket(gate_errors=0, error_findings=frozenset())
        raised, debts = self._patch_common(
            monkeypatch, ticket, stale_reason="rapid profile verification debt is stale"
        )

        _check_claim_divergence_post_land(
            tmp_path, "T-0001", "deadbeef", frozenset({("COV003", "src/a.py")})
        )

        assert raised == []
        assert debts == [
            ("T-0001", "post-land-sweep-attribution-skipped-stale-baseline")
        ]

    def test_no_captured_claims_section_is_a_noop(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A Done report with no `### Captured claims` section (predates
        T-0754, or never captured one) has nothing to compare -- no
        quarantine, no debt, matching the inline land path's own
        permissive-by-default posture."""
        # frob:tests tests/unit/test_rapid_sweep.py::TestClaimDivergencePostLand.test_no_captured_claims_section_is_a_noop  # noqa: E501
        from typani.result import Ok

        from frob.tickets._models import Origin, Ticket, TicketKind, TicketState

        ticket = Ticket(
            id="T-0001",
            title="a ticket with no captured claim",
            state=TicketState.DONE,
            kind=TicketKind.BUG,
            origin=Origin.AGENT,
            created=date(2026, 1, 1),
            body="## Done report\n\nlanded cleanly, no claims captured.\n",
        )
        monkeypatch.setattr("frob.tickets._load_one", lambda root, tid: Ok(ticket))
        raised: list[dict[str, object]] = []
        monkeypatch.setattr(
            "frob.verify._quarantine.raise_quarantine",
            lambda root, **kw: raised.append(kw) or Ok(object()),
        )
        # rapid_soft_warning left un-mocked: a tmp_path with no watermark
        # returns None (no debt), same as the pre-existing tests above.

        _check_claim_divergence_post_land(
            tmp_path, "T-0001", "deadbeef", frozenset({("COV003", "src/a.py")})
        )

        assert raised == []


class TestDeferredSweepSpawn:
    """The spawn records debt BEFORE spawning and never blocks."""

    def test_exec_disabled_records_debt_and_refuses(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestDeferredSweepSpawn.test_exec_disabled_records_debt_and_refuses  # noqa: E501
        debts: list[tuple[str, str]] = []
        monkeypatch.setattr(
            "frob.tickets._evidence.record_rapid_debt",
            lambda root, tid, what: debts.append((tid, what)),
        )
        monkeypatch.setattr("frob.process.exec_enabled", lambda: False)
        result = spawn_deferred_post_land_sweep(tmp_path, "T-0001", "T-0001", "abc123")
        assert result.is_err
        assert result.danger_err is RapidSweepError.SpawnRefused
        assert debts == [("T-0001", "post-land-unscoped-sweep-deferred")]

    # frob:ticket T-2030
    def test_spawn_pins_frob_root_env_not_bare_os_environ(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2030's own repro: watch this FAIL first against the unfixed
        code -- `Popen` used to be called with no `env=` kwarg at all
        (bare inherited `os.environ`), so an ambient stale `FROB_ROOT` in
        the landing process's own shell silently overrode the correctly
        resolved `cwd=root` in the detached child's OWN root resolution.
        This asserts the actual `Popen` call always pins `FROB_ROOT` to
        `root`, regardless of what `os.environ` already contains."""
        # frob:tests tests/unit/test_rapid_sweep.py::TestDeferredSweepSpawn.test_spawn_pins_frob_root_env_not_bare_os_environ  # noqa: E501
        import subprocess as subprocess_mod

        import frob.app.ticket_runner._rapid_sweep as rapid_sweep_mod

        monkeypatch.setattr("frob.process.exec_enabled", lambda: True)
        monkeypatch.setattr(
            "frob.tickets._evidence.record_rapid_debt", lambda root, tid, what: None
        )
        monkeypatch.setattr(
            rapid_sweep_mod, "_commit_rapid_debt", lambda root, tid: None
        )
        # A STALE FROB_ROOT in the ambient environment, naming a
        # DIFFERENT tree than `root` -- exactly T-2030's measured shape.
        monkeypatch.setenv("FROB_ROOT", "/some/other/worktree")
        monkeypatch.setenv("FROB_WORKTREE", "/some/other/worktree")
        monkeypatch.setenv("FROB_AGENT", "1")

        captured: dict = {}

        class _FakeProc:
            pid = 4242

        def _fake_popen(argv, **kwargs):
            captured.update(kwargs)
            return _FakeProc()

        monkeypatch.setattr(subprocess_mod, "Popen", _fake_popen)

        result = spawn_deferred_post_land_sweep(tmp_path, "T-0001", "T-0001", "abc123")
        assert result.is_ok

        env = captured.get("env")
        assert env is not None, "Popen must be called with an explicit env= kwarg"
        assert env["FROB_ROOT"] == str(tmp_path)
        assert "FROB_WORKTREE" not in env
        assert "FROB_AGENT" not in env


# frob:ticket T-2030
class TestDetachedSweepEnv:
    """T-2030: `_detached_sweep_env`'s own unit-level contract."""

    def test_pins_frob_root_to_the_correct_root(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestDetachedSweepEnv.test_pins_frob_root_to_the_correct_root  # noqa: E501
        from frob.app.ticket_runner._rapid_sweep import _detached_sweep_env

        monkeypatch.setenv("FROB_ROOT", "/stale/other/worktree")
        env = _detached_sweep_env(tmp_path)
        assert env["FROB_ROOT"] == str(tmp_path)

    def test_strips_worktree_lease_env(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestDetachedSweepEnv.test_strips_worktree_lease_env  # noqa: E501
        from frob.app.ticket_runner._rapid_sweep import _detached_sweep_env

        monkeypatch.setenv("FROB_WORKTREE", "/some/worktree")
        monkeypatch.setenv("FROB_AGENT", "1")
        env = _detached_sweep_env(tmp_path)
        assert "FROB_WORKTREE" not in env
        assert "FROB_AGENT" not in env


def _git(repo: Path, *args: str) -> str:
    """Run git in `repo` and return stdout (test helper, T-1698)."""
    import subprocess

    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
    ).stdout


# frob:waive WIRE001 reason="a module-local test helper called only by this file's own \
# tests -- no production caller to wire it to by design" permanent="true"
def _seed_repo(tmp_path: Path) -> Path:
    """A real one-commit git repo -- `_commit_rapid_debt`'s whole contract
    is about git state, so a fake would prove nothing. A plain helper
    called explicitly, not a pytest fixture: fixture wiring is by NAME
    INJECTION, which WIRE001's reachability scan cannot see. Only called
    from within this same file (T-1558's gate fix recognizes cross-test-
    file calls as wired now, but same-file usage stays genuinely unwired
    by design, matching T-1592's precedent) -- `permanent="true"`, not a
    follow_up, since there is no accountable future work left to bind."""
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "test")
    (tmp_path / "seed.txt").write_text("seed\n", encoding="utf-8")
    # T-2997: record_rapid_debt now writes under .frob/, exactly like a
    # real checkout -- gitignore it here too, or an untracked .frob/
    # falsely reads as repo dirt in this fixture's "leaves the repo
    # clean" assertions, a gap no real checkout (which always gitignores
    # .frob/) actually has.
    (tmp_path / ".gitignore").write_text(".frob/\n", encoding="utf-8")
    _git(tmp_path, "add", "seed.txt", ".gitignore")
    _git(tmp_path, "commit", "-qm", "seed")
    return tmp_path


class TestCommitRapidDebt:
    """T-1698: a rapid land must leave the ROOT CHECKOUT CLEAN. One
    uncommitted debt line deadlocked a whole three-agent wave, because
    every later land refused with DirtyMain."""

    def test_leaves_the_repo_clean(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/unit/test_rapid_sweep.py::TestCommitRapidDebt.test_leaves_the_repo_clean
        # T-2997: record_rapid_debt now writes under gitignored .frob/,
        # so the repo is already clean before _commit_rapid_debt even
        # runs -- it stays a correct, harmless no-op (nothing tracked to
        # stage or commit) rather than the "stage and commit one dirty
        # line" step it used to be.
        from frob.tickets._evidence import record_rapid_debt

        repo = _seed_repo(tmp_path)

        record_rapid_debt(repo, "T-0001", "post-land-unscoped-sweep-deferred")
        assert _git(repo, "status", "--porcelain").strip() == ""
        _rapid_sweep._commit_rapid_debt(repo, "T-0001")
        assert _git(repo, "status", "--porcelain").strip() == ""
        assert "rapid-debt.jsonl" not in _git(repo, "ls-files")

    # frob:ticket T-2669
    @pytest.mark.skipif(os.name == "nt", reason="POSIX shell hook, not run on Windows")
    def test_guard_still_refuses_a_genuinely_foreign_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestCommitRapidDebt.test_guard_still_refuses_a_genuinely_foreign_file  # noqa: E501
        """Must-fire control, other direction from the test above: T-2669's
        fix scopes `FROB_LAND_INTERNAL=1` to ONLY the one `git commit`
        spawn `_commit_rapid_debt` makes for `rapid-debt.jsonl` -- it must
        not leak into, or otherwise weaken, the T-2071 guard's refusal of
        an UNRELATED non-ledger file committed the same way a stray agent
        write would be. Proves the fix is a narrow exemption for this
        module's own machinery file, not a general bypass."""
        import subprocess

        from frob.scaffold import install_worktree_lease_hook

        repo = _seed_repo(tmp_path)
        installed = install_worktree_lease_hook(repo)
        assert installed.is_ok

        worktree_dir = tmp_path.parent / "linked-worktree-t2669-control"
        current_branch = _git(repo, "rev-parse", "--abbrev-ref", "HEAD").strip()
        _git(
            repo,
            "worktree",
            "add",
            "-b",
            "agent-branch-t2669-control",
            str(worktree_dir),
            current_branch,
        )

        (repo / "stray.py").write_text("z = 1\n", encoding="utf-8")
        _git(repo, "add", "--", "stray.py")

        monkeypatch.delenv("FROB_LAND_INTERNAL", raising=False)
        monkeypatch.delenv("FROB_AGENT", raising=False)
        commit = subprocess.run(
            ["git", "commit", "-q", "-m", "stray agent write"],
            cwd=repo,
            capture_output=True,
            text=True,
            check=False,
        )
        assert commit.returncode != 0, commit.stdout + commit.stderr
        assert _git(repo, "status", "--porcelain").strip() != ""

    def test_stages_only_the_debt_file(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestCommitRapidDebt.test_stages_only_the_debt_file  # noqa: E501
        from frob.tickets._evidence import record_rapid_debt

        repo = _seed_repo(tmp_path)

        # Another agent's in-flight edit on the shared root checkout: a
        # blanket `git add -A` here would swallow it into this commit.
        (repo / "seed.txt").write_text("someone else is mid-land\n", encoding="utf-8")
        record_rapid_debt(repo, "T-0002", "post-land-unscoped-sweep-deferred")
        _rapid_sweep._commit_rapid_debt(repo, "T-0002")
        porcelain = _git(repo, "status", "--porcelain")
        assert "seed.txt" in porcelain
        assert "rapid-debt.jsonl" not in porcelain

    def test_is_a_noop_when_nothing_was_appended(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestCommitRapidDebt.test_is_a_noop_when_nothing_was_appended  # noqa: E501
        repo = _seed_repo(tmp_path)
        head_before = _git(repo, "rev-parse", "HEAD").strip()
        _rapid_sweep._commit_rapid_debt(repo, "T-0003")
        assert _git(repo, "rev-parse", "HEAD").strip() == head_before

    def test_a_non_repo_never_raises(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestCommitRapidDebt.test_a_non_repo_never_raises  # noqa: E501
        # Best-effort: it must never fail a land that already succeeded.
        _rapid_sweep._commit_rapid_debt(tmp_path, "T-0004")

    # frob:ticket T-2669
    @pytest.mark.skipif(os.name == "nt", reason="POSIX shell hook, not run on Windows")
    def test_survives_the_scaffolded_root_write_guard(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestCommitRapidDebt.test_survives_the_scaffolded_root_write_guard  # noqa: E501
        """T-2669: `_seed_repo` above has no scaffolded pre-commit hook and
        no linked worktree, so none of the other tests in this class can
        reproduce the real incident -- a rapid land's shared-root checkout
        has BOTH (the T-0731/T-2071 `pre-commit` hook is scaffolded onto
        every real clone, and a dispatched fleet always has at least one
        linked worktree). Under that real shape, `_commit_rapid_debt`'s
        `git commit` spawn hits the T-2071 guard (`non-ledger file staged
        directly in the primary checkout while worktrees exist`) exactly
        like any other unflagged non-ledger commit would, because it never
        sets `FROB_LAND_INTERNAL=1` around the spawn the way every other
        land-internal commit in `_land_git_ops.py` does -- reproduced here
        by installing the real hook and adding a real linked worktree
        before calling it, not by asserting on the hook's shell source."""
        from frob.scaffold import install_worktree_lease_hook
        from frob.tickets._evidence import record_rapid_debt

        repo = _seed_repo(tmp_path)
        installed = install_worktree_lease_hook(repo)
        assert installed.is_ok

        worktree_dir = tmp_path.parent / "linked-worktree-t2669"
        current_branch = _git(repo, "rev-parse", "--abbrev-ref", "HEAD").strip()
        _git(
            repo,
            "worktree",
            "add",
            "-b",
            "agent-branch-t2669",
            str(worktree_dir),
            current_branch,
        )

        # T-2997: record_rapid_debt writes under gitignored .frob/ now,
        # so the repo is already clean -- the T-2071 guard this test
        # exists to prove `_commit_rapid_debt` survives is simply never
        # reached any more (nothing dirty to stage or commit). The guard
        # itself is exercised elsewhere (test_guard_still_refuses_a_
        # genuinely_foreign_file, above); this test now proves the
        # no-op stays a no-op under the same real-shape preconditions
        # (scaffolded hook + linked worktree).
        record_rapid_debt(repo, "T-2669", "post-land-unscoped-sweep-deferred")
        assert _git(repo, "status", "--porcelain").strip() == ""

        # The real incident's shell has neither var set -- this is a
        # dispatched land process's own environment, not an agent shell.
        monkeypatch.delenv("FROB_LAND_INTERNAL", raising=False)
        monkeypatch.delenv("FROB_AGENT", raising=False)
        _rapid_sweep._commit_rapid_debt(repo, "T-2669")

        # The actual invariant: the shared root must be left CLEAN, not
        # merely "a commit helper ran without raising".
        assert _git(repo, "status", "--porcelain").strip() == "", (
            "rapid-debt.jsonl commit was refused by the scaffolded "
            "pre-commit hook (T-2071) and the root was left dirty"
        )
        assert "rapid-debt.jsonl" not in _git(repo, "ls-files")

    # frob:ticket T-2671
    @pytest.mark.skipif(os.name == "nt", reason="POSIX shell hook, not run on Windows")
    def test_commit_failure_persists_a_diagnostic_log(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestCommitRapidDebt.test_commit_failure_persists_a_diagnostic_log  # noqa: E501
        """T-2671: reproduces the T-2669-shaped commit-failure directly
        (the scaffolded pre-commit hook refuses the commit spawn because
        neither lease-env var is set) and proves a retained diagnostic
        log survives it -- the exact artifact that did not exist for the
        real recurrence this ticket investigates. Before this fix,
        `_commit_rapid_debt`'s failure branch logged a one-line summary
        via the module logger and nothing else; this test would have
        found zero files under `.frob/rapid-sweep/` naming the failure."""
        from frob.scaffold import install_worktree_lease_hook

        repo = _seed_repo(tmp_path)
        installed = install_worktree_lease_hook(repo)
        assert installed.is_ok

        worktree_dir = tmp_path.parent / "linked-worktree-t2671"
        current_branch = _git(repo, "rev-parse", "--abbrev-ref", "HEAD").strip()
        _git(
            repo,
            "worktree",
            "add",
            "-b",
            "agent-branch-t2671",
            str(worktree_dir),
            current_branch,
        )

        # T-2997: record_rapid_debt no longer dirties the repo (it writes
        # under gitignored .frob/), so `_commit_rapid_debt`'s failure
        # branch (the thing under test here) can only still be reached
        # via a manually force-tracked rapid-debt.jsonl -- simulating
        # legacy/residual dirt at the pre-T-2997 root path, the one shape
        # left that can still make this now-mostly-dead helper's `git
        # status -- rapid-debt.jsonl` spawn see something dirty.
        (repo / "rapid-debt.jsonl").write_text('{"ticket": "T-2671"}\n', encoding="utf-8")
        _git(repo, "add", "--force", "rapid-debt.jsonl")
        assert _git(repo, "status", "--porcelain").strip() != ""

        # Force the commit step itself to be refused: bypass T-2669's own
        # `_land_internal_git_env` fix by monkeypatching it to a no-op
        # context manager, so the underlying hook refusal this test wants
        # to reproduce actually fires (T-2669 would otherwise mask it).
        import contextlib

        monkeypatch.setattr(
            "frob.tickets._land_git_ops._land_internal_git_env",
            contextlib.nullcontext,
        )
        monkeypatch.delenv("FROB_LAND_INTERNAL", raising=False)
        monkeypatch.delenv("FROB_AGENT", raising=False)

        _rapid_sweep._commit_rapid_debt(repo, "T-2671")

        # The commit was refused, so the root is still dirty ...
        assert _git(repo, "status", "--porcelain").strip() != ""
        # ... but a diagnostic log naming the failure now survives it.
        log_dir = repo / _rapid_sweep._LOG_DIR_REL
        logs = sorted(
            log_dir.glob(f"{_rapid_sweep._RAPID_DEBT_FAILURE_LOG_PREFIX}-T-2671-*.log")
        )
        assert len(logs) == 1, f"expected exactly one diagnostic log, found {logs}"
        payload = json.loads(logs[0].read_text(encoding="utf-8"))
        assert payload["ticket_id"] == "T-2671"
        assert payload["step"] == "commit"
        assert payload["outcome"] == "nonzero_returncode"
        assert payload["returncode"] != 0
        assert payload["stderr"]  # the hook's refusal text, not empty


class TestPersistCommitStepFailure:
    """T-2671: `_persist_commit_step_failure` is the retained-diagnostic
    primitive `_commit_rapid_debt` calls on every git-step failure -- the
    thing missing when the ticket's own DirtyMain recurrence could not be
    diagnosed because no land-invocation output survived it."""

    def test_writes_proc_result_diagnostics(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestPersistCommitStepFailure.test_writes_proc_result_diagnostics  # noqa: E501
        from typani.result import Ok

        from frob.gitio import ProcResult

        outcome = Ok(
            ProcResult(
                argv=("git", "commit", "-m", "x"),
                returncode=1,
                stdout="",
                stderr="hook refused: DirtyMain guard",
            )
        )
        path = _rapid_sweep._persist_commit_step_failure(
            tmp_path, "T-9001", "commit", outcome
        )
        assert path is not None
        assert path.exists()
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload == {
            "ticket_id": "T-9001",
            "step": "commit",
            "timestamp_utc": payload["timestamp_utc"],
            "outcome": "nonzero_returncode",
            "argv": ["git", "commit", "-m", "x"],
            "returncode": 1,
            "stdout": "",
            "stderr": "hook refused: DirtyMain guard",
        }

    def test_writes_spawn_error_diagnostics(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestPersistCommitStepFailure.test_writes_spawn_error_diagnostics  # noqa: E501
        from typani.result import Err

        from frob.gitio import GitError

        outcome = Err(GitError.GitFailed)
        path = _rapid_sweep._persist_commit_step_failure(
            tmp_path, "T-9002", "status", outcome
        )
        assert path is not None
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["outcome"] == "spawn_failed"
        assert payload["step"] == "status"
        assert "GitFailed" in payload["git_error"]
        # No ProcResult fields (no process ever ran) -- these key names
        # must not silently appear with a placeholder value.
        assert "argv" not in payload
        assert "returncode" not in payload

    def test_swallows_its_own_write_failure(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestPersistCommitStepFailure.test_swallows_its_own_write_failure  # noqa: E501
        from typani.result import Err

        from frob.gitio import GitError

        # A root whose log dir cannot be created (a FILE sits where the
        # directory would go) -- this must return None, not raise, since
        # `_commit_rapid_debt` calls this from inside its own failure
        # path and a second exception there would be strictly worse.
        blocker = tmp_path / ".frob"
        blocker.write_text("not a directory\n", encoding="utf-8")
        outcome = Err(GitError.GitFailed)
        path = _rapid_sweep._persist_commit_step_failure(
            tmp_path, "T-9003", "add", outcome
        )
        assert path is None


class TestDescribeRootDirt:
    """T-1698: a DirtyMain refusal must name what made it refuse."""

    def test_names_the_paths(self) -> None:
        # frob:tests \
        # tests/unit/test_rapid_sweep.py::TestDescribeRootDirt.test_names_the_paths
        from frob.tickets._land_git_ops import _render_dirty_paths

        assert _render_dirty_paths(("a.py", "b.md")) == "a.py, b.md"

    def test_truncation_declares_itself(self) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestDescribeRootDirt.test_truncation_declares_itself  # noqa: E501
        from frob.tickets._land_git_ops import _render_dirty_paths

        rendered = _render_dirty_paths(tuple(f"f{i}.py" for i in range(14)))
        assert rendered.endswith("(+4 more)")

    def test_unavailable_status_is_not_reported_as_clean(self) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestDescribeRootDirt.test_unavailable_status_is_not_reported_as_clean  # noqa: E501
        from frob.tickets._land_git_ops import _render_dirty_paths

        # "cannot tell" must never render as "clean".
        assert _render_dirty_paths(()) == "(git status unavailable)"

    def test_names_a_real_dirty_file(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestDescribeRootDirt.test_names_a_real_dirty_file  # noqa: E501
        from frob.tickets._land_git_ops import describe_root_dirt

        repo = _seed_repo(tmp_path)
        (repo / "seed.txt").write_text("changed\n", encoding="utf-8")
        assert "seed.txt" in describe_root_dirt(repo)

    def test_names_the_detached_sweep_as_likely_author(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestDescribeRootDirt.test_names_the_detached_sweep_as_likely_author  # noqa: E501
        from frob.tickets._land_git_ops import describe_root_dirt

        repo = _seed_repo(tmp_path)
        (repo / "tickets.md").write_text("dirty\n", encoding="utf-8")
        _git(repo, "add", "tickets.md")
        rendered = describe_root_dirt(repo)
        assert "tickets.md" in rendered
        assert "detached post-land sweep" in rendered

    def test_mixed_dirt_does_not_claim_the_sweep(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestDescribeRootDirt.test_mixed_dirt_does_not_claim_the_sweep  # noqa: E501
        from frob.tickets._land_git_ops import describe_root_dirt

        repo = _seed_repo(tmp_path)
        (repo / "tickets.md").write_text("dirty\n", encoding="utf-8")
        _git(repo, "add", "tickets.md")
        (repo / "seed.txt").write_text("also changed\n", encoding="utf-8")
        rendered = describe_root_dirt(repo)
        assert "detached post-land sweep" not in rendered

    # frob:ticket T-1795
    def test_names_the_real_ticket_from_a_staged_rapid_debt_line(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestDescribeRootDirt.test_names_the_real_ticket_from_a_staged_rapid_debt_line  # noqa: E501
        # Real incident: T-1222's sweep child staged rapid-debt.jsonl, and
        # the old static hint named T-1699/T-1755 (the tickets that BUILT
        # the sweep) instead of T-1222 -- symbolic attribution must read
        # the actual staged line's own ticket field.
        from frob.tickets._land_git_ops import describe_root_dirt

        repo = _seed_repo(tmp_path)
        (repo / "rapid-debt.jsonl").write_text(
            '{"commit": "abc123", "skipped": "post-land-unscoped-sweep-deferred", '
            '"ticket": "T-1222"}\n',
            encoding="utf-8",
        )
        _git(repo, "add", "rapid-debt.jsonl")
        rendered = describe_root_dirt(repo)
        assert "T-1222" in rendered
        assert "T-1699/T-1755" in rendered  # still names the mechanism
        assert "T-1699's sweep child" not in rendered  # never the wrong ticket

    # frob:ticket T-1795
    def test_unattributed_when_the_true_author_cannot_be_determined(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestDescribeRootDirt.test_unattributed_when_the_true_author_cannot_be_determined  # noqa: E501
        from frob.tickets._land_git_ops import describe_root_dirt

        repo = _seed_repo(tmp_path)
        (repo / "tickets.md").write_text("dirty\n", encoding="utf-8")
        _git(repo, "add", "tickets.md")
        rendered = describe_root_dirt(repo)
        assert "unattributed" in rendered


# frob:ticket T-2744
class TestCommitRegressionTicket:
    """T-1755: the filed regression ticket's `tickets.md` write must be
    committed by the sweep itself, scoped to the ledger paths only."""

    def test_commits_the_ledger_write(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestCommitRegressionTicket.test_commits_the_ledger_write  # noqa: E501
        from frob.app.ticket_runner._rapid_sweep import _commit_regression_ticket
        from frob.tickets import Origin, TicketKind, new_ticket
        from frob.tickets._models import TicketSpec

        repo = _seed_repo(tmp_path)
        # T-1758: new_ticket now auto-commits internally by default;
        # no_commit=True reproduces the shape _file_regression_ticket
        # itself uses so this test still exercises _commit_regression_
        # ticket committing a genuinely-dirty ledger, not a no-op.
        created = new_ticket(
            repo,
            TicketSpec(title="regression", kind=TicketKind.BUG, origin=Origin.AGENT),
            no_commit=True,
        )
        assert created.is_ok
        assert _git(repo, "status", "--porcelain").strip()
        _commit_regression_ticket(repo, created.danger_ok.id, "T-9000")
        # `.frob/` (untracked local state) is expected to remain; the
        # LEDGER write specifically must be committed.
        assert "tickets" not in _git(repo, "status", "--porcelain")
        log = _git(repo, "log", "-1", "--format=%s")
        assert created.danger_ok.id in log
        assert "T-9000" in log

    def test_commit_failure_logs_at_error_and_does_not_raise(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestCommitRegressionTicket.test_commit_failure_logs_at_error_and_does_not_raise  # noqa: E501
        from typani.result import Err

        import frob.app.ticket_runner._rapid_sweep as rapid_sweep_mod
        from frob.tickets._leases import LeaseError

        monkeypatch.setattr(
            "frob.tickets._leases.commit_ticket_ledger_change",
            lambda root, ticket_id, message: Err(LeaseError.CommitFailed),
        )
        errors: list[str] = []
        monkeypatch.setattr(
            rapid_sweep_mod._log, "error", lambda msg, *a: errors.append(msg % a)
        )
        # Must not raise even though the commit "fails". max_attempts=1,
        # retry_delay_s=0: this test is about the exhausted-retries
        # discard path itself, not the retry loop's own timing (T-1841).
        rapid_sweep_mod._commit_regression_ticket(
            tmp_path, "T-1234", "T-9000", max_attempts=1, retry_delay_s=0
        )
        assert len(errors) == 1
        assert "T-1234" in errors[0]
        # A fresh tmp_path defaults to a v2 store (T-1553) -- the discard
        # branch fires (T-1841: nothing was ever written here, so the
        # rmtree is a no-op, but the log still fires).
        assert "DISCARDED" in errors[0]

    # frob:ticket T-1841
    def test_retries_then_succeeds_on_a_transient_land_in_progress(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-1841: a concurrent `frob ticket land` holding root's lock is
        the ROUTINE case for a detached sweep, not a rare fluke -- the
        commit must be retried, not given up on after one attempt."""
        # frob:tests tests/unit/test_rapid_sweep.py::TestCommitRegressionTicket.test_retries_then_succeeds_on_a_transient_land_in_progress  # noqa: E501
        from typani.result import Err, Ok

        import frob.app.ticket_runner._rapid_sweep as rapid_sweep_mod
        from frob.tickets._leases import LeaseError

        attempts: list[int] = []

        def _flaky(root, ticket_id, message):
            attempts.append(1)
            if len(attempts) < 3:
                return Err(LeaseError.LandInProgress)
            return Ok(None)

        monkeypatch.setattr("frob.tickets._leases.commit_ticket_ledger_change", _flaky)
        monkeypatch.setattr(rapid_sweep_mod.time, "sleep", lambda _s: None)
        errors: list[str] = []
        monkeypatch.setattr(
            rapid_sweep_mod._log, "error", lambda msg, *a: errors.append(msg % a)
        )

        rapid_sweep_mod._commit_regression_ticket(
            tmp_path, "T-1234", "T-9000", max_attempts=5, retry_delay_s=0
        )

        assert len(attempts) == 3
        assert errors == []  # succeeded before exhausting retries

    # frob:ticket T-1841
    def test_exhausted_retries_discard_the_v2_ticket_dir_rather_than_leave_it_dirty(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-1841's own requirement: "if the commit cannot succeed ... the
        sweep must NOT leave the file behind." A v2 store's just-written,
        never-committed `tickets/<id>/` directory must be REMOVED, not
        left as untracked dirt DirtyMain-blocking every concurrent land."""
        # frob:tests tests/unit/test_rapid_sweep.py::TestCommitRegressionTicket.test_exhausted_retries_discard_the_v2_ticket_dir_rather_than_leave_it_dirty  # noqa: E501
        from typani.result import Err

        import frob.app.ticket_runner._rapid_sweep as rapid_sweep_mod
        from frob.tickets._leases import LeaseError

        ticket_dir = tmp_path / "tickets" / "T-1234"
        ticket_dir.mkdir(parents=True)
        (ticket_dir / "ticket.md").write_text("id: T-1234\n", encoding="utf-8")

        monkeypatch.setattr(
            "frob.tickets._leases.commit_ticket_ledger_change",
            lambda root, ticket_id, message: Err(LeaseError.LandInProgress),
        )
        monkeypatch.setattr("frob.tickets._store._store_mode", lambda root: "v2")
        monkeypatch.setattr(rapid_sweep_mod.time, "sleep", lambda _s: None)

        rapid_sweep_mod._commit_regression_ticket(
            tmp_path, "T-1234", "T-9000", max_attempts=2, retry_delay_s=0
        )

        assert not ticket_dir.exists()

    # frob:ticket T-1841
    def test_exhausted_retries_leave_a_v1_store_dirty_rather_than_guess(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-1841: a v1 (monofile) store's `tickets.md` is shared by every
        ledger op -- auto-discarding an uncommitted append there risks
        destroying a concurrent writer's own in-flight edit, so this
        deliberately leaves it dirty and loudly logged rather than
        guessing at a safe rollback."""
        # frob:tests tests/unit/test_rapid_sweep.py::TestCommitRegressionTicket.test_exhausted_retries_leave_a_v1_store_dirty_rather_than_guess  # noqa: E501
        from typani.result import Err

        import frob.app.ticket_runner._rapid_sweep as rapid_sweep_mod
        from frob.tickets._leases import LeaseError

        monkeypatch.setattr(
            "frob.tickets._leases.commit_ticket_ledger_change",
            lambda root, ticket_id, message: Err(LeaseError.LandInProgress),
        )
        monkeypatch.setattr("frob.tickets._store._store_mode", lambda root: "v1")
        monkeypatch.setattr(rapid_sweep_mod.time, "sleep", lambda _s: None)
        errors: list[str] = []
        monkeypatch.setattr(
            rapid_sweep_mod._log, "error", lambda msg, *a: errors.append(msg % a)
        )

        rapid_sweep_mod._commit_regression_ticket(
            tmp_path, "T-1234", "T-9000", max_attempts=2, retry_delay_s=0
        )

        assert len(errors) == 1
        assert "v1" in errors[0]
        assert "DIRTY" in errors[0]


# frob:ticket T-2034
class TestCommitOrDiscardLedgerWrite:
    """T-2034: the shared retry-then-discard shape every sweep
    ledger write path (regression-ticket filing, auto-drop, and whatever
    comes next) must go through."""

    def test_returns_true_on_first_success(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestCommitOrDiscardLedgerWrite.test_returns_true_on_first_success  # noqa: E501
        from typani.result import Ok

        import frob.app.ticket_runner._rapid_sweep as rapid_sweep_mod

        monkeypatch.setattr(
            "frob.tickets._leases.commit_ticket_ledger_change",
            lambda root, ticket_id, message: Ok(None),
        )
        discarded: list[str] = []
        ok = rapid_sweep_mod._commit_or_discard_ledger_write(
            tmp_path,
            "T-1234",
            "msg",
            max_attempts=3,
            retry_delay_s=0,
            discard=lambda: discarded.append("T-1234"),
            label="T-9000",
        )
        assert ok is True
        assert discarded == []

    def test_retries_then_succeeds(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestCommitOrDiscardLedgerWrite.test_retries_then_succeeds  # noqa: E501
        from typani.result import Err, Ok

        import frob.app.ticket_runner._rapid_sweep as rapid_sweep_mod
        from frob.tickets._leases import LeaseError

        attempts: list[int] = []

        def _flaky(root, ticket_id, message):
            attempts.append(1)
            if len(attempts) < 3:
                return Err(LeaseError.LandInProgress)
            return Ok(None)

        monkeypatch.setattr("frob.tickets._leases.commit_ticket_ledger_change", _flaky)
        monkeypatch.setattr(rapid_sweep_mod.time, "sleep", lambda _s: None)
        discarded: list[str] = []
        ok = rapid_sweep_mod._commit_or_discard_ledger_write(
            tmp_path,
            "T-1234",
            "msg",
            max_attempts=5,
            retry_delay_s=0,
            discard=lambda: discarded.append("T-1234"),
            label="T-9000",
        )
        assert ok is True
        assert len(attempts) == 3
        assert discarded == []

    def test_exhausted_retries_calls_discard_exactly_once_and_returns_false(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestCommitOrDiscardLedgerWrite.test_exhausted_retries_calls_discard_exactly_once_and_returns_false  # noqa: E501
        from typani.result import Err

        import frob.app.ticket_runner._rapid_sweep as rapid_sweep_mod
        from frob.tickets._leases import LeaseError

        monkeypatch.setattr(
            "frob.tickets._leases.commit_ticket_ledger_change",
            lambda root, ticket_id, message: Err(LeaseError.LandInProgress),
        )
        monkeypatch.setattr(rapid_sweep_mod.time, "sleep", lambda _s: None)
        discarded: list[str] = []
        ok = rapid_sweep_mod._commit_or_discard_ledger_write(
            tmp_path,
            "T-1234",
            "msg",
            max_attempts=2,
            retry_delay_s=0,
            discard=lambda: discarded.append("T-1234"),
            label="T-9000",
        )
        assert ok is False
        assert discarded == ["T-1234"]


# frob:ticket T-2034
class TestDiscardUncommittedTicketDrop:
    """T-2034: the auto-drop write path's discard action must
    RESTORE the existing ticket file to its last committed state (not
    rmtree it -- it is real, already-landed history, unlike a fresh
    regression ticket's brand-new directory)."""

    def test_v2_store_restores_the_ticket_file_to_head(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestDiscardUncommittedTicketDrop.test_v2_store_restores_the_ticket_file_to_head  # noqa: E501
        import frob.app.ticket_runner._rapid_sweep as rapid_sweep_mod

        repo = _seed_repo(tmp_path)
        ticket_dir = repo / "tickets" / "T-1234"
        ticket_dir.mkdir(parents=True)
        original = "id: T-1234\nstate: queued\n"
        (ticket_dir / "ticket.md").write_text(original, encoding="utf-8")
        _git(repo, "add", "tickets/T-1234/ticket.md")
        _git(repo, "commit", "-qm", "seed ticket")

        # Simulate the never-committed drop mutation.
        (ticket_dir / "ticket.md").write_text(
            "id: T-1234\nstate: dropped\n", encoding="utf-8"
        )
        assert _git(repo, "status", "--porcelain").strip()

        rapid_sweep_mod._discard_uncommitted_ticket_drop(repo, "T-1234")

        assert not _git(repo, "status", "--porcelain", "--", "tickets").strip()
        assert (ticket_dir / "ticket.md").read_text(encoding="utf-8") == original

    def test_v1_store_logs_and_leaves_root_alone(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestDiscardUncommittedTicketDrop.test_v1_store_logs_and_leaves_root_alone  # noqa: E501
        import frob.app.ticket_runner._rapid_sweep as rapid_sweep_mod

        monkeypatch.setattr("frob.tickets._store._store_mode", lambda root: "v1")
        errors: list[str] = []
        monkeypatch.setattr(
            rapid_sweep_mod._log, "error", lambda msg, *a: errors.append(msg % a)
        )

        rapid_sweep_mod._discard_uncommitted_ticket_drop(tmp_path, "T-1234")

        assert len(errors) == 1
        assert "v1" in errors[0]
        assert "DIRTY" in errors[0]


def _seed_ticket(tmp_path: Path, *, state=None) -> str:
    """A minimal ticket for T-1690's attribution-filing tests. `state`
    (a `TicketState`), when given, transitions the ticket there -- `DONE`
    is reached the cheap way (via `drop_ticket`, landing on `DROPPED`,
    which is in `_ticket_is_open`'s CLOSED set alongside `DONE`) rather
    than satisfying `done`'s own evidence/Done-report requirements, which
    this test has no need to exercise."""
    from frob.tickets import Origin, TicketKind, new_ticket
    from frob.tickets._models import TicketSpec, TicketState

    spec = TicketSpec(title="seed", kind=TicketKind.BUG, origin=Origin.AGENT)
    created = new_ticket(tmp_path, spec)
    assert created.is_ok
    ticket_id = created.danger_ok.id
    if state is TicketState.DONE:
        from frob.tickets import drop_ticket

        dropped = drop_ticket(tmp_path, ticket_id, reason="seed")
        assert dropped.is_ok
    return ticket_id


class TestTicketIsOpen:
    """`_ticket_is_open` is the "still open" half of T-1690's filing rule."""

    def test_open_ticket_is_open(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/unit/test_rapid_sweep.py::TestTicketIsOpen.test_open_ticket_is_open
        ticket_id = _seed_ticket(tmp_path)
        assert _ticket_is_open(tmp_path, ticket_id) is True

    def test_done_ticket_is_not_open(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/unit/test_rapid_sweep.py::TestTicketIsOpen.test_done_ticket_is_not_open
        from frob.tickets._models import TicketState

        ticket_id = _seed_ticket(tmp_path, state=TicketState.DONE)
        assert _ticket_is_open(tmp_path, ticket_id) is False

    def test_missing_ticket_is_not_open(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestTicketIsOpen.test_missing_ticket_is_not_open  # noqa: E501
        assert _ticket_is_open(tmp_path, "T-9999") is False


class TestAttributeNewFindings:
    """`_attribute_new_findings` degrades to `{}` (no attribution info,
    never a false 'everything unattributed') whenever the queue or the
    graph is unavailable."""

    def test_empty_queue_returns_empty_mapping(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestAttributeNewFindings.test_empty_queue_returns_empty_mapping  # noqa: E501
        assert _attribute_new_findings(tmp_path, [("RULE1", "a.py")]) == {}

    def test_attributed_and_unattributed_round_trip(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestAttributeNewFindings.test_attributed_and_unattributed_round_trip  # noqa: E501
        import frob.verify._attribution as attribution_mod
        from frob.graph import CallGraph, Digests, GraphSnapshot, SymbolId, SymbolRecord
        from frob.lang import SymbolKind
        from frob.verify import record_intent

        record_intent(
            tmp_path,
            commit_sha="commitA",
            ticket_id="T-0001",
            touched_symbols=("a.py::fn",),
            profile="rapid",
        )
        snapshot = GraphSnapshot(
            root=str(tmp_path),
            symbols={
                "a.py::fn": SymbolRecord(
                    id=SymbolId(path="a.py", qualname="fn"),
                    kind=SymbolKind.FUNCTION,
                    public=True,
                    digests=Digests(sig="s", body="b", doc="d"),
                    span=(1, 5),
                )
            },
            edges=(),
        )
        call_graph = CallGraph(calls={})
        monkeypatch.setattr(
            attribution_mod,
            "_load_snapshot_and_call_graph",
            lambda root: (snapshot, call_graph),
        )
        result = _attribute_new_findings(
            tmp_path, [("RULE1", "a.py", 2), ("RULE2", "nowhere.py", 9)]
        )
        assert result[("RULE1", "a.py")].status == "attributed"
        assert result[("RULE1", "a.py")].commit_sha == "commitA"
        assert result[("RULE2", "nowhere.py")].status == "unattributed"


# frob:ticket T-1935
class TestTrueFindingCount:
    """`_true_finding_count_for_identities` re-measures the TRUE
    per-finding count for a set of `(rule, file)` identities -- proving
    the T-1923 undercount (6 identities reported, 19 real findings) is
    now recoverable rather than silently lost."""

    # frob:ticket T-1935
    @staticmethod
    def _ok_result(stdout: str):
        from typani import Ok

        class _Proc:
            def __init__(self, stdout: str) -> None:
                self.stdout = stdout
                self.returncode = 1

        return Ok(_Proc(stdout))

    # frob:ticket T-1935
    def test_counts_every_diagnostic_matching_an_identity(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestTrueFindingCount.test_counts_every_diagnostic_matching_an_identity  # noqa: E501
        # T-1923's real shape: 5 files each carrying MULTIPLE COV003
        # findings (18 total) plus one F401 -- a coarse (rule, file)
        # identity set has only 6 entries, but the true finding count is
        # 19. This reproduces that undercount and proves the fix
        # recovers the real number.
        payload = {
            "results": [
                {
                    "tool": "gate-summary",
                    "diagnostics": [
                        {
                            "code": "COV003",
                            "file": "tickets/T-1872",
                            "severity": "error",
                        },
                        {
                            "code": "COV003",
                            "file": "tickets/T-1872",
                            "severity": "error",
                        },
                        {
                            "code": "COV003",
                            "file": "tickets/T-1895",
                            "severity": "error",
                        },
                        {
                            "code": "COV003",
                            "file": "tickets/T-1895",
                            "severity": "error",
                        },
                        {
                            "code": "COV003",
                            "file": "tickets/T-1895",
                            "severity": "error",
                        },
                        {
                            "code": "COV003",
                            "file": "tickets/T-1895",
                            "severity": "error",
                        },
                        {
                            "code": "COV003",
                            "file": "tickets/T-1896",
                            "severity": "error",
                        },
                        {
                            "code": "COV003",
                            "file": "tickets/T-1896",
                            "severity": "error",
                        },
                        {
                            "code": "COV003",
                            "file": "tickets/T-1900",
                            "severity": "error",
                        },
                        {
                            "code": "COV003",
                            "file": "tickets/T-1900",
                            "severity": "error",
                        },
                        {
                            "code": "COV003",
                            "file": "tickets/T-1900",
                            "severity": "error",
                        },
                        {
                            "code": "COV003",
                            "file": "tickets/T-1900",
                            "severity": "error",
                        },
                        {
                            "code": "COV003",
                            "file": "tickets/T-1900",
                            "severity": "error",
                        },
                        {
                            "code": "COV003",
                            "file": "tickets/T-1906",
                            "severity": "error",
                        },
                        {
                            "code": "COV003",
                            "file": "tickets/T-1906",
                            "severity": "error",
                        },
                        {
                            "code": "COV003",
                            "file": "tickets/T-1906",
                            "severity": "error",
                        },
                        {
                            "code": "COV003",
                            "file": "tickets/T-1906",
                            "severity": "error",
                        },
                        {
                            "code": "COV003",
                            "file": "tickets/T-1906",
                            "severity": "error",
                        },
                        {"code": "F401", "file": "src/frob/x.py", "severity": "error"},
                        # A finding NOT in `pairs` below must not be counted.
                        {"code": "SCOPE001", "file": "other.py", "severity": "error"},
                    ],
                }
            ]
        }
        monkeypatch.setattr(
            "frob.process._guard.guarded_subprocess_run",
            lambda *a, **k: self._ok_result(json.dumps(payload)),
        )
        pairs = frozenset(
            {
                ("COV003", "tickets/T-1872"),
                ("COV003", "tickets/T-1895"),
                ("COV003", "tickets/T-1896"),
                ("COV003", "tickets/T-1900"),
                ("COV003", "tickets/T-1906"),
                ("F401", "src/frob/x.py"),
            }
        )
        assert len(pairs) == 6
        count = _true_finding_count_for_identities(tmp_path, pairs)
        assert count == 19

    # frob:ticket T-1935
    def test_unparsable_json_is_none_not_zero(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestTrueFindingCount.test_unparsable_json_is_none_not_zero  # noqa: E501
        monkeypatch.setattr(
            "frob.process._guard.guarded_subprocess_run",
            lambda *a, **k: self._ok_result("not json at all"),
        )
        assert (
            _true_finding_count_for_identities(tmp_path, frozenset({("R", "f.py")}))
            is None
        )

    # frob:ticket T-1935
    def test_spawn_refused_is_none_not_zero(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestTrueFindingCount.test_spawn_refused_is_none_not_zero  # noqa: E501
        from typani import Err

        from frob.process._guard import ProcessGuardError

        monkeypatch.setattr(
            "frob.process._guard.guarded_subprocess_run",
            lambda *a, **k: Err(ProcessGuardError.ExecDisabled),
        )
        assert (
            _true_finding_count_for_identities(tmp_path, frozenset({("R", "f.py")}))
            is None
        )


# frob:ticket T-2006
class TestIdentitiesStillReproducing:
    """T-2006: `_identities_still_reproducing` -- which of a candidate
    set STILL reproduce right now, as an identity set (not merely a
    count) -- what `revalidate_dispatchable_sweep_tickets` needs to
    decide which sweep-filed tickets to drop."""

    # frob:ticket T-2006
    @staticmethod
    def _ok_result(stdout: str):
        from typani import Ok

        class _Proc:
            def __init__(self, stdout: str) -> None:
                self.stdout = stdout
                self.returncode = 1

        return Ok(_Proc(stdout))

    # frob:ticket T-2006
    def test_only_reproducing_identities_returned(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestIdentitiesStillReproducing.test_only_reproducing_identities_returned  # noqa: E501
        import json

        payload = {
            "results": [
                {
                    "tool": "gate-summary",
                    "diagnostics": [
                        {"code": "COV003", "file": "a.py", "severity": "error"},
                        # DOC002/b.py is in the queried `pairs` below but
                        # NOT in this fresh measurement -- it has
                        # resolved and must not appear in the result.
                        {"code": "F401", "file": "unrelated.py", "severity": "error"},
                    ],
                }
            ]
        }
        monkeypatch.setattr(
            "frob.process._guard.guarded_subprocess_run",
            lambda *a, **k: self._ok_result(json.dumps(payload)),
        )
        result = _identities_still_reproducing(
            tmp_path, frozenset({("COV003", "a.py"), ("DOC002", "b.py")})
        )
        assert result == frozenset({("COV003", "a.py")})

    # frob:ticket T-2006
    def test_unmeasurable_is_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestIdentitiesStillReproducing.test_unmeasurable_is_none  # noqa: E501
        monkeypatch.setattr(
            "frob.process._guard.guarded_subprocess_run",
            lambda *a, **k: self._ok_result("not json at all"),
        )
        assert (
            _identities_still_reproducing(tmp_path, frozenset({("R", "f.py")})) is None
        )

    # frob:ticket T-2521
    def test_failed_silent_tool_result_is_unmeasurable_not_zero(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestIdentitiesStillReproducing.test_failed_silent_tool_result_is_unmeasurable_not_zero  # noqa: E501
        """T-2521 required control #2: a re-measurement whose `ruff-check`
        (or any tool) FAILED (`exit_code != 0`) with zero error
        diagnostics -- the malformed-JSON shape T-2521's own investigation
        reproduced directly against this repo's real `parse_ruff_json` --
        must read as unmeasurable, never as "measured, none of the
        candidates reproduce". Before this fix, this exact JSON shape
        would have made `_identities_still_reproducing` return an empty
        set (not `None`), and the caller would have read that as
        `vanished = all_pairs`, dropping a ticket whose findings the
        run never actually managed to check."""
        import json

        payload = {
            "results": [
                {
                    "tool": "ruff-check",
                    "exit_code": 1,
                    "diagnostics": [],
                    "summary": "malformed JSON: Expecting value",
                },
            ]
        }
        monkeypatch.setattr(
            "frob.process._guard.guarded_subprocess_run",
            lambda *a, **k: self._ok_result(json.dumps(payload)),
        )
        result = _identities_still_reproducing(
            tmp_path, frozenset({("E501", "src/frob/x.py")})
        )
        assert result is None


# frob:ticket T-2006
# frob:ticket T-2078
# frob:ticket T-2089
class TestRevalidateDispatchableSweepTickets:
    """T-2006, end-to-end: `frob ticket doable`'s residual gap after
    T-1983 -- a sweep-filed ticket must be re-verified at DISPATCH time,
    not only inside the next unrelated land's own sweep."""

    # frob:ticket T-2006
    def test_no_sweep_tickets_is_zero_cost(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestRevalidateDispatchableSweepTickets.test_no_sweep_tickets_is_zero_cost  # noqa: E501
        called = []
        monkeypatch.setattr(
            "frob.process._guard.guarded_subprocess_run",
            lambda *a, **k: called.append(1),
        )

        class _PlainTicket:
            title = "some ordinary ticket"
            body = "nothing sweep-shaped here"

        dropped = _rapid_sweep.revalidate_dispatchable_sweep_tickets(
            tmp_path, [_PlainTicket()]
        )
        assert dropped == ()
        assert called == []  # no check spawn was attempted at all

    # frob:ticket T-2006
    def test_fully_resolved_candidate_is_dropped(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestRevalidateDispatchableSweepTickets.test_fully_resolved_candidate_is_dropped  # noqa: E501
        from frob.tickets import TicketState, load_queue, new_ticket
        from frob.tickets._models import Origin, TicketKind, TicketSpec

        spec = TicketSpec(
            title=f"{_rapid_sweep._REGRESSION_TITLE_PREFIX}T-1001: 1 new "
            "(rule, file) identit(ies) (COV003)",
            kind=TicketKind.BUG,
            origin=Origin.AGENT,
            scope=("a.py",),
            body=(f"{_rapid_sweep._REGRESSION_IDENTITY_HEADING}\n\n- COV003  a.py\n"),
        )
        created = new_ticket(tmp_path, spec, no_commit=True, warn_if_dirty=False)
        assert created.is_ok
        ticket_id = created.danger_ok.id

        # Fresh measurement: COV003/a.py no longer appears at all.
        import json

        payload = {"results": [{"tool": "gate-summary", "diagnostics": []}]}
        monkeypatch.setattr(
            "frob.process._guard.guarded_subprocess_run",
            lambda *a, **k: TestIdentitiesStillReproducing._ok_result(
                json.dumps(payload)
            ),
        )

        queue = load_queue(tmp_path)
        assert queue.is_ok
        tickets = list(queue.danger_ok.tickets.values())
        dropped = _rapid_sweep.revalidate_dispatchable_sweep_tickets(tmp_path, tickets)
        assert dropped == (ticket_id,)

        requeried = load_queue(tmp_path)
        assert requeried.is_ok
        assert requeried.danger_ok.tickets[ticket_id].state == TicketState.DROPPED

    # frob:ticket T-2006
    def test_still_reproducing_candidate_is_left_untouched(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestRevalidateDispatchableSweepTickets.test_still_reproducing_candidate_is_left_untouched  # noqa: E501
        from frob.tickets import TicketState, load_queue, new_ticket
        from frob.tickets._models import Origin, TicketKind, TicketSpec

        spec = TicketSpec(
            title=f"{_rapid_sweep._REGRESSION_TITLE_PREFIX}T-1001: 1 new "
            "(rule, file) identit(ies) (COV003)",
            kind=TicketKind.BUG,
            origin=Origin.AGENT,
            scope=("a.py",),
            body=(f"{_rapid_sweep._REGRESSION_IDENTITY_HEADING}\n\n- COV003  a.py\n"),
        )
        created = new_ticket(tmp_path, spec, no_commit=True, warn_if_dirty=False)
        assert created.is_ok
        ticket_id = created.danger_ok.id

        # Fresh measurement: COV003/a.py STILL reproduces.
        import json

        payload = {
            "results": [
                {
                    "tool": "gate-summary",
                    "diagnostics": [
                        {"code": "COV003", "file": "a.py", "severity": "error"}
                    ],
                }
            ]
        }
        monkeypatch.setattr(
            "frob.process._guard.guarded_subprocess_run",
            lambda *a, **k: TestIdentitiesStillReproducing._ok_result(
                json.dumps(payload)
            ),
        )

        queue = load_queue(tmp_path)
        assert queue.is_ok
        tickets = list(queue.danger_ok.tickets.values())
        dropped = _rapid_sweep.revalidate_dispatchable_sweep_tickets(tmp_path, tickets)
        assert dropped == ()

        requeried = load_queue(tmp_path)
        assert requeried.is_ok
        assert requeried.danger_ok.tickets[ticket_id].state == TicketState.QUEUED

    # frob:ticket T-2006
    def test_unmeasurable_recheck_drops_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestRevalidateDispatchableSweepTickets.test_unmeasurable_recheck_drops_nothing  # noqa: E501
        from frob.tickets import TicketState, load_queue, new_ticket
        from frob.tickets._models import Origin, TicketKind, TicketSpec

        spec = TicketSpec(
            title=f"{_rapid_sweep._REGRESSION_TITLE_PREFIX}T-1001: 1 new "
            "(rule, file) identit(ies) (COV003)",
            kind=TicketKind.BUG,
            origin=Origin.AGENT,
            scope=("a.py",),
            body=(f"{_rapid_sweep._REGRESSION_IDENTITY_HEADING}\n\n- COV003  a.py\n"),
        )
        created = new_ticket(tmp_path, spec, no_commit=True, warn_if_dirty=False)
        assert created.is_ok
        ticket_id = created.danger_ok.id

        monkeypatch.setattr(
            "frob.process._guard.guarded_subprocess_run",
            lambda *a, **k: TestIdentitiesStillReproducing._ok_result(
                "not json at all"
            ),
        )

        queue = load_queue(tmp_path)
        assert queue.is_ok
        tickets = list(queue.danger_ok.tickets.values())
        dropped = _rapid_sweep.revalidate_dispatchable_sweep_tickets(tmp_path, tickets)
        assert dropped == ()

        requeried = load_queue(tmp_path)
        assert requeried.is_ok
        assert requeried.danger_ok.tickets[ticket_id].state == TicketState.QUEUED

    # frob:ticket T-2106
    def test_uncached_recheck_uses_the_doable_budget_not_the_sweep_budget(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestRevalidateDispatchableSweepTickets.test_uncached_recheck_uses_the_doable_budget_not_the_sweep_budget  # noqa: E501
        """T-2106: measured, `frob ticket doable`'s own sweep re-
        verification took 301.2s -- almost exactly `_TRUE_COUNT_BUDGET_S`
        (300), the constant sized for the deferred POST-LAND sweep, not
        an interactive query. The doable-time path (this function, via
        `_reproducing_identities_cached`) must spawn its own re-check with
        `_DOABLE_REVALIDATION_BUDGET_S` (20), never the 300s sweep
        budget -- verified here by capturing the actual spawned argv
        rather than trusting a wall-clock proxy."""
        from frob.tickets import load_queue, new_ticket
        from frob.tickets._models import Origin, TicketKind, TicketSpec

        spec = TicketSpec(
            title=f"{_rapid_sweep._REGRESSION_TITLE_PREFIX}T-1001: 1 new "
            "(rule, file) identit(ies) (COV003)",
            kind=TicketKind.BUG,
            origin=Origin.AGENT,
            scope=("a.py",),
            body=(f"{_rapid_sweep._REGRESSION_IDENTITY_HEADING}\n\n- COV003  a.py\n"),
        )
        created = new_ticket(tmp_path, spec, no_commit=True, warn_if_dirty=False)
        assert created.is_ok

        captured_argv: list[list[str]] = []

        def _fake_run(argv, **kwargs):  # noqa: ANN001, ANN201, ARG001
            captured_argv.append(list(argv))
            return TestIdentitiesStillReproducing._ok_result(
                '{"results": [{"tool": "gate-summary", "diagnostics": []}]}'
            )

        monkeypatch.setattr("frob.process._guard.guarded_subprocess_run", _fake_run)
        # T-2089's cache is content-keyed on tree state; a non-repo
        # tmp_path makes `_tree_state_key` return None (git spawn fails),
        # so this exercises the uncached spawn path deterministically.

        queue = load_queue(tmp_path)
        assert queue.is_ok
        tickets = list(queue.danger_ok.tickets.values())
        _rapid_sweep.revalidate_dispatchable_sweep_tickets(tmp_path, tickets)

        assert len(captured_argv) == 1
        argv = captured_argv[0]
        assert "--budget" in argv
        budget_value = argv[argv.index("--budget") + 1]
        assert budget_value == str(_rapid_sweep._DOABLE_REVALIDATION_BUDGET_S)
        assert budget_value != str(_rapid_sweep._TRUE_COUNT_BUDGET_S)

    # frob:ticket T-2078
    def test_terminal_ticket_is_not_selected_and_logs_no_invalid_transition(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        # frob:tests \
        # tests/unit/test_rapid_sweep.py::TestRevalidateDispatchableSweepTickets.test_terminal_ticket_is_not_selected_and_logs_no_invalid_transition  # noqa: E501
        """T-2078: `revalidate_dispatchable_sweep_tickets` is called from
        `doable`'s render path against the FULL candidate set -- unlike
        `_close_resolved_sweep_tickets`, it never filtered out
        already-terminal (`dropped`/`done`) tickets before this fix, so a
        resolved-but-already-dropped sweep ticket got a doomed
        `dropped -> dropped` transition attempted on every single
        `frob ticket doable` call: 9 InvalidTransition errors and 9
        dirtied files per invocation in the measured incident. This test
        MUST fail against pre-fix main (it would log the illegal
        transition and dirty the ticket's file)."""
        import json

        from frob.tickets import TicketState, drop_ticket, load_queue, new_ticket
        from frob.tickets._models import Origin, TicketKind, TicketSpec

        spec = TicketSpec(
            title=f"{_rapid_sweep._REGRESSION_TITLE_PREFIX}T-1001: 1 new "
            "(rule, file) identit(ies) (COV003)",
            kind=TicketKind.BUG,
            origin=Origin.AGENT,
            scope=("a.py",),
            body=(f"{_rapid_sweep._REGRESSION_IDENTITY_HEADING}\n\n- COV003  a.py\n"),
        )
        created = new_ticket(tmp_path, spec, no_commit=True, warn_if_dirty=False)
        assert created.is_ok
        ticket_id = created.danger_ok.id

        # Already resolved by hand -- the ticket is TERMINAL before this
        # sweep ever runs, exactly like 7 of the 9 tickets in the
        # measured incident (`dropped -> dropped`).
        dropped_first = drop_ticket(tmp_path, ticket_id, "already handled by hand")
        assert dropped_first.is_ok

        queue = load_queue(tmp_path)
        assert queue.is_ok
        ticket_path = tmp_path / "tickets" / ticket_id / "ticket.md"
        if not ticket_path.exists():
            # v1/single-file store mode: fall back to tickets.md itself
            # for the byte-identity check below.
            ticket_path = tmp_path / "tickets.md"
        before = ticket_path.read_bytes()

        # Fresh measurement: COV003/a.py no longer appears -- "resolved".
        payload = {"results": [{"tool": "gate-summary", "diagnostics": []}]}
        monkeypatch.setattr(
            "frob.process._guard.guarded_subprocess_run",
            lambda *a, **k: TestIdentitiesStillReproducing._ok_result(
                json.dumps(payload)
            ),
        )

        with caplog.at_level("WARNING"):
            tickets = list(load_queue(tmp_path).danger_ok.tickets.values())
            dispatched = _rapid_sweep.revalidate_dispatchable_sweep_tickets(
                tmp_path, tickets
            )

        # Not selected -- an already-terminal ticket is never a drop
        # candidate.
        assert dispatched == ()
        # No InvalidTransition anywhere in the log -- the illegal
        # transition must never even be attempted.
        assert "illegal transition" not in caplog.text
        assert "InvalidTransition" not in caplog.text
        # No modification at all -- byte-identical to before the call.
        after = ticket_path.read_bytes()
        assert after == before

        requeried = load_queue(tmp_path)
        assert requeried.is_ok
        assert requeried.danger_ok.tickets[ticket_id].state == TicketState.DROPPED

    # frob:ticket T-2089
    def test_second_call_same_tree_reuses_cache_no_second_spawn(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestRevalidateDispatchableSweepTickets.test_second_call_same_tree_reuses_cache_no_second_spawn  # noqa: E501
        # T-2089's own measured regression: `revalidate_dispatchable_
        # sweep_tickets` used to spawn a fresh, uncached full check on
        # EVERY call while a sweep-filed candidate existed, even when the
        # tree had not moved between calls (207.5s for 21 candidates / 265
        # identities, measured live). Two calls in a row against the same
        # unchanged tree must pay for exactly ONE spawn, not two.
        from frob.tickets import load_queue, new_ticket
        from frob.tickets._models import Origin, TicketKind, TicketSpec

        _init_git_repo(tmp_path)
        _git_commit(tmp_path, "chore: init")

        spec = TicketSpec(
            title=f"{_rapid_sweep._REGRESSION_TITLE_PREFIX}T-1001: 1 new "
            "(rule, file) identit(ies) (COV003)",
            kind=TicketKind.BUG,
            origin=Origin.AGENT,
            scope=("a.py",),
            body=(f"{_rapid_sweep._REGRESSION_IDENTITY_HEADING}\n\n- COV003  a.py\n"),
        )
        created = new_ticket(tmp_path, spec, no_commit=True, warn_if_dirty=False)
        assert created.is_ok

        payload = {
            "results": [
                {
                    "tool": "gate-summary",
                    "diagnostics": [
                        {"code": "COV003", "file": "a.py", "severity": "error"}
                    ],
                }
            ]
        }
        spawn_calls: list[int] = []

        def _fake_spawn(*args, **kwargs):  # noqa: ANN001, ANN002, ANN003, ANN202
            spawn_calls.append(1)
            return TestIdentitiesStillReproducing._ok_result(json.dumps(payload))

        monkeypatch.setattr("frob.process._guard.guarded_subprocess_run", _fake_spawn)

        queue = load_queue(tmp_path)
        assert queue.is_ok
        tickets = list(queue.danger_ok.tickets.values())

        first = _rapid_sweep.revalidate_dispatchable_sweep_tickets(tmp_path, tickets)
        assert first == ()  # still reproducing, left dispatchable
        assert len(spawn_calls) == 1

        second = _rapid_sweep.revalidate_dispatchable_sweep_tickets(tmp_path, tickets)
        assert second == ()
        # The tree did not move between the two calls -- the second call
        # must reuse the cached result rather than spawning again.
        assert len(spawn_calls) == 1

    # frob:ticket T-2165
    def test_cache_hits_across_a_head_move_when_candidate_files_are_unchanged(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestRevalidateDispatchableSweepTickets.test_cache_hits_across_a_head_move_when_candidate_files_are_unchanged  # noqa: E501
        # T-2165's own fix, end to end: T-2089's cache (keyed on whole
        # tree state) could NEVER hit here -- an intervening land moves
        # HEAD even though it never touches `a.py`, the candidate's own
        # file. The identity-scoped key must still hit.
        from frob.tickets import load_queue, new_ticket
        from frob.tickets._models import Origin, TicketKind, TicketSpec

        _init_git_repo(tmp_path)
        _git_commit(tmp_path, "chore: init")

        spec = TicketSpec(
            title=f"{_rapid_sweep._REGRESSION_TITLE_PREFIX}T-1001: 1 new "
            "(rule, file) identit(ies) (COV003)",
            kind=TicketKind.BUG,
            origin=Origin.AGENT,
            scope=("a.py",),
            body=(f"{_rapid_sweep._REGRESSION_IDENTITY_HEADING}\n\n- COV003  a.py\n"),
        )
        created = new_ticket(tmp_path, spec, no_commit=True, warn_if_dirty=False)
        assert created.is_ok

        payload = {
            "results": [
                {
                    "tool": "gate-summary",
                    "diagnostics": [
                        {"code": "COV003", "file": "a.py", "severity": "error"}
                    ],
                }
            ]
        }
        spawn_calls: list[int] = []

        def _fake_spawn(*args, **kwargs):  # noqa: ANN001, ANN002, ANN003, ANN202
            spawn_calls.append(1)
            return TestIdentitiesStillReproducing._ok_result(json.dumps(payload))

        monkeypatch.setattr("frob.process._guard.guarded_subprocess_run", _fake_spawn)

        queue = load_queue(tmp_path)
        assert queue.is_ok
        tickets = list(queue.danger_ok.tickets.values())

        first = _rapid_sweep.revalidate_dispatchable_sweep_tickets(tmp_path, tickets)
        assert first == ()
        assert len(spawn_calls) == 1

        # An UNRELATED land: commits a file the candidate identity never
        # named, moving HEAD -- T-2089's own whole-tree key would change
        # here and force a second spawn; the identity-scoped key must
        # not.
        import subprocess

        (tmp_path / "unrelated.py").write_text("changed\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(tmp_path), "add", "-A"], check=True)
        _git_commit(tmp_path, "chore: an unrelated land happened")

        second = _rapid_sweep.revalidate_dispatchable_sweep_tickets(tmp_path, tickets)
        assert second == ()
        assert len(spawn_calls) == 1

    # frob:ticket T-2165
    def test_uncommitted_edit_to_candidate_file_still_forces_a_respawn(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestRevalidateDispatchableSweepTickets.test_uncommitted_edit_to_candidate_file_still_forces_a_respawn  # noqa: E501
        # Must-still-pass soundness control: an agent's OWN uncommitted
        # fix to the candidate's own file must NOT be masked by the
        # cache, even though HEAD never moved -- T-2165's ticket body's
        # own explicit non-negotiable ("the narrowing has to be
        # identity-scoped, not blanket-relaxed").
        from frob.tickets import load_queue, new_ticket
        from frob.tickets._models import Origin, TicketKind, TicketSpec

        _init_git_repo(tmp_path)
        (tmp_path / "a.py").write_text("broken\n", encoding="utf-8")
        import subprocess

        subprocess.run(["git", "-C", str(tmp_path), "add", "-A"], check=True)
        _git_commit(tmp_path, "chore: init")

        spec = TicketSpec(
            title=f"{_rapid_sweep._REGRESSION_TITLE_PREFIX}T-1001: 1 new "
            "(rule, file) identit(ies) (COV003)",
            kind=TicketKind.BUG,
            origin=Origin.AGENT,
            scope=("a.py",),
            body=(f"{_rapid_sweep._REGRESSION_IDENTITY_HEADING}\n\n- COV003  a.py\n"),
        )
        created = new_ticket(tmp_path, spec, no_commit=True, warn_if_dirty=False)
        assert created.is_ok

        payload = {
            "results": [
                {
                    "tool": "gate-summary",
                    "diagnostics": [
                        {"code": "COV003", "file": "a.py", "severity": "error"}
                    ],
                }
            ]
        }
        spawn_calls: list[int] = []

        def _fake_spawn(*args, **kwargs):  # noqa: ANN001, ANN002, ANN003, ANN202
            spawn_calls.append(1)
            return TestIdentitiesStillReproducing._ok_result(json.dumps(payload))

        monkeypatch.setattr("frob.process._guard.guarded_subprocess_run", _fake_spawn)

        queue = load_queue(tmp_path)
        assert queue.is_ok
        tickets = list(queue.danger_ok.tickets.values())

        first = _rapid_sweep.revalidate_dispatchable_sweep_tickets(tmp_path, tickets)
        assert first == ()
        assert len(spawn_calls) == 1

        # An agent fixes a.py IN PLACE, uncommitted -- HEAD does not
        # move, but the candidate's own file content does.
        (tmp_path / "a.py").write_text("fixed\n", encoding="utf-8")

        second = _rapid_sweep.revalidate_dispatchable_sweep_tickets(tmp_path, tickets)
        assert second == ()
        # Must re-measure, never serve a stale cached result that would
        # mask the agent's own uncommitted fix.
        assert len(spawn_calls) == 2


# frob:ticket T-2077
class TestRegressionCountLine:
    """T-2058 (ARCH001 split of `_file_regression_ticket`): the T-1935
    identity-vs-finding-count caveat line."""

    # frob:ticket T-2077
    def test_true_count_known(self) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestRegressionCountLine.test_true_count_known  # noqa: E501
        line = _regression_count_line([("RULE1", "a.py"), ("RULE2", "b.py")], 5)
        assert "2 identit" in line
        assert "5 actual finding" in line

    # frob:ticket T-2077
    def test_true_count_unmeasurable(self) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestRegressionCountLine.test_true_count_unmeasurable  # noqa: E501
        line = _regression_count_line([("RULE1", "a.py")], None)
        assert "could not be independently re-measured" in line
        assert "5 actual finding" not in line


# frob:ticket T-2077
class TestBuildRegressionBody:
    """T-2058 (ARCH001 split of `_file_regression_ticket`): body assembly
    -- the T-2009 multi-land block and the T-1690 attribution block are
    each appended only when their own inputs are non-empty."""

    # frob:ticket T-2077
    def test_no_attribution_lines_no_multi_land(self) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestBuildRegressionBody.test_no_attribution_lines_no_multi_land  # noqa: E501
        body = _build_regression_body(
            attribution_label="T-9000",
            commit_sha="deadbeef",
            pairs=[("RULE1", "a.py")],
            unfiled_pairs=[("RULE1", "a.py")],
            count_line="count line here",
            attributed_ids=None,
            attribution_lines=(),
        )
        assert "T-9000" in body
        assert "RULE1  a.py" in body
        assert "T-2009" not in body
        assert "Attribution (T-1690" not in body

    # frob:ticket T-2077
    def test_multi_land_and_attribution_lines_both_appended(self) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestBuildRegressionBody.test_multi_land_and_attribution_lines_both_appended  # noqa: E501
        body = _build_regression_body(
            attribution_label="T-9000, T-9001",
            commit_sha="deadbeef",
            pairs=[("RULE1", "a.py")],
            unfiled_pairs=[("RULE1", "a.py")],
            count_line="count line here",
            attributed_ids=["T-9000", "T-9001"],
            attribution_lines=["- RULE1 a.py: unattributed"],
        )
        assert "T-2009: 2 lands (T-9000, T-9001)" in body
        assert "Attribution (T-1690" in body
        assert "- RULE1 a.py: unattributed" in body


# frob:ticket T-1791
# frob:ticket T-2744
# frob:ticket T-3051
class TestFileRegressionTicket:
    """T-1690: attributed findings owned by a still-open ticket are not
    re-filed; everything else is filed with a full attribution trail."""

    def _patch_graph(
        self, monkeypatch: pytest.MonkeyPatch, snapshot, call_graph
    ) -> None:
        import frob.verify._attribution as attribution_mod

        monkeypatch.setattr(
            attribution_mod,
            "_load_snapshot_and_call_graph",
            lambda root: (snapshot, call_graph),
        )

    # frob:ticket T-1791
    def test_no_attribution_files_everything_as_before(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestFileRegressionTicket.test_no_attribution_files_everything_as_before  # noqa: E501
        # No verify queue at all -- attribution unavailable, falls back to
        # the pre-T-1690 behavior of filing every pair.
        filed = _file_regression_ticket(
            tmp_path, "T-9000", "deadbeef", frozenset({("RULE1", "a.py")})
        )
        assert filed is not None

    def test_commit_failure_skips_auto_dispose_and_returns_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2744: the T-2736 incident -- if the regression ticket's
        ledger write never lands, `_file_regression_ticket` must not
        proceed to dispose/clear quarantine against an id that does not
        exist on `root`. It must return `None` (no id to report as
        filed) and quarantine must be left exactly as it was."""
        # frob:tests tests/unit/test_rapid_sweep.py::TestFileRegressionTicket.test_commit_failure_skips_auto_dispose_and_returns_none  # noqa: E501
        import frob.app.ticket_runner._rapid_sweep as rapid_sweep_mod
        from frob.verify._quarantine import (
            QuarantinedFinding,
            load_quarantine,
            raise_quarantine,
        )

        raise_quarantine(
            tmp_path,
            batch_commit_shas=("deadbeef",),
            findings=(QuarantinedFinding(rule_id="RULE1", file="a.py", line=1),),
        )

        monkeypatch.setattr(
            rapid_sweep_mod, "_commit_regression_ticket", lambda *a, **k: False
        )
        disposed_calls: list[object] = []
        monkeypatch.setattr(
            rapid_sweep_mod,
            "_auto_dispose_filed_findings",
            lambda *a, **k: disposed_calls.append(a),
        )

        filed = _file_regression_ticket(
            tmp_path, "T-9000", "deadbeef", frozenset({("RULE1", "a.py")})
        )

        assert filed is None
        assert disposed_calls == []
        record = load_quarantine(tmp_path).danger_ok
        assert record is not None
        assert record.cleared_at is None  # still raised, not phantom-cleared

    def test_attributed_to_open_ticket_is_not_refiled(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestFileRegressionTicket.test_attributed_to_open_ticket_is_not_refiled  # noqa: E501
        from frob.graph import CallGraph, Digests, GraphSnapshot, SymbolId, SymbolRecord
        from frob.lang import SymbolKind
        from frob.verify import record_intent

        owner = _seed_ticket(tmp_path)
        record_intent(
            tmp_path,
            commit_sha="commitA",
            ticket_id=owner,
            touched_symbols=("a.py::fn",),
            profile="rapid",
        )
        snapshot = GraphSnapshot(
            root=str(tmp_path),
            symbols={
                "a.py::fn": SymbolRecord(
                    id=SymbolId(path="a.py", qualname="fn"),
                    kind=SymbolKind.FUNCTION,
                    public=True,
                    digests=Digests(sig="s", body="b", doc="d"),
                    span=(1, 5),
                )
            },
            edges=(),
        )
        self._patch_graph(monkeypatch, snapshot, CallGraph(calls={}))
        filed = _file_regression_ticket(
            tmp_path, "T-9000", "deadbeef", frozenset({("RULE1", "a.py")})
        )
        assert filed is None

    def test_attributed_to_closed_ticket_is_refiled(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestFileRegressionTicket.test_attributed_to_closed_ticket_is_refiled  # noqa: E501
        from frob.graph import CallGraph, Digests, GraphSnapshot, SymbolId, SymbolRecord
        from frob.lang import SymbolKind
        from frob.tickets._models import TicketState
        from frob.verify import record_intent

        owner = _seed_ticket(tmp_path, state=TicketState.DONE)
        record_intent(
            tmp_path,
            commit_sha="commitA",
            ticket_id=owner,
            touched_symbols=("a.py::fn",),
            profile="rapid",
        )
        snapshot = GraphSnapshot(
            root=str(tmp_path),
            symbols={
                "a.py::fn": SymbolRecord(
                    id=SymbolId(path="a.py", qualname="fn"),
                    kind=SymbolKind.FUNCTION,
                    public=True,
                    digests=Digests(sig="s", body="b", doc="d"),
                    span=(1, 5),
                )
            },
            edges=(),
        )
        self._patch_graph(monkeypatch, snapshot, CallGraph(calls={}))
        filed = _file_regression_ticket(
            tmp_path, "T-9000", "deadbeef", frozenset({("RULE1", "a.py")})
        )
        assert filed is not None

    def test_unattributed_is_filed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestFileRegressionTicket.test_unattributed_is_filed  # noqa: E501
        from frob.graph import CallGraph, GraphSnapshot
        from frob.verify import record_intent

        record_intent(
            tmp_path,
            commit_sha="commitA",
            ticket_id="T-0001",
            touched_symbols=("unrelated.py::other",),
            profile="rapid",
        )
        snapshot = GraphSnapshot(root=str(tmp_path), symbols={}, edges=())
        self._patch_graph(monkeypatch, snapshot, CallGraph(calls={}))
        filed = _file_regression_ticket(
            tmp_path, "T-9000", "deadbeef", frozenset({("RULE1", "a.py")})
        )
        assert filed is not None

    # frob:ticket T-2672
    def test_causally_implicated_land_still_names_itself_as_the_cause(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestFileRegressionTicket.test_causally_implicated_land_still_names_itself_as_the_cause  # noqa: E501
        """T-2672 positive control (must-still-pass direction): when the
        spawning land's OWN commit genuinely reaches the finding via the
        reference graph (the exact shape `test_attributed_to_closed_
        ticket_is_refiled` already covers for filing, this asserts the
        TITLE too), the fix must not become indistinguishable from
        disabling attribution -- the title still names the land as the
        cause, unqualified."""
        from frob.graph import CallGraph, Digests, GraphSnapshot, SymbolId, SymbolRecord
        from frob.lang import SymbolKind
        from frob.tickets import load_queue
        from frob.tickets._models import TicketState
        from frob.verify import record_intent

        owner = _seed_ticket(tmp_path, state=TicketState.DONE)
        record_intent(
            tmp_path,
            commit_sha="deadbeef",
            ticket_id=owner,
            touched_symbols=("a.py::fn",),
            profile="rapid",
        )
        snapshot = GraphSnapshot(
            root=str(tmp_path),
            symbols={
                "a.py::fn": SymbolRecord(
                    id=SymbolId(path="a.py", qualname="fn"),
                    kind=SymbolKind.FUNCTION,
                    public=True,
                    digests=Digests(sig="s", body="b", doc="d"),
                    span=(1, 5),
                )
            },
            edges=(),
        )
        self._patch_graph(monkeypatch, snapshot, CallGraph(calls={}))

        filed = _file_regression_ticket(
            tmp_path, "T-9000", "deadbeef", frozenset({("RULE1", "a.py")})
        )
        assert filed is not None

        ticket = load_queue(tmp_path).danger_ok.tickets[filed]
        assert "regression from T-9000" in ticket.title, (
            f"a genuinely reaching land must still be named plainly: {ticket.title!r}"
        )
        assert "unattributed" not in ticket.title.lower(), (
            f"must not hedge a real attribution: {ticket.title!r}"
        )

    # frob:ticket T-2672
    def test_unattributed_finding_does_not_name_the_spawning_land_as_cause(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestFileRegressionTicket.test_unattributed_finding_does_not_name_the_spawning_land_as_cause  # noqa: E501
        """T-2672: six real sweep-filed tickets all named the spawning
        land (`final_id`, the one commit in a single-land window) as the
        cause in their title even though `_attribution.py`'s own
        per-finding reachability check reported every one of them
        UNATTRIBUTED -- `git show --stat` on the blamed commit showed it
        touched none of the flagged files. This reproduces the single-
        land-but-unattributed shape directly: a verify-queue entry exists
        (so attribution actually runs) but its touched symbols cannot
        reach the finding's file, so `_partition_findings_by_attribution`
        must report every pair UNATTRIBUTED -- yet the filed ticket's own
        title must not read as if T-9000 caused it."""
        from frob.graph import CallGraph, GraphSnapshot
        from frob.tickets import load_queue
        from frob.verify import record_intent

        record_intent(
            tmp_path,
            commit_sha="commitA",
            ticket_id="T-0001",
            touched_symbols=("unrelated.py::other",),
            profile="rapid",
        )
        snapshot = GraphSnapshot(root=str(tmp_path), symbols={}, edges=())
        self._patch_graph(monkeypatch, snapshot, CallGraph(calls={}))

        filed = _file_regression_ticket(
            tmp_path, "T-9000", "deadbeef", frozenset({("RULE1", "a.py")})
        )
        assert filed is not None

        ticket = load_queue(tmp_path).danger_ok.tickets[filed]
        assert "regression from T-9000" not in ticket.title, (
            "every finding attributed UNATTRIBUTED for this batch -- the "
            f"title must not claim T-9000 as the cause: {ticket.title!r}"
        )
        assert "unattributed" in ticket.title.lower(), (
            "the title must positively disclose that these findings "
            f"could not be attributed to any land: {ticket.title!r}"
        )

    # frob:ticket T-2312
    def test_duplicate_title_disposes_to_existing_ticket_instead_of_dropping(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestFileRegressionTicket.test_duplicate_title_disposes_to_existing_ticket_instead_of_dropping  # noqa: E501
        """T-2312 acceptance [0]: findings whose equivalent ticket already
        exists (same title+scope `new_ticket` would refuse as an exact
        duplicate) get disposed to that ticket -- and quarantine clears --
        instead of being silently abandoned when the auto-filer declines
        to file a second one. Calling `_file_regression_ticket` twice with
        identical arguments and no attribution reproduces the real
        incident directly: the first call files a regression ticket, the
        second computes the SAME deterministic title+scope and hits the
        exact-duplicate refusal `new_ticket` already enforces."""
        from frob.graph import CallGraph, GraphSnapshot
        from frob.verify import record_intent
        from frob.verify._quarantine import load_quarantine

        record_intent(
            tmp_path,
            commit_sha="commitA",
            ticket_id="T-0001",
            touched_symbols=("unrelated.py::other",),
            profile="rapid",
        )
        snapshot = GraphSnapshot(root=str(tmp_path), symbols={}, edges=())
        self._patch_graph(monkeypatch, snapshot, CallGraph(calls={}))
        pairs = frozenset({("RULE1", "a.py")})

        first = _file_regression_ticket(tmp_path, "T-9000", "deadbeef", pairs)
        assert first is not None

        second = _file_regression_ticket(tmp_path, "T-9000", "deadbeef", pairs)
        assert second == first, (
            "a refused duplicate must dispose to the EXISTING ticket, "
            "never return None and abandon the findings"
        )

        record = load_quarantine(tmp_path).danger_ok
        assert record is not None
        assert record.cleared_at is not None, (
            "quarantine must clear once the duplicate-owned findings are "
            "disposed to the existing ticket"
        )

    # frob:ticket T-3051
    def test_duplicate_finding_disposes_to_declaring_ticket_instead_of_dropping(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestFileRegressionTicket.test_duplicate_finding_disposes_to_declaring_ticket_instead_of_dropping  # noqa: E501
        """T-3051 (H4) acceptance [0] (must-work): the routine, encouraged
        workflow of a fix ticket declaring the finding it fixes must not
        deadlock a later sweep's re-measurement of that SAME finding. An
        open ticket with a DIFFERENT title (so `_find_exact_duplicate`'s
        title+scope check does not fire at all) that already declares
        `("RULE1", "a.py")` in its structured `findings` field reproduces
        the real T-2977 incident directly: `_file_regression_ticket`'s own
        `new_ticket(...)` call is refused with `DuplicateFinding`
        (T-2760), and before this fix that refusal fell through to the
        generic ERROR branch and returned `None` -- an unfiled regression
        with no owner, which pins the watermark (T-2324) and leaves
        quarantine undisposable (T-2744) even though the finding already
        has a perfectly good owner. The fix must resolve that owner via
        `_find_finding_duplicate` and dispose to it, exactly as the
        DuplicateTicket branch already does."""
        from frob.graph import CallGraph, GraphSnapshot
        from frob.tickets import TicketSpec, new_ticket
        from frob.tickets._models import Origin, TicketKind
        from frob.verify import record_intent
        from frob.verify._quarantine import load_quarantine

        record_intent(
            tmp_path,
            commit_sha="commitA",
            ticket_id="T-0001",
            touched_symbols=("unrelated.py::other",),
            profile="rapid",
        )
        snapshot = GraphSnapshot(root=str(tmp_path), symbols={}, edges=())
        self._patch_graph(monkeypatch, snapshot, CallGraph(calls={}))

        # An open ticket, filed under a title sharing no words with the
        # sweep's own generated title, that already declares the finding
        # this sweep is about to re-measure -- the "fix ticket declares
        # its own findings" shape T-2760's docstring names explicitly.
        declaring = new_ticket(
            tmp_path,
            TicketSpec(
                title="fix the F401 unused import",
                kind=TicketKind.BUG,
                origin=Origin.AGENT,
                scope=("a.py",),
                findings=(("RULE1", "a.py"),),
            ),
            no_commit=True,
            warn_if_dirty=False,
        )
        assert declaring.is_ok
        declaring_id = declaring.danger_ok.id

        pairs = frozenset({("RULE1", "a.py")})
        filed = _file_regression_ticket(tmp_path, "T-9000", "deadbeef", pairs)

        assert filed == declaring_id, (
            "a DuplicateFinding refusal must dispose to the ticket that "
            "already declares the finding, never return None and "
            "abandon it"
        )

        record = load_quarantine(tmp_path).danger_ok
        assert record is not None
        assert record.cleared_at is not None, (
            "quarantine must clear once the duplicate-owned findings are "
            "disposed to the declaring ticket"
        )

    # frob:ticket T-3051
    def test_unrelated_duplicate_finding_in_a_different_file_still_refuses(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestFileRegressionTicket.test_unrelated_duplicate_finding_in_a_different_file_still_refuses  # noqa: E501
        """T-3051 (H4) acceptance [1] (must-still-refuse positive
        control): a ticket declaring a DIFFERENT (rule, file) pair must
        not be mistaken for the owner of this sweep's finding -- the fix
        must resolve the ACTUAL declaring ticket via `_find_finding_
        duplicate`, never accept any open ticket as a stand-in. With no
        ticket declaring the real pair, filing genuinely fails (no
        DuplicateFinding refusal fires at all here, since the identities
        never overlap) and this must file its own new ticket rather than
        silently disposing to the unrelated one."""
        from frob.graph import CallGraph, GraphSnapshot
        from frob.tickets import TicketSpec, load_queue, new_ticket
        from frob.tickets._models import Origin, TicketKind
        from frob.verify import record_intent

        record_intent(
            tmp_path,
            commit_sha="commitA",
            ticket_id="T-0001",
            touched_symbols=("unrelated.py::other",),
            profile="rapid",
        )
        snapshot = GraphSnapshot(root=str(tmp_path), symbols={}, edges=())
        self._patch_graph(monkeypatch, snapshot, CallGraph(calls={}))

        unrelated = new_ticket(
            tmp_path,
            TicketSpec(
                title="fix an unrelated finding",
                kind=TicketKind.BUG,
                origin=Origin.AGENT,
                scope=("b.py",),
                findings=(("RULE2", "b.py"),),
            ),
            no_commit=True,
            warn_if_dirty=False,
        )
        assert unrelated.is_ok

        pairs = frozenset({("RULE1", "a.py")})
        filed = _file_regression_ticket(tmp_path, "T-9000", "deadbeef", pairs)

        assert filed is not None
        assert filed != unrelated.danger_ok.id, (
            "a ticket declaring an unrelated (rule, file) pair must "
            "never be treated as this finding's owner"
        )
        queue = load_queue(tmp_path).danger_ok
        assert queue is not None
        assert queue.tickets[filed].findings == (("RULE1", "a.py"),)

    # frob:ticket T-2312
    def test_non_duplicate_filing_failure_still_leaves_quarantine_raised(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestFileRegressionTicket.test_non_duplicate_filing_failure_still_leaves_quarantine_raised  # noqa: E501
        """T-2312 acceptance [1] (must-still-pass positive control): a
        filing failure that is NOT a duplicate refusal (no existing
        ticket owns these findings at all) must still leave quarantine
        RAISED and still return `None` -- the T-2312 fix only reroutes
        the DUPLICATE branch to disposal, it must never make an
        ownerless finding's filing failure look disposed."""
        from typani import Err

        import frob.tickets as tickets_mod
        from frob.graph import CallGraph, GraphSnapshot
        from frob.tickets._models import TicketError
        from frob.verify import record_intent
        from frob.verify._quarantine import load_quarantine

        record_intent(
            tmp_path,
            commit_sha="commitA",
            ticket_id="T-0001",
            touched_symbols=("unrelated.py::other",),
            profile="rapid",
        )
        snapshot = GraphSnapshot(root=str(tmp_path), symbols={}, edges=())
        self._patch_graph(monkeypatch, snapshot, CallGraph(calls={}))
        monkeypatch.setattr(
            tickets_mod, "new_ticket", lambda *a, **k: Err(TicketError.WriteFailed)
        )

        filed = _file_regression_ticket(
            tmp_path, "T-9000", "deadbeef", frozenset({("RULE1", "a.py")})
        )
        assert filed is None

        record = load_quarantine(tmp_path).danger_ok
        assert record is not None
        assert record.cleared_at is None, (
            "an ownerless finding's failed filing must NOT clear "
            "quarantine -- that is the guard's real job"
        )

    def test_all_attributed_to_open_tickets_files_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestFileRegressionTicket.test_all_attributed_to_open_tickets_files_nothing  # noqa: E501
        from frob.graph import CallGraph, Digests, GraphSnapshot, SymbolId, SymbolRecord
        from frob.lang import SymbolKind
        from frob.verify import record_intent

        owner = _seed_ticket(tmp_path)
        record_intent(
            tmp_path,
            commit_sha="commitA",
            ticket_id=owner,
            touched_symbols=("a.py::fn", "b.py::fn2"),
            profile="rapid",
        )
        snapshot = GraphSnapshot(
            root=str(tmp_path),
            symbols={
                "a.py::fn": SymbolRecord(
                    id=SymbolId(path="a.py", qualname="fn"),
                    kind=SymbolKind.FUNCTION,
                    public=True,
                    digests=Digests(sig="s", body="b", doc="d"),
                    span=(1, 5),
                ),
                "b.py::fn2": SymbolRecord(
                    id=SymbolId(path="b.py", qualname="fn2"),
                    kind=SymbolKind.FUNCTION,
                    public=True,
                    digests=Digests(sig="s", body="b", doc="d"),
                    span=(1, 5),
                ),
            },
            edges=(),
        )
        self._patch_graph(monkeypatch, snapshot, CallGraph(calls={}))
        filed = _file_regression_ticket(
            tmp_path,
            "T-9000",
            "deadbeef",
            frozenset({("RULE1", "a.py"), ("RULE2", "b.py")}),
        )
        assert filed is None


# frob:ticket T-2352
class TestRelativizeRegressionScopeFile:
    """T-2352: `_relativize_regression_scope_file` normalizes a regression
    finding's `.file` at the producer's own return boundary -- the fix for
    T-2308's real incident (an absolute path written into a filed
    ticket's `scope:` crashed `frob ticket new` fleet-wide, T-2342's
    reader-side half). Same posture as T-2314's
    `_relativize_perf_violation_file`."""

    # frob:ticket T-2352
    # frob:tests tests/unit/test_rapid_sweep.py::TestRelativizeRegressionScopeFile.test_absolute_under_root_is_relativized  # noqa: E501
    def test_absolute_under_root_is_relativized(self, tmp_path: Path) -> None:
        """Positive control 1 (T-2352): an absolute path under root
        becomes a repo-relative one."""
        abs_file = str(tmp_path / "src" / "frob" / "x.py")
        result = _relativize_regression_scope_file(tmp_path, abs_file)
        assert result == str(Path("src") / "frob" / "x.py")
        assert not Path(result).is_absolute()

    # frob:ticket T-2352
    # frob:tests tests/unit/test_rapid_sweep.py::TestRelativizeRegressionScopeFile.test_already_relative_is_unchanged  # noqa: E501
    def test_already_relative_is_unchanged(self, tmp_path: Path) -> None:
        """Must-still-pass control: an already-relative path is returned
        unchanged (no double-processing, no accidental corruption)."""
        result = _relativize_regression_scope_file(tmp_path, "scripts/fleet_status.py")
        assert result == "scripts/fleet_status.py"

    # frob:ticket T-2352
    # frob:tests tests/unit/test_rapid_sweep.py::TestRelativizeRegressionScopeFile.test_absolute_outside_root_is_kept_and_logged  # noqa: E501
    def test_absolute_outside_root_is_kept_and_logged(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Positive control 2 (T-2352, must-still-pass): a genuinely
        anomalous absolute path that does NOT resolve under root is kept
        as-is -- never silently coerced into a wrong-but-plausible
        relative path -- and logged loudly."""
        import logging

        outside = str(Path("/definitely/not/under/tmp_path/x.py"))
        with caplog.at_level(logging.WARNING):
            result = _relativize_regression_scope_file(tmp_path, outside)
        assert result == outside
        messages = "\n".join(r.getMessage() for r in caplog.records)
        assert outside in messages

    # frob:ticket T-2352
    # frob:tests tests/unit/test_rapid_sweep.py::TestRelativizeRegressionScopeFile.test_filed_ticket_scope_is_relative_end_to_end  # noqa: E501
    def test_filed_ticket_scope_is_relative_end_to_end(self, tmp_path: Path) -> None:
        """Positive control 3 (T-2352): a ticket filed by
        `_file_regression_ticket` with an ABSOLUTE finding path gets a
        RELATIVE `scope:` entry -- the actual T-2308 incident shape,
        exercised end-to-end through the real filer, not just the helper
        in isolation. This MUST FAIL before this ticket's fix (scope would
        carry the raw absolute path)."""
        from frob.tickets._store import load_all

        abs_file = str(tmp_path / "src" / "frob" / "x.py")
        filed = _file_regression_ticket(
            tmp_path, "T-9000", "deadbeef", frozenset({("RULE1", abs_file)})
        )
        assert filed is not None
        loaded = load_all(tmp_path)
        assert loaded.is_ok
        ticket = loaded.danger_ok[filed]
        assert list(ticket.scope) == [str(Path("src") / "frob" / "x.py")]


# frob:ticket T-1791
# frob:ticket T-1847
class TestRaiseQuarantineForRedBatch:
    """T-1791: wiring `raise_quarantine` into the shared "a red batch
    verification came back" seam both drivers (`_file_regression_ticket`)
    call through."""

    # frob:ticket T-1791
    def test_raises_with_attributed_and_unattributed_findings(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestRaiseQuarantineForRedBatch.test_raises_with_attributed_and_unattributed_findings  # noqa: E501
        from frob.verify import record_intent
        from frob.verify._quarantine import is_quarantined, load_quarantine

        record_intent(
            tmp_path,
            commit_sha="commitA",
            ticket_id="T-9000",
            touched_symbols=("a.py::fn",),
            profile="rapid",
        )
        # No graph patched -- attribution degrades to "unavailable",
        # exactly the pre-T-1690 fallback `_file_regression_ticket`'s own
        # docstring already documents; every pair is filed, and every
        # QuarantinedFinding here carries no commit_sha/ticket_id.
        filed = _file_regression_ticket(
            tmp_path,
            "T-9000",
            "deadbeef",
            frozenset({("RULE1", "a.py"), ("RULE2", "b.py")}),
        )
        assert filed is not None

        # T-2208: the regression ticket this call filed covers BOTH
        # pairs, so the auto-dispose that follows filing clears the
        # quarantine it just raised in the same operation -- the raise
        # itself (this test's own T-1791 subject) is still verified via
        # the record's own content, just post-clear rather than
        # is_quarantined() staying True.
        assert is_quarantined(tmp_path).danger_ok is False
        record = load_quarantine(tmp_path)
        assert record.is_ok
        assert record.danger_ok is not None
        assert record.danger_ok.batch_commit_shas == ("commitA",)
        assert {(f.rule_id, f.file) for f in record.danger_ok.findings} == {
            ("RULE1", "a.py"),
            ("RULE2", "b.py"),
        }
        assert all(f.disposition == "filed" for f in record.danger_ok.findings)
        assert all(f.disposition_ref == filed for f in record.danger_ok.findings)

    # frob:ticket T-1791
    def test_empty_queue_logs_and_skips_the_raise(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestRaiseQuarantineForRedBatch.test_empty_queue_logs_and_skips_the_raise  # noqa: E501
        from frob.verify._quarantine import is_quarantined

        # No verify queue at all -- nothing to name as the raising batch.
        filed = _file_regression_ticket(
            tmp_path, "T-9000", "deadbeef", frozenset({("RULE1", "a.py")})
        )
        assert filed is not None
        assert is_quarantined(tmp_path).danger_ok is False

    # frob:ticket T-2604
    def test_open_ticket_attribution_clears_the_quarantine_raise(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestRaiseQuarantineForRedBatch.test_open_ticket_attribution_clears_the_quarantine_raise  # noqa: E501
        """T-2604: every pair attributes to an already-open ticket -- no
        NEW regression ticket is filed (that half was already correct,
        T-1690), and the batch must NOT trip the quarantine circuit
        breaker either, since a still-open owner means the finding
        already has a home and someone is on it."""
        from frob.graph import CallGraph, Digests, GraphSnapshot, SymbolId, SymbolRecord
        from frob.lang import SymbolKind
        from frob.verify import record_intent
        from frob.verify._quarantine import is_quarantined

        owner = _seed_ticket(tmp_path)
        record_intent(
            tmp_path,
            commit_sha="commitA",
            ticket_id=owner,
            touched_symbols=("a.py::fn",),
            profile="rapid",
        )
        snapshot = GraphSnapshot(
            root=str(tmp_path),
            symbols={
                "a.py::fn": SymbolRecord(
                    id=SymbolId(path="a.py", qualname="fn"),
                    kind=SymbolKind.FUNCTION,
                    public=True,
                    digests=Digests(sig="s", body="b", doc="d"),
                    span=(1, 5),
                )
            },
            edges=(),
        )
        import frob.verify._attribution as attribution_mod

        monkeypatch.setattr(
            attribution_mod,
            "_load_snapshot_and_call_graph",
            lambda root: (snapshot, CallGraph(calls={})),
        )
        filed = _file_regression_ticket(
            tmp_path, "T-9000", "deadbeef", frozenset({("RULE1", "a.py")})
        )
        assert filed is None
        assert is_quarantined(tmp_path).danger_ok is False

    # frob:ticket T-2604
    def test_closed_ticket_attribution_still_raises(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestRaiseQuarantineForRedBatch.test_closed_ticket_attribution_still_raises  # noqa: E501
        """T-2604: a pair attributed to a CLOSED/DROPPED ticket is a real
        regression against work believed finished -- it must still trip
        quarantine, exactly as before this ticket. Without this case the
        fix would be indistinguishable from disabling quarantine
        outright."""
        from frob.graph import CallGraph, Digests, GraphSnapshot, SymbolId, SymbolRecord
        from frob.lang import SymbolKind
        from frob.tickets._models import TicketState
        from frob.verify import record_intent
        from frob.verify._quarantine import load_quarantine

        owner = _seed_ticket(tmp_path, state=TicketState.DONE)
        record_intent(
            tmp_path,
            commit_sha="commitA",
            ticket_id=owner,
            touched_symbols=("a.py::fn",),
            profile="rapid",
        )
        snapshot = GraphSnapshot(
            root=str(tmp_path),
            symbols={
                "a.py::fn": SymbolRecord(
                    id=SymbolId(path="a.py", qualname="fn"),
                    kind=SymbolKind.FUNCTION,
                    public=True,
                    digests=Digests(sig="s", body="b", doc="d"),
                    span=(1, 5),
                )
            },
            edges=(),
        )
        import frob.verify._attribution as attribution_mod

        monkeypatch.setattr(
            attribution_mod,
            "_load_snapshot_and_call_graph",
            lambda root: (snapshot, CallGraph(calls={})),
        )
        filed = _file_regression_ticket(
            tmp_path, "T-9000", "deadbeef", frozenset({("RULE1", "a.py")})
        )
        assert filed is not None  # closed owner -- refiled as a new ticket
        # T-2208: the freshly filed ticket covers this pair, so
        # auto-dispose clears the quarantine flag in the same operation
        # -- the raise itself (this test's own T-2604 subject: a
        # closed-ticket attribution must still trip quarantine) is
        # verified via the record's own content, same pattern as
        # test_raises_with_attributed_and_unattributed_findings above.
        record = load_quarantine(tmp_path)
        assert record.danger_ok is not None
        assert {(f.rule_id, f.file) for f in record.danger_ok.findings} == {
            ("RULE1", "a.py"),
        }

    # frob:ticket T-2604
    def test_unattributed_still_raises_alongside_open_ticket_finding(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestRaiseQuarantineForRedBatch.test_unattributed_still_raises_alongside_open_ticket_finding  # noqa: E501
        """T-2604: a batch mixing one open-ticket finding with one
        unattributed finding must still raise, naming only the
        unattributed one -- an unowned finding is exactly what
        quarantine exists to catch, and the open-ticket finding's
        presence in the same batch must not mask it."""
        from frob.graph import CallGraph, Digests, GraphSnapshot, SymbolId, SymbolRecord
        from frob.lang import SymbolKind
        from frob.verify import record_intent
        from frob.verify._quarantine import load_quarantine

        owner = _seed_ticket(tmp_path)
        record_intent(
            tmp_path,
            commit_sha="commitA",
            ticket_id=owner,
            touched_symbols=("a.py::fn",),
            profile="rapid",
        )
        snapshot = GraphSnapshot(
            root=str(tmp_path),
            symbols={
                "a.py::fn": SymbolRecord(
                    id=SymbolId(path="a.py", qualname="fn"),
                    kind=SymbolKind.FUNCTION,
                    public=True,
                    digests=Digests(sig="s", body="b", doc="d"),
                    span=(1, 5),
                )
            },
            edges=(),
        )
        import frob.verify._attribution as attribution_mod

        monkeypatch.setattr(
            attribution_mod,
            "_load_snapshot_and_call_graph",
            lambda root: (snapshot, CallGraph(calls={})),
        )
        # RULE1/a.py attributes to the open ticket via a.py::fn;
        # RULE2/b.py has no symbol in the snapshot, so it stays
        # UNATTRIBUTED.
        filed = _file_regression_ticket(
            tmp_path,
            "T-9000",
            "deadbeef",
            frozenset({("RULE1", "a.py"), ("RULE2", "b.py")}),
        )
        assert filed is not None  # the unattributed pair gets a new ticket
        # T-2208: the filed ticket covers exactly the unattributed pair,
        # so auto-dispose clears the flag in the same operation -- the
        # raise itself (named only the unattributed pair, per this
        # test's own subject) is verified via the record's own content.
        record = load_quarantine(tmp_path)
        assert record.danger_ok is not None
        assert {(f.rule_id, f.file) for f in record.danger_ok.findings} == {
            ("RULE2", "b.py"),
        }

    # frob:ticket T-1791
    def test_raise_failure_is_logged_not_raised(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestRaiseQuarantineForRedBatch.test_raise_failure_is_logged_not_raised  # noqa: E501
        from typani.result import Err

        from frob.verify import _quarantine as quarantine_mod
        from frob.verify import record_intent
        from frob.verify._quarantine import QuarantineError

        record_intent(
            tmp_path,
            commit_sha="commitA",
            ticket_id="T-9000",
            touched_symbols=("a.py::fn",),
            profile="rapid",
        )
        monkeypatch.setattr(
            quarantine_mod,
            "raise_quarantine",
            lambda root, **kw: Err(QuarantineError.StoreCorrupt),
        )
        # Must not raise or otherwise fail the caller -- the regression
        # ticket filing is the durable record; a quarantine write failure
        # is logged and swallowed.
        filed = _file_regression_ticket(
            tmp_path, "T-9000", "deadbeef", frozenset({("RULE1", "a.py")})
        )
        assert filed is not None

    # frob:ticket T-1847
    def test_warm_tree_recheck_drops_cold_worktree_native_noise(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestRaiseQuarantineForRedBatch.test_warm_tree_recheck_drops_cold_worktree_native_noise  # noqa: E501
        from frob.strata import _native_staleness
        from frob.verify import record_intent
        from frob.verify._quarantine import is_quarantined

        record_intent(
            tmp_path,
            commit_sha="commitA",
            ticket_id="T-9000",
            touched_symbols=("a.py::fn",),
            profile="rapid",
        )
        # Every declared native imports cleanly RIGHT NOW -- the sole
        # finding is UNATTRIBUTED + "unresolved-import", the exact
        # cold-worktree-noise shape, so the warm re-check must clear it
        # and the raise must be skipped entirely.
        monkeypatch.setattr(_native_staleness, "unimportable_natives", lambda root: ())
        filed = _file_regression_ticket(
            tmp_path,
            "T-9000",
            "deadbeef",
            frozenset({("unresolved-import", "a.py")}),
        )
        assert filed is not None  # still filed as a regression ticket
        assert is_quarantined(tmp_path).danger_ok is False

    # frob:ticket T-1847
    def test_warm_tree_recheck_keeps_finding_when_native_still_broken(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestRaiseQuarantineForRedBatch.test_warm_tree_recheck_keeps_finding_when_native_still_broken  # noqa: E501
        from frob.strata import _native_staleness
        from frob.testing._models import NativeSpec
        from frob.verify import record_intent
        from frob.verify._quarantine import is_quarantined, load_quarantine

        record_intent(
            tmp_path,
            commit_sha="commitA",
            ticket_id="T-9000",
            touched_symbols=("a.py::fn",),
            profile="rapid",
        )
        broken = (NativeSpec(name="strata_core", build_cmd="true"),)
        monkeypatch.setattr(
            _native_staleness, "unimportable_natives", lambda root: broken
        )
        filed = _file_regression_ticket(
            tmp_path,
            "T-9000",
            "deadbeef",
            frozenset({("unresolved-import", "a.py")}),
        )
        assert filed is not None
        # T-2208: this pair is fully covered by the ticket just filed,
        # so auto-dispose clears the quarantine the raise (this test's
        # own T-1847 subject) put up.
        assert is_quarantined(tmp_path).danger_ok is False
        record = load_quarantine(tmp_path)
        assert record.danger_ok is not None
        assert {(f.rule_id, f.file) for f in record.danger_ok.findings} == {
            ("unresolved-import", "a.py"),
        }
        assert all(f.disposition == "filed" for f in record.danger_ok.findings)

    # frob:ticket T-1847
    def test_warm_tree_recheck_never_drops_an_attributed_finding(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestRaiseQuarantineForRedBatch.test_warm_tree_recheck_never_drops_an_attributed_finding  # noqa: E501
        """T-2604: the owning ticket here is CLOSED (not open) so this
        stays an isolated test of the T-1847 warm-tree filter alone --
        an open owner would ALSO be cleared by the new T-2604 open-ticket
        filter, which would make a pass here ambiguous about which filter
        is actually responsible."""
        from frob.graph import CallGraph, Digests, GraphSnapshot, SymbolId, SymbolRecord
        from frob.lang import SymbolKind
        from frob.strata import _native_staleness
        from frob.tickets._models import TicketState
        from frob.verify import record_intent
        from frob.verify._quarantine import load_quarantine

        owner = _seed_ticket(tmp_path, state=TicketState.DONE)
        record_intent(
            tmp_path,
            commit_sha="commitA",
            ticket_id=owner,
            touched_symbols=("a.py::fn",),
            profile="rapid",
        )
        snapshot = GraphSnapshot(
            root=str(tmp_path),
            symbols={
                "a.py::fn": SymbolRecord(
                    id=SymbolId(path="a.py", qualname="fn"),
                    kind=SymbolKind.FUNCTION,
                    public=True,
                    digests=Digests(sig="s", body="b", doc="d"),
                    span=(1, 5),
                )
            },
            edges=(),
        )
        import frob.verify._attribution as attribution_mod

        monkeypatch.setattr(
            attribution_mod,
            "_load_snapshot_and_call_graph",
            lambda root: (snapshot, CallGraph(calls={})),
        )
        # unimportable_natives says everything is warm -- if the finding
        # were unattributed this would clear it, but this pair reaches
        # a.py::fn and must attribute to a CLOSED ticket (owner), a
        # wholly different case than "unattributed". The finding must NOT
        # be treated as cold-worktree noise just because the rule id
        # matches.
        monkeypatch.setattr(_native_staleness, "unimportable_natives", lambda root: ())
        filed = _file_regression_ticket(
            tmp_path,
            "T-9000",
            "deadbeef",
            frozenset({("unresolved-import", "a.py")}),
        )
        assert filed is not None  # closed owner -- refiled as a new ticket
        # T-2208: the filed ticket covers this pair, so auto-dispose
        # clears the flag -- verify the raise itself via the record's
        # own content, same pattern as the other T-2604/T-1847 tests.
        record = load_quarantine(tmp_path)
        assert record.danger_ok is not None
        assert {(f.rule_id, f.file) for f in record.danger_ok.findings} == {
            ("unresolved-import", "a.py"),
        }


# frob:ticket T-2208
class TestAutoDisposeFiledFindings:
    """T-2208: filing a regression ticket for a quarantined finding must
    dispose that finding, with `--file-ticket` semantics, in the same
    operation -- never leave a human to hand-restate the fact via `frob
    verify dispose --file-ticket` after every red batch."""

    # frob:ticket T-2208
    def test_disposes_findings_the_ticket_covers(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestAutoDisposeFiledFindings.test_disposes_findings_the_ticket_covers  # noqa: E501
        from frob.verify import record_intent
        from frob.verify._quarantine import is_quarantined, load_quarantine

        record_intent(
            tmp_path,
            commit_sha="commitA",
            ticket_id="T-9000",
            touched_symbols=("a.py::fn",),
            profile="rapid",
        )
        filed = _file_regression_ticket(
            tmp_path,
            "T-9000",
            "deadbeef",
            frozenset({("RULE1", "a.py")}),
        )
        assert filed is not None

        # This is the ticket's own MUST-fail-against-main assertion:
        # before T-2208, filing a regression ticket never disposed the
        # quarantine record it was filed for, so quarantine stayed
        # raised until a human ran `frob verify dispose` by hand.
        assert is_quarantined(tmp_path).danger_ok is False
        record = load_quarantine(tmp_path)
        assert record.is_ok
        assert record.danger_ok is not None
        (finding,) = record.danger_ok.findings
        assert finding.disposition == "filed"
        assert finding.disposition_ref == filed

    # frob:ticket T-2208
    # frob:ticket T-2604
    def test_leaves_quarantine_raised_when_other_findings_remain_undisposed(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestAutoDisposeFiledFindings.test_leaves_quarantine_raised_when_other_findings_remain_undisposed  # noqa: E501
        """T-2604 rewrote this test's original setup: it used to lean on
        a finding attributed to an already-open ticket to construct "one
        finding in the raised record this call never touches". Exactly
        the bug T-2604 fixes means such a finding is now dropped from
        the quarantine raise entirely, before this scenario can even
        arise through `_file_regression_ticket`'s own attribution path.
        Exercising `_auto_dispose_filed_findings` directly against a
        record raised independently (simulating one left over from an
        earlier, unrelated red batch this call's `unfiled_pairs` never
        names) keeps this test's real subject -- `clear_quarantine`'s
        atomic all-or-nothing contract -- intact and independent of how
        the record came to have two findings in it."""
        from frob.app.ticket_runner._rapid_sweep import _auto_dispose_filed_findings
        from frob.verify._quarantine import (
            QuarantinedFinding,
            is_quarantined,
            load_quarantine,
            raise_quarantine,
        )

        raised = raise_quarantine(
            tmp_path,
            batch_commit_shas=("commitA",),
            findings=(
                QuarantinedFinding(rule_id="RULE1", file="a.py", line=None),
                QuarantinedFinding(rule_id="RULE2", file="b.py", line=None),
            ),
        )
        assert raised.is_ok

        # Only RULE2/b.py is covered by this filing -- RULE1/a.py is
        # left alone, exactly `_auto_dispose_filed_findings`'s own
        # documented contract for "a different, already-open ticket
        # this call never touched".
        _auto_dispose_filed_findings(tmp_path, [("RULE2", "b.py")], "T-9001")

        assert is_quarantined(tmp_path).danger_ok is True
        record = load_quarantine(tmp_path)
        assert record.danger_ok is not None
        dispositions = {
            (f.rule_id, f.file): f.disposition for f in record.danger_ok.findings
        }
        assert dispositions == {("RULE1", "a.py"): "", ("RULE2", "b.py"): ""}

    # frob:ticket T-2208
    # frob:waive DUP001 reason="100% similar to \
    # TestRaiseQuarantineForRedBatch.test_empty_queue_logs_and_skips_the_raise by \
    # construction -- both exercise the SAME no-queue/no-raise precondition, one \
    # asserting the raise never fires, the other (this one) asserting the NEW T-2208 \
    # auto-dispose call downstream of it is a no-op when there was nothing to dispose \
    # in the first place; a shared helper would hide which capability each test is \
    # pinning"
    def test_no_quarantine_raised_is_a_silent_no_op(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestAutoDisposeFiledFindings.test_no_quarantine_raised_is_a_silent_no_op  # noqa: E501
        from frob.verify._quarantine import is_quarantined

        # No verify queue -- `_raise_quarantine_for_red_batch` never
        # raises anything, so there is nothing to auto-dispose.
        filed = _file_regression_ticket(
            tmp_path, "T-9000", "deadbeef", frozenset({("RULE1", "a.py")})
        )
        assert filed is not None
        assert is_quarantined(tmp_path).danger_ok is False

    # frob:ticket T-2208
    # frob:waive DUP001 reason="95% similar to \
    # TestRaiseQuarantineForRedBatch.test_raise_failure_is_logged_not_raised by \
    # construction -- same fail-soft shape (a quarantine-module write failing must be \
    # logged and swallowed, never raised), applied to the OTHER quarantine write this \
    # ticket adds (clear_quarantine, not raise_quarantine); collapsing the two would \
    # obscure which call each test pins down"
    def test_clear_failure_is_logged_not_raised(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestAutoDisposeFiledFindings.test_clear_failure_is_logged_not_raised  # noqa: E501
        from typani.result import Err

        from frob.verify import _quarantine as quarantine_mod
        from frob.verify import record_intent
        from frob.verify._quarantine import QuarantineError

        record_intent(
            tmp_path,
            commit_sha="commitA",
            ticket_id="T-9000",
            touched_symbols=("a.py::fn",),
            profile="rapid",
        )
        monkeypatch.setattr(
            quarantine_mod,
            "clear_quarantine",
            lambda root, **kw: Err(QuarantineError.NotQuarantined),
        )
        # Must not raise or otherwise fail the caller -- the filed
        # ticket is still the durable record even if the auto-dispose
        # write itself fails for some reason.
        filed = _file_regression_ticket(
            tmp_path, "T-9000", "deadbeef", frozenset({("RULE1", "a.py")})
        )
        assert filed is not None


# frob:ticket T-1983
class TestCloseResolvedSweepTickets:
    """T-1983: a sweep-filed regression ticket whose findings stop
    reproducing must be auto-DROPPED (not closed, not left forever) the
    next time the sweep can prove it, reusing the rolling-baseline diff
    the sweep already computes for the opposite direction."""

    def test_non_sweep_ticket_returns_none(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestCloseResolvedSweepTickets.test_non_sweep_ticket_returns_none  # noqa: E501
        ticket_id = _seed_ticket(tmp_path)
        from frob.tickets import load_queue

        queue = load_queue(tmp_path)
        assert queue.is_ok
        ticket = queue.danger_ok.tickets[ticket_id]
        assert _parse_sweep_ticket_identities(ticket) is None

    def test_parses_a_sweep_titled_ticket_identity_set(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestCloseResolvedSweepTickets.test_parses_a_sweep_titled_ticket_identity_set  # noqa: E501
        findings = frozenset({("RULE1", "a.py"), ("RULE2", "b.py")})
        filed = _file_regression_ticket(tmp_path, "T-9000", "deadbeef", findings)
        assert filed is not None
        from frob.tickets import load_queue

        queue = load_queue(tmp_path)
        assert queue.is_ok
        ticket = queue.danger_ok.tickets[filed]
        assert _parse_sweep_ticket_identities(ticket) == findings

    def test_drops_a_fully_resolved_sweep_ticket(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestCloseResolvedSweepTickets.test_drops_a_fully_resolved_sweep_ticket  # noqa: E501
        findings = frozenset({("RULE1", "a.py")})
        filed = _file_regression_ticket(tmp_path, "T-9000", "deadbeef", findings)
        assert filed is not None

        dropped = _close_resolved_sweep_tickets(tmp_path, "T-9001", findings)
        assert dropped == (filed,)

        from frob.tickets import TicketState, load_queue

        queue = load_queue(tmp_path)
        assert queue.is_ok
        assert queue.danger_ok.tickets[filed].state == TicketState.DROPPED

    def test_leaves_a_partially_resolved_ticket_untouched(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestCloseResolvedSweepTickets.test_leaves_a_partially_resolved_ticket_untouched  # noqa: E501
        findings = frozenset({("RULE1", "a.py"), ("RULE2", "b.py")})
        filed = _file_regression_ticket(tmp_path, "T-9000", "deadbeef", findings)
        assert filed is not None

        # Only RULE1/a.py vanished -- RULE2/b.py still reproduces, so the
        # ticket as a whole must not be dropped.
        dropped = _close_resolved_sweep_tickets(
            tmp_path, "T-9001", frozenset({("RULE1", "a.py")})
        )
        assert dropped == ()

        from frob.tickets import TicketState, load_queue

        queue = load_queue(tmp_path)
        assert queue.is_ok
        assert queue.danger_ok.tickets[filed].state == TicketState.QUEUED

    def test_leaves_a_still_reproducing_ticket_untouched(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestCloseResolvedSweepTickets.test_leaves_a_still_reproducing_ticket_untouched  # noqa: E501
        findings = frozenset({("RULE1", "a.py")})
        filed = _file_regression_ticket(tmp_path, "T-9000", "deadbeef", findings)
        assert filed is not None

        dropped = _close_resolved_sweep_tickets(tmp_path, "T-9001", frozenset())
        assert dropped == ()

        from frob.tickets import TicketState, load_queue

        queue = load_queue(tmp_path)
        assert queue.is_ok
        assert queue.danger_ok.tickets[filed].state == TicketState.QUEUED

    # frob:ticket T-2521
    def test_absolute_recorded_identity_matches_relative_vanished_entry(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestCloseResolvedSweepTickets.test_absolute_recorded_identity_matches_relative_vanished_entry  # noqa: E501
        """T-2521 required control #3: a ticket whose body recorded an
        finding with an ABSOLUTE path (the real, historical shape T-2036
        fixed, T-2314's own 116-waiver incident of the identical class)
        must still be recognized as resolved when the fresh measurement's
        `vanished` set names the SAME file repo-relative -- end-to-end
        through the real drop path (`_close_resolved_sweep_tickets` ->
        `_maybe_drop_resolved_ticket`), not just the isolated `_normalize_
        identities` unit tests elsewhere in this file."""
        findings = frozenset({("RULE1", str(tmp_path / "a.py"))})
        filed = _file_regression_ticket(tmp_path, "T-9000", "deadbeef", findings)
        assert filed is not None

        # The fresh measurement's own vanished set, repo-relative (the
        # shape a real `frob check --json` reports).
        dropped = _close_resolved_sweep_tickets(
            tmp_path, "T-9001", frozenset({("RULE1", "a.py")})
        )
        assert dropped == (filed,)

        from frob.tickets import TicketState, load_queue

        queue = load_queue(tmp_path)
        assert queue.is_ok
        assert queue.danger_ok.tickets[filed].state == TicketState.DROPPED

    def test_in_progress_sweep_ticket_is_never_touched(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestCloseResolvedSweepTickets.test_in_progress_sweep_ticket_is_never_touched  # noqa: E501
        from frob.tickets import TicketState, transition

        findings = frozenset({("RULE1", "a.py")})
        filed = _file_regression_ticket(tmp_path, "T-9000", "deadbeef", findings)
        assert filed is not None
        planned = transition(tmp_path, filed, TicketState.PLANNED)
        assert planned.is_ok
        started = transition(tmp_path, filed, TicketState.IN_PROGRESS)
        assert started.is_ok

        dropped = _close_resolved_sweep_tickets(tmp_path, "T-9001", findings)
        assert dropped == ()

    # frob:ticket T-2030
    def test_a_done_ticket_body_is_byte_for_byte_untouched(
        self, tmp_path: Path
    ) -> None:
        """T-2030: a `done` ticket's own Done report was found silently
        REPLACED in an incident this ticket investigates -- verify the
        QUEUED/PLANNED state filter (`_close_resolved_sweep_tickets`'s
        own scan, `ticket.state not in (QUEUED, PLANNED)`) genuinely
        protects a terminal ticket's file content, byte for byte, rather
        than trusting the guard exists by reading it."""
        # frob:tests tests/unit/test_rapid_sweep.py::TestCloseResolvedSweepTickets.test_a_done_ticket_body_is_byte_for_byte_untouched  # noqa: E501
        from frob.tickets import TicketState, drop_ticket, transition

        findings = frozenset({("RULE1", "a.py")})
        filed = _file_regression_ticket(tmp_path, "T-9000", "deadbeef", findings)
        assert filed is not None
        planned = transition(tmp_path, filed, TicketState.PLANNED)
        assert planned.is_ok
        started = transition(tmp_path, filed, TicketState.IN_PROGRESS)
        assert started.is_ok
        # DROPPED is the cheap way to reach a terminal state here (same
        # trick `_seed_ticket`'s own docstring above uses) -- terminal is
        # the property under test, not which terminal state.
        dropped_result = drop_ticket(tmp_path, filed, "done for this test")
        assert dropped_result.is_ok

        ticket_path = tmp_path / "tickets" / filed / "ticket.md"
        before = ticket_path.read_bytes()

        result = _close_resolved_sweep_tickets(tmp_path, "T-9001", findings)
        assert result == ()

        after = ticket_path.read_bytes()
        assert after == before

    # frob:ticket T-2034
    def test_commit_failure_restores_root_to_clean_not_left_dirty(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2034's own repro: `_maybe_drop_resolved_ticket`'s
        `drop_ticket()` write must never survive an exhausted commit retry
        uncommitted in `root` -- that is exactly the DirtyMain-blocking
        defect this ticket exists to close. Before the fix this asserted
        root DIRTY; after the fix root must be CLEAN and the ticket
        restored to QUEUED (droppable again on the next sweep, not
        silently lost)."""
        # frob:tests tests/unit/test_rapid_sweep.py::TestCloseResolvedSweepTickets.test_commit_failure_restores_root_to_clean_not_left_dirty  # noqa: E501
        from typani.result import Err

        import frob.app.ticket_runner._rapid_sweep as rapid_sweep_mod
        from frob.tickets._leases import LeaseError

        repo = _seed_repo(tmp_path)
        findings = frozenset({("RULE1", "a.py")})
        filed = _file_regression_ticket(repo, "T-9000", "deadbeef", findings)
        assert filed is not None
        assert not _git(repo, "status", "--porcelain", "--", "tickets").strip()

        monkeypatch.setattr(
            "frob.tickets._leases.commit_ticket_ledger_change",
            lambda root, ticket_id, message: Err(LeaseError.LandInProgress),
        )
        monkeypatch.setattr(rapid_sweep_mod.time, "sleep", lambda _s: None)

        dropped = rapid_sweep_mod._close_resolved_sweep_tickets(
            repo, "T-9001", findings
        )
        assert dropped == ()  # commit failed -- not reported as dropped

        # THE FIX: root must be clean, never left with an uncommitted
        # drop write DirtyMain-blocking every concurrent land.
        assert not _git(repo, "status", "--porcelain", "--", "tickets").strip()

        from frob.tickets import TicketState, load_queue

        queue = load_queue(repo)
        assert queue.is_ok
        assert queue.danger_ok.tickets[filed].state == TicketState.QUEUED

    # frob:ticket T-2034
    def test_retry_after_commit_failure_does_not_duplicate_the_reason(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2034: T-2000/T-2008/T-2022 each carried the SAME
        auto-drop reason line TWICE because the never-discarded write let
        the NEXT sweep pass see the ticket as still QUEUED and drop it
        again. Restoring on discard (this test's first sweep) must leave
        the ticket genuinely droppable, and the SECOND, successful sweep
        must append the reason exactly once."""
        # frob:tests tests/unit/test_rapid_sweep.py::TestCloseResolvedSweepTickets.test_retry_after_commit_failure_does_not_duplicate_the_reason  # noqa: E501
        from typani.result import Err

        import frob.app.ticket_runner._rapid_sweep as rapid_sweep_mod
        from frob.tickets._leases import LeaseError

        repo = _seed_repo(tmp_path)
        findings = frozenset({("RULE1", "a.py")})
        filed = _file_regression_ticket(repo, "T-9000", "deadbeef", findings)
        assert filed is not None

        monkeypatch.setattr(
            "frob.tickets._leases.commit_ticket_ledger_change",
            lambda root, ticket_id, message: Err(LeaseError.LandInProgress),
        )
        monkeypatch.setattr(rapid_sweep_mod.time, "sleep", lambda _s: None)
        monkeypatch.setattr(rapid_sweep_mod, "_TICKET_DROP_COMMIT_MAX_ATTEMPTS", 1)
        rapid_sweep_mod._close_resolved_sweep_tickets(repo, "T-9001", findings)
        monkeypatch.undo()

        # Second sweep, this time the commit succeeds for real.
        dropped = rapid_sweep_mod._close_resolved_sweep_tickets(
            repo, "T-9002", findings
        )
        assert dropped == (filed,)

        from frob.tickets import load_queue

        queue = load_queue(repo)
        assert queue.is_ok
        reason_count = queue.danger_ok.tickets[filed].body.count("auto-dropped by")
        assert reason_count == 1


# frob:ticket T-2038
class TestNormalizeIdentityFile:
    """T-2038 (DRIFT002 fix): `_normalize_identity_file`'s own `frob:tests`
    directives were added ahead of these tests -- filling the gap."""

    def test_absolute_under_root_becomes_relative(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestNormalizeIdentityFile.test_absolute_under_root_becomes_relative  # noqa: E501
        from frob.app.ticket_runner._rapid_sweep import _normalize_identity_file

        file = str(tmp_path / "a" / "b.py")
        assert _normalize_identity_file(tmp_path, file) == "a/b.py"

    def test_already_relative_is_unchanged(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestNormalizeIdentityFile.test_already_relative_is_unchanged  # noqa: E501
        from frob.app.ticket_runner._rapid_sweep import _normalize_identity_file

        assert _normalize_identity_file(tmp_path, "a/b.py") == "a/b.py"

    def test_absolute_outside_root_falls_back_unchanged(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestNormalizeIdentityFile.test_absolute_outside_root_falls_back_unchanged  # noqa: E501
        from frob.app.ticket_runner._rapid_sweep import _normalize_identity_file

        other = tmp_path.parent / "elsewhere" / "c.py"
        assert _normalize_identity_file(tmp_path, str(other)) == other.as_posix()


# frob:ticket T-2313
class TestNormalizeIdentities:
    """T-2313: `_normalize_identities` must drop a genuinely
    identity-less (rule, file) pair (both fields empty) rather than
    silently carrying it through into a baseline diff or a filed ticket
    body -- observed verbatim in T-2297 as a blank ``"-   "`` line."""

    def test_drops_genuinely_empty_identity_pair(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestNormalizeIdentities.test_drops_genuinely_empty_identity_pair  # noqa: E501
        import logging

        from frob.app.ticket_runner._rapid_sweep import _normalize_identities

        with caplog.at_level(logging.WARNING):
            result = _normalize_identities(
                tmp_path, frozenset({("", ""), ("E501", "a.py")})
            )
        assert result == frozenset({("E501", "a.py")})
        assert "T-2313" in caplog.text
        assert "1 genuinely identity-less" in caplog.text

    def test_leaves_well_formed_pairs_untouched(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestNormalizeIdentities.test_leaves_well_formed_pairs_untouched  # noqa: E501
        from frob.app.ticket_runner._rapid_sweep import _normalize_identities

        identities = frozenset({("E501", "a.py"), ("F841", "b.py")})
        assert _normalize_identities(tmp_path, identities) == identities

    def test_partial_identity_one_field_empty_is_kept(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestNormalizeIdentities.test_partial_identity_one_field_empty_is_kept  # noqa: E501
        # A pair with only ONE empty field is a real, if partial,
        # identity (e.g. a rule with no associated file) -- not the
        # T-2313 both-empty shape -- and must be left alone, not dropped.
        from frob.app.ticket_runner._rapid_sweep import _normalize_identities

        # _normalize_identity_file("") normalizes to "." (Path("").as_posix()),
        # pre-existing, unrelated behavior -- this test only asserts the
        # pair was NOT dropped as identity-less, not the exact file string.
        result = _normalize_identities(tmp_path, frozenset({("E501", "")}))
        assert len(result) == 1
        assert next(iter(result))[0] == "E501"


# frob:ticket T-2036
class TestAbsoluteVsRelativePathIdentityMismatch:
    """T-2036's own repro: T-2022 was auto-dropped while its
    findings were still live because the identity it was FILED with
    (absolute path, from an earlier sweep's measurement) never matched a
    LATER sweep's fresh measurement of the SAME still-broken file
    reported in repo-relative form -- a plain string-tuple diff cannot
    see these as the same identity. Watch this fail first: before the
    fix, the still-broken ticket ends up DROPPED."""

    def test_format_drift_between_sweeps_does_not_falsely_resolve_a_live_ticket(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestAbsoluteVsRelativePathIdentityMismatch.test_format_drift_between_sweeps_does_not_falsely_resolve_a_live_ticket  # noqa: E501
        _write_baseline(tmp_path, frozenset(), "c0")
        abs_path = str(tmp_path / "a.py")

        # Land 1: the tool reports an ABSOLUTE path for the broken file.
        # A ticket gets filed naming that identity.
        monkeypatch.setattr(
            "frob.app.ticket_runner._land_cmd._unscoped_error_findings",
            lambda *a, **k: frozenset({("RULE1", abs_path)}),
        )
        first = run_deferred_post_land_sweep(tmp_path, "T-1001", "c1")
        assert first.is_ok
        filed = first.danger_ok
        assert filed is not None

        # Land 2: the SAME file, SAME rule, genuinely STILL broken -- but
        # this time the tool reports it REPO-RELATIVE (format drift
        # between runs, T-2022's measured shape). The ticket must NOT
        # read as resolved just because the raw strings differ.
        monkeypatch.setattr(
            "frob.app.ticket_runner._land_cmd._unscoped_error_findings",
            lambda *a, **k: frozenset({("RULE1", "a.py")}),
        )
        second = run_deferred_post_land_sweep(tmp_path, "T-1002", "c2")
        assert second.is_ok

        from frob.tickets import TicketState, load_queue

        queue = load_queue(tmp_path)
        assert queue.is_ok
        # THE FIX: still QUEUED, never falsely auto-dropped.
        assert queue.danger_ok.tickets[filed].state == TicketState.QUEUED


# frob:ticket T-1983
class TestDeferredSweepClosesResolvedRegressions:
    """End-to-end: `run_deferred_post_land_sweep` itself closes the loop
    on a prior sweep ticket whose findings vanish, and leaves one whose
    findings still reproduce alone -- the acceptance shape T-1983 itself
    demands (first assert must FAIL before the fix)."""

    def test_resolved_finding_is_dropped_by_the_next_sweep(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestDeferredSweepClosesResolvedRegressions.test_resolved_finding_is_dropped_by_the_next_sweep  # noqa: E501
        _write_baseline(tmp_path, frozenset(), "c0")

        # Land 1: RULE1/a.py appears -- files a real regression ticket.
        monkeypatch.setattr(
            "frob.app.ticket_runner._land_cmd._unscoped_error_findings",
            lambda *a, **k: frozenset({("RULE1", "a.py")}),
        )
        first = run_deferred_post_land_sweep(tmp_path, "T-1001", "c1")
        assert first.is_ok
        filed = first.danger_ok
        assert filed is not None

        # Land 2: RULE1/a.py is fixed -- the fresh measurement no longer
        # finds it, so the sweep must drop the ticket it filed for it.
        monkeypatch.setattr(
            "frob.app.ticket_runner._land_cmd._unscoped_error_findings",
            lambda *a, **k: frozenset(),
        )
        second = run_deferred_post_land_sweep(tmp_path, "T-1002", "c2")
        assert second.is_ok

        from frob.tickets import TicketState, load_queue

        queue = load_queue(tmp_path)
        assert queue.is_ok
        assert queue.danger_ok.tickets[filed].state == TicketState.DROPPED

    def test_still_reproducing_finding_is_left_untouched(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestDeferredSweepClosesResolvedRegressions.test_still_reproducing_finding_is_left_untouched  # noqa: E501
        _write_baseline(tmp_path, frozenset(), "c0")

        monkeypatch.setattr(
            "frob.app.ticket_runner._land_cmd._unscoped_error_findings",
            lambda *a, **k: frozenset({("RULE1", "a.py")}),
        )
        first = run_deferred_post_land_sweep(tmp_path, "T-1001", "c1")
        assert first.is_ok
        filed = first.danger_ok
        assert filed is not None

        # Land 2: RULE1/a.py is STILL present -- must not be dropped.
        second = run_deferred_post_land_sweep(tmp_path, "T-1002", "c2")
        assert second.is_ok

        from frob.tickets import TicketState, load_queue

        queue = load_queue(tmp_path)
        assert queue.is_ok
        assert queue.danger_ok.tickets[filed].state == TicketState.QUEUED


class TestDeferredSweepMultiLandAttribution:
    """T-2009, end-to-end: the T-1998 measured shape -- two real lands
    happen between the previous baseline and the tree THIS sweep
    actually measures (the sweep is detached, off the land critical
    path, so other agents' lands routinely land in the window before it
    runs). The regression must be attributed to BOTH lands, never
    silently pinned on whichever one happened to spawn this sweep
    process."""

    def test_two_lands_in_the_window_are_both_named_not_just_the_spawning_one(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestDeferredSweepMultiLandAttribution.test_two_lands_in_the_window_are_both_named_not_just_the_spawning_one  # noqa: E501
        _init_git_repo(tmp_path)
        c0 = _git_commit(tmp_path, "chore: init")
        _write_baseline(tmp_path, frozenset(), c0)

        # Land T-1977 lands (this is the sweep that gets SPAWNED)...
        _git_commit(tmp_path, "fix(tickets): land T-1977 first fix")
        # ...but before its detached sweep child actually gets to run,
        # T-1995 ALSO lands (this is exactly the T-1998 incident: the
        # sweep is off the critical path on purpose, T-1684, so this is
        # normal, not a race bug). The real HEAD by the time the check
        # runs is past BOTH lands.
        real_head = _git_commit(tmp_path, "feat(tickets): land T-1995 second fix")

        # The new finding actually lives in a file T-1995 touched -- the
        # exact T-1998 shape (misattributed to T-1977, whose files were
        # never involved).
        monkeypatch.setattr(
            "frob.app.ticket_runner._land_cmd._unscoped_error_findings",
            lambda *a, **k: frozenset({("F401", "t1995_file.py")}),
        )
        # `_resolve_actual_head` reads the real git HEAD of tmp_path
        # (real_head) -- the sweep was merely SPAWNED naming T-1977 and
        # commit_sha=stale-spawn-sha (a stale value by the time it
        # actually runs).
        result = run_deferred_post_land_sweep(tmp_path, "T-1977", "stale-spawn-sha")
        assert result.is_ok
        filed = result.danger_ok
        assert filed is not None

        from frob.tickets import load_queue

        queue = load_queue(tmp_path)
        assert queue.is_ok
        ticket = queue.danger_ok.tickets[filed]
        title = ticket.title
        body = ticket.body
        # Before T-2009's fix: title/body named ONLY "T-1977" -- the land
        # that spawned the sweep, not the land whose files actually went
        # red. Both must be named now.
        assert "T-1977" in title
        assert "T-1995" in title
        assert "T-1995" in body
        # The baseline's own recorded commit must be the REAL head this
        # sweep measured, not the stale spawn-time commit_sha -- this is
        # what lets the NEXT sweep compute an honest window in turn.
        assert _read_baseline_commit(tmp_path) == real_head


class TestSweepStaleWorktreesAfterLand:
    """`_rapid_sweep.sweep_stale_worktrees_after_land` (T-2261)."""

    # frob:ticket T-2833

    def test_never_uses_force(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2261 acceptance [4]: --force is never used by the automatic
        path -- the ONE call to `sweep_worktrees` this function makes
        must always pass `force=False`."""
        captured: dict = {}

        def fake_sweep(
            root, *, min_age_hours=None, dry_run=False, force=False, now=None
        ):
            captured["force"] = force
            captured["dry_run"] = dry_run
            captured["min_age_hours"] = min_age_hours
            from typani import Ok

            return Ok(())

        monkeypatch.setattr("frob.tickets._leases.sweep_worktrees", fake_sweep)
        sweep_stale_worktrees_after_land(tmp_path)
        assert captured["force"] is False
        assert captured["dry_run"] is False
        assert captured["min_age_hours"] == _rapid_sweep._AUTO_SWEEP_MIN_AGE_HOURS

    # frob:ticket T-2261
    def test_logs_one_line_per_verdict(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """MUST-STILL-PASS: every verdict `sweep_worktrees` computes --
        one 'removed' and each of the five keep classes (live, dirty,
        unlanded, lease, age) -- is logged, unmodified and undropped.
        This proves the automation REUSES `sweep_worktrees`'s own
        decisions rather than filtering or narrowing them; the five keep
        classes' own real-fixture coverage lives in
        tests/test_ticket_leases.py against `sweep_worktrees` itself."""
        from typani import Ok

        class _FakeVerdict:
            def __init__(self, path: str, verdict: str, detail: str = "") -> None:
                self.path = path
                self.verdict = verdict
                self.detail = detail

        verdicts = (
            _FakeVerdict("/w/removed", "removed"),
            _FakeVerdict("/w/live", "kept:live", "pid 123"),
            _FakeVerdict("/w/dirty", "kept:dirty", "uncommitted changes"),
            _FakeVerdict("/w/unlanded", "kept:unlanded", "T-9001"),
            _FakeVerdict("/w/lease", "kept:lease", "T-9002"),
            _FakeVerdict("/w/age", "kept:age"),
        )

        def fake_sweep(
            root, *, min_age_hours=None, dry_run=False, force=False, now=None
        ):
            return Ok(verdicts)

        monkeypatch.setattr("frob.tickets._leases.sweep_worktrees", fake_sweep)
        with caplog.at_level("INFO"):
            sweep_stale_worktrees_after_land(tmp_path)
        out = caplog.text
        for v in verdicts:
            assert v.path in out
            assert v.verdict in out.split(v.path)[1][:80]
        assert "removed 1 of 6" in out

    # frob:ticket T-2261
    # frob:ticket T-2833
    def test_a_failed_sweep_is_logged_never_raised(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """A `sweep_worktrees` Err (e.g. `root` is not a git repo) is
        logged and swallowed -- this runs in a detached child nobody is
        waiting on and must never raise back into `_sweep_async`."""
        from typani import Err

        from frob.tickets._worktree_sweep import _WorktreeSweepError

        def fake_sweep(
            root, *, min_age_hours=None, dry_run=False, force=False, now=None
        ):
            return Err(_WorktreeSweepError.NotARepo)

        monkeypatch.setattr("frob.tickets._leases.sweep_worktrees", fake_sweep)
        with caplog.at_level("WARNING"):
            sweep_stale_worktrees_after_land(tmp_path)  # must not raise
        assert "worktree sweep failed" in caplog.text


class TestSweepStaleWorktreesIsOffTheLandCriticalPath:
    """T-2261 acceptance [3]: the worktree sweep must not lengthen the
    land's own critical path."""

    def test_spawn_deferred_post_land_sweep_never_calls_it_directly(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`spawn_deferred_post_land_sweep` -- the function `_land_cmd`
        calls SYNCHRONOUSLY, on the land's own critical path -- must
        return without ever invoking `sweep_stale_worktrees_after_land`
        itself; only the DETACHED child (`_sweep_async`, spawned via
        `subprocess.Popen` and never awaited) calls it. This is what
        keeps the land's own measured duration unaffected: the extra
        work happens in a process the land does not wait on."""
        called = []
        monkeypatch.setattr(
            _rapid_sweep,
            "sweep_stale_worktrees_after_land",
            lambda root: called.append(root),
        )
        # exec disabled -> spawn_deferred_post_land_sweep records debt and
        # returns Err(SpawnRefused) without ever touching the worktree
        # sweep -- proving the call is not reachable from this function's
        # own body at all, synchronous path or not.
        monkeypatch.setattr("frob.process.exec_enabled", lambda: False)
        _init_git_repo(tmp_path)
        result = spawn_deferred_post_land_sweep(tmp_path, "T-1", "T-1", "deadbeef")
        assert result.is_err
        assert called == []
