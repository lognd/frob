"""T-3861 (EXHAUST002/003/004 burn-down) repro suite: proves the family's
per-file waiver fixes actually clear the real gate + waive-application
pipeline, not just the raw unwaived-violation count. Kept as its own module
(not folded into tests/gates_suite/test_compliance.py) because that file is
under a different ticket's (T-4420) declared scope while this burn-down is
in flight.

frob:ticket T-3861
"""

from pathlib import Path

from frob.gates._exhaustive_handling import exhaustive_handling_gate
from frob.gates._waive import _apply_waivers
from tests.conftest import _snapshot, _write


# frob:ticket T-3861
class TestExhaustBurndownFleetStatus:
    """`scripts/fleet_status.py` was this repo's single largest
    EXHAUST003/004 concentration (56 findings: 38 EXHAUST003 + 18
    EXHAUST004) on the 2026-09-20 `frob check --base dev` baseline -- every
    one traced to `frob.arch._mayraise`'s deliberately narrow same-module,
    curated-table-only callee resolution reporting `Unknown`/subscript-
    derived `LookupError` for ordinary stdlib calls an existing `except`
    clause already covers (see the `frob:waive` reasons in the real
    file)."""

    def test_fleet_status_exhaust003_004_findings_are_all_waived(
        self, tmp_path: Path
    ) -> None:
        """Copies the real, checked-out `scripts/fleet_status.py`'s CURRENT
        content (not a synthetic fixture) into `tmp_path` and runs the real
        gate + `_apply_waivers` spine together: at dev (before T-3861's
        fix) this fails with 56 kept (unwaived) violations; after the fix,
        every one of them is waived and `kept` is empty for this file."""
        repo_root = Path(__file__).resolve().parents[2]
        real_source = (repo_root / "scripts" / "fleet_status.py").read_text(
            encoding="utf-8"
        )
        _write(tmp_path, "scripts/fleet_status.py", real_source)
        violations = exhaustive_handling_gate(tmp_path)
        exhaust_violations = tuple(
            v for v in violations if v.rule in ("EXHAUST003", "EXHAUST004")
        )
        assert exhaust_violations, "fixture drifted: file no longer has any findings"
        snap = _snapshot(tmp_path)
        kept, waived = _apply_waivers(exhaust_violations, snap)
        assert kept == (), (
            f"{len(kept)} EXHAUST003/004 finding(s) in scripts/fleet_status.py "
            "are not waived (T-3861 regression): "
            f"{[(v.line, v.rule) for v in kept]}"
        )
        assert len(waived) == len(exhaust_violations)
