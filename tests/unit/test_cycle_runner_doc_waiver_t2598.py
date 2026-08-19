"""T-2598 regression: the AFFECT001 waiver on `cycle_runner.run` promised a
follow-up ticket to update `docs/modules/app.md#runners`'s stale bullet once
T-2582's lease cleared -- the lease cleared and the follow-up was never
filed, so the waiver kept suppressing a live doc-drift finding nobody owned.

This test locks two things directly, without relying on gate output: the
doc bullet describes the CURRENT `cycle_runner.run` contract (nearest-
enclosing-`pyproject.toml` root resolution, real 0/1/2 exit codes), and the
AFFECT001 waiver is gone from `cycle_runner.py` while the still-valid
ARCH103 waiver directly above it remains untouched.
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]


class TestCycleRunnerDocWaiver:
    """Doc content and waiver-removal checks for the T-2598 fix."""

    def test_app_doc_describes_current_cycle_runner_contract(self) -> None:
        """`docs/modules/app.md`'s `cycle_runner.run` bullet must describe
        the T-2588 root-resolution and exit-code behavior, not the old
        always-exit-0 contract."""
        doc_text = (_REPO_ROOT / "docs/modules/app.md").read_text()
        start = doc_text.index("`cycle_runner.run` --")
        end = doc_text.index("\n- `map_runner.run`", start)
        bullet = doc_text[start:end]

        assert "pyproject.toml" in bullet, (
            "doc bullet does not mention nearest-enclosing-pyproject.toml "
            "root resolution (T-2588)"
        )
        assert "1 when real cycles are found" in bullet or "exit" in bullet.lower()
        assert "2" in bullet, "doc bullet does not describe the exit-2 case"

    def test_affect001_waiver_removed_arch103_waiver_kept(self) -> None:
        """The stale AFFECT001 waiver above `cycle_runner.run` is gone; the
        separate, still-valid ARCH103 waiver is untouched."""
        src_text = (_REPO_ROOT / "src/frob/app/cycle_runner.py").read_text()

        assert "frob:waive AFFECT001" not in src_text, (
            "stale AFFECT001 waiver on cycle_runner.run was not removed"
        )
        assert 'frob:waive ARCH103 reason="T-0977' in src_text, (
            "the separate, still-valid ARCH103 waiver must remain"
        )
