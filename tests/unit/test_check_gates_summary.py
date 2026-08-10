"""Tests for T-1664's UNRESOLVED outcome: a distinguished, countable
severity for a gate that could not determine an answer, kept separate
from real error/warning findings and never counted toward `frob check`'s
exit code (docs/modules/gates.md#unresolved-t-1664).
"""
# frob:ticket T-1664

from __future__ import annotations

from frob.gates._models import GateReport, GateStats, Severity, Violation


def _violation(rule: str, severity: Severity, file: str = "x.py") -> Violation:
    return Violation(
        rule=rule, severity=severity, file=file, line=1, message=f"{rule} finding"
    )


class TestSeverityUnresolved:
    def test_unresolved_is_a_distinct_severity_value(self) -> None:
        # frob:tests src/frob/gates/_models.py::Severity
        assert Severity.UNRESOLVED != Severity.ERROR
        assert Severity.UNRESOLVED != Severity.WARN
        assert Severity.UNRESOLVED.value == "unresolved"


class TestUnresolvedCount:
    def test_counts_only_unresolved_violations(self) -> None:
        # frob:tests src/frob/check/_python.py::_unresolved_count
        from frob.check._python import _unresolved_count

        violations = [
            _violation("REF001", Severity.ERROR),
            _violation("REF001", Severity.WARN),
            _violation("REF001", Severity.UNRESOLVED),
            _violation("REF001", Severity.UNRESOLVED),
        ]
        assert _unresolved_count(violations) == 2

    def test_zero_when_no_unresolved_present(self) -> None:
        # frob:tests src/frob/check/_python.py::_unresolved_count
        from frob.check._python import _unresolved_count

        violations = [_violation("REF001", Severity.ERROR)]
        assert _unresolved_count(violations) == 0


class TestDiagSeverity:
    def test_error_maps_to_error(self) -> None:
        # frob:tests src/frob/check/_python.py::_diag_severity
        from frob.check._python import _diag_severity

        assert _diag_severity(_violation("R", Severity.ERROR)) == "error"

    def test_warn_maps_to_warning(self) -> None:
        # frob:tests src/frob/check/_python.py::_diag_severity
        from frob.check._python import _diag_severity

        assert _diag_severity(_violation("R", Severity.WARN)) == "warning"

    def test_unresolved_maps_to_info_not_warning(self) -> None:
        # frob:tests src/frob/check/_python.py::_diag_severity
        # T-1664: UNRESOLVED must render distinctly from an ordinary
        # completed WARN finding, never collapse to "warning".
        from frob.check._python import _diag_severity

        assert _diag_severity(_violation("R", Severity.UNRESOLVED)) == "info"


class TestGatesFamilyResultUnresolved:
    def test_unresolved_findings_never_fail_the_family(self) -> None:
        # frob:tests src/frob/check/_python.py::_gates_family_result
        # A family with ONLY unresolved findings (no errors) must still
        # exit 0 -- UNRESOLVED is visible/countable, never a silent
        # second failure mode that floods the floor.
        from frob.check._python import _gates_family_result

        violations = [_violation("REF001", Severity.UNRESOLVED)]
        result = _gates_family_result("REF", violations, [])
        assert result.exit_code == 0
        assert "1 unresolved" in result.summary
        assert "0 errors" in result.summary

    def test_unresolved_count_shown_as_its_own_term_not_folded_into_warn(
        self,
    ) -> None:
        # frob:tests src/frob/check/_python.py::_gates_family_result
        from frob.check._python import _gates_family_result

        violations = [
            _violation("REF001", Severity.WARN),
            _violation("REF001", Severity.UNRESOLVED),
        ]
        result = _gates_family_result("REF", violations, [])
        assert "1 warning" in result.summary
        assert "1 unresolved" in result.summary

    def test_errors_still_fail_the_family_regardless_of_unresolved(self) -> None:
        # frob:tests src/frob/check/_python.py::_gates_family_result
        from frob.check._python import _gates_family_result

        violations = [
            _violation("REF001", Severity.ERROR),
            _violation("REF001", Severity.UNRESOLVED),
        ]
        result = _gates_family_result("REF", violations, [])
        assert result.exit_code == 1


class TestGatesSummaryUnresolved:
    def test_summary_line_names_unresolved_as_its_own_term(self) -> None:
        # frob:tests src/frob/check/_python.py::_gates_summary
        from frob.check._python import _gates_summary

        violations = [
            _violation("REF001", Severity.ERROR),
            _violation("REF001", Severity.UNRESOLVED),
            _violation("REF001", Severity.UNRESOLVED),
        ]
        report = GateReport(violations=tuple(violations), waived=(), stats=GateStats())
        summary = _gates_summary(violations, report, n_err=1, delta=False)
        assert "1 error" in summary
        assert "0 warning" in summary
        assert "2 unresolved" in summary
        assert "0 waived" in summary

    def test_zero_unresolved_still_names_the_term(self) -> None:
        # frob:tests src/frob/check/_python.py::_gates_summary
        # T-0228 (extended by T-1664): never omit a term just because it
        # is zero -- an omitted term reads as "not applicable", a
        # different, false claim from "checked, zero found".
        from frob.check._python import _gates_summary

        violations = [_violation("REF001", Severity.WARN)]
        report = GateReport(violations=tuple(violations), waived=(), stats=GateStats())
        summary = _gates_summary(violations, report, n_err=0, delta=False)
        assert "0 unresolved" in summary
