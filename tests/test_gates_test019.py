"""Tests for TEST019: `frob.gates._test019_deflated_symbols` -- the
Violation-emitting wire-up of T-1824's per-symbol deflation heuristic
(`frob.gates._coverage._suspect_deflated_symbols`), added by T-1877.

Split into its own file rather than `tests/test_gates.py` because T-1887
held a live cross-worktree lease on that file at the time this ticket was
worked (see this ticket's Done report).
"""

from __future__ import annotations

from frob.gates import CoverageData, Severity, _test019_deflated_symbols


class TestTest019DeflatedSymbols:
    """`frob.gates._test019_deflated_symbols`: turns a non-empty
    `CoverageData.suspect_deflated_symbols` into a WARN-severity TEST019
    Violation; a clean/empty tuple emits nothing."""

    def test_flags_suspect_symbol(self) -> None:
        """A non-empty `suspect_deflated_symbols` tuple produces exactly one
        TEST019 WARN Violation naming every suspect symref in its message."""
        # frob:ticket T-1877
        # frob:tests \
        # tests/test_gates_test019.py::TestTest019DeflatedSymbols.test_flags_suspect_sy\
        # mbol
        data = CoverageData(
            source_sha="deadbeef",
            suspect_deflated_symbols=("src/frob/pkg/a.py::helper",),
        )
        violations = _test019_deflated_symbols(data)
        assert len(violations) == 1
        violation = violations[0]
        assert violation.rule == "TEST019"
        assert violation.severity == Severity.WARN
        assert "src/frob/pkg/a.py::helper" in violation.message

    def test_clean_when_no_suspects(self) -> None:
        """An empty `suspect_deflated_symbols` tuple (the default, and the
        shape of clean input) emits no TEST019 Violation at all."""
        # frob:ticket T-1877
        # frob:tests \
        # tests/test_gates_test019.py::TestTest019DeflatedSymbols.test_clean_when_no_su\
        # spects
        data = CoverageData(source_sha="deadbeef")
        assert _test019_deflated_symbols(data) == ()
