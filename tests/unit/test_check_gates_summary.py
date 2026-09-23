"""Tests for T-1664's UNRESOLVED outcome and T-5304's ADVISORY tier: two
distinguished, countable severities kept separate from real error/warning
findings and never counted toward `frob check`'s exit code
(docs/modules/gates.md#unresolved-t-1664,
docs/modules/gates.md#advisory-t-5304).
"""
# frob:ticket T-1664
# frob:ticket T-5304

from __future__ import annotations

from frob.gates._models import GateReport, GateStats, Severity, Violation


def _violation(rule: str, severity: Severity, file: str = "x.py") -> Violation:
    return Violation(
        rule=rule, severity=severity, file=file, line=1, message=f"{rule} finding"
    )


class TestSeverityUnresolved:
    def test_unresolved_is_a_distinct_severity_value(self) -> None:
        # frob:tests src/frob/findings.py::Severity
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
    """T-3985 made `root` a required positional on `_gates_family_result`
    (it drives `_family_subject_count`'s real filesystem probes, so a
    default risks silently computing a subject count against the wrong
    tree rather than failing loudly) -- every call site here passes
    `tmp_path` rather than reverting the signature. "REF" has no
    registered subject-count probe (only PROFILE001 does), so these
    calls are inert to `root`'s value; `tmp_path` keeps them isolated
    from this repo's own config regardless."""

    def test_unresolved_findings_never_fail_the_family(self, tmp_path) -> None:
        # frob:tests src/frob/check/_python.py::_gates_family_result
        # A family with ONLY unresolved findings (no errors) must still
        # exit 0 -- UNRESOLVED is visible/countable, never a silent
        # second failure mode that floods the floor.
        from frob.check._python import _gates_family_result

        violations = [_violation("REF001", Severity.UNRESOLVED)]
        result = _gates_family_result("REF", violations, [], tmp_path)
        assert result.exit_code == 0
        assert "1 unresolved" in result.summary
        assert "0 errors" in result.summary

    def test_unresolved_count_shown_as_its_own_term_not_folded_into_warn(
        self, tmp_path
    ) -> None:
        # frob:tests src/frob/check/_python.py::_gates_family_result
        from frob.check._python import _gates_family_result

        violations = [
            _violation("REF001", Severity.WARN),
            _violation("REF001", Severity.UNRESOLVED),
        ]
        result = _gates_family_result("REF", violations, [], tmp_path)
        assert "1 warning" in result.summary
        assert "1 unresolved" in result.summary

    def test_errors_still_fail_the_family_regardless_of_unresolved(
        self, tmp_path
    ) -> None:
        # frob:tests src/frob/check/_python.py::_gates_family_result
        from frob.check._python import _gates_family_result

        violations = [
            _violation("REF001", Severity.ERROR),
            _violation("REF001", Severity.UNRESOLVED),
        ]
        result = _gates_family_result("REF", violations, [], tmp_path)
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


class TestSeverityAdvisory:
    """T-5304: `Severity.ADVISORY` is a real, fourth `Severity` member --
    the LAUNCH-checklist tier that is always reported but never fails a
    gate, never raises the quarantine, and never counts toward the exit
    code or the ratchet (docs/modules/gates.md#advisory-t-5304)."""

    def test_advisory_is_a_distinct_severity_value(self) -> None:
        # frob:tests src/frob/findings.py::Severity
        assert Severity.ADVISORY != Severity.ERROR
        assert Severity.ADVISORY != Severity.WARN
        assert Severity.ADVISORY != Severity.UNRESOLVED
        assert Severity.ADVISORY.value == "advisory"

    def test_advisory_count_counts_only_advisory_violations(self) -> None:
        # frob:tests src/frob/check/_python.py::_advisory_count
        from frob.check._python import _advisory_count

        violations = [
            _violation("LAUNCH001", Severity.ERROR),
            _violation("LAUNCH001", Severity.WARN),
            _violation("LAUNCH001", Severity.ADVISORY),
            _violation("LAUNCH001", Severity.ADVISORY),
        ]
        assert _advisory_count(violations) == 2

    def test_advisory_maps_to_note_not_warning(self) -> None:
        # frob:tests src/frob/check/_python.py::_diag_severity
        # T-5304: ADVISORY must render distinctly from an ordinary
        # completed WARN finding, never collapse to "warning".
        from frob.check._python import _diag_severity

        assert _diag_severity(_violation("R", Severity.ADVISORY)) == "note"

    def test_advisory_only_family_result_exits_zero_and_is_not_quarantined(
        self, tmp_path
    ) -> None:
        # frob:tests src/frob/check/_python.py::_gates_family_result
        # Positive control (T-5304): a gate result containing only
        # advisory findings exits 0 and is not gate-blocking -- the
        # never-fail contract the owner directive requires.
        from frob.check._python import _gates_family_result

        violations = [_violation("LAUNCH001", Severity.ADVISORY)]
        result = _gates_family_result("LAUNCH", violations, [], tmp_path)
        assert result.exit_code == 0
        assert "1 advisory" in result.summary
        assert "0 errors" in result.summary

    def test_errors_still_fail_the_family_regardless_of_advisory(
        self, tmp_path
    ) -> None:
        # frob:tests src/frob/check/_python.py::_gates_family_result
        from frob.check._python import _gates_family_result

        violations = [
            _violation("LAUNCH001", Severity.ERROR),
            _violation("LAUNCH001", Severity.ADVISORY),
        ]
        result = _gates_family_result("LAUNCH", violations, [], tmp_path)
        assert result.exit_code == 1

    def test_advisory_count_shown_as_its_own_term_not_folded_into_warn(
        self, tmp_path
    ) -> None:
        # frob:tests src/frob/check/_python.py::_gates_family_result
        from frob.check._python import _gates_family_result

        violations = [
            _violation("LAUNCH001", Severity.WARN),
            _violation("LAUNCH001", Severity.ADVISORY),
        ]
        result = _gates_family_result("LAUNCH", violations, [], tmp_path)
        assert "1 warning" in result.summary
        assert "1 advisory" in result.summary


class TestGatesSummaryAdvisory:
    def test_advisory_only_summary_line_prints_the_advisory_count_and_exits_zero(
        self,
    ) -> None:
        # frob:tests src/frob/check/_python.py::_gates_summary
        # Positive control (T-5304): `frob check`'s own summary line
        # counts advisory findings, and an all-advisory report's n_err
        # (as `_gate_summary_result`/`_gates_family_results` would
        # compute it) stays zero.
        from frob.check._python import _error_count, _gates_summary

        violations = [
            _violation("LAUNCH001", Severity.ADVISORY),
            _violation("LAUNCH001", Severity.ADVISORY),
        ]
        report = GateReport(violations=tuple(violations), waived=(), stats=GateStats())
        n_err = _error_count(violations)
        assert n_err == 0
        summary = _gates_summary(violations, report, n_err=n_err, delta=False)
        assert "2 advisory" in summary
        assert "0 error" in summary
        assert "0 warning" in summary


class TestSeverityOverridesAdvisory:
    def test_advisory_string_accepted_as_a_per_rule_override_value(
        self, tmp_path
    ) -> None:
        # frob:tests src/frob/gates/_waive.py::_severity_overrides
        # [gates.severity] must accept "advisory" as a valid per-rule
        # override value, alongside "warn"/"error".
        from frob.gates._waive import _severity_overrides

        (tmp_path / "frob.toml").write_text(
            '[gates.severity]\nLAUNCH001 = "advisory"\n'
        )
        overrides = _severity_overrides(tmp_path)
        assert overrides["LAUNCH001"] == Severity.ADVISORY

    def test_apply_severity_overrides_re_severities_to_advisory(self, tmp_path) -> None:
        # frob:tests src/frob/gates/_waive.py::_apply_severity_overrides
        from frob.gates._waive import _apply_severity_overrides

        (tmp_path / "frob.toml").write_text(
            '[gates.severity]\nLAUNCH001 = "advisory"\n'
        )
        violations = (_violation("LAUNCH001", Severity.WARN),)
        result = _apply_severity_overrides(violations, tmp_path)
        assert result[0].severity == Severity.ADVISORY
