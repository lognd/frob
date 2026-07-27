"""T-0712: `frob.perf._ratchet`'s regression-ratchet check and its
persisted findings round trip / gate-facing violations."""

from __future__ import annotations

from pathlib import Path

from frob.perf._ratchet import (
    RatchetFinding,
    check_ratchet,
    load_ratchet_findings,
    ratchet_violations,
    save_ratchet_findings,
)
from frob.stats._sketch import DEFAULT_ALPHA, add_value, new_sketch


def _sketch(values: list[float]):
    sketch = new_sketch(alpha=DEFAULT_ALPHA)
    for value in values:
        sketch = add_value(sketch, value)
    return sketch


class TestCheckRatchet:
    """`check_ratchet`'s pure comparison logic."""

    def test_no_prior_never_fires(self) -> None:
        current = _sketch([10.0])
        assert check_ratchet("key", "label", None, current, tolerance=0.5) is None

    def test_within_tolerance_does_not_fire(self) -> None:
        prior = _sketch([10.0] * 20)
        current = _sketch([11.0] * 20)  # ~10% shift, under 50% tolerance
        assert check_ratchet("key", "label", prior, current, tolerance=0.5) is None

    def test_regression_beyond_tolerance_fires(self) -> None:
        prior = _sketch([10.0] * 20)
        current = _sketch([100.0] * 20)  # ~10x shift
        finding = check_ratchet("key", "hot_loop", prior, current, tolerance=0.5)
        assert finding is not None
        assert finding.section_key == "key"
        assert finding.label == "hot_loop"
        assert finding.worst_relative_shift > 0.5
        assert set(finding.prior_deciles) == {"p50", "p90"}
        assert set(finding.current_deciles) == {"p50", "p90"}


class TestPersistRoundTrip:
    """`save_ratchet_findings`/`load_ratchet_findings` round trip."""

    def test_save_then_load_round_trips(self, tmp_path: Path) -> None:
        findings = [
            RatchetFinding(
                section_key="k1",
                label="pkg.mod.fn",
                prior_deciles={"p50": 1.0, "p90": 2.0},
                current_deciles={"p50": 3.0, "p90": 4.0},
                worst_relative_shift=2.0,
            )
        ]
        save_ratchet_findings(tmp_path, findings)
        loaded = load_ratchet_findings(tmp_path)
        assert loaded == findings

    def test_missing_file_is_empty(self, tmp_path: Path) -> None:
        assert load_ratchet_findings(tmp_path) == []


class TestRatchetViolations:
    """`ratchet_violations` -- PERF009's gate-facing shape."""

    def test_no_findings_file_is_zero_violations(self, tmp_path: Path) -> None:
        assert ratchet_violations(tmp_path) == []

    def test_findings_become_perf009_violations(self, tmp_path: Path) -> None:
        findings = [
            RatchetFinding(
                section_key="k1",
                label="pkg.mod.fn",
                prior_deciles={"p50": 1.0, "p90": 2.0},
                current_deciles={"p50": 3.0, "p90": 4.0},
                worst_relative_shift=2.0,
            )
        ]
        save_ratchet_findings(tmp_path, findings)
        violations = ratchet_violations(tmp_path)
        assert len(violations) == 1
        assert violations[0].rule == "PERF009"
        assert "pkg.mod.fn" in violations[0].message
