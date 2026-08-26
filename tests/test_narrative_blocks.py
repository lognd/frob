"""NARR001 (T-2993) fixtures: a must-fire long archaeology block and a
must-stay-quiet short KEEP block, plus the `_socketd.py` T-2961 block
itself (verbatim, as a string fixture -- `serve/` is a live agent's own
work area this drive, so this test copies the text rather than reading
the real file, and still proves the same block reads clean at the
default threshold)."""

from __future__ import annotations

import subprocess
from pathlib import Path

from frob.gates._narrative_blocks import (
    NARR001_THRESHOLD_LINES,
    narrative_blocks_gate,
    scan_narrative_blocks,
)

# The KEEP sentence from T-2993's own cited example (_socketd.py, T-2961):
# load-bearing for anyone editing the guard, must never fire.
_SOCKETD_T2961_BLOCK = """\
# T-2961: `socketserver.ThreadingUnixStreamServer` (the unix-domain-socket
# server base this class needs) is POSIX-only -- no cross-platform
# equivalent exists in the standard library. Unlike the fcntl/msvcrt
# pattern this repo uses for FUNCTIONS (T-2918/T-2934/T-2952/T-2953), a
# CLASS statement referencing a missing base at module scope raises
# `AttributeError` the instant this module is IMPORTED, not merely when
# the daemon is used -- structurally the same bug class as a bare
# `import fcntl`, just at class-definition time instead of import
# statement time. Both branches bind the SAME name `_DaemonServer` (never
# leaving it unbound on win32) so every annotation/reference elsewhere in
# this module resolves on every platform, mirroring how `fcntl = None`
# keeps that name bound rather than omitting it under `except ImportError`.
if True:
    pass
"""

# A short block that genuinely explains the code (T-2993's own KEEP
# standard) -- must stay quiet regardless of threshold tuning.
_MUST_STAY_QUIET = """\
# T-2961: this branch only runs on non-Windows platforms because the
# stdlib base class it needs does not exist on win32.
if True:
    pass
"""

# A long block that is pure archaeology -- cross-ticket references and
# historical framing, nothing a reader needs to safely modify this code.
# Must fire.
_MUST_FIRE = "\n".join(
    ["# T-1000: this records how we got here"]
    + [
        f"# revision {i}: superseded by T-{1000 + i}, see that ticket for why"
        for i in range(NARR001_THRESHOLD_LINES + 5)
    ]
)


class TestNarrativeBlocksGate:
    """Both fixture directions required by T-2993's acceptance."""

    def test_must_fire_long_archaeology_block(self) -> None:
        """A block well past the threshold, with no code-facing content,
        raises NARR001."""
        violations = scan_narrative_blocks(Path("fixture.py"), _MUST_FIRE)
        assert len(violations) == 1
        assert violations[0].rule == "NARR001"

    def test_must_stay_quiet_short_keep_block(self) -> None:
        """A short block genuinely explaining the code stays quiet."""
        violations = scan_narrative_blocks(Path("fixture.py"), _MUST_STAY_QUIET)
        assert violations == ()

    def test_socketd_t2961_block_stays_quiet_at_default_threshold(self) -> None:
        """T-2993's own cited example: this exact block (12 comment lines,
        equal to the default threshold, all load-bearing utility -- see
        this module's own docstring) must NOT fire. Verbatim copy of
        `src/frob/serve/_socketd.py`'s block as of this ticket -- `serve/`
        is a live agent's own area this drive, so this test does not read
        the real file directly."""
        violations = scan_narrative_blocks(Path("fixture.py"), _SOCKETD_T2961_BLOCK)
        assert violations == (), (
            "the socketd T-2961 block is exactly at threshold and pure "
            "utility -- it must not fire"
        )

    def test_threshold_boundary_is_inclusive(self) -> None:
        """A block of exactly `threshold` lines does not fire; one past it
        does -- the off-by-one this gate's own `<=` check must get right."""
        at_threshold = "\n".join(
            f"# T-1000: line {i}" for i in range(NARR001_THRESHOLD_LINES)
        )
        one_over = at_threshold + "\n# T-1000: one more line"
        assert scan_narrative_blocks(Path("f.py"), at_threshold) == ()
        assert len(scan_narrative_blocks(Path("f.py"), one_over)) == 1


class TestNarrativeBlocksGateRepoScan:
    """`narrative_blocks_gate`'s own tracked-file walk, over a throwaway
    git repo (not this repo) so the test does not depend on live counts."""

    def test_fires_on_a_tracked_file_with_a_long_block(self, tmp_path: Path) -> None:
        """A tracked `.py` file with a `_MUST_FIRE`-shaped block is found."""
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        (tmp_path / "offender.py").write_text(_MUST_FIRE + "\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        violations = narrative_blocks_gate(tmp_path)
        assert len(violations) == 1
        assert violations[0].rule == "NARR001"
