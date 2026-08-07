"""T-0846 (TEST016 round): unit tests for `_check_gate_findings_fn`, the CLI
closure that spawns a fresh `frob check --ticket` and parses its `## Errors`
diagnostic lines into a `frozenset[(rule_id, file)]` identity set -- the
land-side masking-gap fix's real data source. Also covers `_python_for_tree`
(T-0846 follow-up: the interpreter both this closure and
`_check_gates_summary_fn` spawn under must resolve from the CHECKED tree,
not the calling process -- the T-0441 catch-22).

Follows `tests/unit/test_ticket_runner_land_release.py`'s precedent:
monkeypatch the actual `subprocess.run` seam `guarded_subprocess_run` calls
(`frob.process._guard.subprocess.run`), never a real `frob check` spawn --
these are pure/unit tests for the parsing and kwarg-shape logic, not an
end-to-end integration test (that already exists in
`tests/test_ticket_land.py::TestDoneReportThenLandRealClosuresEndToEnd`)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from frob.app import ticket_runner
from frob.process import _guard


class _FakeProc:
    """Minimal stand-in for `subprocess.CompletedProcess` -- only the
    attributes `_check_gate_findings_fn` actually reads."""

    def __init__(self, returncode: int, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


# frob:ticket T-1703
def _check_result_json(
    *,
    errors: list[tuple[str, str, str]] = (),  # (tool, code, file)
    warnings: list[tuple[str, str, str]] = (),
    gate_summary: str | None,
) -> str:
    """A minimal `frob check --json` `CheckResult` payload (T-1703): every
    in-scope caller of `_parse_error_findings_from_stdout`/
    `_check_gates_summary_fn` now spawns `--json`, so these fixtures must
    be real structured payloads, not the pre-T-1703 rendered-text shape
    they replace -- a fixture built from a well-formed complete text
    `## Errors` section would prove nothing about the failure mode T-1703
    actually closed (a diagnostic whose renderer never matched the old
    regex at all, and a run whose `results` never got a chance to
    populate a section because a stage never ran). `gate_summary=None`
    omits the `"gate-summary"` tool result entirely, simulating a run
    that never reached/reported gates (unmeasured)."""
    results: list[dict] = []
    for tool, code, file in errors:
        results.append(
            {
                "tool": tool,
                "exit_code": 1,
                "diagnostics": [
                    {"file": file, "severity": "error", "code": code, "message": code}
                ],
                "tests": [],
                "summary": "",
            }
        )
    for tool, code, file in warnings:
        results.append(
            {
                "tool": tool,
                "exit_code": 0,
                "diagnostics": [
                    {"file": file, "severity": "warning", "code": code, "message": code}
                ],
                "tests": [],
                "summary": "",
            }
        )
    if gate_summary is not None:
        results.append(
            {
                "tool": "gate-summary",
                "exit_code": 0,
                "diagnostics": [],
                "tests": [],
                "summary": gate_summary,
            }
        )
    return json.dumps({"path": ".", "results": results})


# frob:ticket T-0850
# frob:ticket T-1703
_TWO_FINDINGS_STDOUT = _check_result_json(
    errors=[
        ("gate:SEC", "SEC110", "src/frob/x.py"),
        ("gate:PII", "PII010", "tests/other.py"),
    ],
    warnings=[("gate:PERF", "PERF001", "src/x.py")],
    gate_summary="2 errors, 1 warnings, 0 waived  [archgate=1.00s]",
)

# frob:ticket T-0850
# frob:ticket T-1703
# T-0850: a fixture whose error set mixes two `SCOPED_RUN_FLAKY_RULE_IDS`
# findings (SCOPE001, COV002) with one non-flaky finding (SEC110) -- the
# flaky pair must be excluded from both `_check_gate_findings_fn`'s
# identity set and `_check_gates_summary_fn`'s derived error count,
# leaving only the non-flaky finding/count of 1.
_MIXED_FLAKY_AND_REAL_FINDINGS_STDOUT = _check_result_json(
    errors=[
        ("gate:SCOPE", "SCOPE001", "src/frob/tickets/_land.py"),
        ("gate:COV", "COV002", "tests/other.py"),
        ("gate:SEC", "SEC110", "src/frob/x.py"),
    ],
    gate_summary="3 errors, 0 warnings, 0 waived  [archgate=1.00s]",
)

_NO_ERRORS_HEADING_MEASURED_STDOUT = _check_result_json(
    gate_summary="0 errors, 0 warnings, 0 waived  [archgate=1.00s]",
)

_UNPARSABLE_STDOUT = "some garbage output with no gate-summary line at all\n"

# frob:ticket T-1703
# T-1703's own live incident, reconstructed exactly: a `ty` diagnostic
# (`file:line:col`, the shape `_GATE_ERROR_LINE_RE`'s pre-T-1703 regex
# never matched, since its capture group required `:\d+\s` immediately
# after `file` with no room for a `:col` suffix) alongside an ordinary
# gate error -- both must appear in the parsed identity set now that
# extraction reads the structured `code`/`file` fields directly instead
# of re-deriving them from rendered text.
_TY_AND_GATE_ERROR_STDOUT = _check_result_json(
    errors=[
        ("ty", "unresolved-attribute", "src/frob/x.py"),
        ("gate:SEC", "SEC110", "src/frob/y.py"),
    ],
    gate_summary="2 errors, 0 warnings, 0 waived  [archgate=1.00s]",
)

# frob:ticket T-1703
# A `--budget`-truncated run's own JSON shape: a `"budget"` tool result
# carrying a BUDGET001 diagnostic, alongside whatever DID run -- the
# truncated/partial-run failure mode T-1703 closed. Must parse as `None`
# (unmeasured), never as "the stage groups that ran, zero findings".
_BUDGET_TRUNCATED_STDOUT = json.dumps(
    {
        "path": ".",
        "results": [
            {
                "tool": "gate:SEC",
                "exit_code": 0,
                "diagnostics": [],
                "tests": [],
                "summary": "",
            },
            {
                "tool": "gate-summary",
                "exit_code": 0,
                "diagnostics": [],
                "tests": [],
                "summary": "0 errors, 0 warnings, 0 waived  [archgate=1.00s]",
            },
            {
                "tool": "budget",
                "exit_code": 0,
                "diagnostics": [
                    {
                        "file": None,
                        "line": None,
                        "col": None,
                        "severity": "warning",
                        "code": "BUDGET001",
                        "message": (
                            "BUDGET001: --budget 300 deferred 1 stage "
                            "group(s) to a later run: static. Resume state "
                            "persisted -- run `frob check --budget "
                            "<seconds>` again to continue."
                        ),
                    }
                ],
                "tests": [],
                "summary": "deferred 1 stage group(s): static",
            },
        ],
    }
)


class TestCheckGateFindingsFn:
    """`_check_gate_findings_fn` parsing/filtering behavior -- each method
    below carries its own `frob:tests` edge (T-1055: this class docstring
    used to itself be a class-level `frob:tests` directive, flagged
    PLACE001 as class-falling-back when it was really meant for the
    method immediately below, which already has its own directive)."""

    # frob:ticket T-0846
    # frob:ticket T-0850
    def test_parses_multiple_findings_from_errors_section(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_ticket_runner_gate_findings.py::TestCheckGateFindingsFn.test_parses_multiple_findings_from_errors_section  # noqa: E501
        """The happy path: a real `## Errors` section with two diagnostic
        lines parses into the exact `(rule_id, file)` pair set, ignoring
        the `## Warnings` section entirely (only errors are identity-
        compared at land)."""

        def _fake_run(argv, **kwargs):  # noqa: ANN001, ANN202
            return _FakeProc(1, stdout=_TWO_FINDINGS_STDOUT)

        monkeypatch.setattr(_guard.subprocess, "run", _fake_run)
        fn = ticket_runner._check_gate_findings_fn(tmp_path, "T-0001")
        result = fn()
        assert result == frozenset(
            {
                ("SEC110", "src/frob/x.py"),
                ("PII010", "tests/other.py"),
            }
        )

    # frob:ticket T-0850
    def test_scoped_run_flaky_rule_excluded_from_findings(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_ticket_runner_gate_findings.py::TestCheckGateFindingsFn.test_scoped_run_flaky_rule_excluded_from_findings  # noqa: E501
        """T-0850: SCOPE001/COV002 findings are diff-scoped and can flap
        between two `--ticket`-scoped runs on base drift alone, not a real
        regression -- `_check_gate_findings_fn` must exclude them from its
        returned identity set entirely, leaving only the non-flaky SEC110
        finding. An asymmetric exclusion (only at land's reverify end, not
        also at done-report's capture end -- both routed through this SAME
        closure factory) would still diverge on pure drift noise, so this
        also pins that both callers get the filtered result via one shared
        code path rather than each needing its own filter."""

        def _fake_run(argv, **kwargs):  # noqa: ANN001, ANN202
            return _FakeProc(1, stdout=_MIXED_FLAKY_AND_REAL_FINDINGS_STDOUT)

        monkeypatch.setattr(_guard.subprocess, "run", _fake_run)
        fn = ticket_runner._check_gate_findings_fn(tmp_path, "T-0001")
        result = fn()
        assert result == frozenset({("SEC110", "src/frob/x.py")})

    # frob:ticket T-0846
    def test_refused_spawn_returns_none_not_empty_set(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_ticket_runner_gate_findings.py::TestCheckGateFindingsFn.test_refused_spawn_returns_none_not_empty_set  # noqa: E501
        """T-0803-style kill-switch proof: with `FROB_DISABLE_EXEC=1`,
        `guarded_subprocess_run` refuses BEFORE ever calling
        `subprocess.run` -- proven with a spy that would observe a real
        spawn attempt. Must return `None` (unmeasured), never
        `frozenset()` (which would read as "measured, definitely zero" and
        let land's identity comparison wrongly treat this as authoritative
        of a genuinely empty finding set)."""
        monkeypatch.setenv("FROB_DISABLE_EXEC", "1")
        spawned = False
        real_run = _guard.subprocess.run

        def _spy(*args, **kwargs):  # noqa: ANN001, ANN202
            nonlocal spawned
            spawned = True
            return real_run(*args, **kwargs)

        monkeypatch.setattr(_guard.subprocess, "run", _spy)
        fn = ticket_runner._check_gate_findings_fn(tmp_path, "T-0001")
        assert fn() is None
        assert not spawned

    # frob:ticket T-0846
    def test_unparsable_output_returns_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_ticket_runner_gate_findings.py::TestCheckGateFindingsFn.test_unparsable_output_returns_none  # noqa: E501
        """Output with no `## Errors` heading AND no parsable gate-summary
        line at all (a crash, a corrupted run) is UNMEASURED -- `None`,
        never a false "zero findings" claim."""

        def _fake_run(argv, **kwargs):  # noqa: ANN001, ANN202
            return _FakeProc(1, stdout=_UNPARSABLE_STDOUT)

        monkeypatch.setattr(_guard.subprocess, "run", _fake_run)
        fn = ticket_runner._check_gate_findings_fn(tmp_path, "T-0001")
        assert fn() is None

    # frob:ticket T-0846
    def test_no_errors_heading_with_parsable_summary_is_measured_empty(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_ticket_runner_gate_findings.py::TestCheckGateFindingsFn.test_no_errors_heading_with_parsable_summary_is_measured_empty  # noqa: E501
        """Boundary pin for the `len(section) < 2` guard (`section =
        stdout.split("## Errors", 1)` always has length 1 or 2, since
        `_section_lines` omits an empty section entirely): when the
        heading is genuinely ABSENT (`len(section) == 1`, the boundary
        just below the `< 2` cutoff) but the gate-summary line parses and
        confirms zero errors, this is a REAL measured empty set
        (`frozenset()`), not `None`.

        This pins the comparison DIRECTION, not just its outcome: an
        operand-swapped mutant (`2 < len(section)` instead of
        `len(section) < 2`) is never true for `len(section) in {1, 2}` --
        the "heading absent" branch would never fire, and the mutant would
        instead fall through to `section[1]`, which does not exist for a
        length-1 list -- an uncaught `IndexError`, which fails this test
        rather than silently returning the right-looking value by luck."""

        def _fake_run(argv, **kwargs):  # noqa: ANN001, ANN202
            return _FakeProc(0, stdout=_NO_ERRORS_HEADING_MEASURED_STDOUT)

        monkeypatch.setattr(_guard.subprocess, "run", _fake_run)
        fn = ticket_runner._check_gate_findings_fn(tmp_path, "T-0001")
        result = fn()
        assert result == frozenset()
        assert result is not None

    # frob:ticket T-0846
    def test_spawn_kwargs_capture_output_text_and_no_check(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_ticket_runner_gate_findings.py::TestCheckGateFindingsFn.test_spawn_kwargs_capture_output_text_and_no_check  # noqa: E501
        """Pins the exact `subprocess.run` kwarg SHAPE `guarded_subprocess_
        run` forwards verbatim -- `capture_output=True` and `text=True` (so
        `result.stdout` is a decoded str this closure can regex-match, not
        raw bytes or nothing at all) and `check=False` (a non-zero `frob
        check` exit -- the COMMON case, since `frob check --ticket` exits
        1 whenever it finds any error -- must not raise; this closure
        parses `result.stdout` regardless of exit code). A test asserting
        the real captured kwarg values, not just an end-to-end outcome, so
        each of the three flipped to its opposite is independently caught
        even where the parsed RESULT would otherwise look unchanged for
        this particular crafted stdout."""
        captured: dict[str, object] = {}

        def _fake_run(argv, **kwargs):  # noqa: ANN001, ANN202
            captured.update(kwargs)
            return _FakeProc(1, stdout=_TWO_FINDINGS_STDOUT)

        monkeypatch.setattr(_guard.subprocess, "run", _fake_run)
        fn = ticket_runner._check_gate_findings_fn(tmp_path, "T-0001")
        fn()
        assert captured["capture_output"] is True
        assert captured["text"] is True
        assert captured["check"] is False


class TestCheckGatesSummaryFn:
    """T-0850: `_check_gates_summary_fn`'s `errors` count must exclude
    `SCOPED_RUN_FLAKY_RULE_IDS` findings the same way
    `_check_gate_findings_fn`'s identity set does, so the count-only
    `ClaimDivergence` fallback (used whenever either side of the identity
    comparison is unavailable) does not diverge on the same diff-scoped
    base-drift noise the identity path already excludes."""

    # frob:ticket T-0850
    def test_scoped_run_flaky_rule_excluded_from_error_count(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_ticket_runner_gate_findings.py::TestCheckGatesSummaryFn.test_scoped_run_flaky_rule_excluded_from_error_count  # noqa: E501
        """The raw gate-summary line claims 3 errors (SCOPE001, COV002,
        SEC110), but SCOPE001/COV002 are `SCOPED_RUN_FLAKY_RULE_IDS` --
        the returned `errors` count must be 1 (only SEC110), not the raw
        3, proving the count is derived from the filtered `## Errors`
        section rather than trusting the printed summary count verbatim."""

        def _fake_run(argv, **kwargs):  # noqa: ANN001, ANN202
            return _FakeProc(1, stdout=_MIXED_FLAKY_AND_REAL_FINDINGS_STDOUT)

        monkeypatch.setattr(_guard.subprocess, "run", _fake_run)
        fn = ticket_runner._check_gates_summary_fn(tmp_path, "T-0001")
        errors, warnings, waived = fn()
        assert errors == 1
        assert warnings == 0
        assert waived == 0

    # frob:ticket T-0850
    def test_unparsable_errors_section_falls_back_to_raw_summary_count(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_ticket_runner_gate_findings.py::TestCheckGatesSummaryFn.test_unparsable_errors_section_falls_back_to_raw_summary_count  # noqa: E501
        """A parsable gate-summary line with no `## Errors` heading and no
        parsable identity set at all still returns a real measured count
        (0, from `_NO_ERRORS_HEADING_MEASURED_STDOUT`'s own summary line),
        matching this closure's pre-T-0850 unfiltered behavior when the
        `## Errors` section genuinely has nothing to filter."""

        def _fake_run(argv, **kwargs):  # noqa: ANN001, ANN202
            return _FakeProc(0, stdout=_NO_ERRORS_HEADING_MEASURED_STDOUT)

        monkeypatch.setattr(_guard.subprocess, "run", _fake_run)
        fn = ticket_runner._check_gates_summary_fn(tmp_path, "T-0001")
        errors, warnings, waived = fn()
        assert (errors, warnings, waived) == (0, 0, 0)


class TestParseErrorFindingsFromJson:
    """T-1703: the highest-integrity fix in this file -- a truncated/
    partial `--budget` run must yield `None`, never a smaller set, and a
    diagnostic whose OLD rendered-text shape never matched `_GATE_ERROR_
    LINE_RE` (`ty`'s `file:line:col`) must now appear in the parsed set
    since extraction reads structured `code`/`file` fields directly."""

    # frob:ticket T-1703
    def test_ty_and_gate_error_both_appear_in_parsed_set(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_ticket_runner_gate_findings.py::TestParseErrorFindingsFromJson.test_ty_and_gate_error_both_appear_in_parsed_set  # noqa: E501
        """T-1703's second named defect: `_GATE_ERROR_LINE_RE`'s text scan
        assumed every diagnostic renders as `[tag] file:line CODE
        message` -- `ty`'s `file:line:col` (an extra `:col` the regex's
        `:\\d+\\s` never matches) silently dropped every `ty` error from
        the identity set. Reading `code`/`file` off the structured JSON
        `Diagnostic` instead is immune to how a tool renders itself, so
        BOTH the `ty` error and an ordinary gate error must appear."""
        findings = ticket_runner._parse_error_findings_from_stdout(
            "T-0001", _TY_AND_GATE_ERROR_STDOUT, 1
        )
        assert findings == frozenset(
            {
                ("unresolved-attribute", "src/frob/x.py"),
                ("SEC110", "src/frob/y.py"),
            }
        )

    # frob:ticket T-1703
    def test_budget_truncated_run_yields_none_not_a_partial_set(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_ticket_runner_gate_findings.py::TestParseErrorFindingsFromJson.test_budget_truncated_run_yields_none_not_a_partial_set  # noqa: E501
        """T-1703's first, highest-integrity named defect: a `--budget`
        run that deferred any stage group must parse as `None`
        (unmeasured), never as the (possibly empty) set of what the
        stage groups that DID run happened to find -- a gate that never
        ran emits no diagnostic lines, so a partial run's error set is
        structurally indistinguishable from a genuinely clean full run
        unless the caller is told which stages actually ran. The live
        incident this closes: a deferred rapid-profile sweep logged
        `CLEAN, 0 errors` at a commit a full unscoped `frob check` found
        5 real errors in."""
        findings = ticket_runner._parse_error_findings_from_stdout(
            "T-0001", _BUDGET_TRUNCATED_STDOUT, 0
        )
        assert findings is None

    # frob:ticket T-1703
    def test_check_gates_summary_fn_returns_none_on_budget_truncated_run(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_ticket_runner_gate_findings.py::TestParseErrorFindingsFromJson.test_check_gates_summary_fn_returns_none_on_budget_truncated_run  # noqa: E501
        """The count-only path must refuse a truncated run the same way
        the identity-set path does -- a partial run's raw gate-summary
        count is not a smaller, still-trustworthy answer; it is a
        different question `_check_gates_summary_fn` must not answer at
        all."""

        def _fake_run(argv, **kwargs):  # noqa: ANN001, ANN202
            return _FakeProc(0, stdout=_BUDGET_TRUNCATED_STDOUT)

        monkeypatch.setattr(_guard.subprocess, "run", _fake_run)
        fn = ticket_runner._check_gates_summary_fn(tmp_path, "T-0001")
        assert fn() is None


class TestPythonForTree:
    """`_python_for_tree` resolution -- each method below carries its own
    `frob:tests` edge (T-1055: this class docstring used to itself be a
    class-level `frob:tests` directive, flagged PLACE001 as class-falling-
    back when it was really meant for the method immediately below,
    which already has its own directive)."""

    # frob:ticket T-0846
    def test_uses_tree_venv_python_when_present(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_ticket_runner_gate_findings.py::TestPythonForTree.test_uses_tree_venv_python_when_present  # noqa: E501
        """T-0441 catch-22 fix: when `root/.venv/bin/python` exists, that
        path is returned -- NOT `sys.executable` -- so a fresh `frob
        check` spawn runs the CHECKED tree's own installed code (the
        worktree's or root's own editable install), never whatever
        interpreter the calling process happens to run under."""
        venv_bin = tmp_path / ".venv" / "bin"
        venv_bin.mkdir(parents=True)
        venv_python = venv_bin / "python"
        venv_python.write_text("#!/bin/sh\n")

        assert ticket_runner._python_for_tree(tmp_path) == str(venv_python)

    # frob:ticket T-0846
    def test_falls_back_to_sys_executable_when_no_tree_venv(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/test_ticket_runner_gate_findings.py::TestPythonForTree.test_falls_back_to_sys_executable_when_no_tree_venv  # noqa: E501
        """No `.venv/bin/python` under `root` at all (a bare checkout, or a
        non-uv-managed tree) falls back to `sys.executable` -- never a
        hard error; this is strictly a refinement over the prior
        unconditional `sys.executable`, not a new failure mode."""
        assert ticket_runner._python_for_tree(tmp_path) == sys.executable

    # frob:ticket T-0846
    def test_check_gate_findings_fn_spawns_the_tree_venv_python(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_ticket_runner_gate_findings.py::TestPythonForTree.test_check_gate_findings_fn_spawns_the_tree_venv_python  # noqa: E501
        """End-to-end within `_check_gate_findings_fn`: given a `root` with
        its own `.venv/bin/python`, the spawned argv's interpreter is that
        path, not `sys.executable` -- the concrete T-0441 reproduction is
        exactly this: a root-checkout `land` re-verification must run
        against the WORKTREE/root tree's own installed `frob`, not the
        calling process's."""
        venv_bin = tmp_path / ".venv" / "bin"
        venv_bin.mkdir(parents=True)
        venv_python = venv_bin / "python"
        venv_python.write_text("#!/bin/sh\n")

        captured_argv: list[str] = []

        def _fake_run(argv, **kwargs):  # noqa: ANN001, ANN202
            captured_argv.extend(argv)
            return _FakeProc(1, stdout=_TWO_FINDINGS_STDOUT)

        monkeypatch.setattr(_guard.subprocess, "run", _fake_run)
        fn = ticket_runner._check_gate_findings_fn(tmp_path, "T-0001")
        fn()
        assert captured_argv[0] == str(venv_python)
        assert captured_argv[0] != sys.executable

    # frob:ticket T-0846
    def test_check_gates_summary_fn_spawns_the_tree_venv_python(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_ticket_runner_gate_findings.py::TestPythonForTree.test_check_gates_summary_fn_spawns_the_tree_venv_python  # noqa: E501
        """Same T-0441 fix, the sibling count-only closure: `_check_gates_
        summary_fn` must resolve the SAME tree-local interpreter, not just
        `_check_gate_findings_fn` -- both closures hit the identical
        catch-22 independently before this fix."""
        venv_bin = tmp_path / ".venv" / "bin"
        venv_bin.mkdir(parents=True)
        venv_python = venv_bin / "python"
        venv_python.write_text("#!/bin/sh\n")

        captured_argv: list[str] = []

        def _fake_run(argv, **kwargs):  # noqa: ANN001, ANN202
            captured_argv.extend(argv)
            return _FakeProc(
                0,
                stdout="frob check .  [PASS]  0 errors  0 warnings\n\ngate-summary 0 errors, 0 warnings, 0 waived\n",
            )

        monkeypatch.setattr(_guard.subprocess, "run", _fake_run)
        fn = ticket_runner._check_gates_summary_fn(tmp_path, "T-0001")
        fn()
        assert captured_argv[0] == str(venv_python)
        assert captured_argv[0] != sys.executable


class TestSharedCheckSpawnFn:
    """T-0919: `_shared_check_spawn_fn` spawns `frob check --ticket <id>`
    AT MOST ONCE, caching the result for every later call -- the fix for
    `done-report`/`land` each wiring up BOTH `_check_gates_summary_fn` and
    `_check_gate_findings_fn`, which before this ticket meant two full,
    serial `frob check --ticket` subprocess runs per command."""

    # frob:ticket T-0919
    def test_second_call_does_not_spawn_again(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_ticket_runner_gate_findings.py::TestSharedCheckSpawnFn.test_second_call_does_not_spawn_again  # noqa: E501
        """Calling the returned closure twice spawns `subprocess.run`
        exactly ONCE -- the second call returns the cached result."""
        spawn_count = 0

        def _fake_run(argv, **kwargs):  # noqa: ANN001, ANN202
            nonlocal spawn_count
            spawn_count += 1
            return _FakeProc(1, stdout=_TWO_FINDINGS_STDOUT)

        monkeypatch.setattr(_guard.subprocess, "run", _fake_run)
        spawn = ticket_runner._shared_check_spawn_fn(tmp_path, "T-0001")
        first = spawn()
        second = spawn()
        assert spawn_count == 1
        assert first is second

    # frob:ticket T-0919
    def test_spawn_kwargs_capture_output_text_and_no_check(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_ticket_runner_gate_findings.py::TestSharedCheckSpawnFn.test_spawn_kwargs_capture_output_text_and_no_check  # noqa: E501
        """Pins the exact `subprocess.run` kwarg SHAPE `_shared_check_spawn_
        fn`'s own `guarded_subprocess_run` call forwards -- `capture_output
        =True` and `text=True` (so `result.stdout` is a decoded str this
        closure's callers can regex-match, not raw bytes or nothing at all)
        and `check=False` (a non-zero `frob check` exit -- the COMMON case,
        since `frob check --ticket` exits 1 whenever it finds any error --
        must not raise; callers parse `result.stdout` regardless of exit
        code). Each of the three flipped to its opposite (`capture_output=
        False` drops `result.stdout` to `None`, `text=False` returns raw
        bytes a `str`-based regex can never match, `check=True` raises
        instead of returning a non-zero-exit result) is independently
        caught here, even where a same-shaped fake `subprocess.run` would
        otherwise look unchanged to a call-count-only assertion."""
        captured: dict[str, object] = {}

        def _fake_run(argv, **kwargs):  # noqa: ANN001, ANN202
            captured.update(kwargs)
            return _FakeProc(1, stdout=_TWO_FINDINGS_STDOUT)

        monkeypatch.setattr(_guard.subprocess, "run", _fake_run)
        spawn = ticket_runner._shared_check_spawn_fn(tmp_path, "T-0001")
        spawn()
        assert captured["capture_output"] is True
        assert captured["text"] is True
        assert captured["check"] is False

    # frob:ticket T-0919
    def test_check_gates_summary_fn_and_check_gate_findings_fn_share_one_spawn(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_ticket_runner_gate_findings.py::TestSharedCheckSpawnFn.test_check_gates_summary_fn_and_check_gate_findings_fn_share_one_spawn  # noqa: E501
        """The T-0919 fix itself, proven at the consumer level: passing the
        SAME `_shared_check_spawn_fn(...)` closure into both
        `_check_gates_summary_fn`'s and `_check_gate_findings_fn`'s
        `spawn` parameter (exactly what `_done_report`/`_land` now do)
        means calling BOTH resulting closures spawns `subprocess.run`
        exactly ONCE total, not twice -- the root cause this ticket
        fixes."""
        spawn_count = 0

        def _fake_run(argv, **kwargs):  # noqa: ANN001, ANN202
            nonlocal spawn_count
            spawn_count += 1
            return _FakeProc(1, stdout=_TWO_FINDINGS_STDOUT)

        monkeypatch.setattr(_guard.subprocess, "run", _fake_run)
        shared_spawn = ticket_runner._shared_check_spawn_fn(tmp_path, "T-0001")
        gates_fn = ticket_runner._check_gates_summary_fn(
            tmp_path, "T-0001", spawn=shared_spawn
        )
        findings_fn = ticket_runner._check_gate_findings_fn(
            tmp_path, "T-0001", spawn=shared_spawn
        )
        errors, warnings, waived = gates_fn()
        findings = findings_fn()
        assert spawn_count == 1
        assert (errors, warnings, waived) == (2, 1, 0)
        assert findings == frozenset(
            {("SEC110", "src/frob/x.py"), ("PII010", "tests/other.py")}
        )

    # frob:ticket T-0919
    def test_default_spawn_none_keeps_each_closure_independent(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_ticket_runner_gate_findings.py::TestSharedCheckSpawnFn.test_default_spawn_none_keeps_each_closure_independent  # noqa: E501
        """Backward-compat pin: NOT passing `spawn` (the pre-T-0919 call
        shape every existing test in this file still uses) still spawns
        once per closure -- two closures built with `spawn=None` (the
        default) spawn `subprocess.run` TWICE total, proving the sharing
        is opt-in via an explicit shared `spawn`, never implicit/global."""
        spawn_count = 0

        def _fake_run(argv, **kwargs):  # noqa: ANN001, ANN202
            nonlocal spawn_count
            spawn_count += 1
            return _FakeProc(1, stdout=_TWO_FINDINGS_STDOUT)

        monkeypatch.setattr(_guard.subprocess, "run", _fake_run)
        gates_fn = ticket_runner._check_gates_summary_fn(tmp_path, "T-0001")
        findings_fn = ticket_runner._check_gate_findings_fn(tmp_path, "T-0001")
        gates_fn()
        findings_fn()
        assert spawn_count == 2
