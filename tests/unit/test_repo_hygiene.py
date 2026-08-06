"""Repo-hygiene locks for artifacts that must not be tracked (T-1612).

`FROBLEMS.md` is frob's own `frob clean --deep` tier-3 artifact and is
listed in `.gitignore`; this repo had it force-tracked anyway, where it
went stale (newest entry 2026-07-21) and was read as current. T-1612
removed it. Without a lock, `git add -f FROBLEMS.md` silently restores
exactly that state -- the file's presence is what made it look
authoritative in the first place.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

# frob:ticket T-1612
_UNTRACKED_ARTIFACTS = ("FROBLEMS.md",)


# frob:ticket T-1612
def _tracked_paths(root: Path) -> set[str]:
    """Every path git currently tracks at `root`, as repo-relative posix
    strings -- read from git rather than the filesystem so a file that is
    present-but-ignored is correctly distinguished from a tracked one."""
    proc = subprocess.run(
        ["git", "ls-files"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )
    return {line.strip() for line in proc.stdout.splitlines() if line.strip()}


# frob:ticket T-1612
class TestUntrackedArtifacts:
    """T-1612: derived artifacts stay out of git, permanently."""

    # frob:ticket T-1612
    def test_froblems_md_is_not_tracked(self) -> None:
        """`FROBLEMS.md` is a generated, per-checkout artifact. Tracking it
        publishes one machine's stale snapshot as if it were the repo's
        current problem list."""
        root = Path(__file__).resolve().parents[2]
        tracked = _tracked_paths(root)
        still_tracked = [p for p in _UNTRACKED_ARTIFACTS if p in tracked]
        assert not still_tracked, (
            f"{still_tracked} is tracked again despite being a generated "
            "artifact listed in .gitignore (T-1612); it was removed because "
            "a tracked copy goes stale and is then read as authoritative"
        )
