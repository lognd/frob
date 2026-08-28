"""Ground-truth fixture suite for `scripts/fleet_status.py` (T-3157).

Four separate defects were found in this file in a single day
(2026-08-27): (a) `_FROB_CHECK_TOKEN_RE` never matched `python -m frob
check` (fixed T-3093), (b) the LAND LOCK line reported fd-open waiters as
holders (fixed T-3093), (c) a false LEAK against a live registered
worktree (fixed T-3128), (d) orphan forkserver counting applied no age
floor (fixed T-3139). Each got a reactive point-fix and, separately, unit
coverage in `tests/unit/test_coordinator_scripts.py` -- but the four kept
arriving one at a time anyway, because no single suite treated "does this
script's four core CLAIMS survive a constructed ground-truth scenario
shaped like the last incident" as one denominator.

This file is that denominator. One test class per claim fleet_status
makes about the host it is reporting on -- checks running, land lock
holder-vs-waiter, worktree lease liveness, orphaned forkservers -- each
with a MUST-FIRE case (the condition is real, fleet_status must report
it) and a MUST-STAY-QUIET case (a similar-looking condition that is NOT
the thing, fleet_status must not report it). All four defects are
reproduced here as fixtures that fail, verified by hand against the
parent commit predating each one's fix, exactly as fooled by the pre-fix
code. Defect (c)'s own parent commit is NOT its recorded land commit
(T-3128's land commit, dac790e6e, carries zero code -- its fix was
folded into sibling ticket T-3139's squash, 6f04de4c8, because the two
shared a worktree and landed sequentially); the true parent is
`6f04de4c8^`. See `TestWorktreeLeaseLeakClaim`'s own docstring, and the
separately-filed ticket for the land-proof misattribution this exposed.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from tests.unit import test_coordinator_scripts as _tcs
from tests.unit.conftest import _load_script

#: NO DUPLICATION: reuse `tests/unit/test_coordinator_scripts.py`'s own
#: fixture helpers (`_run_git`, `_init_bare_repo`, `_write_proc_locks`,
#: `TestOrphanedForkserverCount`'s writers) via a qualified module
#: reference rather than a second copy of any of them -- see each usage
#: site below (`_tcs.<name>`).
_init_repo = _tcs._init_bare_repo
_run_git = _tcs._run_git
_write_proc_locks = _tcs._write_proc_locks
_OrphanedForkserverFixtures = _tcs.TestOrphanedForkserverCount

fleet_status = _load_script("fleet_status")


class TestChecksRunningClaim:
    """Claim: "a `frob check` is currently running" -- backed by
    `_is_live_check_cmdline` (T-3093's fix for defect (a)).

    Defect (a) reproduced: the pre-fix regex `(?:^|/)frob\\x00` anchored
    only the WHOLE cmdline blob's start, so a bare `frob` token that is
    neither first nor preceded by `/` -- exactly `python -m frob check`'s
    own shape (`-m` precedes `frob`, not `/`) -- never matched, and two
    live `python -m frob check ...` launchers were reported as not
    running at all (T-3072's own Done report)."""

    def test_must_fire_on_python_dash_m_frob_check(self) -> None:
        """MUST-FIRE: `python -m frob check ...`, this fleet's own
        dominant invocation shape under `uv run`, is a live check. This is
        defect (a)'s exact repro shape -- at the parent commit predating
        T-3093 this assertion fails."""
        raw = b"python3\x00-m\x00frob\x00check\x00--only\x00gates\x00"
        assert fleet_status._is_live_check_cmdline(raw) is True

    def test_must_fire_on_venv_executable_path_form(self) -> None:
        """MUST-FIRE: the installed-console-script shape, `/x/.venv/bin/
        frob check` -- token ends `/frob`, not merely contains it."""
        raw = b"/home/x/.venv/bin/frob\x00check\x00"
        assert fleet_status._is_live_check_cmdline(raw) is True

    def test_must_stay_quiet_on_frob_as_a_substring(self) -> None:
        """MUST-STAY-QUIET: a process whose cmdline merely CONTAINS the
        text "frob" inside an unrelated token (e.g. a differently-named
        tool, or a path component) must never read as a live check --
        whole-token comparison, never substring/regex over the joined
        bytes."""
        raw = b"frobnicate-tool\x00check\x00"
        assert fleet_status._is_live_check_cmdline(raw) is False

    def test_must_stay_quiet_on_frob_without_check_subcommand(self) -> None:
        """MUST-STAY-QUIET: a live `frob` invocation that is NOT `check`
        (e.g. `frob ticket doable`) must not count as a running check."""
        raw = b"frob\x00ticket\x00doable\x00"
        assert fleet_status._is_live_check_cmdline(raw) is False


class TestLandLockHolderClaim:
    """Claim: "the land lock is held by pid=N" -- backed by
    `_true_flock_holder_pid` reading `/proc/locks` (T-3093's fix for
    defect (b)), NOT `land_lock_holder_pids`'s raw fd-open scan alone.

    Defect (b) reproduced: `land_lock_holder_pids` reports every pid with
    the lock file merely OPEN -- `_land_land`'s non-blocking flock poll
    loop means a WAITING process holds the file open for its whole
    polling window too, so three fd-open pids read as three simultaneous
    "holders" when it was one real holder plus two waiters."""

    def test_must_fire_the_true_holder_among_waiters(self, tmp_path: Path) -> None:
        """MUST-FIRE: one real flock holder (in `/proc/locks`) plus two
        fd-open waiters (no flock entry). The raw fd-open scan
        (`land_lock_holder_pids`) reports all three as "holders" -- this
        is defect (b)'s exact shape. `_true_flock_holder_pid`, reading
        `/proc/locks` directly, must report ONLY the real holder."""
        root = tmp_path / "repo"
        (root / ".frob").mkdir(parents=True)
        lock_path = root / ".frob" / "land.lock"
        lock_path.write_text("{}", encoding="utf-8")
        st = lock_path.stat()
        maj, minor = os.major(st.st_dev), os.minor(st.st_dev)

        proc = tmp_path / "proc"
        # pid 100: the real holder -- granted in /proc/locks AND (like
        # every land.lock holder) has the file fd-open too.
        _write_proc_locks(
            proc,
            [f"1: FLOCK  ADVISORY  WRITE 100 {maj:02x}:{minor:02x}:{st.st_ino} 0 EOF"],
        )
        # pids 100, 200, 300 all hold the fd open -- 100 is the real
        # holder, 200/300 are waiters (a non-blocking poll loop holds
        # the fd open for its whole waiting window without ever holding
        # the flock).
        for waiter_pid in (100, 200, 300):
            fd_dir = proc / str(waiter_pid) / "fd"
            fd_dir.mkdir(parents=True)
            (fd_dir / "7").symlink_to(lock_path)

        # The raw fd-open signal alone is ambiguous -- all three pids
        # look like holders from fd membership. This is exactly the
        # pre-fix behavior that misreported waiters as holders.
        fd_open_pids = fleet_status.land_lock_holder_pids(root, proc=proc)
        assert set(fd_open_pids) == {100, 200, 300}

        # The true-holder read disambiguates: only pid 100 actually
        # holds the flock.
        assert fleet_status._true_flock_holder_pid(lock_path, proc=proc) == (
            True,
            100,
        )

    def test_must_stay_quiet_when_only_waiters_hold_the_fd_open(
        self, tmp_path: Path
    ) -> None:
        """MUST-STAY-QUIET: fd-open pids exist (waiters), but NONE holds
        the flock (e.g. the real holder has just released it in the
        race window between the fd-scan and the /proc/locks read, or the
        polling loop has not yet acquired). `_true_flock_holder_pid` must
        report "no true holder", never promote a waiter to holder status
        just because it is the only fd-open candidate."""
        root = tmp_path / "repo"
        (root / ".frob").mkdir(parents=True)
        lock_path = root / ".frob" / "land.lock"
        lock_path.write_text("{}", encoding="utf-8")

        proc = tmp_path / "proc"
        _write_proc_locks(proc, [])  # nothing currently granted
        fd_dir = proc / "200" / "fd"
        fd_dir.mkdir(parents=True)
        (fd_dir / "7").symlink_to(lock_path)

        assert fleet_status.land_lock_holder_pids(root, proc=proc) == [200]
        assert fleet_status._true_flock_holder_pid(lock_path, proc=proc) == (
            True,
            None,
        )


class TestOrphanedForkserverAgeFloorClaim:
    """Claim: "N forkservers are orphaned (leaked, safe to reap)" --
    backed by `orphaned_forkserver_count` applying `_ORPHAN_AGE_FLOOR_S`
    (T-3139's fix for defect (d)).

    Defect (d) reproduced: `orphaned_forkserver_count` applied NO age
    floor at all while `reap_orphaned_forkservers` has always applied a
    300s `DEFAULT_ORPHAN_AGE_FLOOR_S` before ever SIGTERMing a candidate
    -- a forkserver spawned seconds ago by a live pytest-xdist worker (a
    legitimate `frob test` run, which structurally has no `frob check`
    ancestor by design) read as ORPHANED the instant it appeared, while
    `reap` correctly left it alone."""

    #: reuse `TestOrphanedForkserverCount`'s own fixture-writers rather
    #: than a second copy (NO DUPLICATION): `_write_entry` builds the
    #: `/proc/<pid>` forkserver-shaped entry (cmdline + age-derived
    #: `stat`), `_write_xdist_worker` builds the live xdist-worker parent.
    # frob:waive DUP001 reason="an alias binding to the canonical helper, not a second \
    # definition -- DUP's similarity scan resolves the alias back to the same source \
    # object it is bound to." permanent="true"
    _write_forkserver = staticmethod(_OrphanedForkserverFixtures._write_entry)
    # frob:waive DUP001 reason="an alias binding to the canonical helper, not a second \
    # definition -- DUP's similarity scan resolves the alias back to the same source \
    # object it is bound to." permanent="true"
    _write_live_xdist_worker = staticmethod(
        _OrphanedForkserverFixtures._write_xdist_worker
    )

    def test_must_fire_on_old_forkserver_with_no_check_ancestor(
        self, tmp_path: Path
    ) -> None:
        """MUST-FIRE: a forkserver well past `_ORPHAN_AGE_FLOOR_S` (300s),
        no live `frob check` anywhere in its ancestry -- a genuine leak,
        must be counted."""
        proc = tmp_path / "proc"
        proc.mkdir()
        self._write_live_xdist_worker(proc, 999, ppid=1)
        self._write_forkserver(
            proc,
            4242,
            cmdline=_OrphanedForkserverFixtures._FORKSERVER_CMDLINE,
            ppid=999,
            age_s=400.0,
        )
        assert fleet_status.orphaned_forkserver_count(proc) == 1

    def test_must_stay_quiet_on_young_forkserver_with_no_check_ancestor(
        self, tmp_path: Path
    ) -> None:
        """MUST-STAY-QUIET: defect (d)'s exact repro -- a forkserver
        spawned 10s ago (well under the 300s floor) by a live xdist
        worker, no `frob check` ancestor by design (it belongs to a
        `frob test` run, not a check). At the parent commit predating
        T-3139 this read as ORPHANED on sight; the fix must report it not
        orphaned until it clears the age floor."""
        proc = tmp_path / "proc"
        proc.mkdir()
        self._write_live_xdist_worker(proc, 999, ppid=1)
        self._write_forkserver(
            proc,
            4242,
            cmdline=_OrphanedForkserverFixtures._FORKSERVER_CMDLINE,
            ppid=999,
            age_s=10.0,
        )
        assert fleet_status.orphaned_forkserver_count(proc) == 0

    def test_age_floor_matches_reap_orphaned_forkservers_default(self) -> None:
        """Cross-check half of defect (d)'s fix: fleet_status's own
        duplicated floor must equal `frob.process._reap`'s canonical
        `DEFAULT_ORPHAN_AGE_FLOOR_S` -- the two tools disagreeing about
        the exact same processes at the exact same moment is what T-3139
        was filed from."""
        from frob.process._reap import DEFAULT_ORPHAN_AGE_FLOOR_S

        assert fleet_status._ORPHAN_AGE_FLOOR_S == DEFAULT_ORPHAN_AGE_FLOOR_S


class TestWorktreeLeaseLeakClaim:
    """Claim: "ticket T-<id>'s lease is leaked / not leaked" -- backed by
    `worktrees_touching_ticket`'s fallback scan, exercised over REAL git
    worktrees, not string fixtures.

    Defect (c) (T-3128, MEASURED 2026-08-27: a live registered worktree
    at `.claude/worktrees/t-3122` read as `[LEAK]`) has a LAND-PROOF
    misattribution of its own: T-3128's recorded land commit (dac790e6e)
    contains ONLY `CHANGELOG.md`/`changelog.d/T-3128.md`/`rapid-debt.
    jsonl` -- zero code. The actual fix (the `elif not _worktree_
    started_ticket_ids(path): matched = _worktree_matches_ticket_by_
    scope_only(...)` branch below) was folded into sibling ticket
    T-3139's squash commit (6f04de4c8) because the two tickets shared a
    worktree and landed sequentially -- filed separately as the
    misattribution defect itself (see this ticket's Done report). The
    TRUE parent commit predating T-3128's own fix is therefore
    `6f04de4c8^` (= `4da2a85c2`, the same commit `TestOrphanedForkserver
    AgeFloorClaim` already uses as T-3139's own parent -- both tickets'
    fixes landed together), not T-3128's own recorded land commit. The
    must-fire fixture below is verified BY HAND to fail at `4da2a85c2`
    and pass at HEAD -- a genuine, falsifiable T-3128 repro, not a
    substitution for an unreproducible one."""

    def test_must_fire_worktree_whose_start_transition_already_landed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """MUST-FIRE (defect (c) itself, T-3128): T-2740's start-
        transition commit is already ON `main` (as if landed via a
        sibling ticket's squash), so it can never appear in this
        worktree's `main..HEAD`. The worktree's OWN unlanded history
        holds only a genuine, scope-touching work commit -- no start-
        transition commit for ANY ticket at all
        (`_worktree_started_ticket_ids(path)` is empty), which is
        exactly T-3128's own `elif` discriminator branch, not T-2747's
        `if` branch (T-2747 only handles a worktree that DID start this
        exact ticket; T-3128 extended it to a worktree that started NO
        ticket at all). `worktrees_touching_ticket` must still report
        this worktree -- at `4da2a85c2` (T-3128's TRUE parent commit,
        `6f04de4c8^`; see this class's own docstring for why that is not
        T-3128's own recorded land commit) this assertion fails (empty
        list), verified by hand. Passes at HEAD."""
        repo = tmp_path / "repo"
        repo.mkdir()
        _init_repo(repo)
        src = repo / "src"
        src.mkdir()
        (src / "a.py").write_text("def existing():\n    pass\n")
        tdir = repo / "tickets" / "T-2740"
        tdir.mkdir(parents=True)
        (tdir / "ticket.md").write_text(
            "---\nid: T-2740\nstate: in-progress\nscope:\n- src/a.py\n---\n"
        )
        _run_git(["add", "-A"], repo)
        _run_git(
            ["commit", "-q", "-m", "chore(tickets): record T-2740 start transition"],
            repo,
        )

        worktrees_dir = tmp_path / "worktrees"
        worktrees_dir.mkdir()
        worktree = worktrees_dir / "waive-liveness"
        _run_git(["worktree", "add", "-q", "-b", "t-2740-wt", str(worktree)], repo)
        (worktree / "src" / "a.py").write_text(
            "def existing():\n    pass\n\n\ndef fix_applied():\n    return 1\n"
        )
        _run_git(["add", "-A"], worktree)
        _run_git(
            ["commit", "-q", "-m", "wt: real work on T-2740's own scope"], worktree
        )

        monkeypatch.setattr(fleet_status, "WORKTREES", worktrees_dir)
        assert fleet_status.worktrees_touching_ticket("T-2740", ["src/a.py"]) == [
            "waive-liveness"
        ], (
            "a worktree whose start-transition commit already landed to "
            "main must still be recognized via its scope-touching "
            "unlanded commit, never reported as a leaked lease"
        )

    def test_must_stay_quiet_abandoned_ticket_with_no_worktree_at_all(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """MUST-STAY-QUIET (positive control the fix must not regress):
        a ticket genuinely abandoned -- no worktree started it, no
        worktree touches its scope -- must still resolve to no hits,
        i.e. still read as a real leak. Trading a false LEAK for a false
        LIVE would be the more dangerous direction: a stranded lease
        would never get reclaimed."""
        repo = tmp_path / "repo"
        repo.mkdir()
        _init_repo(repo)
        src = repo / "src"
        src.mkdir()
        (src / "a.py").write_text("def existing():\n    pass\n")
        _run_git(["add", "-A"], repo)
        _run_git(["commit", "-q", "-m", "c1: existing()"], repo)

        worktrees_dir = tmp_path / "worktrees"
        worktrees_dir.mkdir()
        unrelated = worktrees_dir / "unrelated"
        _run_git(["worktree", "add", "-q", "-b", "unrelated", str(unrelated)], repo)
        (unrelated / "src" / "b.py").write_text("def other():\n    pass\n")
        _run_git(["add", "-A"], unrelated)
        _run_git(
            ["commit", "-q", "-m", "wt: unrelated work for a different ticket"],
            unrelated,
        )

        monkeypatch.setattr(fleet_status, "WORKTREES", worktrees_dir)
        assert fleet_status.worktrees_touching_ticket("T-9999", ["src/a.py"]) == []
