import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.unit.conftest import (
    _completed,  # noqa: F401 -- T-3596
    fleet_status,
)


class TestLandProcessRows:
    """`fleet_status.land_process_rows` (T-2180, T-2475)."""

    def test_parses_matching_rows_and_skips_others(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Rows whose argv contains `ticket land` are parsed into
        structured dicts (pid, etimes, cputime, argv); the header line
        and rows for unrelated commands are skipped. `proc` is an
        isolated empty tmp dir (T-2475: `_pid_has_land_argv_tokens`
        cannot re-confirm a pid it has no `/proc/<pid>/cmdline` for, so
        it returns `None` and the row is kept on the text pre-filter
        alone) -- never the real host `/proc`, which would make this
        test's verdict depend on whatever pid 100 happens to be on
        whatever machine runs it."""
        proc = tmp_path / "proc"
        proc.mkdir()
        stdout = (
            "    PID  ETIMES     TIME COMMAND\n"
            "    100     300    00:10 /venv/bin/python -m frob ticket land "
            "--ticket T-1234\n"
            "    200      50    00:00 vim some_file.py\n"
        )
        monkeypatch.setattr(subprocess, "run", lambda *a, **k: _completed(stdout))
        rows = fleet_status.land_process_rows(proc)
        assert len(rows) == 1
        assert rows[0]["pid"] == 100
        assert rows[0]["etimes"] == 300
        assert rows[0]["cputime"] == "00:10"
        assert "ticket land" in rows[0]["argv"]

    def test_failed_ps_returns_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A nonzero `ps` exit reads as no rows, never a raised error."""
        monkeypatch.setattr(
            subprocess, "run", lambda *a, **k: _completed("", returncode=1)
        )
        assert fleet_status.land_process_rows() == []

    # frob:ticket T-2475
    def test_watcher_pgrep_pattern_is_not_counted_as_a_land(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """T-2475's measured incident: a coordinator's own wait-loop
        shell running `pgrep -f "frob ticket land T-2408"` reads
        identically to a real land in `ps -eo args` TEXT (both contain
        the substring 'ticket land T-2408'), and was misreported as a
        live land (elapsed=306s, cpu=0s) after the real land had
        already finished. The watcher's `/proc/<pid>/cmdline` has
        `ticket`/`land` GLUED inside one single argv element (the
        quoted `-f` pattern), never as two separate elements -- this
        must be dropped, while a genuine land row (pid 101, `ticket`/
        `land` as separate argv elements) must survive alongside it."""
        proc = tmp_path / "proc"
        proc.mkdir()
        watcher = proc / "100"
        watcher.mkdir()
        (watcher / "cmdline").write_bytes(b"pgrep\x00-f\x00frob ticket land T-2408\x00")
        real_land = proc / "101"
        real_land.mkdir()
        (real_land / "cmdline").write_bytes(
            b"timeout\x00540\x00uv\x00run\x00frob\x00ticket\x00land\x00T-2408\x00"
            b"--worktree\x00/w\x00"
        )
        stdout = (
            "    PID  ETIMES     TIME COMMAND\n"
            "    100     306    00:00 bash -c pgrep -f frob ticket land T-2408\n"
            "    101     300    00:10 timeout 540 uv run frob ticket land "
            "T-2408 --worktree /w\n"
        )
        monkeypatch.setattr(subprocess, "run", lambda *a, **k: _completed(stdout))
        rows = fleet_status.land_process_rows(proc)
        assert [r["pid"] for r in rows] == [101]


class TestLandInvocations:
    """`fleet_status.land_invocations` (T-2180)."""

    def test_collapses_process_fan_out_by_ticket_id(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The ~4-row process fan-out for a single real land (bash
        wrapper, timeout, uv run, the python process -- T-1344's own
        measured shape) collapses to ONE invocation keyed on the ticket id
        parsed from argv, not a per-row count. `ps aux | grep -c "frob
        ticket land"` returns ~4 for this same input; this must return 1.
        T-2193: the ticket id is a POSITIONAL argument after `land`
        (`frob ticket land T-1234 --worktree ...`) -- there is no
        `--ticket` flag on this subcommand -- so this fixture uses the
        real argv shape, not a flag form that would never match a live
        land."""
        rows = [
            {
                "pid": 100,
                "etimes": 300,
                "cputime": "00:10",
                "argv": "bash -c timeout 540 uv run frob ticket land T-1234 --worktree /w",
            },
            {
                "pid": 101,
                "etimes": 298,
                "cputime": "00:05",
                "argv": "timeout 540 uv run frob ticket land T-1234 --worktree /w",
            },
            {
                "pid": 102,
                "etimes": 295,
                "cputime": "00:05",
                "argv": "uv run frob ticket land T-1234 --worktree /w",
            },
            {
                "pid": 103,
                "etimes": 290,
                "cputime": "04:30",
                "argv": "/venv/bin/python -m frob ticket land T-1234 --worktree /w",
            },
        ]
        monkeypatch.setattr(fleet_status, "land_process_rows", lambda: rows)
        invocations = fleet_status.land_invocations()
        assert len(invocations) == 1
        inv = invocations[0]
        assert inv["ticket_id"] == "T-1234"
        assert sorted(inv["pids"]) == [100, 101, 102, 103]
        # elapsed = MAX etimes across the group (the longest-lived row)
        assert inv["elapsed_s"] == 300
        # cpu = MAX parsed cpu time across the group (270s = 4:30)
        assert inv["cpu_s"] == 270

    # frob:ticket T-2193
    def test_must_pass_control_one_land_many_processes_reports_one(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2193's own must-pass control: a fixture representing exactly
        ONE real land as several processes (the measured live incident --
        13 rows for pid 2298926, its wrapper processes and sibling
        invocations, most at cpu=0s and one at cpu=67s) reports exactly
        ONE invocation. A test that only asserts 'some lands are
        reported' cannot distinguish working from inflated; this asserts
        the exact count."""
        rows = [
            {
                "pid": 2298899,
                "etimes": 90,
                "cputime": "00:00",
                "argv": "bash -c timeout 540 uv run frob ticket land T-9999 --worktree /w",
            },
            {
                "pid": 2298920,
                "etimes": 90,
                "cputime": "00:00",
                "argv": "timeout 540 uv run frob ticket land T-9999 --worktree /w",
            },
            {
                "pid": 2298926,
                "etimes": 90,
                "cputime": "01:07",
                "argv": "/venv/bin/python -m frob ticket land T-9999 --worktree /w",
            },
        ]
        monkeypatch.setattr(fleet_status, "land_process_rows", lambda: rows)
        invocations = fleet_status.land_invocations()
        assert len(invocations) == 1
        assert invocations[0]["ticket_id"] == "T-9999"
        assert invocations[0]["cpu_s"] == 67

    def test_rows_with_no_ticket_id_are_dropped_not_reported(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2193: a row whose argv parses no ticket id at all (a
        coordinator's own long-lived wait-loop shell whose command line
        merely CONTAINS the substring 'frob ticket land', measured for
        real at elapsed=101983s -- ~28 hours, plainly not a land) is
        DROPPED from `land_invocations` entirely, not reported as its own
        `ticket_id=None` invocation -- the earlier behavior still
        inflated `LANDS IN FLIGHT` by one per such row."""
        rows = [
            {
                "pid": 428763,
                "etimes": 101983,
                "cputime": "00:07",
                "argv": (
                    "/bin/bash -c until [ \"$(pgrep -f 'frob ticket land T-' "
                    '| wc -l)" -eq 0 ]; do sleep 15; done'
                ),
            },
        ]
        monkeypatch.setattr(fleet_status, "land_process_rows", lambda: rows)
        assert fleet_status.land_invocations() == []

    # frob:ticket T-2249
    def test_child_cpu_s_sums_live_descendants_not_tracked_rows(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Fold-in fix (not separately ticketed): a healthy land's own 4
        tracked rows can each read ~0 CPU while the real work happens in
        a CHILD process (e.g. `frob check`) neither `land_process_rows`
        nor its `cpu_s` ever sees. `child_cpu_s` must total that child's
        own CPU time, found by walking `_all_process_ppid_cpu`'s ppid
        links from the tracked pids -- summing descendants only, never
        double-counting the tracked pids themselves."""
        rows = [
            {
                "pid": 200,
                "etimes": 60,
                "cputime": "00:01",
                "argv": "uv run frob ticket land T-5555 --worktree /w",
            },
        ]
        monkeypatch.setattr(fleet_status, "land_process_rows", lambda: rows)
        monkeypatch.setattr(
            fleet_status,
            "_all_process_ppid_cpu",
            lambda: {
                200: (1, 1),  # the tracked land pid itself: ppid=1, 1s cpu
                201: (200, 45),  # child: frob check, 45s cpu
                202: (201, 5),  # grandchild spawned by frob check
            },
        )
        invocations = fleet_status.land_invocations()
        assert len(invocations) == 1
        assert invocations[0]["cpu_s"] == 1
        assert invocations[0]["child_cpu_s"] == 50


class TestDescendantCpuSeconds:
    """`fleet_status._descendant_cpu_seconds` (T-2249)."""

    def test_sums_only_live_descendants_not_the_root(self) -> None:
        """The root pid's own cpu-seconds are never included -- only
        pids reachable by following ppid links FROM the root."""
        table = {1: (0, 999), 100: (1, 3), 101: (100, 7), 200: (1, 4)}
        assert fleet_status._descendant_cpu_seconds([100], table) == 7
        # 200 is a sibling of 100 under pid 1, not a descendant of 100
        assert fleet_status._descendant_cpu_seconds([1], table) == 3 + 7 + 4

    def test_no_children_returns_zero(self) -> None:
        table = {100: (1, 5)}
        assert fleet_status._descendant_cpu_seconds([100], table) == 0


class TestLandLockHolderPids:
    """`fleet_status.land_lock_holder_pids` (T-2180)."""

    def test_finds_a_pid_holding_the_lock_open(self, tmp_path: Path) -> None:
        """A pid whose `fd` table contains a symlink resolving to
        `.frob/land.lock` is reported as a live holder -- the /proc-fd
        liveness check, not the recorded pid or the lock's file age."""
        root = tmp_path / "repo"
        (root / ".frob").mkdir(parents=True)
        lock_path = root / ".frob" / "land.lock"
        lock_path.write_text("{}", encoding="utf-8")

        proc = tmp_path / "proc"
        # pid 555 holds the lock open via fd 7
        fd_dir = proc / "555" / "fd"
        fd_dir.mkdir(parents=True)
        (fd_dir / "7").symlink_to(lock_path)
        # pid 999 holds an unrelated file open
        other_fd_dir = proc / "999" / "fd"
        other_fd_dir.mkdir(parents=True)
        (other_fd_dir / "3").symlink_to(root / ".frob" / "quarantine.json")

        assert fleet_status.land_lock_holder_pids(root, proc=proc) == [555]

    def test_no_live_holder_returns_empty(self, tmp_path: Path) -> None:
        """No pid's fd table points at the lock file: reported as no live
        holder, distinct from the lock file's own existence."""
        root = tmp_path / "repo"
        (root / ".frob").mkdir(parents=True)
        (root / ".frob" / "land.lock").write_text("{}", encoding="utf-8")

        proc = tmp_path / "proc"
        fd_dir = proc / "111" / "fd"
        fd_dir.mkdir(parents=True)
        (fd_dir / "1").symlink_to(root / ".frob" / "quarantine.json")

        assert fleet_status.land_lock_holder_pids(root, proc=proc) == []


# frob:ticket T-2691
class TestReadLandStatusMarker:
    """`fleet_status.read_land_status_marker` (T-2691): reads the
    `frob.tickets._land`-written land-status marker best-effort."""

    # frob:ticket T-2691
    def test_reads_a_written_marker(self, tmp_path: Path) -> None:
        (tmp_path / ".frob").mkdir(parents=True)
        (tmp_path / ".frob" / "land-status.json").write_text(
            '{"ticket_id": "T-2691", "phase": "running", "pid": 42}',
            encoding="utf-8",
        )
        marker = fleet_status.read_land_status_marker(tmp_path)
        assert marker == {"ticket_id": "T-2691", "phase": "running", "pid": 42}

    # frob:ticket T-2691
    def test_missing_marker_returns_none(self, tmp_path: Path) -> None:
        assert fleet_status.read_land_status_marker(tmp_path) is None

    # frob:ticket T-2691
    def test_unparseable_marker_returns_none(self, tmp_path: Path) -> None:
        (tmp_path / ".frob").mkdir(parents=True)
        (tmp_path / ".frob" / "land-status.json").write_text(
            "not json", encoding="utf-8"
        )
        assert fleet_status.read_land_status_marker(tmp_path) is None


# frob:ticket T-2691
class TestLandStatusMarkerLine:
    """`fleet_status._land_status_marker_line` (T-2691): the LANDS-section
    rendering of a land-status marker."""

    # frob:ticket T-2691
    def test_no_marker_renders_nothing(self) -> None:
        assert fleet_status._land_status_marker_line(None) is None

    # frob:ticket T-2691
    def test_marker_renders_phase_ticket_and_pid(self) -> None:
        marker = {"ticket_id": "T-2691", "phase": "waiting-for-lock", "pid": 42}
        line = fleet_status._land_status_marker_line(marker)
        assert line is not None
        assert "T-2691" in line
        assert "waiting-for-lock" in line
        assert "42" in line


class TestPrintLandStatus:
    """`fleet_status._print_land_status` (T-2180)."""

    def test_prints_invocations_and_live_lock_holder(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Each invocation prints its ticket id, pids, elapsed, and cpu
        time; a live lock holder prints its pid(s), never the recorded-pid
        or lock-age language."""
        monkeypatch.setattr(
            fleet_status,
            "land_invocations",
            lambda: [
                {
                    "ticket_id": "T-1234",
                    "pids": [100, 101],
                    "elapsed_s": 300,
                    "cpu_s": 270,
                }
            ],
        )
        monkeypatch.setattr(fleet_status, "land_lock_holder_pids", lambda root: [100])
        monkeypatch.setattr(
            fleet_status, "_true_flock_holder_pid", lambda lock_path: (True, 100)
        )
        monkeypatch.setattr(fleet_status, "host_load", lambda: (19.5, 10 * 1024 * 1024))
        monkeypatch.setattr(fleet_status, "leases", lambda: [{"ticket_id": "T-1"}])
        monkeypatch.setattr(fleet_status, "live_lease_count", lambda held: 1)
        fleet_status._print_land_status()
        out = capsys.readouterr().out
        assert "LANDS IN FLIGHT: 1" in out
        assert "T-1234" in out and "elapsed=300s" in out and "cpu=270s" in out
        assert "LAND LOCK: held by pid=100" in out
        assert "LOAD 19.5" in out and "MEM 10.0GB avail" in out
        assert "1 live lease(s) (1 total)" in out

    # frob:ticket T-2249
    def test_prints_child_cpu_when_nonzero_omits_when_zero(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Fold-in fix: an invocation with `child_cpu_s` > 0 prints the
        `(+Ns in children)` suffix; one with `child_cpu_s` == 0 (or the
        key entirely absent, matching a caller on an older shape) prints
        exactly as before -- never a spurious `(+0s in children)`."""
        monkeypatch.setattr(
            fleet_status,
            "land_invocations",
            lambda: [
                {
                    "ticket_id": "T-1111",
                    "pids": [10],
                    "elapsed_s": 60,
                    "cpu_s": 1,
                    "child_cpu_s": 45,
                },
                {
                    "ticket_id": "T-2222",
                    "pids": [20],
                    "elapsed_s": 60,
                    "cpu_s": 30,
                    "child_cpu_s": 0,
                },
            ],
        )
        monkeypatch.setattr(fleet_status, "land_lock_holder_pids", lambda root: [])
        monkeypatch.setattr(fleet_status, "host_load", lambda: None)
        monkeypatch.setattr(fleet_status, "swap_pressure", lambda: None)
        monkeypatch.setattr(fleet_status, "leases", lambda: [])
        monkeypatch.setattr(fleet_status, "live_lease_count", lambda held: 0)
        fleet_status._print_land_status()
        out = capsys.readouterr().out
        assert "T-1111" in out and "cpu=1s (+45s in children)" in out
        assert "T-2222" in out and "cpu=30s" in out
        assert "cpu=30s (+0s in children)" not in out

    def test_prints_no_live_holder_as_normal_resting_state_not_stale(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """A lock file that exists but has no live /proc-fd holder --
        the NORMAL resting state for an idle repo, since flock is
        kernel-released the instant its holder dies -- must never read
        as 'stale' (fold-in fix, not separately ticketed: this exact
        wording contributed to one retracted ticket claiming a stale
        lock deadlocked the fleet). Still names the real state (no live
        holder) and still warns against trusting the recorded pid or
        lock age -- it is a liveness fact, not silence. REPO is
        monkeypatched to a scratch directory so this test never touches
        the real repo's own `.frob/land.lock`."""
        fake_repo = tmp_path / "repo"
        (fake_repo / ".frob").mkdir(parents=True)
        (fake_repo / ".frob" / "land.lock").write_text("{}", encoding="utf-8")
        monkeypatch.setattr(fleet_status, "REPO", fake_repo)
        monkeypatch.setattr(fleet_status, "land_invocations", lambda: [])
        monkeypatch.setattr(fleet_status, "land_lock_holder_pids", lambda root: [])
        monkeypatch.setattr(fleet_status, "host_load", lambda: None)
        monkeypatch.setattr(fleet_status, "swap_pressure", lambda: None)
        monkeypatch.setattr(fleet_status, "orphaned_forkserver_count", lambda: None)
        monkeypatch.setattr(fleet_status, "concurrent_check_count", lambda: None)
        monkeypatch.setattr(
            fleet_status, "stale_forkserver_count", lambda **kwargs: None
        )
        monkeypatch.setattr(fleet_status, "forkserver_swap_held_kb", lambda: None)
        fleet_status._print_land_status()
        out = capsys.readouterr().out
        assert "LANDS IN FLIGHT: 0" in out
        # T-2517: "stale" is now a legitimate word in the (separate,
        # forkserver-specific) STALE FORKSERVERS line -- this test only
        # cares that the LAND LOCK line itself never uses it.
        land_lock_line = next(
            line for line in out.splitlines() if line.startswith("LAND LOCK")
        )
        assert "stale" not in land_lock_line.lower()
        assert "no live holder" in out.lower()
        assert "normal resting state" in out.lower()
        assert "LOAD: unknown" in out

    def test_distinguishes_true_holder_from_waiters(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # frob:tests tests/unit/coordinator_suite/test_fleet_land.py::TestPrintLandStatus.test_distinguishes_true_holder_from_waiters  # noqa: E501
        """T-3093 must-fire: one land running, two waiting -- the output
        must name the single true holder and count the waiters
        separately, never label all three "holder"."""
        monkeypatch.setattr(fleet_status, "land_invocations", lambda: [])
        monkeypatch.setattr(
            fleet_status, "land_lock_holder_pids", lambda root: [100, 200, 300]
        )
        monkeypatch.setattr(
            fleet_status, "_true_flock_holder_pid", lambda lock_path: (True, 100)
        )
        monkeypatch.setattr(fleet_status, "host_load", lambda: None)
        monkeypatch.setattr(fleet_status, "swap_pressure", lambda: None)
        monkeypatch.setattr(fleet_status, "leases", lambda: [])
        monkeypatch.setattr(fleet_status, "live_lease_count", lambda held: 0)
        monkeypatch.setattr(fleet_status, "orphaned_forkserver_count", lambda: None)
        monkeypatch.setattr(fleet_status, "concurrent_check_count", lambda: None)
        monkeypatch.setattr(
            fleet_status, "stale_forkserver_count", lambda **kwargs: None
        )
        monkeypatch.setattr(fleet_status, "forkserver_swap_held_kb", lambda: None)
        fleet_status._print_land_status()
        out = capsys.readouterr().out
        land_lock_line = next(
            line for line in out.splitlines() if line.startswith("LAND LOCK")
        )
        assert "held by pid=100" in land_lock_line
        assert "2 waiter(s)" in land_lock_line
        assert "200" in land_lock_line and "300" in land_lock_line

    def test_must_stay_quiet_single_holder_no_waiters_unchanged_meaning(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # frob:tests tests/unit/coordinator_suite/test_fleet_land.py::TestPrintLandStatus.test_must_stay_quiet_single_holder_no_waiters_unchanged_meaning  # noqa: E501
        """T-3093 must-stay-quiet: a single land, no waiters -- the
        output's MEANING is unchanged (still names pid=100 as the
        holder, no waiter count printed)."""
        monkeypatch.setattr(fleet_status, "land_invocations", lambda: [])
        monkeypatch.setattr(fleet_status, "land_lock_holder_pids", lambda root: [100])
        monkeypatch.setattr(
            fleet_status, "_true_flock_holder_pid", lambda lock_path: (True, 100)
        )
        monkeypatch.setattr(fleet_status, "host_load", lambda: None)
        monkeypatch.setattr(fleet_status, "swap_pressure", lambda: None)
        monkeypatch.setattr(fleet_status, "leases", lambda: [])
        monkeypatch.setattr(fleet_status, "live_lease_count", lambda held: 0)
        monkeypatch.setattr(fleet_status, "orphaned_forkserver_count", lambda: None)
        monkeypatch.setattr(fleet_status, "concurrent_check_count", lambda: None)
        monkeypatch.setattr(
            fleet_status, "stale_forkserver_count", lambda **kwargs: None
        )
        monkeypatch.setattr(fleet_status, "forkserver_swap_held_kb", lambda: None)
        fleet_status._print_land_status()
        out = capsys.readouterr().out
        land_lock_line = next(
            line for line in out.splitlines() if line.startswith("LAND LOCK")
        )
        assert "held by pid=100" in land_lock_line
        assert "waiter" not in land_lock_line.lower()

    def test_indeterminate_true_holder_says_so_not_a_confident_number(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # frob:tests tests/unit/coordinator_suite/test_fleet_land.py::TestPrintLandStatus.test_indeterminate_true_holder_says_so_not_a_confident_number  # noqa: E501
        """T-3093's own explicit requirement: when the true holder cannot
        be determined from /proc, say so -- never print the fd-open set
        under a "holder" label."""
        monkeypatch.setattr(fleet_status, "land_invocations", lambda: [])
        monkeypatch.setattr(
            fleet_status, "land_lock_holder_pids", lambda root: [100, 200]
        )
        monkeypatch.setattr(
            fleet_status, "_true_flock_holder_pid", lambda lock_path: (False, None)
        )
        monkeypatch.setattr(fleet_status, "host_load", lambda: None)
        monkeypatch.setattr(fleet_status, "swap_pressure", lambda: None)
        monkeypatch.setattr(fleet_status, "leases", lambda: [])
        monkeypatch.setattr(fleet_status, "live_lease_count", lambda held: 0)
        monkeypatch.setattr(fleet_status, "orphaned_forkserver_count", lambda: None)
        monkeypatch.setattr(fleet_status, "concurrent_check_count", lambda: None)
        monkeypatch.setattr(
            fleet_status, "stale_forkserver_count", lambda **kwargs: None
        )
        monkeypatch.setattr(fleet_status, "forkserver_swap_held_kb", lambda: None)
        fleet_status._print_land_status()
        out = capsys.readouterr().out
        land_lock_line = next(
            line for line in out.splitlines() if line.startswith("LAND LOCK")
        )
        assert "not determinable" in land_lock_line.lower()
        assert "held by pid=" not in land_lock_line

    # frob:ticket T-2222
    def test_guidance_line_uses_live_count_not_raw_count(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """T-2222 acceptance [2]: the concurrency guidance clause's own
        number is the LIVE count, never `len(leases())` -- 6 raw leases
        with only 4 live must print '4 live lease(s) (6 total)', not
        '6 lease(s)' (the measured incident: a coordinator held dispatch
        believing 6 leases meant 6 live agents)."""
        monkeypatch.setattr(fleet_status, "land_invocations", lambda: [])
        monkeypatch.setattr(fleet_status, "land_lock_holder_pids", lambda root: [])
        monkeypatch.setattr(fleet_status, "host_load", lambda: (1.0, 1024 * 1024))
        monkeypatch.setattr(
            fleet_status, "leases", lambda: [{"ticket_id": f"T-{i}"} for i in range(6)]
        )
        monkeypatch.setattr(fleet_status, "live_lease_count", lambda held: 4)
        fleet_status._print_land_status()
        out = capsys.readouterr().out
        assert "4 live lease(s) (6 total)" in out
        assert "6 lease(s) --" not in out

    # frob:ticket T-2443
    def test_orphaned_forkserver_count_printed_alongside_swap_guidance(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Acceptance [2]: orphaned forkservers present must show up in
        the same report as the swap-pressure guidance -- turning an
        unexplained '1 agent (SWAP ...)' clause into an actionable
        number."""
        monkeypatch.setattr(fleet_status, "land_invocations", lambda: [])
        monkeypatch.setattr(fleet_status, "land_lock_holder_pids", lambda root: [])
        monkeypatch.setattr(fleet_status, "host_load", lambda: (1.0, 1024 * 1024))
        monkeypatch.setattr(
            fleet_status, "swap_pressure", lambda: (2 * 1024 * 1024, 24 * 1024 * 1024)
        )
        monkeypatch.setattr(fleet_status, "leases", lambda: [])
        monkeypatch.setattr(fleet_status, "live_lease_count", lambda held: 0)
        monkeypatch.setattr(fleet_status, "orphaned_forkserver_count", lambda: 94)
        fleet_status._print_land_status()
        out = capsys.readouterr().out
        assert "ORPHANED FORKSERVERS: 94 do not have a live" in out

    # frob:ticket T-2443
    def test_zero_orphaned_forkservers_prints_zero_not_omitted(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """MUST-STILL-PASS: a clean host (0 orphans) prints the line as
        '0', never omits it -- the same 'absence of data vs. a real zero'
        distinction `swap_pressure`/`host_load` already enforce."""
        monkeypatch.setattr(fleet_status, "land_invocations", lambda: [])
        monkeypatch.setattr(fleet_status, "land_lock_holder_pids", lambda root: [])
        monkeypatch.setattr(fleet_status, "host_load", lambda: None)
        monkeypatch.setattr(fleet_status, "swap_pressure", lambda: None)
        monkeypatch.setattr(fleet_status, "orphaned_forkserver_count", lambda: 0)
        fleet_status._print_land_status()
        out = capsys.readouterr().out
        assert "ORPHANED FORKSERVERS: 0" in out


# frob:ticket T-3211
class TestFlockHoldersMatchingWin32Guard:
    """T-3211: `_flock_holders_matching` gained a `sys.platform == "win32"`
    guard purely so `ty --python-platform win32` can narrow past
    `os.major`/`os.minor` (POSIX-only per typeshed) -- this whole function
    is `/proc/locks`-only anyway, meaningless off Linux/POSIX. Confirms
    the guard's own behavior at both ends: win32 returns empty (never
    calls the POSIX-only os functions), and the ordinary POSIX path is
    unchanged."""

    def test_win32_platform_returns_empty_without_calling_os_major_minor(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """MUST-FIRE: on a win32 platform, the function must short-circuit
        to an empty set -- never reach `os.major`/`os.minor`, which would
        raise `AttributeError` on a real Windows interpreter."""
        # frob:tests \
        # tests/unit/coordinator_suite/test_fleet_land.py::TestFlockHoldersMatchingWin3\
        # 2Guard.test_win32_platform_returns_empty_without_calling_os_major_minor
        monkeypatch.setattr(fleet_status._sys, "platform", "win32")
        lock_stat = os.stat(__file__)
        result = fleet_status._flock_holders_matching(
            ["1: FLOCK  ADVISORY  WRITE 100 08:01:12345 0 EOF"], lock_stat
        )
        assert result == set()

    def test_posix_platform_still_matches_normally(self) -> None:
        """MUST-STAY-QUIET control: the win32 guard must not narrow the
        ordinary POSIX path -- a real matching /proc/locks line still
        resolves to the holder pid, exactly as before this ticket."""
        if sys.platform == "win32":
            pytest.skip("POSIX-only (T-3244)")
        # frob:tests \
        # tests/unit/coordinator_suite/test_fleet_land.py::TestFlockHoldersMatchingWin3\
        # 2Guard.test_posix_platform_still_matches_normally
        lock_stat = os.stat(__file__)
        maj, minor = os.major(lock_stat.st_dev), os.minor(lock_stat.st_dev)
        line = f"1: FLOCK  ADVISORY  WRITE 100 {maj:02x}:{minor:02x}:{lock_stat.st_ino} 0 EOF"
        result = fleet_status._flock_holders_matching([line], lock_stat)
        assert result == {100}


def _write_proc_locks(proc: Path, lines: list[str]) -> None:
    """Fake `<proc>/locks` (T-3093) -- `_true_flock_holder_pid` reads
    this exact path."""
    proc.mkdir(parents=True, exist_ok=True)
    (proc / "locks").write_text("\n".join(lines) + "\n", encoding="utf-8")


class TestTrueFlockHolderPid:
    """`fleet_status._true_flock_holder_pid` (T-3093): the true-holder-vs-
    waiter distinction, read from `/proc/locks` rather than fd-open
    membership."""

    def test_finds_the_true_holder(self, tmp_path: Path) -> None:
        if sys.platform == "win32":
            pytest.skip("POSIX-only (T-3244)")
        # frob:tests tests/unit/coordinator_suite/test_fleet_land.py::TestTrueFlockHolderPid.test_finds_the_true_holder  # noqa: E501
        lock_path = tmp_path / "land.lock"
        lock_path.write_text("{}", encoding="utf-8")
        st = lock_path.stat()
        maj, minor = os.major(st.st_dev), os.minor(st.st_dev)
        proc = tmp_path / "proc"
        _write_proc_locks(
            proc,
            [f"1: FLOCK  ADVISORY  WRITE 555 {maj:02x}:{minor:02x}:{st.st_ino} 0 EOF"],
        )
        assert fleet_status._true_flock_holder_pid(lock_path, proc=proc) == (
            True,
            555,
        )

    def test_ignores_a_lock_on_a_different_inode(self, tmp_path: Path) -> None:
        if sys.platform == "win32":
            pytest.skip("POSIX-only (T-3244)")
        # frob:tests tests/unit/coordinator_suite/test_fleet_land.py::TestTrueFlockHolderPid.test_ignores_a_lock_on_a_different_inode  # noqa: E501
        """A waiter that later acquires an UNRELATED file's lock must
        never be misread as this lock's holder."""
        lock_path = tmp_path / "land.lock"
        lock_path.write_text("{}", encoding="utf-8")
        st = lock_path.stat()
        maj, minor = os.major(st.st_dev), os.minor(st.st_dev)
        proc = tmp_path / "proc"
        _write_proc_locks(
            proc,
            [
                f"1: FLOCK  ADVISORY  WRITE 999 {maj:02x}:{minor:02x}:{st.st_ino + 1} 0 EOF"
            ],
        )
        assert fleet_status._true_flock_holder_pid(lock_path, proc=proc) == (
            True,
            None,
        )

    def test_unreadable_proc_locks_is_indeterminate(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/coordinator_suite/test_fleet_land.py::TestTrueFlockHolderPid.test_unreadable_proc_locks_is_indeterminate  # noqa: E501
        """T-3093's own explicit requirement: when `/proc/locks` cannot
        be read at all, this MUST say "not determinable", never guess a
        pid or silently claim "no holder"."""
        lock_path = tmp_path / "land.lock"
        lock_path.write_text("{}", encoding="utf-8")
        proc = tmp_path / "proc-does-not-exist"
        assert fleet_status._true_flock_holder_pid(lock_path, proc=proc) == (
            False,
            None,
        )

    def test_missing_lock_file_is_true_none(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/coordinator_suite/test_fleet_land.py::TestTrueFlockHolderPid.test_missing_lock_file_is_true_none  # noqa: E501
        proc = tmp_path / "proc"
        _write_proc_locks(proc, [])
        assert fleet_status._true_flock_holder_pid(
            tmp_path / "does-not-exist.lock", proc=proc
        ) == (True, None)
