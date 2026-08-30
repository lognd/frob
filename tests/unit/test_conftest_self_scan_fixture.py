"""T-3495: `tests/conftest.py::frob_self_scan_artifacts` shares ONE
`build_graph`/`sys_gate` pass across every `frob_self_scan_heavy` test
that consumes it -- these tests prove the shared-artifact refactor did
not change each consumer's OWN pass/fail behavior: a violation only the
BROAD filter (`== ()`) cares about must not fail a NARROWER consumer
(MUST-STAY-QUIET), and a violation a narrow filter DOES match must still
fail that consumer (MUST-FIRE) -- exactly as when each test built its
own independent graph, before this ticket's refactor. Exercises the real
`FrobSelfScanArtifacts` carrier and the SAME filter expressions `tests/
system/test_frob_self_model.py`/`tests/unit/strata/test_sys003_
calibration.py` use, over a synthetic `violations` tuple -- no real
repo scan needed to prove the CONTRACT (one shared tuple, independent
per-test filtering) holds.
"""

from __future__ import annotations

from pathlib import Path

from tests.unit._conftest_test_helpers import load_conftest_module

_conftest = load_conftest_module("_t3495_conftest_under_test")
FrobSelfScanArtifacts = _conftest.FrobSelfScanArtifacts


class _FakeViolation:
    """A minimal stand-in for `frob.gates.Violation` carrying only the
    two fields every consumer's own filter reads (`.rule`/`.message`)."""

    __slots__ = ("rule", "message")

    def __init__(self, rule: str, message: str) -> None:
        """Store the two fields a `sys_gate`/`perf_gate` consumer's own
        narrow filter reads."""
        self.rule = rule
        self.message = message


def _fake_violation(rule: str, message: str) -> _FakeViolation:
    """Build one `_FakeViolation` -- see its own docstring."""
    return _FakeViolation(rule, message)


# frob:ticket T-3495
# frob:tests \
# tests/unit/test_conftest_self_scan_fixture.py::TestFrobSelfScanArtifactsSharing.test_\
# narrow_filter_ignores_unrelated_violation
# frob:tests \
# tests/unit/test_conftest_self_scan_fixture.py::TestFrobSelfScanArtifactsSharing.test_\
# broad_filter_fails_on_any_violation
# frob:tests \
# tests/unit/test_conftest_self_scan_fixture.py::TestFrobSelfScanArtifactsSharing.test_\
# narrow_filter_fires_on_its_own_violation
# frob:tests \
# tests/unit/test_conftest_self_scan_fixture.py::TestFrobSelfScanArtifactsSharing.test_\
# sys003_filter_ignores_other_rules
class TestFrobSelfScanArtifactsSharing:
    """`FrobSelfScanArtifacts.violations` is ONE shared tuple; every
    consumer filters it independently -- these are the exact filter
    shapes the real consuming tests use."""

    # frob:ticket T-3495
    def test_narrow_filter_ignores_unrelated_violation(self) -> None:
        """MUST-STAY-QUIET: a violation the BROAD `test_sys_gate_zero_
        violations`-shaped check would fail on must NOT fail a narrower
        `_fragments.py`-only filter (`test_fragments_module_fs_read_is_
        declared_not_selfaudit001`'s own shape) when it names an
        unrelated file."""
        artifacts = FrobSelfScanArtifacts(
            repo_root=Path("."),
            build_result=None,
            violations=(_fake_violation("SYS101", "unrelated/other.py"),),
        )
        fragments_violations = [
            v for v in artifacts.violations if "_fragments.py" in v.message
        ]
        assert fragments_violations == []

    # frob:ticket T-3495
    def test_broad_filter_fails_on_any_violation(self) -> None:
        """MUST-FIRE: the SAME shared violation the narrow filter above
        correctly ignores still fails the BROAD `violations == ()` bar
        `test_sys_gate_zero_violations` uses -- the shared artifact is
        never silently emptied for one consumer to satisfy another."""
        artifacts = FrobSelfScanArtifacts(
            repo_root=Path("."),
            build_result=None,
            violations=(_fake_violation("SYS101", "unrelated/other.py"),),
        )
        assert artifacts.violations != ()

    # frob:ticket T-3495
    def test_narrow_filter_fires_on_its_own_violation(self) -> None:
        """MUST-FIRE: a violation naming `_fragments.py` DOES fail the
        narrow filter `test_fragments_module_fs_read_is_declared_not_
        selfaudit001` uses, proving the shared tuple's real content still
        reaches that consumer's own assertion."""
        artifacts = FrobSelfScanArtifacts(
            repo_root=Path("."),
            build_result=None,
            violations=(
                _fake_violation(
                    "SELFAUDIT001", "undeclared fs.read in src/frob/release/_fragments.py"
                ),
            ),
        )
        fragments_violations = [
            v for v in artifacts.violations if "_fragments.py" in v.message
        ]
        assert fragments_violations != []

    # frob:ticket T-3495
    def test_sys003_filter_ignores_other_rules(self) -> None:
        """MUST-STAY-QUIET (test_sys003_calibration.py's own shape): a
        non-SYS003 violation in the shared tuple must not fail `test_
        sys003_zero_against_live_repo_design`'s `rule == "SYS003"`
        filter, even though it WOULD fail the broad bar."""
        artifacts = FrobSelfScanArtifacts(
            repo_root=Path("."),
            build_result=None,
            violations=(_fake_violation("SYS101", "some/file.py"),),
        )
        sys003 = [v for v in artifacts.violations if v.rule == "SYS003"]
        assert sys003 == []
        assert artifacts.violations != ()
