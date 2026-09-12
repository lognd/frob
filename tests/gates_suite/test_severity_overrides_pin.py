"""T-4447: `[gates.severity]` re-severitying must never touch a
`severity_pinned` violation -- a verdict builder that already chose its
severity as a final answer (currently the COV003/TEST002 platform-skip
WARN/UNRESOLVED verdicts) is not a genuine finding subject to the
legacy-adoption strictness dial `_apply_severity_overrides` implements.
Kept separate from `tests/gates_suite/test_depr003_severity_override.py`
per that file's own precedent (T-3912's docstring): a narrow scope for
the exact files this ticket's fix touches, not a shared home that would
drag in unrelated DEPR/DEBT scope-closure fan-out.
"""

from pathlib import Path

from frob.gates import Severity, Violation
from frob.gates._waive import _apply_severity_overrides
from tests.conftest import _write as _write_fixture


# frob:ticket T-4447
def test_override_never_escalates_pinned_warn(tmp_path: Path) -> None:
    """T-4447: a `severity_pinned=True` WARN (the COV003 platform-skip
    shape) must stay WARN even when `[gates.severity]` sets COV003=error --
    the bug this ticket fixes: Windows CI showed 56 false COV003 ERRORs
    because the override could not tell a pinned platform-skip WARN apart
    from an ordinary one."""
    # frob:tests \
    # tests/gates_suite/test_severity_overrides_pin.py::test_override_never_escalates_p\
    # inned_warn
    _write_fixture(tmp_path, "frob.toml", '[gates.severity]\nCOV003 = "error"\n')
    v = Violation(
        rule="COV003",
        severity=Severity.WARN,
        file="tickets/T-0001",
        line=0,
        message="COV003: T-0001 evidence 'x' is platform-unavailable; this is a WARN",
        severity_pinned=True,
    )
    overridden = _apply_severity_overrides((v,), tmp_path)
    assert overridden[0].severity == Severity.WARN


# frob:ticket T-4447
def test_override_still_escalates_unpinned_warn(tmp_path: Path) -> None:
    """T-4447: the pin is precise, not a blanket exemption for the rule --
    an ordinary (unpinned) COV003 WARN of the same rule must still be
    promoted to ERROR when `[gates.severity]` says so, exactly as before
    this ticket's fix."""
    # frob:tests \
    # tests/gates_suite/test_severity_overrides_pin.py::test_override_still_escalates_u\
    # npinned_warn
    _write_fixture(tmp_path, "frob.toml", '[gates.severity]\nCOV003 = "error"\n')
    v = Violation(
        rule="COV003",
        severity=Severity.WARN,
        file="tickets/T-0002",
        line=0,
        message="COV003: T-0002 evidence 'y' does not resolve",
    )
    overridden = _apply_severity_overrides((v,), tmp_path)
    assert overridden[0].severity == Severity.ERROR
