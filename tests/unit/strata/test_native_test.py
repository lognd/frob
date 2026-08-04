"""T-1470: TEST005 branch-coverage burn-down for
`frob.strata._native_test`, the in-process `frob sys audit` invocation
`frob.testing._runners.run_selected` uses for a touched `.strata`
selection (T-0242). `tests/test_testing.py::TestNativeStrataAudit`
already exercises `run_native_sys_audit`'s happy path plus its
`ids.errors`/`repo_benign.is_err` branches through the full `run_selected`
integration surface; this module fills the remaining gaps that surface
never reaches: `evaluate_exhaustiveness`'s and `check_self_conformance`'s
own `is_err` branches (139-140/144-145), and `_summarize`'s
zero-gaps "PROVED" branch (91) -- the latter two never fire through a
real design tree in this repo's own fixtures without deliberately
crafting a warning-free, violation-free model, so this module targets
them directly instead."""

from __future__ import annotations

from pathlib import Path

import pytest
from typani.result import Err, Ok

from frob.strata import _native_test
from frob.strata._audit import AuditReport, FamilyGap
from frob.strata._errors import StrataError
from frob.strata._native_test import (
    _format_gaps,
    _format_selfconform,
    _summarize,
    run_native_sys_audit,
)
from frob.strata._selfconform import SelfConformReport, SelfConformViolation


def _write(root: Path, rel: str, text: str) -> None:
    """Write `text` to `root/rel`, creating parent directories as needed."""
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


_MODEL = """module m
node client : foreign { clearance Public; }
node api : authenticated { clearance Internal; }
flow f_login : client -> api
boundary b_login endorse f_login : foreign -> authenticated when "jwt_verified"
"""


class TestSummarize:
    """`_summarize`/`_format_gaps`/`_format_selfconform` direct unit
    coverage -- the "PROVED, zero unwaived gaps" branch (line 91) never
    fires through this repo's own real design tree (it always has
    findings), so it is exercised directly against synthetic reports
    here rather than end-to-end."""

    # frob:tests \
    # tests/unit/strata/test_native_test.py::TestSummarize.test_no_gaps_reports_proved
    def test_no_gaps_reports_proved(self) -> None:
        """Zero unwaived gaps on both the exhaustiveness and
        self-conformance reports takes `_summarize`'s ELSE branch."""
        report = AuditReport(views_checked=("security:owasp-top-10",))
        selfconform = SelfConformReport()

        summary = _summarize(report, selfconform)

        assert "checked 1 view(s): security:owasp-top-10" in summary
        assert "PROVED -- zero unwaived gaps" in summary

    # frob:tests \
    # tests/unit/strata/test_native_test.py::TestSummarize.test_gaps_present_lists_them\
    # _instead_of_proved
    def test_gaps_present_lists_them_instead_of_proved(self) -> None:
        """A non-empty gap list takes the `if gap_lines:` branch, not the
        else -- and never prints the PROVED sentinel."""
        gap = FamilyGap(
            family="security", view="owasp-top-10", rule="A1", target="m", detail="d"
        )
        report = AuditReport(views_checked=("security:owasp-top-10",), gaps=(gap,))
        selfconform = SelfConformReport()

        summary = _summarize(report, selfconform)

        assert "PROVED" not in summary
        assert "GAP family=security view=owasp-top-10 rule=A1 target=m detail=d" in summary

    # frob:tests \
    # tests/unit/strata/test_native_test.py::TestSummarize.test_format_selfconform_one_\
    # line_per_violation
    def test_format_selfconform_one_line_per_violation(self) -> None:
        """`_format_selfconform` renders one `GAP family=sys` line per
        unwaived `SelfConformViolation`, independent of `_format_gaps`."""
        violation = SelfConformViolation(rule="SYS100", node="frob.app", detail="bad")

        lines = _format_selfconform(SelfConformReport(violations=(violation,)))

        assert lines == ["GAP family=sys rule=SYS100 node=frob.app detail=bad"]

    # frob:tests \
    # tests/unit/strata/test_native_test.py::TestSummarize.test_format_gaps_empty_is_em\
    # pty_list
    def test_format_gaps_empty_is_empty_list(self) -> None:
        """No gaps on the report -- `_format_gaps` returns an empty list,
        not None or a sentinel."""
        assert _format_gaps(AuditReport()) == []


class TestRunNativeSysAuditErrorBranches:
    """`run_native_sys_audit`'s two downstream-`is_err` branches
    (`evaluate_exhaustiveness`, `check_self_conformance`) -- neither is
    reachable through a real design tree without a genuinely broken
    kernel/scan, so both are exercised via monkeypatch, matching how
    `tests/test_testing.py::TestNativeStrataAudit.test_bad_design_file_fails`
    already isolates `run_native_sys_audit`'s OTHER error branch
    (`ids.errors`) the same way."""

    # frob:tests \
    # tests/unit/strata/test_native_test.py::TestRunNativeSysAuditErrorBranches.test_ex\
    # haustiveness_error_propagates
    def test_exhaustiveness_error_propagates(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`evaluate_exhaustiveness` returning `Err` short-circuits
        `run_native_sys_audit` with that same error -- `check_self_
        conformance` is never reached (lines 138-140)."""
        _write(tmp_path, "design/m.strata", _MODEL)
        monkeypatch.setattr(
            _native_test,
            "evaluate_exhaustiveness",
            lambda model, benign: Err(StrataError.UnknownReference),
        )

        result = run_native_sys_audit(tmp_path)

        assert result.is_err
        assert result.danger_err == StrataError.UnknownReference

    # frob:tests \
    # tests/unit/strata/test_native_test.py::TestRunNativeSysAuditErrorBranches.test_se\
    # lfconform_error_propagates
    def test_selfconform_error_propagates(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`check_self_conformance` returning `Err` after a SUCCESSFUL
        exhaustiveness evaluation surfaces as `run_native_sys_audit`'s own
        `Err` (lines 142-145) -- the real exhaustiveness result is
        computed and discarded, never inspected once self-conformance
        fails."""
        _write(tmp_path, "design/m.strata", _MODEL)
        monkeypatch.setattr(
            _native_test,
            "check_self_conformance",
            lambda model, root: Err(StrataError.MalformedLattice),
        )

        result = run_native_sys_audit(tmp_path)

        assert result.is_err
        assert result.danger_err == StrataError.MalformedLattice

    # frob:tests \
    # tests/unit/strata/test_native_test.py::TestRunNativeSysAuditErrorBranches.test_bo\
    # th_reports_clean_is_proved
    def test_both_reports_clean_is_proved(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A clean exhaustiveness report AND a clean self-conformance
        report together take the happy path all the way through
        `proved=True` -- exercised via monkeypatch since this repo's own
        real design tree always carries some findings, unlike a minimal
        synthetic fixture model."""
        _write(tmp_path, "design/m.strata", _MODEL)
        monkeypatch.setattr(
            _native_test,
            "evaluate_exhaustiveness",
            lambda model, benign: Ok(AuditReport(views_checked=("security:owasp-top-10",))),
        )
        monkeypatch.setattr(
            _native_test,
            "check_self_conformance",
            lambda model, root: Ok(SelfConformReport()),
        )

        result = run_native_sys_audit(tmp_path)

        assert result.is_ok
        outcome = result.danger_ok
        assert outcome.proved is True
        assert "PROVED -- zero unwaived gaps" in outcome.summary
