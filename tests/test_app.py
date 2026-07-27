"""Tests for `frob test --wait-coverage` (T-0322): the foreground,
single-flight, blocking-until-fresh coverage contract that replaces
backgrounding `make coverage` and stalling on a notification a dispatched
sub-agent can never receive (docs/guides/agent-playbook.md section 6b);
and for the flake-quarantine stability wiring into `frob test`'s own run
path (T-0635)."""

from __future__ import annotations

from pathlib import Path

import pytest
from typani import Err, Ok

from frob.app.config import AppConfig
from frob.app.test_runner import _track_python_stability_and_gate, run
from frob.gates import stamp_coverage
from frob.graph import build_graph
from frob.testing import (
    CoverageWaitError,
    CoverageWaitOutcome,
    coverage_lock_path,
    quarantine,
    record_outcomes,
    run_coverage_wait,
)
from frob.testing._models import RunnerOutcome, SelectionReport, TestRunReport
from frob.tickets import Origin, TicketKind, TicketSpec, new_ticket


def _outcome(language: str, exit_code: int) -> RunnerOutcome:
    """A minimal `RunnerOutcome` for `TestStabilityGate`'s fixtures."""
    return RunnerOutcome(
        language=language,
        argv=(),
        exit_code=exit_code,
        duration_s=0.1,
        stdout_tail="",
        stderr_tail="",
    )


def _make_repo(tmp_path: Path) -> Path:
    """A minimal single-module repo `run_coverage_wait` can build a graph
    snapshot against."""
    root = tmp_path / "repo"
    pkg = root / "src" / "pkg"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "mod.py").write_text("def fn():\n    return 1\n", encoding="utf-8")
    return root


# frob:ticket T-0803
class TestRunCoverageWait:
    def test_coverage_lock_path_is_under_frob_dir(self, tmp_path):
        # frob:tests \
        # tests/test_app.py::TestRunCoverageWait.test_coverage_lock_path_is_under_frob_\
        # dir  # noqa: E501
        assert coverage_lock_path(tmp_path) == tmp_path / ".frob" / "coverage.lock"

    # frob:ticket T-0803
    def test_no_stamp_runs_command_and_reports_ran(self, tmp_path, monkeypatch):
        # frob:tests \
        # tests/test_app.py::TestRunCoverageWait.test_no_stamp_runs_command_and_reports\
        # _ran  # noqa: E501
        root = _make_repo(tmp_path)
        calls: list[list[str]] = []

        def _fake_run(cmd, cwd, check):  # noqa: ANN001
            calls.append(list(cmd))

            class _Result:
                returncode = 0

            return _Result()

        monkeypatch.setattr("frob.process._guard.subprocess.run", _fake_run)
        result = run_coverage_wait(root, command=("true",))
        assert result.is_ok
        outcome = result.danger_ok
        assert outcome.ran is True
        assert calls == [["true"]]

    # frob:ticket T-0803
    def test_fresh_stamp_skips_the_run(self, tmp_path, monkeypatch):
        # frob:tests \
        # tests/test_app.py::TestRunCoverageWait.test_fresh_stamp_skips_the_run  # \
        # noqa: E501
        root = _make_repo(tmp_path)
        cache = root / ".frob" / "cache.db"
        build_graph(root, cache).danger_ok
        (root / "coverage.xml").write_text("<coverage/>", encoding="utf-8")
        stamped = stamp_coverage(root)
        assert stamped.is_ok

        called = False

        def _fake_run(cmd, cwd, check):  # noqa: ANN001
            nonlocal called
            called = True

            class _Result:
                returncode = 0

            return _Result()

        monkeypatch.setattr("frob.process._guard.subprocess.run", _fake_run)
        result = run_coverage_wait(root, command=("true",))
        assert result.is_ok
        assert result.danger_ok.ran is False
        assert called is False

    # frob:ticket T-0803
    def test_failed_command_is_err(self, tmp_path, monkeypatch):
        # frob:tests tests/test_app.py::TestRunCoverageWait.test_failed_command_is_err  \
        # # noqa: E501
        root = _make_repo(tmp_path)

        def _fake_run(cmd, cwd, check):  # noqa: ANN001
            class _Result:
                returncode = 1

            return _Result()

        monkeypatch.setattr("frob.process._guard.subprocess.run", _fake_run)
        result = run_coverage_wait(root, command=("false",))
        assert result.is_err
        assert result.danger_err == CoverageWaitError.RunFailed

    def test_kill_switch_refuses_without_spawning(self, tmp_path, monkeypatch):
        # frob:tests \
        # tests/test_app.py::TestRunCoverageWait.test_kill_switch_refuses_without_spawn\
        # ing  # noqa: E501
        # T-0803: FROB_DISABLE_EXEC=1 must make `run_coverage_wait`'s
        # coverage-suite spawn refuse (via `guarded_subprocess_run`)
        # instead of bypassing the T-0200/T-0778 exec guard -- proven with
        # a spy on the real `subprocess.run` so a spawn attempt would be
        # observed, not assumed.
        import subprocess

        root = _make_repo(tmp_path)
        monkeypatch.setenv("FROB_DISABLE_EXEC", "1")
        spawned = False
        real_run = subprocess.run

        def _spy(*args, **kwargs):  # noqa: ANN001, ANN202
            nonlocal spawned
            spawned = True
            return real_run(*args, **kwargs)

        monkeypatch.setattr("frob.process._guard.subprocess.run", _spy)
        result = run_coverage_wait(root, command=("true",))
        assert not spawned
        assert result.is_err
        assert result.danger_err == CoverageWaitError.RunFailed


class TestWaitCoverage:
    """`frob test --wait-coverage` dispatch (test_runner.py::run)."""

    def test_wait_coverage_flag_dispatches_and_exits_zero_on_success(
        self, tmp_path, monkeypatch
    ) -> None:
        # frob:tests \
        # tests/test_app.py::TestWaitCoverage.test_wait_coverage_flag_dispatches_and_ex\
        # its_zero_on_success  # noqa: E501
        import subprocess

        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        recorded: dict[str, object] = {}

        def _fake_wait(root):  # noqa: ANN001
            recorded["root"] = root
            return Ok(CoverageWaitOutcome(ran=True, duration_s=1.5))

        monkeypatch.setattr("frob.testing.run_coverage_wait", _fake_wait)
        cfg = AppConfig(
            test_wait_coverage=True,
            test_path=tmp_path,
        )
        run(cfg)  # must not raise/exit
        assert recorded["root"] == tmp_path.resolve()

    def test_wait_coverage_flag_exits_1_on_failure(self, tmp_path, monkeypatch) -> None:
        # frob:tests \
        # tests/test_app.py::TestWaitCoverage.test_wait_coverage_flag_exits_1_on_failur\
        # e  # noqa: E501
        import subprocess

        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)

        def _fake_wait(root):  # noqa: ANN001
            return Err(CoverageWaitError.RunFailed)

        monkeypatch.setattr("frob.testing.run_coverage_wait", _fake_wait)
        cfg = AppConfig(
            test_wait_coverage=True,
            test_path=tmp_path,
        )
        with pytest.raises(SystemExit) as exc_info:
            run(cfg)
        assert exc_info.value.code == 1


# frob:ticket T-0983
class TestStabilityGate:
    """Flake-quarantine tracking wired into `frob test`'s own run path
    (`_track_python_stability_and_gate`, T-0635 -- T-0575's disclosed
    cut; T-0983 added the dotted-symref-to-pytest-node-id conversion
    regression test)."""

    def test_all_sentinel_selection_is_noop(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_app.py::TestStabilityGate.test_all_sentinel_selection_is_noop  # \
        # noqa: E501
        report = SelectionReport(
            touched=(),
            selected={"python": ("*",)},
            ripple=(),
            unbound=(),
            fallback="all",
        )
        test_run = TestRunReport(
            selection=report, outcomes=(_outcome("python", 1),), ok=False
        )
        assert _track_python_stability_and_gate(tmp_path, report, test_run) is False

    def test_empty_python_selection_is_noop(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_app.py::TestStabilityGate.test_empty_python_selection_is_noop  # \
        # noqa: E501
        report = SelectionReport(
            touched=(), selected={}, ripple=(), unbound=(), fallback="package"
        )
        test_run = TestRunReport(selection=report, outcomes=(), ok=True)
        assert _track_python_stability_and_gate(tmp_path, report, test_run) is True

    def test_quarantined_failure_promotes_to_ok(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests \
        # tests/test_app.py::TestStabilityGate.test_quarantined_failure_promotes_to_ok  \
        # # noqa: E501
        node_id = "tests/t.py::a"
        ticket = new_ticket(
            tmp_path,
            TicketSpec(title="flake", kind=TicketKind.BUG, origin=Origin.AGENT),
        ).danger_ok
        quarantine(tmp_path, node_id, ticket_id=ticket.id)
        record_outcomes(tmp_path, {node_id: True})
        monkeypatch.setattr(
            "frob.testing.capture_python_outcomes",
            lambda root, node_ids: Ok({node_id: False}),
        )
        report = SelectionReport(
            touched=(),
            selected={"python": (node_id,)},
            ripple=(),
            unbound=(),
            fallback="package",
        )
        test_run = TestRunReport(
            selection=report, outcomes=(_outcome("python", 1),), ok=False
        )
        assert _track_python_stability_and_gate(tmp_path, report, test_run) is True

    def test_hard_regressed_quarantine_stays_failed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests \
        # tests/test_app.py::TestStabilityGate.test_hard_regressed_quarantine_stays_fai\
        # led  # noqa: E501
        node_id = "tests/t.py::a"
        ticket = new_ticket(
            tmp_path,
            TicketSpec(title="flake", kind=TicketKind.BUG, origin=Origin.AGENT),
        ).danger_ok
        quarantine(tmp_path, node_id, ticket_id=ticket.id)
        record_outcomes(tmp_path, {node_id: False})
        record_outcomes(tmp_path, {node_id: False})
        monkeypatch.setattr(
            "frob.testing.capture_python_outcomes",
            lambda root, node_ids: Ok({node_id: False}),
        )
        report = SelectionReport(
            touched=(),
            selected={"python": (node_id,)},
            ripple=(),
            unbound=(),
            fallback="package",
        )
        test_run = TestRunReport(
            selection=report, outcomes=(_outcome("python", 1),), ok=False
        )
        assert _track_python_stability_and_gate(tmp_path, report, test_run) is False

    def test_other_language_failure_not_masked(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests \
        # tests/test_app.py::TestStabilityGate.test_other_language_failure_not_masked  \
        # # noqa: E501
        node_id = "tests/t.py::a"
        ticket = new_ticket(
            tmp_path,
            TicketSpec(title="flake", kind=TicketKind.BUG, origin=Origin.AGENT),
        ).danger_ok
        quarantine(tmp_path, node_id, ticket_id=ticket.id)
        record_outcomes(tmp_path, {node_id: True})
        monkeypatch.setattr(
            "frob.testing.capture_python_outcomes",
            lambda root, node_ids: Ok({node_id: False}),
        )
        report = SelectionReport(
            touched=(),
            selected={"python": (node_id,), "rust": ("crate",)},
            ripple=(),
            unbound=(),
            fallback="package",
        )
        test_run = TestRunReport(
            selection=report,
            outcomes=(_outcome("python", 1), _outcome("rust", 1)),
            ok=False,
        )
        # the python failure alone is fully excused, but the rust outcome
        # is untouched by this gate -- the overall run must stay failed.
        assert _track_python_stability_and_gate(tmp_path, report, test_run) is False

    # frob:ticket T-0983
    def test_dotted_symref_converted_to_pytest_node_id(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests \
        # tests/test_app.py::TestStabilityGate.test_dotted_symref_converted_to_pytest_node_id  # noqa: E501
        """T-0983: `report.selected["python"]` holds the graph's dotted
        symref form (`path::Class.method`), never a real pytest node id --
        `capture_python_outcomes` must receive the `::`-joined form
        (`path::Class::method`), the same conversion `run_selected` applies
        for the primary run via `_to_node_id`. Before the fix this pass
        handed pytest the dotted form directly, which pytest cannot collect
        (exit 5, 0 outcomes) -- silently no-oping stability recording."""
        symref = "tests/t.py::A.b"
        seen: list[tuple] = []

        def _fake_capture(root: Path, node_ids: tuple):  # noqa: ANN001, ANN202
            seen.append(node_ids)
            return Ok({node_ids[0]: True})

        monkeypatch.setattr(
            "frob.testing.capture_python_outcomes",
            _fake_capture,
        )
        report = SelectionReport(
            touched=(),
            selected={"python": (symref,)},
            ripple=(),
            unbound=(),
            fallback="package",
        )
        test_run = TestRunReport(
            selection=report, outcomes=(_outcome("python", 0),), ok=True
        )
        _track_python_stability_and_gate(tmp_path, report, test_run)
        assert seen == [("tests/t.py::A::b",)]

    def test_capture_error_skips_gate(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_app.py::TestStabilityGate.test_capture_error_skips_gate \
        #  # noqa: E501
        from frob.testing import FlakeError

        monkeypatch.setattr(
            "frob.testing.capture_python_outcomes",
            lambda root, node_ids: Err(FlakeError.CaptureSpawnFailed),
        )
        report = SelectionReport(
            touched=(),
            selected={"python": ("tests/t.py::a",)},
            ripple=(),
            unbound=(),
            fallback="package",
        )
        test_run = TestRunReport(
            selection=report, outcomes=(_outcome("python", 1),), ok=False
        )
        # capture failed -- the original (unquarantined) result stands.
        assert _track_python_stability_and_gate(tmp_path, report, test_run) is False
