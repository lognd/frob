"""T-2612: regression lock for the lease-premise waiver audit.

`frob:waive` reasons that justify a suppression by naming a ticket as
holding a "LIVE cross-worktree lease" go stale silently once that ticket
terminates (T-2612's own measured finding: 0 of the originally-cited
holder tickets still held a live lease). These tests pin the specific
stale citations T-2612 found and fixed so a future edit cannot
reintroduce the exact same expired-premise text without failing here.
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent

#: (file, stale substring that must never reappear) pairs -- each one was
#: a `frob:waive` reason citing a now-terminal ticket's "LIVE"/"live"
#: lease as the reason a doc/anchor could not be added, audited by
#: T-2612. A hit here means the exact expired-premise text crept back in.
_STALE_LEASE_CITATIONS: tuple[tuple[str, str], ...] = (
    ("src/frob/scaffold/project.py", "held by T-1382's LIVE cross-worktree lease"),
    (
        "src/frob/__main__.py",
        "a live T-1382 cross-worktree lease and cannot be extended",
    ),
    (
        "src/frob/tickets/_reconcile.py",
        "held by T-1720's LIVE cross-worktree lease",
    ),
    (
        "src/frob/tickets/_reconcile.py",
        "same T-1720 live-lease conflict",
    ),
    (
        "src/frob/lang/_nodes.py",
        "under T-2365's live cross-worktree",
    ),
    (
        "src/frob/gates/_mutation_evidence.py",
        "leased by another in-progress agent (T-1715/T-1739)",
    ),
    (
        "src/frob/tickets/_models.py",
        "leased by another in-progress agent (T-1715/T-1739)",
    ),
    (
        "src/frob/tickets/_evidence.py",
        "leased by another in-progress agent (T-1715/T-1739)",
    ),
    (
        "src/frob/app/check_runner.py",
        "held by T-2485's LIVE cross-worktree scope lease",
    ),
)


class TestNoStaleLeasePremiseWaivers:
    """Every stale expired-lease citation T-2612 found is gone for good."""

    def test_stale_lease_citations_are_gone(self) -> None:
        """None of T-2612's audited stale citations exist in the current tree."""
        hits: list[str] = []
        for rel_path, needle in _STALE_LEASE_CITATIONS:
            text = (_REPO_ROOT / rel_path).read_text(encoding="utf-8")
            if needle in text:
                hits.append(f"{rel_path}: still contains {needle!r}")
        assert not hits, "\n".join(hits)
