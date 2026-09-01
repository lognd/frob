"""Rolling-baseline and CAS state tests for `frob.app.ticket_runner._rapid_sweep`
(T-3595 split of the former tests/unit/test_rapid_sweep.py)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

from frob.app.ticket_runner import _rapid_sweep
from frob.app.ticket_runner._rapid_sweep import (
    _baseline_write_survived,
    _files_deleted_between,
    _filter_phantom_deleted_findings,
    _identity_scoped_state_key,
    _land_ids_between,
    _read_baseline,
    _read_baseline_commit,
    _read_revalidation_cache,
    _resolve_actual_head,
    _tree_state_key,
    _write_baseline,
    _write_revalidation_cache,
    run_deferred_post_land_sweep,
)
from tests.conftest import (
    _git_commit,
    _init_git_repo,
)


class TestRollingBaseline:
    """The rolling baseline is what lets a deferred sweep cost ONE check
    instead of the two `standard` pays."""

    def test_absent_baseline_reads_as_none_not_empty(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_baseline.py::TestRollingBaseline.test_absent_baseline_reads_as_none_not_empty  # noqa: E501
        assert _read_baseline(tmp_path) is None

    def test_corrupt_baseline_reads_as_none_not_empty(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_baseline.py::TestRollingBaseline.test_corrupt_baseline_reads_as_none_not_empty  # noqa: E501
        path = tmp_path / ".frob" / "rapid-sweep-baseline.json"
        path.parent.mkdir(parents=True)
        path.write_text("{not json", encoding="utf-8")
        assert _read_baseline(tmp_path) is None

    def test_write_then_read_round_trips(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_baseline.py::TestRollingBaseline.test_write_then_read_round_trips  # noqa: E501
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
        # frob:tests tests/unit/rapid_sweep_suite/test_baseline.py::TestRollingBaseline.test_read_baseline_commit_absent_is_none  # noqa: E501
        assert _read_baseline_commit(tmp_path) is None

    def test_read_baseline_commit_round_trips(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_baseline.py::TestRollingBaseline.test_read_baseline_commit_round_trips  # noqa: E501
        _write_baseline(tmp_path, frozenset({("COV003", "a.py")}), "abc123")
        assert _read_baseline_commit(tmp_path) == "abc123"



class TestLandIdsBetween:
    """T-2009: the mechanical fix for misattribution -- tell how many
    lands (and which) actually landed in a commit range, instead of
    assuming it was always exactly the one that spawned this sweep."""

    def test_single_land_in_range(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_baseline.py::TestLandIdsBetween.test_single_land_in_range  # noqa: E501
        _init_git_repo(tmp_path)
        start = _git_commit(tmp_path, "chore: init")
        _git_commit(tmp_path, "fix(tickets): land T-1001 something")
        end = _git_commit(tmp_path, "chore(rapid): record T-1001's deferred sweep")
        assert _land_ids_between(tmp_path, start, end) == ["T-1001"]

    def test_multiple_lands_in_range_oldest_first(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_baseline.py::TestLandIdsBetween.test_multiple_lands_in_range_oldest_first  # noqa: E501
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
        # frob:tests tests/unit/rapid_sweep_suite/test_baseline.py::TestLandIdsBetween.test_non_land_commits_are_ignored  # noqa: E501
        _init_git_repo(tmp_path)
        start = _git_commit(tmp_path, "chore: init")
        _git_commit(tmp_path, "chore(tickets): file T-2000")
        _git_commit(tmp_path, "fix(tickets): land T-2001 real fix")
        end = _git_commit(tmp_path, "chore: unrelated housekeeping")
        assert _land_ids_between(tmp_path, start, end) == ["T-2001"]

    def test_non_repo_returns_empty_list(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_baseline.py::TestLandIdsBetween.test_non_repo_returns_empty_list  # noqa: E501
        # tmp_path is not a git repo -- degrade to [] rather than raise,
        # so a caller falls back to the pre-T-2009 single-attribution
        # behavior instead of crashing an otherwise-successful sweep.
        assert _land_ids_between(tmp_path, "abc", "def") == []


class TestResolveActualHead:
    def test_non_repo_falls_back_to_the_given_commit(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_baseline.py::TestResolveActualHead.test_non_repo_falls_back_to_the_given_commit  # noqa: E501
        assert _resolve_actual_head(tmp_path, "fallback-sha") == "fallback-sha"

    def test_real_repo_resolves_the_true_head(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_baseline.py::TestResolveActualHead.test_real_repo_resolves_the_true_head  # noqa: E501
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
        # frob:tests tests/unit/rapid_sweep_suite/test_baseline.py::TestFilesDeletedBetween.test_deleted_file_is_reported  # noqa: E501
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
        # frob:tests tests/unit/rapid_sweep_suite/test_baseline.py::TestFilesDeletedBetween.test_modified_only_file_is_not_reported  # noqa: E501
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
        # frob:tests tests/unit/rapid_sweep_suite/test_baseline.py::TestFilesDeletedBetween.test_non_repo_or_missing_since_returns_empty  # noqa: E501
        assert _files_deleted_between(tmp_path, None, "abc123") == frozenset()
        assert _files_deleted_between(tmp_path, "abc", "abc") == frozenset()
        assert _files_deleted_between(tmp_path, "abc", "def") == frozenset()

class TestFilterPhantomDeletedFindings:
    def test_deleted_file_finding_is_excluded(self) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_baseline.py::TestFilterPhantomDeletedFindings.test_deleted_file_finding_is_excluded  # noqa: E501
        fresh = frozenset({("TICK003", "tickets.md"), ("COV003", "a.py")})
        result = _filter_phantom_deleted_findings(
            "T-2571", fresh, frozenset({"tickets.md"})
        )
        assert result == frozenset({("COV003", "a.py")})

    def test_live_file_finding_is_kept(self) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_baseline.py::TestFilterPhantomDeletedFindings.test_live_file_finding_is_kept  # noqa: E501
        fresh = frozenset({("COV003", "a.py")})
        result = _filter_phantom_deleted_findings("T-2571", fresh, frozenset())
        assert result == fresh

    def test_no_deletions_is_a_noop(self) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_baseline.py::TestFilterPhantomDeletedFindings.test_no_deletions_is_a_noop  # noqa: E501
        fresh = frozenset({("COV003", "a.py"), ("DOC011", "b.md")})
        assert _filter_phantom_deleted_findings("T-2571", fresh, frozenset()) is fresh


class TestBaselineWriteSurvived:
    def test_matching_commit_survived(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_baseline.py::TestBaselineWriteSurvived.test_matching_commit_survived  # noqa: E501
        _write_baseline(tmp_path, frozenset({("COV003", "a.py")}), "abc123")
        assert _baseline_write_survived(tmp_path, "abc123") is True

    def test_mismatched_commit_did_not_survive(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_baseline.py::TestBaselineWriteSurvived.test_mismatched_commit_did_not_survive  # noqa: E501
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
        # frob:tests tests/unit/rapid_sweep_suite/test_baseline.py::TestDeferredSweepBaselineCasRace.test_a_sweep_computed_against_a_stale_tree_does_not_clobber_a_fresher_ones_baseline  # noqa: E501
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
        # frob:tests tests/unit/rapid_sweep_suite/test_baseline.py::TestBaselineLock.test_no_lock_primitive_refuses_loudly  # noqa: E501
        import frob.process._lock as _lock_mod
        from frob.app.ticket_runner._rapid_sweep import (
            BaselineLockUnavailable,
            _baseline_lock,
        )

        monkeypatch.setattr(_lock_mod, "fcntl", None)
        monkeypatch.setattr(_lock_mod, "msvcrt", None)
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
        # frob:tests tests/unit/rapid_sweep_suite/test_baseline.py::TestBaselineLock.test_windows_backend_serializes_two_concurrent_holders  # noqa: E501
        if sys.platform == "win32":
            pytest.skip(
                "POSIX-only: the fake backend below is real fcntl.flock under the hood (T-3244)"
            )
        import fcntl as _fcntl

        import frob.process._lock as _lock_mod
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

        monkeypatch.setattr(_lock_mod, "fcntl", None)
        monkeypatch.setattr(_lock_mod, "msvcrt", _FakeMsvcrt)

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
        if sys.platform == "win32":
            pytest.skip("POSIX-only (T-3244)")
        # frob:tests tests/unit/rapid_sweep_suite/test_baseline.py::TestBaselineLock.test_serializes_two_concurrent_holders  # noqa: E501
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
        # frob:tests tests/unit/rapid_sweep_suite/test_baseline.py::TestIsAncestor.test_true_when_older_is_ancestor  # noqa: E501
        from frob.app.ticket_runner._rapid_sweep import _is_ancestor

        _init_git_repo(tmp_path)
        older = _git_commit(tmp_path, "c1")
        newer = _git_commit(tmp_path, "c2")
        assert _is_ancestor(tmp_path, older, newer) is True

    def test_equal_commits_are_ancestors(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_baseline.py::TestIsAncestor.test_equal_commits_are_ancestors  # noqa: E501
        from frob.app.ticket_runner._rapid_sweep import _is_ancestor

        _init_git_repo(tmp_path)
        commit = _git_commit(tmp_path, "c1")
        assert _is_ancestor(tmp_path, commit, commit) is True

    def test_false_when_not_an_ancestor(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_baseline.py::TestIsAncestor.test_false_when_not_an_ancestor  # noqa: E501
        from frob.app.ticket_runner._rapid_sweep import _is_ancestor

        _init_git_repo(tmp_path)
        older = _git_commit(tmp_path, "c1")
        newer = _git_commit(tmp_path, "c2")
        # `newer` is NOT an ancestor of `older` -- the reverse direction.
        assert _is_ancestor(tmp_path, newer, older) is False

    def test_none_on_git_failure(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_baseline.py::TestIsAncestor.test_none_on_git_failure  # noqa: E501
        from frob.app.ticket_runner._rapid_sweep import _is_ancestor

        # tmp_path is not a git repo at all.
        assert _is_ancestor(tmp_path, "deadbeef" * 5, "beefdead" * 5) is None


# frob:ticket T-2595
class TestWriteBaselineCas:
    """T-2595's actual fix: `_write_baseline_cas` must never let a write
    computed from a STALE (older) view of the tree discard a baseline a
    concurrent sweep already wrote from a FRESHER one."""

    def test_writes_when_no_prior_baseline(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_baseline.py::TestWriteBaselineCas.test_writes_when_no_prior_baseline  # noqa: E501
        from frob.app.ticket_runner._rapid_sweep import _write_baseline_cas

        findings = frozenset({("COV003", "a.py")})
        assert _write_baseline_cas(tmp_path, findings, "deadbeef" * 5) is True
        assert _read_baseline(tmp_path) == findings

    def test_writes_when_prior_is_an_ancestor(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_baseline.py::TestWriteBaselineCas.test_writes_when_prior_is_an_ancestor  # noqa: E501
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
        # frob:tests tests/unit/rapid_sweep_suite/test_baseline.py::TestWriteBaselineCas.test_skips_when_prior_is_not_an_ancestor  # noqa: E501
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
        # frob:tests tests/unit/rapid_sweep_suite/test_baseline.py::TestWriteBaselineCas.test_writes_when_ancestry_is_unresolvable  # noqa: E501
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
        # frob:tests tests/unit/rapid_sweep_suite/test_baseline.py::TestPhantomDeletedPathNotFiledAsRegression.test_phantom_deleted_path_is_not_filed_first  # noqa: E501
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
        # frob:tests tests/unit/rapid_sweep_suite/test_baseline.py::TestTreeStateKey.test_non_repo_is_none  # noqa: E501
        assert _tree_state_key(tmp_path) is None

    # frob:ticket T-2089
    def test_real_repo_returns_a_key(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_baseline.py::TestTreeStateKey.test_real_repo_returns_a_key  # noqa: E501
        _init_git_repo(tmp_path)
        _git_commit(tmp_path, "chore: init")
        key = _tree_state_key(tmp_path)
        assert key is not None
        # Same tree state, called twice: identical key.
        assert _tree_state_key(tmp_path) == key

    # frob:ticket T-2089
    def test_dirty_tree_changes_the_key(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_baseline.py::TestTreeStateKey.test_dirty_tree_changes_the_key  # noqa: E501
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
        # frob:tests tests/unit/rapid_sweep_suite/test_baseline.py::TestIdentityScopedStateKey.test_unchanged_files_same_key_across_a_head_move  # noqa: E501
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
        # frob:tests tests/unit/rapid_sweep_suite/test_baseline.py::TestIdentityScopedStateKey.test_editing_a_named_file_changes_the_key  # noqa: E501
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
        # frob:tests tests/unit/rapid_sweep_suite/test_baseline.py::TestIdentityScopedStateKey.test_editing_an_unrelated_file_does_not_change_the_key  # noqa: E501
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
        # frob:tests tests/unit/rapid_sweep_suite/test_baseline.py::TestIdentityScopedStateKey.test_uncommitted_edit_to_a_named_file_changes_the_key  # noqa: E501
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
        # frob:tests tests/unit/rapid_sweep_suite/test_baseline.py::TestIdentityScopedStateKey.test_missing_file_has_a_stable_sentinel_digest  # noqa: E501
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
        # frob:tests tests/unit/rapid_sweep_suite/test_baseline.py::TestRevalidationCache.test_absent_cache_is_none  # noqa: E501
        assert _read_revalidation_cache(tmp_path, "key", frozenset()) is None

    # frob:ticket T-2089
    def test_corrupt_cache_is_none(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_baseline.py::TestRevalidationCache.test_corrupt_cache_is_none  # noqa: E501
        path = tmp_path / ".frob" / "doable-revalidation-cache.json"
        path.parent.mkdir(parents=True)
        path.write_text("{not json", encoding="utf-8")
        assert _read_revalidation_cache(tmp_path, "key", frozenset()) is None

    # frob:ticket T-2089
    def test_write_then_read_round_trips(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_baseline.py::TestRevalidationCache.test_write_then_read_round_trips  # noqa: E501
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
        # frob:tests tests/unit/rapid_sweep_suite/test_baseline.py::TestRevalidationCache.test_mismatched_tree_key_is_none  # noqa: E501
        pairs = frozenset({("COV003", "a.py")})
        _write_revalidation_cache(tmp_path, "key-a", pairs, pairs)
        assert _read_revalidation_cache(tmp_path, "key-b", pairs) is None

    # frob:ticket T-2089
    def test_mismatched_pairs_is_none(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_baseline.py::TestRevalidationCache.test_mismatched_pairs_is_none  # noqa: E501
        written = frozenset({("COV003", "a.py")})
        queried = frozenset({("COV003", "b.py")})
        _write_revalidation_cache(tmp_path, "key", written, written)
        assert _read_revalidation_cache(tmp_path, "key", queried) is None

    # frob:ticket T-2089
    def test_expired_ttl_is_none(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_baseline.py::TestRevalidationCache.test_expired_ttl_is_none  # noqa: E501
        pairs = frozenset({("COV003", "a.py")})
        _write_revalidation_cache(tmp_path, "key", pairs, pairs)
        path = tmp_path / ".frob" / "doable-revalidation-cache.json"
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["timestamp"] = 0.0  # far in the past -- well past the TTL
        path.write_text(json.dumps(raw), encoding="utf-8")
        assert _read_revalidation_cache(tmp_path, "key", pairs) is None
