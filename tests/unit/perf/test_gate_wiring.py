"""T-0756 new-gate-rule acceptance proof: PERF008 (T-0775) and PERF009
(T-0712) firing through `frob.gates.__init__.perf_gate` -- the PRODUCTION
function `frob check` actually invokes, not just the pure-function unit
tests in test_loop_effects.py / test_ratchet.py. Each test is a
before-fails/after-passes fixture: the "before" state (no loop-invariant
effect / no ratchet findings file) produces zero violations of the rule;
the "after" state (the fixture that should fire) produces at least one.
"""

from __future__ import annotations

import json
from pathlib import Path

from frob.graph import build_graph


def _write(root: Path, rel: str, text: str) -> Path:
    """Write `text` to `root/rel`, returning the path -- shared test setup."""
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def _snapshot(root: Path):
    """A fresh `GraphSnapshot` over `root` -- matches `tests/test_gates.py`'s
    own `_snapshot` helper."""
    cache = root / ".frob" / "cache.db"
    return build_graph(root, cache).danger_ok


class TestPerf008ProductionInvocation:
    """PERF008 fires through the real `perf_gate` gate function, not just
    `loop_invariant_effect_violations` called directly."""

    def test_before_no_effect_fails_to_find_perf008(self, tmp_path: Path) -> None:
        """BEFORE: a loop with no effectful call -- `perf_gate` reports
        zero PERF008 findings."""
        from frob.gates import perf_gate

        _write(
            tmp_path,
            "src/a.py",
            "def scan(items):\n"
            "    total = 0\n"
            "    for item in items:\n"
            "        total += item\n"
            "    return total\n",
        )
        snap = _snapshot(tmp_path)
        violations = perf_gate(tmp_path, snap)
        assert not any(v.rule == "PERF008" for v in violations)

    def test_after_loop_invariant_fs_walk_passes_perf008(self, tmp_path: Path) -> None:
        """AFTER: a loop-invariant `os.walk` call inside a loop -- `perf_gate`
        reports at least one PERF008 finding through the production path."""
        from frob.gates import perf_gate

        _write(
            tmp_path,
            "src/a.py",
            "import os\n\n\n"
            "def scan_all(items, fixed_root):\n"
            "    for _item in items:\n"
            "        for _dirpath, _dirs, _files in os.walk(fixed_root):\n"
            "            pass\n",
        )
        snap = _snapshot(tmp_path)
        violations = perf_gate(tmp_path, snap)
        assert any(v.rule == "PERF008" for v in violations)


class TestPerf009ProductionInvocation:
    """PERF009 (T-0712's regression ratchet) fires through the real
    `perf_gate` gate function, reading `.frob/perf/ratchet_findings.json`
    -- the artifact `frob perf collect` writes and `frob check` consumes,
    never re-collecting live."""

    def test_before_no_findings_file_fails_to_find_perf009(
        self, tmp_path: Path
    ) -> None:
        """BEFORE: no `.frob/perf/ratchet_findings.json` exists yet --
        `perf_gate` reports zero PERF009 findings."""
        from frob.gates import perf_gate

        _write(tmp_path, "src/a.py", "def scan(x):\n    return x\n")
        snap = _snapshot(tmp_path)
        violations = perf_gate(tmp_path, snap)
        assert not any(v.rule == "PERF009" for v in violations)

    def test_after_regression_finding_passes_perf009(self, tmp_path: Path) -> None:
        """AFTER: `frob perf collect` (simulated here by writing the same
        artifact it writes) recorded a regression -- `perf_gate` reports
        at least one PERF009 finding through the production path."""
        from frob.gates import perf_gate

        _write(tmp_path, "src/a.py", "def scan(x):\n    return x\n")
        findings_path = tmp_path / ".frob" / "perf" / "ratchet_findings.json"
        findings_path.parent.mkdir(parents=True, exist_ok=True)
        findings_path.write_text(
            json.dumps(
                [
                    {
                        "section_key": "k1",
                        "label": "pkg.mod.hot_loop",
                        "prior_deciles": {"p50": 1.0, "p90": 2.0},
                        "current_deciles": {"p50": 10.0, "p90": 20.0},
                        "worst_relative_shift": 9.0,
                    }
                ]
            )
        )
        snap = _snapshot(tmp_path)
        violations = perf_gate(tmp_path, snap)
        assert any(v.rule == "PERF009" for v in violations)
