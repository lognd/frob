"""T-2911: `frob status`'s one genuinely new computation
(`compute_findings_movement`) plus the honesty rules that computation must
obey -- a stale/absent baseline, or no current measurement, must never
render a fabricated delta.

Subprocess-free, matching `tests/test_gates.py::TestBaselineDelta`'s own
style precedent for the same `Violation`/`violation_fingerprint` primitives
this module reuses directly -- no new fingerprint logic to test twice."""

from __future__ import annotations

from pathlib import Path

from frob.app.status_runner import (
    FindingsMovement,
    compute_findings_movement,
)
from frob.gates import Severity, Violation, stamp_baseline, violation_fingerprint


def _violation(rule="R1", file="a.py", message="m", severity=Severity.WARN, line=1):
    return Violation(
        rule=rule, severity=severity, file=file, line=line, message=message
    )


class TestComputeFindingsMovement:
    """The one new computation this ticket adds: healed/introduced/net
    over a baseline dict's fingerprints vs. a current violation tuple."""

    # frob:tests tests/test_status.py::TestComputeFindingsMovement.test_must_not_invent_missing_baseline kind="unit"  # noqa: E501
    def test_must_not_invent_missing_baseline(self) -> None:
        """T-2911 must-not-invent control: no baseline at all -> `measured`
        is `False`, every count stays `None` (never coerced to 0), and the
        note names the exact remedy command."""
        result = compute_findings_movement(
            None, stale=False, current_violations=None, gates_covered=()
        )
        assert result.measured is False
        assert result.healed is None
        assert result.introduced is None
        assert result.net is None
        assert "frob check --stamp-baseline" in result.note

    # frob:tests tests/test_status.py::TestComputeFindingsMovement.test_must_not_invent_stale_baseline kind="unit"  # noqa: E501
    def test_must_not_invent_stale_baseline(self) -> None:
        """T-2911 must-not-invent control: a STALE baseline -- the exact
        shape that produced this session's own 53-commit-stale-watermark
        incident -- must refuse a delta, not print a confident-but-wrong
        one."""
        result = compute_findings_movement(
            {"fingerprints": ["x"]},
            stale=True,
            current_violations=None,
            gates_covered=(),
        )
        assert result.measured is False
        assert result.stale is True
        assert result.healed is None
        assert "STALE" in result.note

    # frob:tests tests/test_status.py::TestComputeFindingsMovement.test_must_not_invent_no_current_run kind="unit"  # noqa: E501
    def test_must_not_invent_no_current_run(self) -> None:
        """A fresh, non-stale baseline but NO current violation set (the
        gate scan itself failed, or was never run) must still refuse a
        delta -- `measured=False` is not exclusively a baseline-side
        condition."""
        result = compute_findings_movement(
            {"fingerprints": ["x"]},
            stale=False,
            current_violations=None,
            gates_covered=(),
        )
        assert result.measured is False
        assert result.healed is None

    # frob:tests tests/test_status.py::TestComputeFindingsMovement.test_must_show_healed_and_introduced kind="unit"  # noqa: E501
    def test_must_show_healed_and_introduced(self) -> None:
        """T-2911 must-show control: a baseline with two known findings, a
        current run with one of them fixed and one new one introduced --
        `healed=1`, `introduced=1`, `net=0`, and `measured=True`."""
        fixed = _violation(rule="R1", file="a.py", message="old")
        still_present = _violation(rule="R2", file="b.py", message="still")
        new_finding = _violation(rule="R3", file="c.py", message="new")
        baseline = {
            "fingerprints": [
                violation_fingerprint(fixed),
                violation_fingerprint(still_present),
            ]
        }
        result = compute_findings_movement(
            baseline,
            stale=False,
            current_violations=(still_present, new_finding),
            gates_covered=("invariant", "test"),
        )
        assert result.measured is True
        assert result.healed == 1
        assert result.introduced == 1
        assert result.net == 0
        assert result.gates_covered == ("invariant", "test")

    # frob:tests tests/test_status.py::TestComputeFindingsMovement.test_must_show_pure_healing_is_positive_net kind="unit"  # noqa: E501
    def test_must_show_pure_healing_is_positive_net(self) -> None:
        """Pure improvement (everything fixed, nothing new) reports a
        positive net -- the shape the coordinator's own "read as winning"
        goal depends on."""
        fixed_a = _violation(rule="R1", file="a.py")
        fixed_b = _violation(rule="R2", file="b.py")
        baseline = {
            "fingerprints": [
                violation_fingerprint(fixed_a),
                violation_fingerprint(fixed_b),
            ]
        }
        result = compute_findings_movement(
            baseline, stale=False, current_violations=(), gates_covered=("test",)
        )
        assert result.measured is True
        assert result.healed == 2
        assert result.introduced == 0
        assert result.net == 2

    # frob:tests tests/test_status.py::TestComputeFindingsMovement.test_honest_zero_when_nothing_moved kind="unit"  # noqa: E501
    def test_honest_zero_when_nothing_moved(self) -> None:
        """A real measurement that finds NO movement reports a real `0`,
        not `None` -- the honest-zero distinction cuts both ways: `None`
        means "not measured", `0` means "measured, nothing moved"."""
        same = _violation(rule="R1", file="a.py")
        baseline = {"fingerprints": [violation_fingerprint(same)]}
        result = compute_findings_movement(
            baseline,
            stale=False,
            current_violations=(same,),
            gates_covered=("test",),
        )
        assert result.measured is True
        assert result.healed == 0
        assert result.introduced == 0
        assert result.net == 0


class TestFindingsMovementModel:
    """`FindingsMovement`'s own field defaults -- construction sanity, not
    behavior already covered above."""

    # frob:tests tests/test_status.py::TestFindingsMovementModel.test_defaults_are_unmeasured_shaped kind="unit"  # noqa: E501
    def test_defaults_are_unmeasured_shaped(self) -> None:
        movement = FindingsMovement(measured=False, note="x")
        assert movement.healed is None
        assert movement.introduced is None
        assert movement.net is None
        assert movement.gates_covered == ()


# frob:ticket T-2999
class TestBuildStatusReportIntegration:
    """A thin integration check against a real (empty) worktree -- proves
    the assembly wiring itself (baseline load -> verify status -> ticket
    flow) does not crash end to end, complementing the pure-function
    coverage above."""

    # frob:tests tests/test_status.py::TestBuildStatusReportIntegration.test_no_baseline_reports_unmeasured_findings kind="unit"  # noqa: E501
    def test_no_baseline_reports_unmeasured_findings(self, tmp_path: Path) -> None:
        """A fresh directory with no `.frob/baseline` at all: `findings.
        measured` is `False`, and the assembly never raises trying to read
        a store that does not exist."""
        import subprocess

        from frob.app.status_runner import build_status_report

        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=tmp_path, check=True)
        report = build_status_report(tmp_path, only=[], include_tickets=False)
        assert report.findings.measured is False
        assert report.tickets_open is None

    # frob:tests tests/test_status.py::TestBuildStatusReportIntegration.test_baseline_locks_section_is_always_populated kind="unit"  # noqa: E501
    def test_baseline_locks_section_is_always_populated(self, tmp_path: Path) -> None:
        """T-2999: the baseline-locks section has no opt-out flag (unlike
        ticket flow) -- it is always present on `build_status_report`'s
        output, one entry per `frob.gates._lock_producer.KNOWN_LOCKS`,
        even against a fresh repo with none of the three locks committed
        (every entry reads UNMEASURED, not silently absent)."""
        import subprocess

        from frob.app.status_runner import build_status_report
        from frob.gates._lock_producer import KNOWN_LOCKS

        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=tmp_path, check=True)
        report = build_status_report(tmp_path, only=[], include_tickets=False)
        assert len(report.baseline_locks) == len(KNOWN_LOCKS)
        assert {lock.verdict for lock in report.baseline_locks} == {"UNMEASURED"}

    # frob:tests tests/test_status.py::TestBuildStatusReportIntegration.test_print_status_human_renders_every_baseline_lock_verdict kind="unit"  # noqa: E501
    def test_print_status_human_renders_every_baseline_lock_verdict(self) -> None:
        """T-2999: `_print_status_human`'s baseline-locks branch renders a
        distinct, verdict-specific line for ABANDONED/PINNED/UNMEASURED/
        FRESH -- one fixture status per verdict, asserting the rendered
        text actually differs (kills the `compare Eq swapped` mutants a
        pure-model test cannot reach)."""
        import io

        from frob.app.status_runner import (
            FindingsMovement,
            StatusReport,
            _print_status_human,
        )
        from frob.gates._lock_producer import LockPin, LockProducerStatus
        from frob.render import Renderer

        locks = (
            LockProducerStatus(
                name="abandoned-one",
                path_rel="a.lock.json",
                exists=True,
                last_stamp_commit="abc",
                last_stamp_date="2020-01-01",
                commits_since=100,
                code_commits_since=99,
                pin=None,
                verdict="ABANDONED",
            ),
            LockProducerStatus(
                name="pinned-one",
                path_rel="b.lock.json",
                exists=True,
                last_stamp_commit="abc",
                last_stamp_date="2020-01-01",
                commits_since=100,
                code_commits_since=99,
                pin=LockPin(reason="frozen on purpose"),
                verdict="PINNED",
            ),
            LockProducerStatus(
                name="unmeasured-one",
                path_rel="c.lock.json",
                exists=False,
                last_stamp_commit=None,
                last_stamp_date=None,
                commits_since=None,
                code_commits_since=None,
                pin=None,
                verdict="UNMEASURED",
            ),
            LockProducerStatus(
                name="fresh-one",
                path_rel="d.lock.json",
                exists=True,
                last_stamp_commit="abc",
                last_stamp_date="2020-01-01",
                commits_since=1,
                code_commits_since=1,
                pin=None,
                verdict="FRESH",
            ),
        )
        report = StatusReport(
            findings=FindingsMovement(measured=False, note="x"),
            verify_watermark_commit=None,
            verify_commits_since_watermark=None,
            verify_quarantine_raised=None,
            tickets_open=None,
            tickets_landed_today=None,
            trailing_net_rate=None,
            baseline_locks=locks,
        )
        buf = io.StringIO()
        r = Renderer.for_stream(buf, color_flag="never", no_color_flag=True)
        _print_status_human(r, report)
        text = buf.getvalue()
        assert "ABANDONED -- 99 commit(s)" in text
        assert "PINNED -- frozen on purpose" in text
        assert "UNMEASURED -- no committed lock" in text
        assert "fresh (1 commit(s) since last stamp)" in text

    # frob:tests tests/test_status.py::TestBuildStatusReportIntegration.test_stamped_baseline_with_no_tree_change_is_a_real_zero kind="unit"  # noqa: E501
    def test_stamped_baseline_with_no_tree_change_is_a_real_zero(
        self, tmp_path: Path
    ) -> None:
        """T-2911 must-show control against a real (not mocked) baseline
        store: stamp a baseline for one violation, then ask for findings
        movement over a `current_violations` set that reproduces the
        identical finding -- `measured=True`, `net=0`, a real zero, not a
        refusal."""
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "a.py").write_text("x = 1\n", encoding="utf-8")
        v = _violation(file="src/a.py")
        stamp_baseline(tmp_path, (v,))

        from frob.app.status_runner import compute_findings_movement
        from frob.gates import load_baseline

        baseline = load_baseline(tmp_path)
        assert baseline is not None
        result = compute_findings_movement(
            baseline, stale=False, current_violations=(v,), gates_covered=("x",)
        )
        assert result.measured is True
        assert result.healed == 0
        assert result.introduced == 0
        assert result.net == 0


class TestRunEndToEnd:
    """`run(cfg)`'s own dispatch: builds a report and prints it, in either
    rendering mode -- covers the one public symbol not otherwise exercised
    by the pure-function/integration tests above."""

    # frob:tests tests/test_status.py::TestRunEndToEnd.test_run_prints_human_text_by_default kind="unit"  # noqa: E501
    def test_run_prints_human_text_by_default(
        self, tmp_path: Path, capsys
    ) -> None:
        """`run(cfg)` with no `--json` prints the human-readable sections,
        not a JSON blob."""
        import subprocess

        from frob.app.config import AppConfig, Subcommand
        from frob.app.status_runner import run

        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=tmp_path, check=True)
        cfg = AppConfig(
            subcommand=Subcommand.status,
            status_path=tmp_path,
            status_no_tickets=True,
        )
        run(cfg)
        out = capsys.readouterr().out
        assert "== findings movement ==" in out
        assert "== verification lag ==" in out
        assert "== ticket movement ==" in out

    # frob:tests tests/test_status.py::TestRunEndToEnd.test_run_prints_json_when_requested kind="unit"  # noqa: E501
    def test_run_prints_json_when_requested(self, tmp_path: Path, capsys) -> None:
        """`run(cfg)` with `status_json=True` prints a single JSON document
        matching `StatusReport`'s own schema."""
        import json
        import subprocess

        from frob.app.config import AppConfig, Subcommand
        from frob.app.status_runner import run

        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=tmp_path, check=True)
        cfg = AppConfig(
            subcommand=Subcommand.status,
            status_path=tmp_path,
            status_no_tickets=True,
            status_json=True,
        )
        run(cfg)
        out = capsys.readouterr().out
        payload = json.loads(out)
        assert payload["findings"]["measured"] is False
        assert payload["tickets_open"] is None

    # frob:tests tests/test_status.py::TestRunEndToEnd.test_default_cfg_skips_ticket_flow_and_says_so kind="unit"  # noqa: E501
    def test_default_cfg_skips_ticket_flow_and_says_so(
        self, tmp_path: Path, capsys
    ) -> None:
        """T-2950: a bare `AppConfig` (no `--tickets`, no `--no-tickets` --
        the real `frob status` default) must never even attempt the
        expensive ticket-flow mining, and must say so honestly rather than
        silently omitting the section."""
        import subprocess

        from frob.app.config import AppConfig, Subcommand
        from frob.app.status_runner import run

        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=tmp_path, check=True)
        cfg = AppConfig(subcommand=Subcommand.status, status_path=tmp_path)
        assert cfg.status_tickets is False
        run(cfg)
        out = capsys.readouterr().out
        assert "== ticket movement ==" in out
        assert "not measured: ticket-flow mining is off by default" in out
        assert "--tickets" in out


class TestAddStatusParser:
    """`_add_status_parser`'s own argparse wiring -- the CLI layer `run()`
    sits behind, otherwise untested (its only other reference is the
    single `from ._status import` in `_cli_parsers/__init__.py`)."""

    # frob:tests tests/test_status.py::TestAddStatusParser.test_registers_status_subcommand_with_expected_flags kind="unit"  # noqa: E501
    def test_registers_status_subcommand_with_expected_flags(self) -> None:
        """`frob status --path DIR --json --only GATE --tickets
        --no-tickets` parses into the exact `status_*` dest names
        `AppConfig`'s forwarding tuples expect."""
        import argparse

        from frob._cli_parsers._status import _add_status_parser

        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(dest="subcommand")
        _add_status_parser(sub)

        args = parser.parse_args(
            [
                "status",
                "--path",
                "/tmp/x",
                "--json",
                "--only",
                "invariant",
                "--only",
                "test",
                "--tickets",
                "--no-tickets",
            ]
        )
        assert args.status_path == "/tmp/x"
        assert args.status_json is True
        assert args.status_only == ["invariant", "test"]
        assert args.status_tickets is True
        assert args.status_no_tickets is True

    # frob:tests tests/test_status.py::TestAddStatusParser.test_bare_status_has_no_op_defaults kind="unit"  # noqa: E501
    def test_bare_status_has_no_op_defaults(self) -> None:
        """A bare `frob status` with no flags parses with every optional
        dest at its non-invasive default -- T-2950: `status_tickets`
        defaults to `False`, so the expensive ticket-flow mining is off
        unless explicitly requested."""
        import argparse

        from frob._cli_parsers._status import _add_status_parser

        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(dest="subcommand")
        _add_status_parser(sub)

        args = parser.parse_args(["status"])
        assert args.status_path is None
        assert args.status_json is False
        assert args.status_only == []
        assert args.status_tickets is False
        assert args.status_no_tickets is False
