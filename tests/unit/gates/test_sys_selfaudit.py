"""Unit tests for `frob.gates._sys_selfaudit`'s T-1451 severity-escalation
addition: SYS107 (via-less-may-on-a-large-node advisory) defaults to
`Severity.WARN` inside SELFAUDIT001 and is escalated to `Severity.ERROR`
only by `[strata] require_may_scope` in `frob.toml`
(docs/modules/gates.md#self-audit-at-land-selfaudit001-t-0756)."""

from __future__ import annotations

from pathlib import Path

from frob.gates._models import Severity
from frob.gates._sys_selfaudit import _selfaudit_severity, _selfaudit_violation


class TestSelfauditSeverity:
    # frob:tests src/frob/gates/_sys_selfaudit.py::_selfaudit_severity kind="unit"
    def test_sys107_defaults_to_warn(self, tmp_path: Path) -> None:
        """No `frob.toml` (or one with no `[strata]` table) -- SYS107
        stays WARN, the advisory default."""
        assert _selfaudit_severity("SYS107", tmp_path) == Severity.WARN

    # frob:tests src/frob/gates/_sys_selfaudit.py::_selfaudit_severity kind="unit"
    def test_sys107_escalates_to_error_under_require_may_scope(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / "frob.toml").write_text(
            "[strata]\nrequire_may_scope = true\n", encoding="utf-8"
        )
        assert _selfaudit_severity("SYS107", tmp_path) == Severity.ERROR

    # frob:tests src/frob/gates/_sys_selfaudit.py::_selfaudit_severity kind="unit"
    def test_other_sub_rules_stay_error_regardless_of_config(
        self, tmp_path: Path
    ) -> None:
        """SYS100-106/SYS2xx/REL2xx keep the original unconditional-ERROR
        posture -- only SYS107 is special-cased."""
        assert _selfaudit_severity("SYS100", tmp_path) == Severity.ERROR
        assert _selfaudit_severity("SYS106", tmp_path) == Severity.ERROR
        (tmp_path / "frob.toml").write_text(
            "[strata]\nrequire_may_scope = true\n", encoding="utf-8"
        )
        assert _selfaudit_severity("SYS100", tmp_path) == Severity.ERROR

    # frob:tests src/frob/gates/_sys_selfaudit.py::_selfaudit_violation kind="unit"
    def test_selfaudit_violation_carries_sys107_warn_severity(
        self, tmp_path: Path
    ) -> None:
        v = _selfaudit_violation("SYS107", "widget", "detail text", "design", tmp_path)
        assert v.severity == Severity.WARN
        assert v.rule == "SELFAUDIT001"
        assert "SYS107" in v.message

    # frob:ticket T-2224
    # frob:tests src/frob/gates/_sys_selfaudit.py::_selfaudit_severity kind="unit"
    def test_sys107_fail_closed_atoms_are_always_error(self, tmp_path: Path) -> None:
        """T-2224: exec/eval/install-hook/ffi are ALWAYS ERROR under
        SYS107 -- no `[strata] require_may_scope` opt-in needed. This
        MUST fail against current main (SYS107 currently returns WARN
        for exactly this case, `_selfaudit_severity` had no `capability`
        parameter at all) and pass after the fix."""
        for atom in ("exec", "eval", "install-hook", "ffi"):
            assert (
                _selfaudit_severity("SYS107", tmp_path, capability=atom)
                == Severity.ERROR
            ), atom

    # frob:ticket T-2224
    # frob:tests src/frob/gates/_sys_selfaudit.py::_selfaudit_severity kind="unit"
    def test_sys107_net_via_less_still_defaults_to_warn(self, tmp_path: Path) -> None:
        """Must-still-pass control: net/fs.read/fs.write are explicitly
        OUT of scope for the T-2224 escalation -- a via-less net grant
        must still be WARN by default, same as before this ticket."""
        assert (
            _selfaudit_severity("SYS107", tmp_path, capability="net") == Severity.WARN
        )

    # frob:ticket T-2224
    # frob:tests src/frob/gates/_sys_selfaudit.py::_selfaudit_severity kind="unit"
    def test_sys107_net_via_less_still_escalates_under_require_may_scope(
        self, tmp_path: Path
    ) -> None:
        """Must-still-pass control: the PRE-existing `require_may_scope`
        escalation path for a non-fail-closed capability is untouched."""
        (tmp_path / "frob.toml").write_text(
            "[strata]\nrequire_may_scope = true\n", encoding="utf-8"
        )
        assert (
            _selfaudit_severity("SYS107", tmp_path, capability="net")
            == Severity.ERROR
        )

    # frob:ticket T-2224
    # frob:tests src/frob/gates/_sys_selfaudit.py::_selfaudit_severity kind="unit"
    def test_sys107_no_capability_falls_back_to_config_gated_behavior(
        self, tmp_path: Path
    ) -> None:
        """`capability=None` (the pre-T-2224 call shape) must behave
        EXACTLY as before -- never silently promoted to ERROR just
        because the fail-closed check could not run."""
        assert _selfaudit_severity("SYS107", tmp_path) == Severity.WARN
        assert (
            _selfaudit_severity("SYS107", tmp_path, capability=None) == Severity.WARN
        )

    # frob:ticket T-2224
    # frob:tests src/frob/gates/_sys_selfaudit.py::_selfaudit_violation kind="unit"
    def test_selfaudit_violation_escalates_sys107_exec_to_error(
        self, tmp_path: Path
    ) -> None:
        """T-2224 acceptance criterion 1's shape at the `_selfaudit_
        violation` level: a via-less exec finding reaches ERROR through
        the full Violation-building path, not just the raw severity
        function in isolation."""
        v = _selfaudit_violation(
            "SYS107", "widget", "detail text", "design", tmp_path, capability="exec"
        )
        assert v.severity == Severity.ERROR
        assert v.rule == "SELFAUDIT001"
