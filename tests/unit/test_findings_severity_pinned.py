"""T-4447: the two platform-skip verdict builders (`_platform_skip_violation`
COV003 in `frob.gates`, `_test002_platform_skipped` TEST002 in the same
module) must set `Violation.severity_pinned=True` on the `Violation` they
construct -- that is the marker `_apply_severity_overrides`
(`frob.gates._waive`) checks to leave a deliberate platform-skip verdict
alone regardless of what `[gates.severity]` says for its rule. This module
is `tests/unit/test_findings*.py` per T-4447's scope: it exercises the
`Violation` field itself (`src/frob/findings.py`) plus the two builders
that set it (`src/frob/gates/__init__.py`), and is kept separate from the
gates_suite override-behavior tests
(`tests/gates_suite/test_severity_overrides_pin.py`) which cover
`_apply_severity_overrides`'s own decision.
"""

from types import SimpleNamespace

from frob.findings import Severity, Violation
from frob.gates import _platform_skip_violation, _test002_platform_skipped
from tests.conftest import _ticket


def test_violation_defaults_severity_pinned_false() -> None:
    """T-4447: an ordinary `Violation` (no verdict-builder involvement) is
    unpinned by default, so `[gates.severity]` continues to govern it as
    before this ticket's fix."""
    # frob:tests \
    # tests/unit/test_findings_severity_pinned.py::test_violation_defaults_severity_pin\
    # ned_false
    v = Violation(
        rule="COV003", severity=Severity.WARN, file="a.py", line=1, message="m"
    )
    assert v.severity_pinned is False


def test_platform_skip_violation_is_pinned() -> None:
    """T-4447: `_platform_skip_violation` (COV003) must set
    `severity_pinned=True` -- without it, `_apply_severity_overrides`
    cannot distinguish this deliberate WARN from any other COV003 WARN and
    silently promotes it to ERROR under `[gates.severity]` COV003=error."""
    # frob:tests \
    # tests/unit/test_findings_severity_pinned.py::test_platform_skip_violation_is_pinn\
    # ed
    ticket = _ticket()
    v = _platform_skip_violation(
        ticket, "tests/test_x.py::test_y", "POSIX-only feature"
    )
    assert v.rule == "COV003"
    assert v.severity == Severity.WARN
    assert v.severity_pinned is True


def test_test002_platform_skipped_is_pinned() -> None:
    """T-4447: `_test002_platform_skipped` (TEST002) must also set
    `severity_pinned=True`, belt-and-suspenders alongside its existing
    `Severity.UNRESOLVED` exemption (T-4386)."""
    # frob:tests \
    # tests/unit/test_findings_severity_pinned.py::test_test002_platform_skipped_is_pin\
    # ned
    record = SimpleNamespace(
        symref="pkg.mod::fn",
        span=(10, 20),
        id=SimpleNamespace(path="src/pkg/mod.py"),
    )
    v = _test002_platform_skipped(record, "POSIX-only feature")
    assert v.rule == "TEST002"
    assert v.severity == Severity.UNRESOLVED
    assert v.severity_pinned is True
