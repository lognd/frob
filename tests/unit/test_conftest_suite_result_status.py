"""T-3246: unit coverage for `tests/conftest.py`'s `pytest_sessionfinish`
DID-NOT-COMPLETE labelling -- kept in its OWN file rather than folded into
`tests/unit/test_conftest_stackdump.py`'s pre-existing `TestSuiteResultLine`
class, because that file was under a live scope lease held by T-3244 at the
time this ticket landed (concurrent, unrelated ty-platform-safety work); a
scope-lease conflict, not a design preference, is why this lives separately.
See `tests/unit/test_conftest_stackdump.py::TestSuiteResultLine` for the
ORIGINAL `SUITE-RESULT:` line coverage (T-1596/T-1673) this file extends."""

from __future__ import annotations

from tests.unit._conftest_test_helpers import load_conftest_module


# frob:ticket T-3246
def _load_conftest():
    """T-3252: thin wrapper over the shared `load_conftest_module` helper
    (DUP001 consolidation, T-3252) -- keeps this file's own call sites
    (`_load_conftest()`) unchanged. Each call gets its OWN fresh module
    instance (a new `spec_from_file_location` load), so `_last_internal_
    error` never leaks between tests."""
    return load_conftest_module("_t3246_conftest_under_test")


# frob:ticket T-3246
class _FakeReporter:
    """Records every `write_line` call so a test can assert on exactly what
    `pytest_sessionfinish` sent it, without a real terminal."""

    # frob:ticket T-3246
    def __init__(self) -> None:
        self.lines: list[str] = []

    # frob:ticket T-3246
    def write_line(self, line: str, **_markup: bool) -> None:
        """Append `line` to the recorded transcript, mirroring the subset
        of `TerminalReporter.write_line`'s signature this hook uses."""
        self.lines.append(line)


# frob:ticket T-3246
class _StatsReporter(_FakeReporter):
    """`_FakeReporter` plus a `.stats` dict, mirroring the real
    `TerminalReporter`'s outcome-keyed report list."""

    # frob:ticket T-3246
    def __init__(self, stats: "dict[str, list]") -> None:
        """Store `stats` for `pytest_sessionfinish` to read failing/erroring
        node ids from, exactly as the real `TerminalReporter` would."""
        super().__init__()
        self.stats = stats


# frob:ticket T-3246
class _FakePluginManager:
    """Stand-in for `pytest.Config.pluginmanager`, returning a fixed
    `terminalreporter` regardless of the requested plugin name."""

    # frob:ticket T-3246
    def __init__(self, reporter: object | None) -> None:
        self._reporter = reporter

    # frob:ticket T-3246
    def get_plugin(self, name: str) -> object | None:
        """Assert the hook only ever asks for `terminalreporter`, then hand
        back the reporter this test wired in."""
        assert name == "terminalreporter"
        return self._reporter


# frob:ticket T-3246
class _FakeConfig:
    """Stand-in for `pytest.Config`, carrying just the `pluginmanager`
    attribute `pytest_sessionfinish` reads."""

    # frob:ticket T-3246
    def __init__(self, *, reporter: object | None) -> None:
        """Build a controller-shaped config (no `workerinput`) wired to
        `reporter` via `_FakePluginManager`."""
        self.pluginmanager = _FakePluginManager(reporter)


# frob:ticket T-3246
class _FakeSession:
    """Stand-in for `pytest.Session`, carrying just the `config`/
    `testscollected`/`testsfailed` attributes `pytest_sessionfinish` reads."""

    # frob:ticket T-3246
    def __init__(self, *, config: object, collected: int = 0, failed: int = 0) -> None:
        """Store the fields `pytest_sessionfinish` reads off a real
        `pytest.Session` at the given values."""
        self.config = config
        self.testscollected = collected
        self.testsfailed = failed


# frob:ticket T-3246
class _FakeReport:
    """Minimal stand-in for pytest's `TestReport`, carrying just the
    `nodeid` attribute `pytest_sessionfinish` reads off `stats`."""

    # frob:ticket T-3246
    def __init__(self, nodeid: str) -> None:
        """Store `nodeid` for `pytest_sessionfinish` to read."""
        self.nodeid = nodeid


# frob:ticket T-3246
class TestSuiteResultDidNotComplete:
    """T-3246: `pytest_sessionfinish`'s DID-NOT-COMPLETE labelling of an
    ABORTED run (pytest exitstatus 2/3/4/5) -- the fix for a confirmed
    conflation: an aborted run (e.g. exitstatus=3, xdist's loadscope
    scheduler crashing on a dead worker) rendered in the EXACT SAME
    `SUITE-RESULT:` line shape as a completed run with real failures,
    differing only in an unlabelled `exitstatus=` digit. `failed=24` on an
    aborted run is a lower bound of unknown looseness, not a count -- the
    author of this fix mistook it for one themselves before noticing the
    exit status, which is the evidence the old format was misleading."""

    # frob:tests tests/unit/test_conftest_suite_result_status.py::TestSuiteResultDidNotComplete.test_sessionfinish_labels_did_not_complete_runs  # noqa: E501
    # frob:waive FMT001 reason="single-line frob:tests directive naming a long test \
    # node id -- already at frob fmt's own canonical form (verified: `frob fmt` \
    # reports it unchanged), same unwrappable shape as src/frob/app/_json_guard.py's \
    # existing FMT001 waivers"
    # frob:ticket T-3246
    def test_sessionfinish_labels_did_not_complete_runs(self) -> None:
        """MUST-FIRE: an ABORTED run (exitstatus=3, INTERNALERROR) produces
        a line that says `DID-NOT-COMPLETE` and marks both counts as
        partial -- a reader can no longer mistake it for a completed run's
        real failure count."""
        module = _load_conftest()
        reporter = _FakeReporter()
        config = _FakeConfig(reporter=reporter)
        session = _FakeSession(config=config, collected=12491, failed=24)

        module.pytest_sessionfinish(session=session, exitstatus=3)

        line = reporter.lines[0]
        assert "DID-NOT-COMPLETE" in line
        assert "exitstatus=3" in line
        assert "(INTERNAL-ERROR)" in line
        assert "collected=12491 (partial)" in line
        assert "failed=24 (partial, lower-bound)" in line
        # `src/frob/gates/_bug_repro.py::_classify_designated_test_exit`
        # regex-matches the bare `collected=0`/`collected=N` substring
        # against this line (T-2025) -- the partial annotation must stay a
        # trailing suffix, never folded into the key, or that sibling
        # consumer silently breaks.
        assert "collected=12491" in line

    # frob:tests tests/unit/test_conftest_suite_result_status.py::TestSuiteResultDidNotComplete.test_sessionfinish_completed_run_format_is_unchanged  # noqa: E501
    # frob:waive FMT001 reason="single-line frob:tests directive naming a long test \
    # node id -- already at frob fmt's own canonical form (verified: `frob fmt` \
    # reports it unchanged), same unwrappable shape as src/frob/app/_json_guard.py's \
    # existing FMT001 waivers"
    # frob:ticket T-3246
    def test_sessionfinish_completed_run_format_is_unchanged(self) -> None:
        """MUST-STAY-QUIET: a normal completed run (exitstatus=0 or 1)
        still produces the EXACT pre-existing line format --
        `tests/unit/test_conftest_stackdump.py::TestSuiteResultLine`
        already pins exitstatus=1; this pins exitstatus=0 too so neither
        completed code is accidentally relabelled by this change."""
        module = _load_conftest()
        reporter = _FakeReporter()
        config = _FakeConfig(reporter=reporter)
        session = _FakeSession(config=config, collected=50, failed=0)

        module.pytest_sessionfinish(session=session, exitstatus=0)

        assert reporter.lines == ["SUITE-RESULT: exitstatus=0 collected=50 failed=0"]

    # frob:tests tests/unit/test_conftest_suite_result_status.py::TestSuiteResultDidNotComplete.test_sessionfinish_marks_failing_set_incomplete_on_abort  # noqa: E501
    # frob:waive FMT001 reason="single-line frob:tests directive naming a long test \
    # node id -- already at frob fmt's own canonical form (verified: `frob fmt` \
    # reports it unchanged), same unwrappable shape as src/frob/app/_json_guard.py's \
    # existing FMT001 waivers"
    # frob:ticket T-3246
    def test_sessionfinish_marks_failing_set_incomplete_on_abort(self) -> None:
        """MUST-FIRE: on an aborted run, whatever `SUITE-RESULT-FAILED:`
        node ids WERE recorded before the abort are still printed (the
        partial record is not suppressed, per the ticket), but are now
        preceded by an explicit line saying the failing set is
        INCOMPLETE."""
        module = _load_conftest()
        stats = {"failed": [_FakeReport("tests/a.py::test_one")], "error": []}
        reporter = _StatsReporter(stats)
        config = _FakeConfig(reporter=reporter)
        session = _FakeSession(config=config, collected=100, failed=1)

        module.pytest_sessionfinish(session=session, exitstatus=3)

        incomplete_lines = [
            line for line in reporter.lines if "failing set INCOMPLETE" in line
        ]
        assert len(incomplete_lines) == 1
        assert "SUITE-RESULT-FAILED: tests/a.py::test_one (failed)" in reporter.lines
        # the incomplete-set warning must come BEFORE the node ids it warns about
        assert reporter.lines.index(incomplete_lines[0]) < reporter.lines.index(
            "SUITE-RESULT-FAILED: tests/a.py::test_one (failed)"
        )

    # frob:tests tests/unit/test_conftest_suite_result_status.py::TestSuiteResultDidNotComplete.test_sessionfinish_completed_run_never_marked_incomplete  # noqa: E501
    # frob:waive FMT001 reason="single-line frob:tests directive naming a long test \
    # node id -- already at frob fmt's own canonical form (verified: `frob fmt` \
    # reports it unchanged), same unwrappable shape as src/frob/app/_json_guard.py's \
    # existing FMT001 waivers"
    # frob:ticket T-3246
    def test_sessionfinish_completed_run_never_marked_incomplete(self) -> None:
        """MUST-STAY-QUIET: a completed run with real failures never gets
        the INCOMPLETE warning line, even though it also has
        `SUITE-RESULT-FAILED:` node ids -- that warning is reserved for
        aborted runs only."""
        module = _load_conftest()
        stats = {"failed": [_FakeReport("tests/a.py::test_one")], "error": []}
        reporter = _StatsReporter(stats)
        config = _FakeConfig(reporter=reporter)
        session = _FakeSession(config=config, collected=100, failed=1)

        module.pytest_sessionfinish(session=session, exitstatus=1)

        assert not any("failing set INCOMPLETE" in line for line in reporter.lines)

    # frob:tests tests/unit/test_conftest_suite_result_status.py::TestSuiteResultDidNotComplete.test_sessionfinish_names_internalerror_cause  # noqa: E501
    # frob:waive FMT001 reason="single-line frob:tests directive naming a long test \
    # node id -- already at frob fmt's own canonical form (verified: `frob fmt` \
    # reports it unchanged), same unwrappable shape as src/frob/app/_json_guard.py's \
    # existing FMT001 waivers"
    # frob:ticket T-3246
    def test_sessionfinish_names_internalerror_cause(self) -> None:
        """MUST-FIRE: when `pytest_internalerror` fired earlier in the same
        process (the real sequence pytest follows on an INTERNALERROR
        abort), the `SUITE-RESULT:` line names the recorded cause instead
        of just the bare exit status."""
        module = _load_conftest()
        reporter = _FakeReporter()
        config = _FakeConfig(reporter=reporter)
        session = _FakeSession(config=config, collected=12491, failed=24)

        # frob:ticket T-3246
        class _FakeExcInfo:
            typename = "KeyError"
            value = "<WorkerController gw6>"

        module.pytest_internalerror(excrepr=object(), excinfo=_FakeExcInfo())
        module.pytest_sessionfinish(session=session, exitstatus=3)

        line = reporter.lines[0]
        assert "cause=KeyError: <WorkerController gw6>" in line

    # frob:tests tests/unit/test_conftest_suite_result_status.py::TestSuiteResultDidNotComplete.test_sessionfinish_configure_resets_stale_internal_error  # noqa: E501
    # frob:waive FMT001 reason="single-line frob:tests directive naming a long test \
    # node id -- already at frob fmt's own canonical form (verified: `frob fmt` \
    # reports it unchanged), same unwrappable shape as src/frob/app/_json_guard.py's \
    # existing FMT001 waivers"
    # frob:ticket T-3246
    def test_sessionfinish_configure_resets_stale_internal_error(self) -> None:
        """MUST-STAY-QUIET: `pytest_configure` resets `_last_internal_error`
        to `None` -- a value stashed by an earlier in-process run cannot
        leak into a LATER run's `SUITE-RESULT:` line."""
        module = _load_conftest()

        # frob:ticket T-3246
        class _FakeExcInfo:
            typename = "KeyError"
            value = "<WorkerController gw6>"

        module.pytest_internalerror(excrepr=object(), excinfo=_FakeExcInfo())
        assert module._last_internal_error is not None

        # frob:ticket T-3246
        class _FakeConfigureConfig:
            pass

        module.pytest_configure(config=_FakeConfigureConfig())

        assert module._last_internal_error is None
