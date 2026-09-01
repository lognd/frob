import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.unit.conftest import (
    fleet_status,
)


class TestLeaseClassification:
    """`fleet_status.lease_classification` / `live_lease_count` (T-2222)."""

    def _record(self, tmp_path: Path, **overrides: object) -> dict:
        worktree = tmp_path / "wt"
        worktree.mkdir(exist_ok=True)
        record: dict = {
            "ticket_id": "T-9001",
            "worktree": str(worktree),
            "scope": ["src/frob/**"],
            "branch": "t-9001",
            "recorded_at": datetime.now(UTC).isoformat(),
        }
        record.update(overrides)
        return record

    def test_live_lease_stays_live(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The must-still-pass control: a genuinely live lease (worktree
        exists, ticket in-progress on main, well within TTL) MUST STILL
        report 'live' -- a fix that marks everything reclaimable would
        satisfy every other test here and be catastrophic (T-2222
        acceptance [4])."""
        record = self._record(tmp_path)
        monkeypatch.setattr(
            fleet_status,
            "ticket_frontmatter_on_main",
            lambda tid: {"state": "in-progress", "scope": [], "blocked_by": []},
        )
        assert fleet_status.lease_classification(record) == "live"
        assert fleet_status.live_lease_count([record]) == 1

    def test_holder_dead_is_reclaimable(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Past TTL with no live process cwd'd into the worktree ->
        reclaimable (T-1382's own real shape: `holder-dead`)."""
        stale_recorded = (
            datetime.now(UTC).timestamp() - fleet_status._LEASE_TTL_SECONDS - 3600
        )
        record = self._record(
            tmp_path,
            recorded_at=datetime.fromtimestamp(stale_recorded, tz=UTC).isoformat(),
        )
        monkeypatch.setattr(
            fleet_status,
            "ticket_frontmatter_on_main",
            lambda tid: {"state": "in-progress", "scope": [], "blocked_by": []},
        )
        monkeypatch.setattr(
            fleet_status, "_scan_for_live_worktree_process", lambda path: None
        )
        assert fleet_status.lease_classification(record) == "reclaimable"
        assert fleet_status.live_lease_count([record]) == 0

    def test_ticket_terminal_is_reclaimable(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A ticket whose `main` state is `done`/`dropped` can never
        legitimately still hold a lease -- reclaimable regardless of TTL
        or worktree liveness."""
        record = self._record(tmp_path)
        monkeypatch.setattr(
            fleet_status,
            "ticket_frontmatter_on_main",
            lambda tid: {"state": "done", "scope": [], "blocked_by": []},
        )
        assert fleet_status.lease_classification(record) == "reclaimable"

    def test_path_gone_is_reclaimable(self, tmp_path: Path) -> None:
        """A recorded worktree path that no longer exists on disk at all
        is reclaimable -- the cheapest, most-common shape, checked first
        (no `ticket_frontmatter_on_main` call needed at all)."""
        record = {
            "ticket_id": "T-9002",
            "worktree": str(tmp_path / "gone"),
            "recorded_at": datetime.now(UTC).isoformat(),
        }
        assert fleet_status.lease_classification(record) == "reclaimable"

    def test_root_worktree_is_structurally_unreclaimable(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2222 acceptance [3]: a lease whose `worktree` resolves to
        THIS repo's own root reports `'root-resident'` -- derived from
        comparing the record's own `worktree` field against the resolved
        repo root (`REPO`), never a ticket-id allowlist (T-1686's real
        shape: 53 processes cwd'd into the shared root at once, which
        would otherwise read as 'live' forever). A root-resident lease
        does NOT count toward `live_lease_count` either -- it was never a
        real dispatched agent."""
        monkeypatch.setattr(fleet_status, "REPO", tmp_path)
        record = self._record(tmp_path, worktree=str(tmp_path))
        monkeypatch.setattr(
            fleet_status,
            "ticket_frontmatter_on_main",
            lambda tid: {"state": "in-progress", "scope": [], "blocked_by": []},
        )
        assert fleet_status.lease_classification(record) == "root-resident"
        assert fleet_status.live_lease_count([record]) == 0

    def test_classification_is_strictly_read_only(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2222 acceptance [5]: classifying a batch of leases (including
        reclaimable and root-resident ones) never releases, modifies, or
        deletes anything -- `Path.unlink` is monkeypatched to raise if
        called at all, and both classification calls must still complete
        without hitting it."""

        def _fail_if_called(self: Path) -> None:  # pragma: no cover - guard
            raise AssertionError(
                "lease_classification/live_lease_count must never delete "
                "or modify a lease file"
            )

        monkeypatch.setattr(Path, "unlink", _fail_if_called)
        monkeypatch.setattr(
            fleet_status,
            "ticket_frontmatter_on_main",
            lambda tid: {"state": "in-progress", "scope": [], "blocked_by": []},
        )
        monkeypatch.setattr(fleet_status, "REPO", tmp_path / "not-the-repo-root")
        live_record = self._record(tmp_path)
        gone_record = {
            "ticket_id": "T-9003",
            "worktree": str(tmp_path / "does-not-exist"),
            "recorded_at": datetime.now(UTC).isoformat(),
        }
        assert fleet_status.lease_classification(live_record) == "live"
        assert fleet_status.lease_classification(gone_record) == "reclaimable"
        assert fleet_status.live_lease_count([live_record, gone_record]) == 1


class TestHostLoad:
    """`fleet_status.host_load` (T-2180)."""

    def test_reads_loadavg_and_mem_available(self, tmp_path: Path) -> None:
        """Both values are read from their own structured /proc fields --
        `MemAvailable`, not `MemFree`, so a busy-but-healthy host with
        `MemFree` near 0 does not read as a false alarm."""
        proc = tmp_path / "proc"
        proc.mkdir()
        (proc / "loadavg").write_text("19.48 11.75 9.23 12/616 123\n", encoding="utf-8")
        (proc / "meminfo").write_text(
            "MemTotal:       24000000 kB\n"
            "MemFree:               0 kB\n"
            "MemAvailable:   10485760 kB\n",
            encoding="utf-8",
        )
        result = fleet_status.host_load(proc)
        assert result == (19.48, 10485760)

    def test_missing_proc_files_return_none(self, tmp_path: Path) -> None:
        """A `/proc` with neither file present (a sandboxed or non-Linux
        host) reads as unknown, never a fabricated zero load/plenty of
        memory."""
        proc = tmp_path / "proc"
        proc.mkdir()
        assert fleet_status.host_load(proc) is None


class TestSwapPressure:
    """`fleet_status.swap_pressure` (T-2249)."""

    def test_reads_swap_used_and_total(self, tmp_path: Path) -> None:
        """`swap_used_kb = SwapTotal - SwapFree`, matching `free`'s own
        arithmetic -- the measured incident's own numbers (24GB total,
        17GB free, so 6GB [6291456 kB rounded] used)."""
        proc = tmp_path / "proc"
        proc.mkdir()
        (proc / "meminfo").write_text(
            "MemTotal:       24000000 kB\n"
            "SwapTotal:      25165824 kB\n"
            "SwapFree:       17825792 kB\n",
            encoding="utf-8",
        )
        assert fleet_status.swap_pressure(proc) == (7340032, 25165824)

    def test_swap_total_zero_never_crashes_or_claims_pressure(
        self, tmp_path: Path
    ) -> None:
        """MUST-STILL-PASS: `SwapTotal: 0` (no swap configured, a real
        and common case) reads as `(0, 0)`, never a crash and never fed
        to `_swap_guidance` as pressure."""
        proc = tmp_path / "proc"
        proc.mkdir()
        (proc / "meminfo").write_text(
            "MemTotal:       24000000 kB\nSwapTotal:             0 kB\nSwapFree:              0 kB\n",
            encoding="utf-8",
        )
        assert fleet_status.swap_pressure(proc) == (0, 0)
        assert fleet_status._swap_guidance((0, 0)) == "3-4 agent concurrent"

    def test_missing_proc_file_returns_none(self, tmp_path: Path) -> None:
        """A `/proc` with no `meminfo` at all reads as unknown, never a
        fabricated zero (which `_swap_guidance` would otherwise be unable
        to distinguish from 'genuinely no swap in use')."""
        proc = tmp_path / "proc"
        proc.mkdir()
        assert fleet_status.swap_pressure(proc) is None


# frob:ticket T-2443
class TestOrphanedForkserverCount:
    """`fleet_status.orphaned_forkserver_count` (T-2443, ancestry-walk fix
    T-2818, age-floor fix T-3139)."""

    #: T-3139: `_write_entry`'s default age when a test does not care
    #: about the floor -- comfortably above `fleet_status._ORPHAN_AGE_
    #: FLOOR_S` (300s) so every pre-T-3139 test in this class keeps its
    #: original meaning without having to reason about age at all.
    _OLD_AGE_S = 3600.0

    @staticmethod
    def _write_proc_uptime(proc: Path, *, uptime_s: float = 10_000_000.0) -> None:
        proc.joinpath("uptime").write_text(f"{uptime_s} 0.0\n", encoding="utf-8")

    @classmethod
    def _write_entry(
        cls,
        proc: Path,
        pid: int,
        *,
        cmdline: bytes,
        ppid: int,
        age_s: float | None = None,
    ) -> None:
        """A `/proc/<pid>` forkserver-shaped entry, `age_s` old (default
        `_OLD_AGE_S`, comfortably past the T-3139 floor) -- `age_s=None`
        writes the original short `stat` line (unmeasurable age, matching
        `reap_orphaned_forkservers`'s own 'never a candidate' posture for
        that case, exercised by `test_unmeasurable_age_never_counted`)."""
        if sys.platform == "win32":
            pytest.skip("POSIX-only (T-3244)")
        if not (proc / "uptime").exists():
            cls._write_proc_uptime(proc)
        entry = proc / str(pid)
        entry.mkdir(parents=True)
        (entry / "cmdline").write_bytes(cmdline)
        if age_s is None:
            (entry / "stat").write_text(f"{pid} (python3) S {ppid} {pid} 0 0 -1 0\n")
            return
        clk_tck = os.sysconf("SC_CLK_TCK")
        uptime_s = float((proc / "uptime").read_text(encoding="utf-8").split()[0])
        starttime_ticks = int((uptime_s - age_s) * clk_tck)
        stat_fields = ["S", str(ppid), str(pid), "0", "0", "-1", "0"]
        stat_fields += ["0"] * 12  # pad up through nice/num_threads/itrealvalue
        stat_fields.append(str(starttime_ticks))  # fields[19] == starttime
        (entry / "stat").write_text(f"{pid} (python3) " + " ".join(stat_fields) + "\n")

    @staticmethod
    def _write_live_check(proc: Path, pid: int, *, ppid: int = 1) -> None:
        """A live `frob check` process at `pid` -- no forkserver cmdline,
        so it never enters `_forkserver_snapshot`, but it DOES enter
        `_live_check_pids` and `_all_process_ppids` (T-2818), which is all
        an ancestry test needs of it."""
        entry = proc / str(pid)
        entry.mkdir(parents=True)
        (entry / "cmdline").write_bytes(b"/x/.venv/bin/frob\x00check\x00")
        (entry / "stat").write_text(f"{pid} (frob) S {ppid} {pid} 0 0 -1 0\n")

    @staticmethod
    def _write_xdist_worker(proc: Path, pid: int, *, ppid: int) -> None:
        """A live pytest-xdist remote-exec worker -- T-3139's own MEASURED
        real-fleet shape: alive, no `frob` token anywhere in its cmdline,
        so it is never a `frob check` process, yet it is a perfectly
        legitimate parent for a forkserver a `frob test` run spawned."""
        entry = proc / str(pid)
        entry.mkdir(parents=True)
        (entry / "cmdline").write_bytes(
            b"/x/.venv/bin/python\x00-u\x00-c\x00"
            b"import sys;exec(eval(sys.stdin.readline()))\x00"
        )
        (entry / "stat").write_text(f"{pid} (python) S {ppid} {pid} 0 0 -1 0\n")

    _FORKSERVER_CMDLINE = (
        b"python3\x00-c\x00from multiprocessing.forkserver import main; main(...)\x00"
    )

    def test_counts_forkserver_reparented_to_init(self, tmp_path: Path) -> None:
        proc = tmp_path / "proc"
        proc.mkdir()
        self._write_entry(
            proc, 4242, cmdline=self._FORKSERVER_CMDLINE, ppid=1, age_s=self._OLD_AGE_S
        )
        assert fleet_status.orphaned_forkserver_count(proc) == 1

    def test_ignores_forkserver_with_live_parent(self, tmp_path: Path) -> None:
        """A forkserver whose immediate parent is a genuinely LIVE `frob
        check` process (T-2818: ancestry, not one-level ppid==1, is the
        fix's own required semantics) must not be counted orphaned."""
        proc = tmp_path / "proc"
        proc.mkdir()
        self._write_live_check(proc, 999)
        self._write_entry(
            proc,
            4242,
            cmdline=self._FORKSERVER_CMDLINE,
            ppid=999,
            age_s=self._OLD_AGE_S,
        )
        assert fleet_status.orphaned_forkserver_count(proc) == 0

    def test_ignores_non_forkserver_processes(self, tmp_path: Path) -> None:
        proc = tmp_path / "proc"
        proc.mkdir()
        self._write_entry(
            proc, 4242, cmdline=b"sleep\x00600\x00", ppid=1, age_s=self._OLD_AGE_S
        )
        assert fleet_status.orphaned_forkserver_count(proc) == 0

    def test_missing_proc_returns_none(self, tmp_path: Path) -> None:
        assert fleet_status.orphaned_forkserver_count(tmp_path / "no-proc") is None

    def test_two_level_chain_with_dead_root_is_orphaned(self, tmp_path: Path) -> None:
        """T-2818's own positive control, the case that failed before this
        fix: a forkserver (4242) whose parent is ANOTHER forkserver (5000)
        whose own originating check already died (reparented to init, no
        live check pid anywhere in the tree). The old one-level test read
        4242 as 'live-parented' because 5000 is alive; the ancestry walk
        must classify BOTH as orphaned."""
        proc = tmp_path / "proc"
        proc.mkdir()
        self._write_entry(
            proc, 5000, cmdline=self._FORKSERVER_CMDLINE, ppid=1, age_s=self._OLD_AGE_S
        )
        self._write_entry(
            proc,
            4242,
            cmdline=self._FORKSERVER_CMDLINE,
            ppid=5000,
            age_s=self._OLD_AGE_S,
        )
        assert fleet_status.orphaned_forkserver_count(proc) == 2

    def test_deep_chain_under_a_live_check_is_not_orphaned(
        self, tmp_path: Path
    ) -> None:
        """T-2818's other positive control, the one that matters most: a
        forkserver several hops below a genuinely RUNNING check must never
        read as orphaned, at any depth -- getting this wrong reaps live
        workers mid-check."""
        proc = tmp_path / "proc"
        proc.mkdir()
        self._write_live_check(proc, 6000)
        self._write_entry(
            proc,
            5000,
            cmdline=self._FORKSERVER_CMDLINE,
            ppid=6000,
            age_s=self._OLD_AGE_S,
        )
        self._write_entry(
            proc,
            4242,
            cmdline=self._FORKSERVER_CMDLINE,
            ppid=5000,
            age_s=self._OLD_AGE_S,
        )
        assert fleet_status.orphaned_forkserver_count(proc) == 0

    def test_zero_forkservers_reports_zero(self, tmp_path: Path) -> None:
        """MUST-STILL-PASS: no forkservers at all (even with other, live,
        non-forkserver processes present) reports a clean `0`, never an
        error or `None`."""
        proc = tmp_path / "proc"
        proc.mkdir()
        self._write_live_check(proc, 100)
        assert fleet_status.orphaned_forkserver_count(proc) == 0

    def test_unmeasurable_age_never_counted(self, tmp_path: Path) -> None:
        """T-3139: `stat` too short to derive `starttime` (age
        unmeasurable) must never be counted -- matches `reap_orphaned_
        forkservers`'s own `age_s is None -> continue` posture exactly
        (`_reap._reap_orphaned_pids`), the same conservative direction as
        every other 'cannot confirm' case in this module."""
        proc = tmp_path / "proc"
        proc.mkdir()
        self._write_entry(
            proc, 4242, cmdline=self._FORKSERVER_CMDLINE, ppid=1, age_s=None
        )
        assert fleet_status.orphaned_forkserver_count(proc) == 0

    # frob:ticket T-3139
    def test_young_forkserver_with_no_check_ancestor_is_not_orphaned(
        self, tmp_path: Path
    ) -> None:
        """MUST-STAY-QUIET, T-3139's own measured incident: a forkserver
        spawned SECONDS ago by a live pytest-xdist worker (a `frob test`
        run, not `frob check` -- structurally never has a `frob check`
        ancestor) must NOT be reported orphaned just because the ancestry
        walk finds no `frob check` pid. `frob ops process reap` already
        applies this same age floor before ever treating a forkserver as
        a reap candidate; this is the count this module reports
        disagreeing with that until now."""
        proc = tmp_path / "proc"
        proc.mkdir()
        xdist_ppid = 5555
        self._write_xdist_worker(proc, xdist_ppid, ppid=100)
        self._write_entry(
            proc,
            4242,
            cmdline=self._FORKSERVER_CMDLINE,
            ppid=xdist_ppid,
            age_s=5.0,
        )
        assert fleet_status.orphaned_forkserver_count(proc) == 0

    # frob:ticket T-3139
    def test_old_forkserver_with_no_check_ancestor_is_orphaned(
        self, tmp_path: Path
    ) -> None:
        """MUST-FIRE, the direction a floor-only fix could silently break:
        once a forkserver with no `frob check` ancestor has aged PAST the
        floor, it must still be reported orphaned -- the floor defers
        judgment, it does not grant permanent immunity."""
        proc = tmp_path / "proc"
        proc.mkdir()
        xdist_ppid = 5555
        self._write_xdist_worker(proc, xdist_ppid, ppid=100)
        self._write_entry(
            proc,
            4242,
            cmdline=self._FORKSERVER_CMDLINE,
            ppid=xdist_ppid,
            age_s=self._OLD_AGE_S,
        )
        assert fleet_status.orphaned_forkserver_count(proc) == 1


# frob:ticket T-3139
class TestOrphanedForkserverCountAgreesWithReap:
    """Cross-check (T-3139's own chosen agreement mechanism): `scripts/
    fleet_status.py::orphaned_forkserver_count` and `frob.process._reap.
    reap_orphaned_forkservers` are two independent copies of the same
    liveness rule (fleet_status cannot import the `frob` package -- see
    `_ORPHAN_AGE_FLOOR_S`'s own docstring) -- this class runs BOTH against
    the SAME constructed `/proc` tree and fails if they disagree about
    which pids are orphaned, the cheapest of the three options T-3139
    weighed and the one that would have caught this divergence itself."""

    @staticmethod
    def _write_xdist_worker(proc: Path, pid: int, *, ppid: int) -> None:
        entry = proc / str(pid)
        entry.mkdir(parents=True)
        (entry / "cmdline").write_bytes(
            b"/x/.venv/bin/python\x00-u\x00-c\x00"
            b"import sys;exec(eval(sys.stdin.readline()))\x00"
        )
        (entry / "stat").write_text(f"{pid} (python) S {ppid} {pid} 0 0 -1 0\n")

    @staticmethod
    def _write_forkserver(
        proc: Path, pid: int, *, ppid: int, age_s: float, uptime_s: float
    ) -> None:
        if sys.platform == "win32":
            pytest.skip("POSIX-only (T-3244)")
        clk_tck = os.sysconf("SC_CLK_TCK")
        starttime_ticks = int((uptime_s - age_s) * clk_tck)
        entry = proc / str(pid)
        entry.mkdir(parents=True)
        (entry / "cmdline").write_bytes(
            b"python3\x00-c\x00from multiprocessing.forkserver import main; main(...)\x00"
        )
        stat_fields = ["S", str(ppid), str(pid), "0", "0", "-1", "0"]
        stat_fields += ["0"] * 12
        stat_fields.append(str(starttime_ticks))
        entry.joinpath("stat").write_text(
            f"{pid} (python3) " + " ".join(stat_fields) + "\n"
        )
        # `_reap._process_start_age_s` derives age from the `<proc>/<pid>`
        # DIRECTORY's own mtime (a different, cheaper heuristic than
        # fleet_status's stat-starttime approach) -- backdate it so both
        # tools' independent age computations agree on this fixture.
        now = time.time()
        os.utime(entry, (now - age_s, now - age_s))

    def test_young_xdist_parented_forkserver_agrees(self, tmp_path: Path) -> None:
        """T-3139's exact measured shape: a forkserver, 5s old, parented
        by a live xdist worker. Neither tool may treat it as orphaned."""
        from frob.process import reap_orphaned_forkservers

        proc = tmp_path / "proc"
        proc.mkdir()
        uptime_s = 10_000_000.0
        proc.joinpath("uptime").write_text(f"{uptime_s} 0.0\n", encoding="utf-8")
        self._write_xdist_worker(proc, 5555, ppid=100)
        self._write_forkserver(proc, 4242, ppid=5555, age_s=5.0, uptime_s=uptime_s)

        fleet_status_count = fleet_status.orphaned_forkserver_count(proc)
        reaped = reap_orphaned_forkservers(proc=proc)

        assert fleet_status_count == 0, "fleet_status must not report this orphaned"
        assert reaped == [], "reap must not touch this pid"

    def test_old_no_ancestor_forkserver_agrees(self, tmp_path: Path) -> None:
        """The must-fire counterpart, same shared tree: a forkserver old
        enough to clear both tools' age floor, with no `frob check`
        anywhere in its ancestry, must be flagged as a reap CANDIDATE by
        both tools' own classification logic. Asserted at the classifier
        level (`_reap`'s own ancestry walk plus its age-floor comparison),
        not via `reap_orphaned_forkservers`'s actual `os.kill` -- the
        fixture pid is not a real OS process, so a real SIGTERM would
        raise `ProcessLookupError` regardless of classification and
        `reaped == []` would be true either way, proving nothing."""
        if sys.platform == "win32":
            pytest.skip("POSIX-only (T-3244)")
        from frob.process._reap import (
            DEFAULT_ORPHAN_AGE_FLOOR_S,
            _is_live_check_process,
            _process_start_age_s,
        )
        from frob.process._reap import (
            _all_process_ppids as reap_all_process_ppids,
        )
        from frob.process._reap import (
            _forkserver_root_is_live_check as reap_root_is_live_check,
        )

        proc = tmp_path / "proc"
        proc.mkdir()
        uptime_s = 10_000_000.0
        proc.joinpath("uptime").write_text(f"{uptime_s} 0.0\n", encoding="utf-8")
        self._write_forkserver(proc, 4242, ppid=1, age_s=3600.0, uptime_s=uptime_s)

        fleet_status_count = fleet_status.orphaned_forkserver_count(proc)
        assert fleet_status_count == 1

        reap_ppid_map = reap_all_process_ppids(proc)
        reap_live_check_pids = {
            pid for pid in reap_ppid_map if _is_live_check_process(pid, proc)
        }
        is_orphaned_per_reap = not reap_root_is_live_check(
            4242, reap_ppid_map, reap_live_check_pids
        )
        age_s = _process_start_age_s(4242, proc, uptime_s, os.sysconf("SC_CLK_TCK"))
        is_reap_candidate = (
            is_orphaned_per_reap
            and age_s is not None
            and age_s >= DEFAULT_ORPHAN_AGE_FLOOR_S
        )
        assert is_reap_candidate is True, (
            "reap's own classifier must independently agree this pid is a "
            "genuine orphan past the age floor, matching fleet_status's "
            "count of 1 above"
        )


# frob:ticket T-2517
class TestStaleForkserverCount:
    """`fleet_status.stale_forkserver_count` (T-2517): idle+aged, not
    ancestry-based -- the signal `orphaned_forkserver_count` cannot see
    for a forkserver whose creating agent shell is still alive."""

    @staticmethod
    def _write_proc(proc: Path, *, uptime_s: float) -> None:
        proc.mkdir()
        proc.joinpath("uptime").write_text(f"{uptime_s} 0.0\n", encoding="utf-8")

    @staticmethod
    def _write_forkserver(
        proc: Path, pid: int, *, age_s: float, ppid: int = 999
    ) -> None:
        if sys.platform == "win32":
            pytest.skip("POSIX-only (T-3244)")
        clk_tck = os.sysconf("SC_CLK_TCK")
        uptime_s = float(proc.joinpath("uptime").read_text(encoding="utf-8").split()[0])
        starttime_ticks = int((uptime_s - age_s) * clk_tck)
        entry = proc / str(pid)
        entry.mkdir(parents=True)
        (entry / "cmdline").write_bytes(
            b"python3\x00-c\x00from multiprocessing.forkserver import main; main(...)\x00"
        )
        stat_fields = ["S", str(ppid), str(pid), "0", "0", "-1", "0"]
        stat_fields += ["0"] * 12  # pad up through nice/num_threads/itrealvalue
        stat_fields.append(str(starttime_ticks))  # fields[19] == starttime
        (entry / "stat").write_text(f"{pid} (python3) " + " ".join(stat_fields) + "\n")

    def test_counts_old_forkserver_when_no_checks_running(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/coordinator_suite/test_fleet_host_load.py::TestStaleForkserverCount.test_counts_old_forkserver_when_no_checks_running  # noqa: E501
        proc = tmp_path / "proc"
        self._write_proc(proc, uptime_s=1_000_000.0)
        self._write_forkserver(proc, 4242, age_s=7200.0)  # 2h old
        assert fleet_status.stale_forkserver_count(proc, concurrent_checks=0) == 1

    def test_ignores_young_forkserver(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/coordinator_suite/test_fleet_host_load.py::TestStaleForkserverCount.test_ignores_young_forkserver  # noqa: E501
        proc = tmp_path / "proc"
        self._write_proc(proc, uptime_s=1_000_000.0)
        self._write_forkserver(proc, 4242, age_s=30.0)  # 30s old, still working
        assert fleet_status.stale_forkserver_count(proc, concurrent_checks=0) == 0

    def test_never_counts_anything_while_a_check_is_running(
        self, tmp_path: Path
    ) -> None:
        """T-2517's own explicit caution: a live-parented forkserver MAY
        belong to a check about to start. `concurrent_checks > 0` must
        zero the count even for a forkserver that is genuinely 2h old --
        this function never claims 'stale' while a check might be using
        the pool."""
        # frob:tests tests/unit/coordinator_suite/test_fleet_host_load.py::TestStaleForkserverCount.test_never_counts_anything_while_a_check_is_running  # noqa: E501
        proc = tmp_path / "proc"
        self._write_proc(proc, uptime_s=1_000_000.0)
        self._write_forkserver(proc, 4242, age_s=7200.0)
        assert fleet_status.stale_forkserver_count(proc, concurrent_checks=1) == 0

    def test_unknown_concurrent_checks_never_counts_anything(
        self, tmp_path: Path
    ) -> None:
        """`concurrent_checks is None` (unknown) must degrade to 0, the
        same conservative posture as a positive count -- never treated as
        'assume zero checks running'."""
        # frob:tests tests/unit/coordinator_suite/test_fleet_host_load.py::TestStaleForkserverCount.test_unknown_concurrent_checks_never_counts_anything  # noqa: E501
        proc = tmp_path / "proc"
        self._write_proc(proc, uptime_s=1_000_000.0)
        self._write_forkserver(proc, 4242, age_s=7200.0)
        assert fleet_status.stale_forkserver_count(proc, concurrent_checks=None) == 0

    def test_missing_proc_returns_none(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/coordinator_suite/test_fleet_host_load.py::TestStaleForkserverCount.test_missing_proc_returns_none  # noqa: E501
        assert (
            fleet_status.stale_forkserver_count(
                tmp_path / "no-proc", concurrent_checks=0
            )
            is None
        )


# frob:ticket T-2818
class TestDeriveForkserverStaleAfterS:
    """`fleet_status._derive_forkserver_stale_after_s` (T-2818): the age
    backstop threshold DERIVED from this repo's own recorded `frob check`
    timings, replacing a hardcoded constant -- the ticket's own explicit
    requirement, citing T-2715/`_TRUE_COUNT_BUDGET_S` as the precedent for
    why a frozen number silently stops tracking repo growth."""

    def test_derives_from_recorded_samples_with_headroom(self, tmp_path: Path) -> None:
        """Sums each group's own MAX sample (worst-case per stage) then
        applies the headroom multiplier -- two groups whose maxima are
        100s and 50s derive to (100 + 50) * headroom, floored only if that
        product is below the floor."""
        # frob:tests tests/unit/coordinator_suite/test_fleet_host_load.py::TestDeriveForkserverStaleAfterS.test_derives_from_recorded_samples_with_headroom  # noqa: E501
        (tmp_path / ".frob").mkdir()
        (tmp_path / ".frob" / "check-budget-timing-samples.json").write_text(
            json.dumps({"gates-fast": [10.0, 100.0, 40.0], "static": [50.0, 20.0]}),
            encoding="utf-8",
        )
        expected = (100.0 + 50.0) * fleet_status._FORKSERVER_STALE_AFTER_HEADROOM
        assert fleet_status._derive_forkserver_stale_after_s(tmp_path) == max(
            expected, fleet_status._FORKSERVER_STALE_AFTER_FLOOR_S
        )

    def test_missing_samples_file_falls_back(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/coordinator_suite/test_fleet_host_load.py::TestDeriveForkserverStaleAfterS.test_missing_samples_file_falls_back  # noqa: E501
        assert (
            fleet_status._derive_forkserver_stale_after_s(tmp_path)
            == fleet_status._FORKSERVER_STALE_AFTER_S_FALLBACK
        )

    def test_malformed_samples_file_falls_back(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/coordinator_suite/test_fleet_host_load.py::TestDeriveForkserverStaleAfterS.test_malformed_samples_file_falls_back  # noqa: E501
        (tmp_path / ".frob").mkdir()
        (tmp_path / ".frob" / "check-budget-timing-samples.json").write_text(
            "not json{{", encoding="utf-8"
        )
        assert (
            fleet_status._derive_forkserver_stale_after_s(tmp_path)
            == fleet_status._FORKSERVER_STALE_AFTER_S_FALLBACK
        )

    def test_thin_samples_never_derive_below_the_floor(self, tmp_path: Path) -> None:
        """A tiny recorded sample (a fresh repo with only a couple of
        quick runs logged) must never derive a threshold below
        `_FORKSERVER_STALE_AFTER_FLOOR_S`, which would risk flagging an
        in-progress check's own forkservers as stale."""
        # frob:tests tests/unit/coordinator_suite/test_fleet_host_load.py::TestDeriveForkserverStaleAfterS.test_thin_samples_never_derive_below_the_floor  # noqa: E501
        (tmp_path / ".frob").mkdir()
        (tmp_path / ".frob" / "check-budget-timing-samples.json").write_text(
            json.dumps({"lint": [0.5]}), encoding="utf-8"
        )
        assert (
            fleet_status._derive_forkserver_stale_after_s(tmp_path)
            == fleet_status._FORKSERVER_STALE_AFTER_FLOOR_S
        )


# frob:ticket T-2517
class TestForkserverSwapHeldKb:
    """`fleet_status.forkserver_swap_held_kb` (T-2517): summed VmSwap,
    never RSS -- a swapped-out process reports near-zero RSS while still
    holding real memory, the exact reading that hid the ticket's own
    12GB incident behind a clean-looking orphan count."""

    @staticmethod
    def _write_entry(
        proc: Path, pid: int, *, cmdline: bytes, vmswap_kb: int | None
    ) -> None:
        entry = proc / str(pid)
        entry.mkdir(parents=True)
        (entry / "cmdline").write_bytes(cmdline)
        (entry / "stat").write_text(f"{pid} (python3) S 999 {pid} 0 0 -1 0\n")
        if vmswap_kb is not None:
            (entry / "status").write_text(
                f"Name:\tpython3\nVmRSS:\t     100 kB\nVmSwap:\t{vmswap_kb} kB\n",
                encoding="utf-8",
            )

    def test_sums_vmswap_across_every_forkserver(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/coordinator_suite/test_fleet_host_load.py::TestForkserverSwapHeldKb.test_sums_vmswap_across_every_forkserver  # noqa: E501
        proc = tmp_path / "proc"
        proc.mkdir()
        fs_cmdline = b"python3\x00-c\x00from multiprocessing.forkserver import main; main(...)\x00"
        self._write_entry(proc, 100, cmdline=fs_cmdline, vmswap_kb=5000)
        self._write_entry(proc, 101, cmdline=fs_cmdline, vmswap_kb=7000)
        self._write_entry(proc, 102, cmdline=b"sleep\x00600\x00", vmswap_kb=9000)
        assert fleet_status.forkserver_swap_held_kb(proc) == 12000

    def test_missing_status_file_degrades_that_entry_to_zero_not_a_crash(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/coordinator_suite/test_fleet_host_load.py::TestForkserverSwapHeldKb.test_missing_status_file_degrades_that_entry_to_zero_not_a_crash  # noqa: E501
        proc = tmp_path / "proc"
        proc.mkdir()
        fs_cmdline = b"python3\x00-c\x00from multiprocessing.forkserver import main; main(...)\x00"
        self._write_entry(proc, 100, cmdline=fs_cmdline, vmswap_kb=None)
        self._write_entry(proc, 101, cmdline=fs_cmdline, vmswap_kb=3000)
        assert fleet_status.forkserver_swap_held_kb(proc) == 3000

    def test_missing_proc_returns_none(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/coordinator_suite/test_fleet_host_load.py::TestForkserverSwapHeldKb.test_missing_proc_returns_none  # noqa: E501
        assert fleet_status.forkserver_swap_held_kb(tmp_path / "no-proc") is None


# frob:ticket T-3407
class TestForkserverRssHeldKb:
    """`fleet_status.forkserver_rss_held_kb` (T-3407): summed VmRSS across
    every live forkserver -- the reading T-2517's swap-only measurement
    structurally could not produce, and the one the ticket's own
    incident (12.5GB RSS, 0 orphaned, 0 stale, 0 swap) needed."""

    @staticmethod
    def _write_entry(
        proc: Path, pid: int, *, cmdline: bytes, vmrss_kb: int | None
    ) -> None:
        entry = proc / str(pid)
        entry.mkdir(parents=True)
        (entry / "cmdline").write_bytes(cmdline)
        (entry / "stat").write_text(f"{pid} (python3) S 999 {pid} 0 0 -1 0\n")
        if vmrss_kb is not None:
            (entry / "status").write_text(
                f"Name:\tpython3\nVmRSS:\t{vmrss_kb} kB\nVmSwap:\t     0 kB\n",
                encoding="utf-8",
            )

    def test_sums_vmrss_across_every_forkserver(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/coordinator_suite/test_fleet_host_load.py::TestForkserverRssHeldKb.test_sums_vmrss_across_every_forkserver  # noqa: E501
        proc = tmp_path / "proc"
        proc.mkdir()
        fs_cmdline = b"python3\x00-c\x00from multiprocessing.forkserver import main; main(...)\x00"
        self._write_entry(proc, 100, cmdline=fs_cmdline, vmrss_kb=1_800_000)
        self._write_entry(proc, 101, cmdline=fs_cmdline, vmrss_kb=1_900_000)
        self._write_entry(proc, 102, cmdline=b"sleep\x00600\x00", vmrss_kb=500_000)
        assert fleet_status.forkserver_rss_held_kb(proc) == 3_700_000

    def test_missing_status_file_degrades_that_entry_to_zero_not_a_crash(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/coordinator_suite/test_fleet_host_load.py::TestForkserverRssHeldKb.test_missing_status_file_degrades_that_entry_to_zero_not_a_crash  # noqa: E501
        proc = tmp_path / "proc"
        proc.mkdir()
        fs_cmdline = b"python3\x00-c\x00from multiprocessing.forkserver import main; main(...)\x00"
        self._write_entry(proc, 100, cmdline=fs_cmdline, vmrss_kb=None)
        self._write_entry(proc, 101, cmdline=fs_cmdline, vmrss_kb=300_000)
        assert fleet_status.forkserver_rss_held_kb(proc) == 300_000

    def test_missing_proc_returns_none(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/coordinator_suite/test_fleet_host_load.py::TestForkserverRssHeldKb.test_missing_proc_returns_none  # noqa: E501
        assert fleet_status.forkserver_rss_held_kb(tmp_path / "no-proc") is None


# frob:ticket T-3407
class TestForkserverCount:
    """`fleet_status.forkserver_count` (T-3407): total live forkserver
    count -- the denominator `_forkserver_rss_headline` attributes
    aggregate RSS across."""

    def test_counts_every_live_forkserver(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/coordinator_suite/test_fleet_host_load.py::TestForkserverCount.test_counts_every_live_forkserver  # noqa: E501
        proc = tmp_path / "proc"
        proc.mkdir()
        fs_cmdline = b"python3\x00-c\x00from multiprocessing.forkserver import main; main(...)\x00"
        for pid in (100, 101, 102):
            entry = proc / str(pid)
            entry.mkdir()
            (entry / "cmdline").write_bytes(fs_cmdline)
            (entry / "stat").write_text(f"{pid} (python3) S 999 {pid} 0 0 -1 0\n")
        non_fs = proc / "200"
        non_fs.mkdir()
        (non_fs / "cmdline").write_bytes(b"sleep\x00600\x00")
        (non_fs / "stat").write_text("200 (sleep) S 999 200 0 0 -1 0\n")
        assert fleet_status.forkserver_count(proc) == 3

    def test_missing_proc_returns_none(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/coordinator_suite/test_fleet_host_load.py::TestForkserverCount.test_missing_proc_returns_none  # noqa: E501
        assert fleet_status.forkserver_count(tmp_path / "no-proc") is None


# frob:ticket T-3407
class TestForkserverRssHeadline:
    """`fleet_status._forkserver_rss_headline` (T-3407): the always-
    printed, LEADING line of the forkserver section -- T-3407's own
    root-cause fix (the aggregate must outrank, not merely join, the
    three reassuring orphan/stale/swap lines)."""

    def test_large_rss_produces_a_visible_warning(self) -> None:
        """MUST-FIRE: healthy, live-parented, non-swapping forkservers
        holding large RSS produce a visible warning (T-3407's own
        fixture)."""
        # frob:tests tests/unit/coordinator_suite/test_fleet_host_load.py::TestForkserverRssHeadline.test_large_rss_produces_a_visible_warning  # noqa: E501
        headline = fleet_status._forkserver_rss_headline(7, 13_107_200, 7)
        assert "WARNING" in headline
        assert "12.5GB" in headline
        assert "7 forkserver(s)" in headline
        assert "7 concurrent check(s)" in headline

    def test_small_rss_stays_quiet(self) -> None:
        """MUST-STAY-QUIET: a small number of forkservers on an idle host
        does not produce a warning (T-3407's own fixture) -- the real
        numbers are still reported, just without the alarm framing."""
        # frob:tests tests/unit/coordinator_suite/test_fleet_host_load.py::TestForkserverRssHeadline.test_small_rss_stays_quiet  # noqa: E501
        headline = fleet_status._forkserver_rss_headline(1, 200_000, 0)
        assert "WARNING" not in headline
        assert "1 forkserver(s)" in headline
        assert "0 concurrent check(s)" in headline

    def test_unknown_inputs_degrade_to_unknown_not_zero(self) -> None:
        """MUST-STILL-PASS: an unreadable `/proc` must read as 'unknown',
        never a clean 0 -- matching every other best-effort line in this
        module."""
        # frob:tests tests/unit/coordinator_suite/test_fleet_host_load.py::TestForkserverRssHeadline.test_unknown_inputs_degrade_to_unknown_not_zero  # noqa: E501
        assert fleet_status._forkserver_rss_headline(None, 100, 1) == (
            "FORKSERVER RSS: unknown (/proc unreadable)"
        )
        assert fleet_status._forkserver_rss_headline(1, None, 1) == (
            "FORKSERVER RSS: unknown (/proc unreadable)"
        )


# frob:ticket T-2818
class TestForkserverContradictionLine:
    """`fleet_status._forkserver_contradiction_line` (T-2818): the loud
    refusal to let '0 orphaned + 0 stale' sit next to multi-gigabyte
    forkserver swap without comment -- the exact combination that hid a
    92-forkserver leak for 45 minutes."""

    def test_fires_on_zero_zero_high_swap(self) -> None:
        # frob:tests tests/unit/coordinator_suite/test_fleet_host_load.py::TestForkserverContradictionLine.test_fires_on_zero_zero_high_swap  # noqa: E501
        line = fleet_status._forkserver_contradiction_line(0, 0, 14 * 1024 * 1024)
        assert line is not None
        assert "CONTRADICTION" in line

    def test_silent_when_swap_below_pressure_floor(self) -> None:
        """MUST-STILL-PASS: 0/0 next to a few MB of ordinary idle swap
        (not the multi-gigabyte incident shape) must never fire -- this is
        not "any swap at all", matching `_SWAP_PRESSURE_FLOOR_KB`'s own
        contract."""
        # frob:tests tests/unit/coordinator_suite/test_fleet_host_load.py::TestForkserverContradictionLine.test_silent_when_swap_below_pressure_floor  # noqa: E501
        assert fleet_status._forkserver_contradiction_line(0, 0, 1024) is None

    def test_silent_when_orphaned_or_stale_nonzero(self) -> None:
        """A nonzero orphaned/stale reading already explains the swap --
        no contradiction to surface."""
        # frob:tests tests/unit/coordinator_suite/test_fleet_host_load.py::TestForkserverContradictionLine.test_silent_when_orphaned_or_stale_nonzero  # noqa: E501
        assert (
            fleet_status._forkserver_contradiction_line(3, 0, 14 * 1024 * 1024) is None
        )
        assert (
            fleet_status._forkserver_contradiction_line(0, 3, 14 * 1024 * 1024) is None
        )

    def test_silent_on_any_unknown_input(self) -> None:
        """MUST-STILL-PASS: a contradiction claim needs all three readings
        to be real -- any `None` (unknown) input suppresses it rather than
        guessing."""
        # frob:tests tests/unit/coordinator_suite/test_fleet_host_load.py::TestForkserverContradictionLine.test_silent_on_any_unknown_input  # noqa: E501
        assert (
            fleet_status._forkserver_contradiction_line(None, 0, 14 * 1024 * 1024)
            is None
        )
        assert (
            fleet_status._forkserver_contradiction_line(0, None, 14 * 1024 * 1024)
            is None
        )
        assert fleet_status._forkserver_contradiction_line(0, 0, None) is None


# frob:ticket T-2473
class TestConcurrentCheckCount:
    """`fleet_status.concurrent_check_count` (T-2473)."""

    @staticmethod
    def _write_entry(proc: Path, pid: int, *, cmdline: bytes) -> None:
        entry = proc / str(pid)
        entry.mkdir(parents=True)
        (entry / "cmdline").write_bytes(cmdline)

    def test_counts_check_processes(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/coordinator_suite/test_fleet_host_load.py::TestConcurrentCheckCount.test_counts_check_processes  # noqa: E501
        proc = tmp_path / "proc"
        proc.mkdir()
        self._write_entry(proc, 100, cmdline=b"frob\x00check\x00")
        self._write_entry(
            proc, 101, cmdline=b"/x/.venv/bin/frob\x00check\x00--json\x00"
        )
        assert fleet_status.concurrent_check_count(proc) == 2

    def test_ignores_non_check_processes(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/coordinator_suite/test_fleet_host_load.py::TestConcurrentCheckCount.test_ignores_non_check_processes  # noqa: E501
        proc = tmp_path / "proc"
        proc.mkdir()
        self._write_entry(proc, 200, cmdline=b"frob\x00ticket\x00land\x00")
        self._write_entry(proc, 201, cmdline=b"frob\x00checkpointer\x00")
        assert fleet_status.concurrent_check_count(proc) == 0

    def test_missing_proc_returns_none(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/coordinator_suite/test_fleet_host_load.py::TestConcurrentCheckCount.test_missing_proc_returns_none  # noqa: E501
        assert fleet_status.concurrent_check_count(tmp_path / "no-proc") is None

    def test_counts_module_invoked_check(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/coordinator_suite/test_fleet_host_load.py::TestConcurrentCheckCount.test_counts_module_invoked_check  # noqa: E501
        """T-3093 regression: `python -m frob check ...` -- the fleet's
        own dominant invocation shape under `uv run` -- must count, not
        silently vanish. The anchor-bugged regex this replaced
        (`re.compile(rb"(?:^|/)frob\\x00")`) never matched a bare `frob`
        token that is neither the first token nor preceded by `/`."""
        proc = tmp_path / "proc"
        proc.mkdir()
        self._write_entry(
            proc,
            100,
            cmdline=(
                b"/x/.venv/bin/python\x00-m\x00frob\x00check\x00--json\x00"
                b"--budget\x00300\x00"
            ),
        )
        assert fleet_status.concurrent_check_count(proc) == 1


class TestIsLiveCheckCmdline:
    """`fleet_status._is_live_check_cmdline` (T-3093)."""

    def test_does_not_match_check_repro_subcommand(self) -> None:
        # frob:tests tests/unit/coordinator_suite/test_fleet_host_load.py::TestIsLiveCheckCmdline.test_does_not_match_check_repro_subcommand  # noqa: E501
        """Must not fire on a DIFFERENT ticket subcommand that merely
        contains the substring 'check' -- token equality, never a
        substring match."""
        assert (
            fleet_status._is_live_check_cmdline(
                b"frob\x00ticket\x00check-repro\x00T-1\x00"
            )
            is False
        )


class TestSwapGuidance:
    """`fleet_status._swap_guidance` (T-2249)."""

    def test_swap_above_floor_overrides_the_static_guidance(self) -> None:
        """(MUST FAIL FIRST, pre-fix) Swap usage at/above
        `_SWAP_PRESSURE_FLOOR_KB` (1GB) replaces the static '3-4 agent'
        text with the real pressure, using the measured incident's own
        6GB figure."""
        guidance = fleet_status._swap_guidance((6 * 1024 * 1024, 24 * 1024 * 1024))
        assert "3-4 agent" not in guidance
        assert "SWAP" in guidance
        assert "6.0GB" in guidance

    def test_swap_below_floor_keeps_the_static_guidance(self) -> None:
        """A few MB of swap (well under the 1GB floor, the ticket's own
        'not any swap at all' caution) must NOT trip the pressure
        guidance -- a machine legitimately using a little swap is not
        automatically over-committed."""
        guidance = fleet_status._swap_guidance((10 * 1024, 24 * 1024 * 1024))
        assert guidance == "3-4 agent concurrent"

    def test_unknown_swap_keeps_the_static_guidance(self) -> None:
        """`swap is None` (unreadable /proc) must never be read as
        'pressure' -- pressure is only ever claimed from a real reading,
        same posture as `host_load` returning `None`."""
        assert fleet_status._swap_guidance(None) == "3-4 agent concurrent"
