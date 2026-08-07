"""T-1433: unit coverage for `tests/conftest.py`'s `SIGUSR1` stack-dump
handler -- the between-tests/session-teardown wedge diagnostic the two
`make coverage` incidents actually needed (pytest's own per-test
`--timeout` watchdog cannot reach that state; see T-1433's ticket body)."""

from __future__ import annotations

import importlib
import importlib.util
import os
import signal
import sys
from pathlib import Path

import pytest

if sys.platform == "win32":  # pragma: no cover - POSIX-only feature
    pytest.skip("SIGUSR1 is POSIX-only", allow_module_level=True)

_CONFTEST_PATH = Path(__file__).resolve().parent.parent / "conftest.py"


def _load_conftest():
    """Import `tests/conftest.py` as a standalone module (not via pytest's
    own plugin machinery, which already has it loaded once as a fixture
    provider) so these tests can call its private stack-dump helpers
    directly without depending on pytest's conftest-import identity."""
    spec = importlib.util.spec_from_file_location(
        "_t1433_conftest_under_test", _CONFTEST_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestStackdumpHandler:
    """T-1433: `_install_stackdump_handler`/`_dump_all_thread_stacks`."""

    # frob:tests tests/unit/test_conftest_stackdump.py::TestStackdumpHandler.test_sigusr1_writes_all_thread_stacks_when_enabled  # noqa: E501
    def test_sigusr1_writes_all_thread_stacks_when_enabled(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """With `FROB_COVERAGE_STACKDUMP=1` set, installing the handler and
        then raising `SIGUSR1` in-process writes a `.frob/stackdumps/
        pid-<pid>.txt` file containing a recognizable stack-dump marker --
        the exact artifact a coordinator investigating a wedge would go
        looking for."""
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

    # frob:tests tests/unit/test_conftest_stackdump.py::TestStackdumpHandler.test_handler_not_installed_when_env_unset  # noqa: E501
    def test_handler_not_installed_when_env_unset(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Without `FROB_COVERAGE_STACKDUMP` set (the default for an
        ordinary `pytest`/`frob test` invocation), installing must be a
        no-op -- the default handler (whatever it was before) stays in
        place, so an unrelated `SIGUSR1` sender is not silently
        intercepted by a debug-only feature."""
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

    # frob:tests tests/unit/test_conftest_stackdump.py::TestSelfScanHeavyGrouping.test_self_scan_heavy_tests_share_one_xdist_group  # noqa: E501
    def test_self_scan_heavy_tests_share_one_xdist_group(self) -> None:
        """A collected item whose name matches one of the known full-repo
        self-scan tests gets the SAME `xdist_group` marker as the others --
        the exact grouping that makes `--dist=loadgroup` schedule them
        onto one worker sequentially instead of several workers at once."""
        module = _load_conftest()

        class _FakeItem:
            def __init__(self, name: str) -> None:
                self.name = name
                self.own_markers: list = []

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
            assert len(item.own_markers) == 1, item.name
            marker = item.own_markers[0]
            assert marker.name == "xdist_group"
            group_names.add(marker.kwargs["name"])
        assert group_names == {"frob_self_scan_heavy"}
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

    # frob:tests tests/unit/test_conftest_stackdump.py::TestSuiteResultLine.test_sessionfinish_prints_greppable_line_at_any_verbosity  # noqa: E501
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

    # frob:tests tests/unit/test_conftest_stackdump.py::TestSuiteResultLine.test_sessionfinish_skips_on_xdist_worker  # noqa: E501
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

    # frob:tests tests/unit/test_conftest_stackdump.py::TestSuiteResultLine.test_sessionfinish_lists_failing_node_ids  # noqa: E501
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

    # frob:tests tests/unit/test_conftest_stackdump.py::TestSuiteResultLine.test_sessionfinish_caps_failing_node_ids_with_and_n_more  # noqa: E501
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
