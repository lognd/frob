"""T-1433: unit coverage for `tests/conftest.py`'s `SIGUSR1` stack-dump
handler -- the between-tests/session-teardown wedge diagnostic the two
`make coverage` incidents actually needed (pytest's own per-test
`--timeout` watchdog cannot reach that state; see T-1433's ticket body)."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
from pathlib import Path

import pytest

from tests.unit._conftest_test_helpers import _CONFTEST_PATH, load_conftest_module

if sys.platform == "win32":  # pragma: no cover - POSIX-only feature
    pytest.skip("SIGUSR1 is POSIX-only", allow_module_level=True)


def _load_conftest():
    """T-3252: thin wrapper over the shared `load_conftest_module` helper
    (DUP001 consolidation) -- keeps this file's own call sites (`_load_
    conftest()`) unchanged."""
    return load_conftest_module("_t1433_conftest_under_test")


class TestStackdumpHandler:
    """T-1433: `_install_stackdump_handler`/`_dump_all_thread_stacks`."""

    # frob:tests \
    # tests/unit/test_conftest_stackdump.py::TestStackdumpHandler.test_sigusr1_writes_a\
    # ll_thread_stacks_when_enabled
    def test_sigusr1_writes_all_thread_stacks_when_enabled(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """With `FROB_COVERAGE_STACKDUMP=1` set, installing the handler and
        then raising `SIGUSR1` in-process writes a `.frob/stackdumps/
        pid-<pid>.txt` file containing a recognizable stack-dump marker --
        the exact artifact a coordinator investigating a wedge would go
        looking for."""
        if sys.platform == "win32":
            pytest.skip("POSIX-only (T-3244)")
        module = _load_conftest()
        monkeypatch.setenv(module._STACKDUMP_ENV, "1")
        monkeypatch.chdir(tmp_path)
        previous = signal.getsignal(signal.SIGUSR1)
        try:
            module._install_stackdump_handler()
            os.kill(os.getpid(), signal.SIGUSR1)
            dump_path = tmp_path / ".frob" / "stackdumps" / f"pid-{os.getpid()}.txt"
            assert dump_path.is_file(), list((tmp_path / ".frob").rglob("*"))
            content = dump_path.read_text(encoding="utf-8")
            assert "SIGUSR1 stack dump" in content
            assert str(os.getpid()) in content
        finally:
            signal.signal(signal.SIGUSR1, previous)

    # frob:tests \
    # tests/unit/test_conftest_stackdump.py::TestStackdumpHandler.test_handler_not_inst\
    # alled_when_env_unset
    def test_handler_not_installed_when_env_unset(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Without `FROB_COVERAGE_STACKDUMP` set (the default for an
        ordinary `pytest`/`frob test` invocation), installing must be a
        no-op -- the default handler (whatever it was before) stays in
        place, so an unrelated `SIGUSR1` sender is not silently
        intercepted by a debug-only feature."""
        if sys.platform == "win32":
            pytest.skip("POSIX-only (T-3244)")
        module = _load_conftest()
        monkeypatch.delenv(module._STACKDUMP_ENV, raising=False)
        previous = signal.getsignal(signal.SIGUSR1)
        try:
            module._install_stackdump_handler()
            assert signal.getsignal(signal.SIGUSR1) is previous
        finally:
            signal.signal(signal.SIGUSR1, previous)


class TestSelfScanHeavyGrouping:
    """T-1433: `pytest_collection_modifyitems`'s full-repo self-scan
    xdist-group forcing -- the mitigation for the root-caused "node down:
    Not properly terminated" worker deaths (kernel OOM-kill, no
    faulthandler fault trace captured, matching an uncatchable SIGKILL)."""

    # frob:tests \
    # tests/unit/test_conftest_stackdump.py::TestSelfScanHeavyGrouping.test_self_scan_h\
    # eavy_tests_share_one_xdist_group
    def test_self_scan_heavy_tests_share_one_xdist_group(self) -> None:
        """A collected item whose name matches one of the known full-repo
        self-scan tests gets the SAME `xdist_group` marker as the others --
        the exact grouping that makes `--dist=loadgroup` schedule them
        onto one worker sequentially instead of several workers at once.

        T-3525: also gets a raised `@pytest.mark.timeout(1200)` -- the
        SAME hook assigns both, so group membership and the raised budget
        can never desync."""
        module = _load_conftest()

        class _FakeItem:
            def __init__(self, name: str) -> None:
                self.name = name
                self.own_markers: list = []

            def get_closest_marker(self, name: str):  # noqa: ANN001
                """T-2637: stub matches the real pytest.Item API surface
                `pytest_collection_modifyitems` calls (T-2099's
                heavy_subprocess check) -- this fixture carries none."""
                return None

            def add_marker(self, marker) -> None:  # noqa: ANN001
                self.own_markers.append(marker)

        items = [
            _FakeItem("test_sys_gate_zero_violations"),
            _FakeItem("test_repo_design_and_declarations_are_self_conformant"),
            _FakeItem("test_repo_unrestricted_scan_is_clean"),
            _FakeItem("test_something_unrelated"),
        ]
        module.pytest_collection_modifyitems(config=None, items=items)

        group_names = set()
        for item in items[:3]:
            assert len(item.own_markers) == 2, item.name
            marker_names = {m.name for m in item.own_markers}
            assert marker_names == {"xdist_group", "timeout"}
            group_marker = next(m for m in item.own_markers if m.name == "xdist_group")
            group_names.add(group_marker.kwargs["name"])
            timeout_marker = next(m for m in item.own_markers if m.name == "timeout")
            assert timeout_marker.args == (1200,)
        assert group_names == {"frob_self_scan_heavy"}
        assert items[3].own_markers == []


class TestHeavySubprocessGrouping:
    """T-2099: `pytest_collection_modifyitems`'s `heavy_subprocess` marker
    handling -- the fix for `tests/test_ticket_land.py` (275 real-git tests,
    NO xdist grouping at all) scattering across workers under the repo
    default `-n auto --dist=loadgroup` and exceeding the 540s foreground
    budget from cross-worker git contention, while the same file finishes
    well under that budget run serially."""

    # frob:tests \
    # tests/unit/test_conftest_stackdump.py::TestHeavySubprocessGrouping.test_heavy_sub\
    # process_marker_groups_per_file
    def test_heavy_subprocess_marker_groups_per_file(self) -> None:
        """A collected item whose module carries the `heavy_subprocess`
        marker gets its OWN `xdist_group`, keyed by module name -- so two
        different heavy modules land in DIFFERENT groups (they may still
        run on different workers, in parallel with each other) while every
        item within ONE heavy module shares the SAME group (that module's
        own tests are pinned to a single worker, serialized against each
        other, matching `--dist=loadgroup` scheduling semantics)."""
        module = _load_conftest()

        class _FakeMarker:
            def __init__(self, name: str) -> None:
                self.name = name

        class _FakeItem:
            def __init__(self, name: str, module_path: str, heavy: bool) -> None:
                self.name = name
                self.own_markers: list = []
                self.nodeid = f"{module_path}::{name}"
                self._heavy = heavy

            def get_closest_marker(self, name: str):  # noqa: ANN001
                if name == "heavy_subprocess" and self._heavy:
                    return _FakeMarker(name)
                return None

            def add_marker(self, marker) -> None:  # noqa: ANN001
                self.own_markers.append(marker)

        items = [
            _FakeItem("test_a", "tests/test_ticket_land.py", heavy=True),
            _FakeItem("test_b", "tests/test_ticket_land.py", heavy=True),
            _FakeItem("test_c", "tests/test_ticket_leases.py", heavy=True),
            _FakeItem("test_d", "tests/test_something_light.py", heavy=False),
        ]
        module.pytest_collection_modifyitems(config=None, items=items)

        def group_name(item) -> str:  # noqa: ANN001
            assert len(item.own_markers) == 1, item.name
            marker = item.own_markers[0]
            assert marker.name == "xdist_group"
            return marker.kwargs["name"]

        land_group_a = group_name(items[0])
        land_group_b = group_name(items[1])
        leases_group = group_name(items[2])

        assert land_group_a == land_group_b
        assert land_group_a != leases_group
        assert "tests/test_ticket_land.py" in land_group_a
        assert "tests/test_ticket_leases.py" in leases_group
        assert items[3].own_markers == []


class TestSuiteResultLine:
    """T-1596: `pytest_sessionfinish`'s always-visible `SUITE-RESULT:` line
    -- the fix for a confirmed, reproduced (not hypothetical) bug: doubling
    `-q` (this repo's own `addopts` already bakes in one, and the exact
    invocation this repo's dispatch guidance recommends adds a second)
    takes pytest's verbosity to -2, at which point `TerminalReporter.
    summary_stats()` silently skips its own final summary line -- with no
    crash, no traceback, no nonzero-looking artifact. This line is written
    via `TerminalReporter.write_line`, which is not gated by that verbosity
    level, so it survives regardless of how many `-q` flags stack."""

    class _FakeReporter:
        """Records every `write_line` call so a test can assert on exactly
        what `pytest_sessionfinish` sent it, without a real terminal."""

        def __init__(self) -> None:
            self.lines: list[str] = []

        def write_line(self, line: str, **_markup: bool) -> None:
            self.lines.append(line)

    class _FakePluginManager:
        def __init__(self, reporter: object | None) -> None:
            self._reporter = reporter

        def get_plugin(self, name: str) -> object | None:
            assert name == "terminalreporter"
            return self._reporter

    class _FakeConfig:
        def __init__(self, *, reporter: object | None, is_worker: bool = False) -> None:
            self.pluginmanager = TestSuiteResultLine._FakePluginManager(reporter)
            if is_worker:
                self.workerinput = {"workerid": "gw0"}

    class _FakeSession:
        def __init__(
            self, *, config: object, collected: int = 0, failed: int = 0
        ) -> None:
            self.config = config
            self.testscollected = collected
            self.testsfailed = failed
            # T-3516: real `pytest.Session` always carries `exitstatus`;
            # `pytest_sessionfinish`'s own WORKER-CRASH-REPORT block reads
            # (and can overwrite) it, so the fake carries it too.
            self.exitstatus = 0

    # frob:tests \
    # tests/unit/test_conftest_stackdump.py::TestSuiteResultLine.test_sessionfinish_pri\
    # nts_greppable_line_at_any_verbosity
    def test_sessionfinish_prints_greppable_line_at_any_verbosity(self) -> None:
        """On the controller (no `workerinput`), the hook writes exactly one
        `SUITE-RESULT:` line carrying the real exit status and counts --
        via `write_line`, which pytest's `-q`/`-qq` verbosity gating never
        suppresses, unlike the built-in `summary_stats()` line this exists
        to back up."""
        module = _load_conftest()
        reporter = self._FakeReporter()
        config = self._FakeConfig(reporter=reporter, is_worker=False)
        session = self._FakeSession(config=config, collected=50, failed=2)

        module.pytest_sessionfinish(session=session, exitstatus=1)

        assert len(reporter.lines) == 1
        line = reporter.lines[0]
        assert line == "SUITE-RESULT: exitstatus=1 collected=50 failed=2"

    # frob:tests \
    # tests/unit/test_conftest_stackdump.py::TestSuiteResultLine.test_sessionfinish_ski\
    # ps_on_xdist_worker
    def test_sessionfinish_skips_on_xdist_worker(self) -> None:
        """On an xdist WORKER (`workerinput` present, mirroring
        `pytest_configure`'s own controller-only guard above the hook),
        nothing is written -- printing once per worker would defeat the
        "exactly one greppable line per run" contract this hook exists to
        provide."""
        module = _load_conftest()
        reporter = self._FakeReporter()
        config = self._FakeConfig(reporter=reporter, is_worker=True)
        session = self._FakeSession(config=config, collected=50, failed=0)

        module.pytest_sessionfinish(session=session, exitstatus=0)

        assert reporter.lines == []

    class _FakeReport:
        """Minimal stand-in for pytest's `TestReport`, carrying just the
        `nodeid` attribute `pytest_sessionfinish` reads off `stats`."""

        def __init__(self, nodeid: str) -> None:
            self.nodeid = nodeid

    class _StatsReporter(_FakeReporter):
        """`_FakeReporter` plus a `.stats` dict, mirroring the real
        `TerminalReporter`'s outcome-keyed report list."""

        def __init__(self, stats: "dict[str, list]") -> None:
            super().__init__()
            self.stats = stats

    # frob:tests \
    # tests/unit/test_conftest_stackdump.py::TestSuiteResultLine.test_sessionfinish_lis\
    # ts_failing_node_ids
    def test_sessionfinish_lists_failing_node_ids(self) -> None:
        """T-1673: alongside the count-only `SUITE-RESULT:` line, the hook
        writes one `SUITE-RESULT-FAILED:` line per failing/erroring node id
        -- the content a reader needs to act without a second full run."""
        module = _load_conftest()
        stats = {
            "failed": [self._FakeReport("tests/a.py::test_one")],
            "error": [self._FakeReport("tests/b.py::test_two")],
        }
        reporter = self._StatsReporter(stats)
        config = self._FakeConfig(reporter=reporter, is_worker=False)
        session = self._FakeSession(config=config, collected=10, failed=2)

        module.pytest_sessionfinish(session=session, exitstatus=1)

        assert reporter.lines[0] == "SUITE-RESULT: exitstatus=1 collected=10 failed=2"
        assert "SUITE-RESULT-FAILED: tests/a.py::test_one (failed)" in reporter.lines
        assert "SUITE-RESULT-FAILED: tests/b.py::test_two (error)" in reporter.lines

    # frob:tests \
    # tests/unit/test_conftest_stackdump.py::TestSuiteResultLine.test_sessionfinish_cap\
    # s_failing_node_ids_with_and_n_more
    def test_sessionfinish_caps_failing_node_ids_with_and_n_more(self) -> None:
        """T-1673: past `_SUITE_RESULT_MAX_NODE_IDS` failures, the hook
        collapses the remainder into a single 'and N more' line instead of
        printing an unbounded list."""
        module = _load_conftest()
        cap = module._SUITE_RESULT_MAX_NODE_IDS
        reports = [self._FakeReport(f"tests/x.py::test_{i}") for i in range(cap + 3)]
        stats = {"failed": reports, "error": []}
        reporter = self._StatsReporter(stats)
        config = self._FakeConfig(reporter=reporter, is_worker=False)
        session = self._FakeSession(config=config, collected=cap + 3, failed=cap + 3)

        module.pytest_sessionfinish(session=session, exitstatus=1)

        failed_lines = [
            line for line in reporter.lines if "SUITE-RESULT-FAILED:" in line
        ]
        assert len(failed_lines) == cap + 1
        assert failed_lines[-1] == "SUITE-RESULT-FAILED: and 3 more"


class TestWorkerCrashReport:
    """T-3516: `pytest_runtest_logstart`/`pytest_runtest_logfinish`'s
    per-worker crash marker, `pytest_handlecrashitem`'s collect-and-cap
    logic, and `pytest_sessionfinish`'s `WORKER-CRASH-REPORT:` section."""

    class _FakeGateway:
        def __init__(self, gateway_id: str) -> None:
            self.id = gateway_id

    class _FakeWorker:
        def __init__(self, gateway_id: str) -> None:
            self.gateway = TestWorkerCrashReport._FakeGateway(gateway_id)

    class _FakeCrashReport:
        """Minimal stand-in for the synthetic `TestReport` xdist's own
        `DSession.handle_crashitem` builds and passes to
        `pytest_handlecrashitem`."""

        def __init__(self, node: object) -> None:
            self.node = node
            self.longrepr: str | None = "worker crashed"

    class _FakeSched:
        """Records every `mark_test_pending` call; `raise_on_mark` lets a
        test exercise the reschedule-failed fallback message."""

        def __init__(self, *, raise_on_mark: bool = False) -> None:
            self.marked: list[str] = []
            self._raise = raise_on_mark

        def mark_test_pending(self, nodeid: str) -> None:
            if self._raise:
                raise RuntimeError("reschedule boom")
            self.marked.append(nodeid)

    class _FakeHookConfig:
        """Stand-in for the `pytest.Config` stashed onto
        `_worker_crash_hook_config` by `pytest_configure` (T-3516) --
        `is_worker=True` mirrors an xdist worker (`workerinput` present),
        `is_worker=False` mirrors the controller (attribute absent)."""

        def __init__(self, *, worker_id: str = "gw0", is_worker: bool = True) -> None:
            if is_worker:
                self.workerinput = {"workerid": worker_id}

        def getoption(self, name: str, default: object = None) -> object:
            assert name == "timeout"
            return default

        def getini(self, name: str) -> str:
            assert name == "timeout"
            return ""

    def setup_method(self) -> None:
        """Every test loads its OWN fresh conftest module instance via
        `_load_conftest()` (module-level state starts empty each time), so
        no explicit cross-test reset is needed here -- kept as a no-op
        hook purely so a future shared-instance refactor of this test
        file fails loudly instead of silently leaking crash state."""

    # frob:tests \
    # tests/unit/test_conftest_stackdump.py::TestWorkerCrashReport.test_logstart_writes\
    # _marker_only_on_worker
    def test_logstart_writes_marker_only_on_worker(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`pytest_runtest_logstart` writes a per-worker marker file when
        `workerinput` is present (an actual xdist worker), and is a no-op
        on the controller (no `workerinput`) or when no config has been
        stashed at all."""
        module = _load_conftest()
        monkeypatch.setattr(module, "_XDIST_CRASH_MARKER_DIR", tmp_path / "markers")

        module._worker_crash_hook_config = self._FakeHookConfig(
            worker_id="gw1", is_worker=True
        )
        module.pytest_runtest_logstart("tests/x.py::test_a", None)
        assert module._xdist_crash_marker_path("gw1").exists()

        module._worker_crash_hook_config = self._FakeHookConfig(is_worker=False)
        module.pytest_runtest_logstart("tests/x.py::test_b", None)
        assert not module._xdist_crash_marker_path("gw0").exists()

    # frob:tests \
    # tests/unit/test_conftest_stackdump.py::TestWorkerCrashReport.test_logfinish_clear\
    # s_marker
    def test_logfinish_clears_marker(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A test that finishes normally (any outcome) clears its worker's
        marker via `pytest_runtest_logfinish` -- only a worker that dies
        WITHOUT reaching this hook leaves a marker behind for
        `pytest_handlecrashitem` to find."""
        module = _load_conftest()
        monkeypatch.setattr(module, "_XDIST_CRASH_MARKER_DIR", tmp_path / "markers")
        module._worker_crash_hook_config = self._FakeHookConfig(worker_id="gw1")

        module.pytest_runtest_logstart("tests/x.py::test_a", None)
        assert module._xdist_crash_marker_path("gw1").exists()
        module.pytest_runtest_logfinish("tests/x.py::test_a", None)
        assert not module._xdist_crash_marker_path("gw1").exists()

    # frob:tests \
    # tests/unit/test_conftest_stackdump.py::TestWorkerCrashReport.test_handlecrashitem\
    # _records_one_entry_and_marks_failed
    def test_handlecrashitem_records_one_entry_and_marks_failed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A single crash records exactly one `WORKER-CRASH-REPORT` entry
        (naming the worker and nodeid), does NOT reschedule at the default
        `_WORKER_CRASH_RERUN_CAP=0` (MUST-FIRE: a deterministic crasher
        must produce exactly one entry, not a reschedule-and-crash-again
        cascade), and never clears/sets `report.outcome` away from
        xdist's own default `\"failed\"` -- so the crash is never a
        silent skip."""
        module = _load_conftest()
        monkeypatch.setattr(module, "_XDIST_CRASH_MARKER_DIR", tmp_path / "markers")
        module._worker_crash_hook_config = self._FakeHookConfig(is_worker=False)
        sched = self._FakeSched()
        report = self._FakeCrashReport(self._FakeWorker("gw2"))

        module.pytest_handlecrashitem("tests/x.py::test_crash", report, sched)

        assert len(module._worker_crash_entries) == 1
        entry = module._worker_crash_entries[0]
        assert "worker=gw2" in entry
        assert "nodeid=tests/x.py::test_crash" in entry
        assert sched.marked == []
        assert "not rescheduled" in entry
        assert not hasattr(report, "outcome") or report.outcome != "passed"
        assert report.longrepr != "worker crashed"  # T-3516's own message replaced it

    # frob:tests \
    # tests/unit/test_conftest_stackdump.py::TestWorkerCrashReport.test_handlecrashitem\
    # _respects_a_raised_rerun_cap
    def test_handlecrashitem_respects_a_raised_rerun_cap(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The reschedule mechanism itself (`_WORKER_CRASH_RERUN_CAP` > 0,
        not this repo's own default of 0) reschedules exactly once per
        nodeid and then stops -- a THIRD crash of the same nodeid past
        the cap is still recorded as its own entry but is not rescheduled
        again."""
        module = _load_conftest()
        monkeypatch.setattr(module, "_XDIST_CRASH_MARKER_DIR", tmp_path / "markers")
        monkeypatch.setattr(module, "_WORKER_CRASH_RERUN_CAP", 1)
        module._worker_crash_hook_config = self._FakeHookConfig(is_worker=False)
        sched = self._FakeSched()
        nodeid = "tests/x.py::test_flaky"

        module.pytest_handlecrashitem(
            nodeid, self._FakeCrashReport(self._FakeWorker("gw3")), sched
        )
        module.pytest_handlecrashitem(
            nodeid, self._FakeCrashReport(self._FakeWorker("gw3")), sched
        )

        assert sched.marked == [nodeid]
        assert len(module._worker_crash_entries) == 2
        assert "rescheduled (1/1)" in module._worker_crash_entries[0]
        assert "not rescheduled" in module._worker_crash_entries[1]

    # frob:tests \
    # tests/unit/test_conftest_stackdump.py::TestWorkerCrashReport.test_sessionfinish_p\
    # rints_report_and_forces_failing_exit
    def test_sessionfinish_prints_report_and_forces_failing_exit(self) -> None:
        """`pytest_sessionfinish` prints exactly one `WORKER-CRASH-REPORT:`
        header plus one line per recorded crash, and forces
        `session.exitstatus` to a failing value if it would otherwise read
        as clean (0) -- a crash whose one capped rerun happened to pass
        must not let the whole run look green."""
        module = _load_conftest()
        module._worker_crash_entries.append(
            "WORKER-CRASH-REPORT: worker=gw0 nodeid=tests/x.py::test_a "
            "cause=... disposition=rescheduled (1/1)"
        )
        reporter = TestSuiteResultLine._StatsReporter({"failed": [], "error": []})
        config = TestSuiteResultLine._FakeConfig(reporter=reporter, is_worker=False)
        session = TestSuiteResultLine._FakeSession(config=config, collected=5, failed=0)
        session.exitstatus = 0

        module.pytest_sessionfinish(session=session, exitstatus=0)

        crash_lines = [
            line for line in reporter.lines if line.startswith("WORKER-CRASH-REPORT:")
        ]
        assert crash_lines[0] == "WORKER-CRASH-REPORT: 1 worker crash(es)"
        assert len(crash_lines) == 2
        assert session.exitstatus == 1

    # frob:tests \
    # tests/unit/test_conftest_stackdump.py::TestWorkerCrashReport.test_sessionfinish_s\
    # tays_quiet_on_a_clean_run
    def test_sessionfinish_stays_quiet_on_a_clean_run(self) -> None:
        """MUST-STAY-QUIET (T-3516): a run with no recorded worker crashes
        prints no `WORKER-CRASH-REPORT:` line at all, and does not touch
        `session.exitstatus`."""
        module = _load_conftest()
        assert module._worker_crash_entries == []
        reporter = TestSuiteResultLine._StatsReporter({"failed": [], "error": []})
        config = TestSuiteResultLine._FakeConfig(reporter=reporter, is_worker=False)
        session = TestSuiteResultLine._FakeSession(config=config, collected=5, failed=0)
        session.exitstatus = 0

        module.pytest_sessionfinish(session=session, exitstatus=0)

        assert not any(
            line.startswith("WORKER-CRASH-REPORT:") for line in reporter.lines
        )
        assert session.exitstatus == 0


class TestWorkerCrashReportIntegration:
    """T-3516 MUST-FIRE/MUST-STAY-QUIET: real subprocess `pytest -n`
    runs exercising the FULL pipeline (`pytest_runtest_logstart` ->
    a worker's `os._exit` -> xdist's own crash machinery ->
    `pytest_handlecrashitem` -> `pytest_sessionfinish`) end-to-end, not
    just the unit-level fakes above -- the shape of bug this ticket
    exists for (an xdist worker actually dying) cannot be reproduced by
    calling the hooks directly in-process."""

    @staticmethod
    def _run(tmp_path: Path, test_body: str) -> "subprocess.CompletedProcess[str]":
        """Run a real, isolated `python -m pytest -n 2` over a synthetic
        one-module suite under `tmp_path`, with THIS repo's real
        `tests/conftest.py` copied in as the suite's own conftest --
        `tmp_path` has no `pyproject.toml`/`frob.toml` of its own, so
        pytest never inherits this repo's real `addopts`/rootdir, only
        the plugin logic under test."""
        (tmp_path / "conftest.py").write_text(
            _CONFTEST_PATH.read_text(encoding="utf-8"), encoding="utf-8"
        )
        (tmp_path / "test_planted.py").write_text(test_body, encoding="utf-8")
        env = dict(os.environ)
        env.pop("PYTEST_ADDOPTS", None)
        return subprocess.run(
            [sys.executable, "-m", "pytest", str(tmp_path), "-n", "2", "-q"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            timeout=90,
            env=env,
        )

    # frob:tests \
    # tests/unit/test_conftest_stackdump.py::TestWorkerCrashReportIntegration.test_must\
    # _fire_planted_os_exit_produces_one_report_and_failing_exit
    def test_must_fire_planted_os_exit_produces_one_report_and_failing_exit(
        self, tmp_path: Path
    ) -> None:
        """MUST-FIRE (T-3516): a planted test that `os._exit()`s its own
        worker produces exactly one `WORKER-CRASH-REPORT` entry naming it,
        a `FAILED` entry in `SUITE-RESULT-FAILED`, and a failing process
        exit status -- with no `INTERNALERROR` abort."""
        body = (
            "import os\n\n"
            "def test_ok():\n"
            "    assert True\n\n"
            "def test_crash():\n"
            "    os._exit(1)\n"
        )
        result = self._run(tmp_path, body)
        combined = result.stdout + result.stderr
        lines = combined.splitlines()

        assert result.returncode != 0, combined
        assert "INTERNALERROR" not in combined, combined

        crash_lines = [
            line for line in lines if line.startswith("WORKER-CRASH-REPORT: worker=")
        ]
        assert len(crash_lines) == 1, combined
        assert "test_planted.py::test_crash" in crash_lines[0]

        failed_lines = [
            line
            for line in lines
            if line.startswith("SUITE-RESULT-FAILED:")
            and "test_planted.py::test_crash" in line
        ]
        assert len(failed_lines) == 1, combined

    # frob:tests \
    # tests/unit/test_conftest_stackdump.py::TestWorkerCrashReportIntegration.test_must\
    # _stay_quiet_on_a_clean_run
    def test_must_stay_quiet_on_a_clean_run(self, tmp_path: Path) -> None:
        """MUST-STAY-QUIET (T-3516): a clean run (no crash) prints no
        `WORKER-CRASH-REPORT` section at all."""
        body = "def test_one():\n    assert True\n\ndef test_two():\n    assert True\n"
        result = self._run(tmp_path, body)
        combined = result.stdout + result.stderr

        assert result.returncode == 0, combined
        assert "WORKER-CRASH-REPORT" not in combined, combined

    # frob:tests \
    # tests/unit/test_conftest_stackdump.py::TestWorkerCrashReportIntegration.test_must\
    # _stay_quiet_normal_failure_reporting_unchanged
    def test_must_stay_quiet_normal_failure_reporting_unchanged(
        self, tmp_path: Path
    ) -> None:
        """MUST-STAY-QUIET (T-3516): an ordinary (non-crashing) failing
        test's `SUITE-RESULT-FAILED` line is unchanged -- no crash-cause
        suffix, no `WORKER-CRASH-REPORT` section."""
        body = "def test_fails():\n    assert False\n"
        result = self._run(tmp_path, body)
        combined = result.stdout + result.stderr
        lines = combined.splitlines()

        assert result.returncode != 0, combined
        assert "WORKER-CRASH-REPORT" not in combined, combined
        failed_lines = [
            line for line in lines if line.startswith("SUITE-RESULT-FAILED:")
        ]
        assert failed_lines == [
            "SUITE-RESULT-FAILED: test_planted.py::test_fails (failed)"
        ], combined


class TestRepoTreeHash:
    """T-3525: `_repo_tree_hash`'s never-raises fallback contract."""

    # frob:tests \
    # tests/unit/test_conftest_stackdump.py::TestRepoTreeHash.test_stable_for_the_same_\
    # clean_tree
    def test_stable_for_the_same_clean_tree(self, tmp_path: Path) -> None:
        """Called twice against the SAME (real, this-repo) tree state,
        `_repo_tree_hash` returns the identical value both times."""
        module = _load_conftest()
        first = module._repo_tree_hash(Path.cwd())
        second = module._repo_tree_hash(Path.cwd())
        assert first == second
        assert first != "no-git-fallback"

    # frob:tests \
    # tests/unit/test_conftest_stackdump.py::TestRepoTreeHash.test_falls_back_without_r\
    # aising_when_git_is_unavailable
    def test_falls_back_without_raising_when_git_is_unavailable(
        self, tmp_path: Path
    ) -> None:
        """A directory with no `.git` at all (git fails, not a real repo)
        returns the fixed fallback sentinel instead of raising -- a
        cache-key MISS just costs one fresh scan, never a hard failure."""
        module = _load_conftest()
        result = module._repo_tree_hash(tmp_path)
        assert result == "no-git-fallback"


class TestCachedSelfScan:
    """T-3525: `_cached_self_scan`'s caching/staleness/corruption logic,
    exercised directly against a cheap fake `compute` -- the primitive
    `frob_self_scan_artifacts` wraps around this repo's own real (slow)
    whole-tree scan."""

    @staticmethod
    def _counting_compute(calls: list) -> "object":
        def _compute() -> tuple:
            calls.append(1)
            return ("violation-a", "violation-b")

        return _compute

    # frob:tests \
    # tests/unit/test_conftest_stackdump.py::TestCachedSelfScan.test_cache_miss_compute\
    # s_once_and_persists
    def test_cache_miss_computes_once_and_persists(self, tmp_path: Path) -> None:
        """An empty cache dir: `compute` is called exactly once, its
        result is returned, and a cache file is left behind for the next
        caller."""
        module = _load_conftest()
        cache_dir = tmp_path / "cache"
        calls: list = []

        result = module._cached_self_scan(
            cache_dir, "hash-a", self._counting_compute(calls)
        )

        assert result == ("violation-a", "violation-b")
        assert len(calls) == 1
        assert (cache_dir / "hash-a.pkl").is_file()

    # frob:tests \
    # tests/unit/test_conftest_stackdump.py::TestCachedSelfScan.test_cache_hit_does_not\
    # _recompute
    def test_cache_hit_does_not_recompute(self, tmp_path: Path) -> None:
        """MUST-FIRE (T-3525, primitive level): once persisted under a
        given tree hash, a SECOND call with the SAME hash loads from disk
        -- `compute` is never called again."""
        module = _load_conftest()
        cache_dir = tmp_path / "cache"
        calls: list = []

        first = module._cached_self_scan(
            cache_dir, "hash-a", self._counting_compute(calls)
        )
        second = module._cached_self_scan(
            cache_dir, "hash-a", self._counting_compute(calls)
        )

        assert first == second == ("violation-a", "violation-b")
        assert len(calls) == 1

    # frob:tests \
    # tests/unit/test_conftest_stackdump.py::TestCachedSelfScan.test_tree_hash_mismatch\
    # _triggers_exactly_one_fresh_scan
    def test_tree_hash_mismatch_triggers_exactly_one_fresh_scan(
        self, tmp_path: Path
    ) -> None:
        """MUST-STAY-QUIET (T-3525): a DIFFERENT tree hash is a cache
        miss of its own -- exactly one fresh `compute` call for the new
        hash, the first hash's own cached entry is untouched."""
        module = _load_conftest()
        cache_dir = tmp_path / "cache"
        calls: list = []

        module._cached_self_scan(cache_dir, "hash-a", self._counting_compute(calls))
        module._cached_self_scan(cache_dir, "hash-b", self._counting_compute(calls))
        module._cached_self_scan(cache_dir, "hash-b", self._counting_compute(calls))

        assert len(calls) == 2  # one for hash-a, one for hash-b (its own first miss)
        assert (cache_dir / "hash-a.pkl").is_file()
        assert (cache_dir / "hash-b.pkl").is_file()

    # frob:tests \
    # tests/unit/test_conftest_stackdump.py::TestCachedSelfScan.test_corrupted_cache_fa\
    # lls_back_to_a_fresh_scan
    def test_corrupted_cache_falls_back_to_a_fresh_scan(self, tmp_path: Path) -> None:
        """A torn/corrupted cache file (a worker that died mid-persist
        before this ticket's fix, say) is treated as a miss -- `compute`
        runs and the caller gets a real result, never an unpickle crash."""
        module = _load_conftest()
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir(parents=True)
        (cache_dir / "hash-a.pkl").write_bytes(b"not a valid pickle stream")
        calls: list = []

        result = module._cached_self_scan(
            cache_dir, "hash-a", self._counting_compute(calls)
        )

        assert result == ("violation-a", "violation-b")
        assert len(calls) == 1

    # frob:tests \
    # tests/unit/test_conftest_stackdump.py::TestCachedSelfScan.test_must_fire_scan_cou\
    # nt_is_one_across_a_simulated_worker_restart
    def test_must_fire_scan_count_is_one_across_a_simulated_worker_restart(
        self, tmp_path: Path
    ) -> None:
        """MUST-FIRE (T-3525, process level): two SEPARATE subprocess
        Python invocations (a fresh interpreter each, standing in for two
        different xdist worker PROCESSES -- the actual "worker restart"
        shape this ticket fixes) share the same cache dir and tree hash.
        A `FROB_SELF_SCAN_COUNTER_FILE` env var, honoured by `_cached_
        self_scan` itself, records one line per REAL `compute` call
        across both processes -- asserting exactly one line is
        scan-count==1 across the simulated restart."""
        cache_dir = tmp_path / "cache"
        counter_path = tmp_path / "counter.txt"
        script = (
            "import sys\n"
            "from pathlib import Path\n"
            "sys.path.insert(0, %r)\n"
            "from tests.unit._conftest_test_helpers import load_conftest_module\n"
            "module = load_conftest_module('_t3525_worker_sim')\n"
            "\n"
            "\n"
            "def _compute():\n"
            "    return ('violation-a',)\n"
            "\n"
            "\n"
            "module._cached_self_scan(Path(%r), 'hash-a', _compute)\n"
        ) % (str(Path.cwd()), str(cache_dir))
        env = dict(os.environ)
        env["FROB_SELF_SCAN_COUNTER_FILE"] = str(counter_path)

        def _run_one_simulated_worker() -> "subprocess.CompletedProcess[str]":
            """One "worker process" attempt: a fresh interpreter running
            `script` against the shared `cache_dir`/`counter_path` --
            called twice below to simulate the original worker plus its
            xdist-spawned replacement (T-3525 de-dup of the identical
            `subprocess.run` call PERF012 flagged)."""
            return subprocess.run(
                [sys.executable, "-c", script],
                capture_output=True,
                text=True,
                timeout=60,
                env=env,
            )

        first = _run_one_simulated_worker()
        second = _run_one_simulated_worker()

        assert first.returncode == 0, first.stdout + first.stderr
        assert second.returncode == 0, second.stdout + second.stderr
        counter_lines = counter_path.read_text(encoding="utf-8").splitlines()
        assert len(counter_lines) == 1, counter_lines
