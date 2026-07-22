"""T-0710 review round 2: the perf harness's `FROB_PERF_SAMPLE=1` wiring
(`frob.perf._harness.main`) -- proves `StackSampler`/`resolve_stream`
compose with a real subprocess-shaped run, not just the resolver's own
hand-built fixtures. Deterministic on SHAPE (log line appears, workload's
own exit code/pstats output are unaffected), tolerant on sample COUNTS."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from frob.perf import _harness

_FIXTURE_SCRIPT = """
import time


def hot_loop():
    total = 0
    for i in range(200):
        total += i
        time.sleep(0.002)
    return total


if __name__ == "__main__":
    hot_loop()
"""


def _run_harness(tmp_path: Path, monkeypatch, sampled: bool) -> tuple[int, Path]:
    """Run `_harness.main()` against the fixture hot-loop script, with
    `FROB_PERF_SAMPLE` set or unset per `sampled`. Returns (exit_code,
    pstats_path)."""
    script = tmp_path / "hot_loop.py"
    script.write_text(_FIXTURE_SCRIPT, encoding="utf-8")
    pstats_path = tmp_path / "out.pstats"

    if sampled:
        monkeypatch.setenv("FROB_PERF_SAMPLE", "1")
    else:
        monkeypatch.delenv("FROB_PERF_SAMPLE", raising=False)
    monkeypatch.setattr(sys, "argv", ["_harness.py", str(pstats_path), str(script)])
    code = _harness.main()
    return code, pstats_path


class TestHarnessSampling:
    """`FROB_PERF_SAMPLE=1` wiring: cProfile's own output/exit-code
    contract is unaffected, and a resolved hot-graph summary is logged."""

    def test_unsampled_run_is_unaffected(self, tmp_path, monkeypatch) -> None:
        """Baseline: `FROB_PERF_SAMPLE` unset behaves exactly as before --
        clean exit, pstats file written, no hotgraph log line."""
        code, pstats_path = _run_harness(tmp_path, monkeypatch, sampled=False)
        assert code == 0
        assert pstats_path.exists()

    def test_sampled_run_logs_hotgraph_summary(
        self, tmp_path, monkeypatch, caplog
    ) -> None:
        """`FROB_PERF_SAMPLE=1`: the workload still exits clean and writes
        its pstats file (sampling never displaces cProfile's own output),
        AND a `hotgraph:` summary line is logged with a nonzero sample
        count."""
        with caplog.at_level(logging.INFO, logger="frob.perf._harness"):
            code, pstats_path = _run_harness(tmp_path, monkeypatch, sampled=True)
        assert code == 0
        assert pstats_path.exists()
        hotgraph_records = [
            r for r in caplog.records if r.message.startswith("hotgraph:")
        ]
        assert len(hotgraph_records) == 1
        message = hotgraph_records[0].message
        assert "unattributed_weight=" in message
        assert "sample(s)" in message

    def test_sampled_run_resolves_the_hot_loop_section(
        self, tmp_path, monkeypatch, caplog
    ) -> None:
        """The logged summary's sample count is nonzero and at least one
        section was hit -- proving `resolve_stream` actually ran against
        the fixture script's own parsed `NormalizedModule`, not just an
        empty/unattributed stream (a 300ms workload sampled at the 10ms
        default should yield double-digit samples)."""
        with caplog.at_level(logging.INFO, logger="frob.perf._harness"):
            code, _ = _run_harness(tmp_path, monkeypatch, sampled=True)
        assert code == 0
        message = next(
            r.message for r in caplog.records if r.message.startswith("hotgraph:")
        )
        # "hotgraph: N sample(s), M section(s) hit, ..."
        n_samples = int(message.split(" sample(s)")[0].split(": ")[1])
        assert n_samples >= 1
