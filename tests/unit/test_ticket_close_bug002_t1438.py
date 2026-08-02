"""T-1438: `frob ticket close`'s BUG002/mutation-evidence check
(`ticket_runner._close_mutation_evidence_for_ticket`) must resolve the
ticket's real base via the git merge-base against `base_ref` (default
"main"), NOT `current_branch(root)`'s own branch tip.

Root cause reproduced directly: `current_branch(root)` in a dispatched
worktree agent's normal flow resolves to the WORKTREE'S OWN branch, which
by close time already carries the ticket's own fix commit at its tip --
`_bug_repro_outcome_at_ref`'s `git worktree add --detach <scratch>
<branch-name>` then checks out the FIX itself, not the pre-fix parent, so
every bug-kind ticket's designated repro test trivially "passes at
parent". This test proves the fix by checking what ref actually reaches
`mutation_evidence_violations`/`bug_repro_violations`: it must be the
merge-base commit (main's tip, the ticket's true starting point), not the
feature branch's own name/tip (which would equal HEAD)."""

# frob:waive OPAQUE001 reason="T-1438: every setattr(...) here is pytest monkeypatch \
# with a LITERAL dotted-path string target (frob.gates.mutation_evidence_violations / \
# bug_repro_violations), the standard test seam this suite already uses -- same \
# disposition as test_ticket_close_bug002_t1427.py's file-level waiver; the mutated \
# sites are restored by monkeypatch teardown and never escape the test process"

from __future__ import annotations

import subprocess
from datetime import date
from pathlib import Path
from typing import Any

import pytest


def _git(root: Path, *args: str) -> None:
    """Run a git subprocess under `root`, raising on failure -- test
    plumbing only."""
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


def _init_repo_with_feature_branch(root: Path) -> str:
    """Build a real git repo: a `main` branch with one commit, then a
    `feature` branch checked out from it with a second commit (simulating
    a worktree agent's own fix commit already sitting at HEAD). Returns
    main's tip sha -- the merge-base the fix must be diffed/repro'd
    against, not `feature`'s own tip (== HEAD)."""
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "Test")
    _git(root, "checkout", "-q", "-b", "main")
    (root / "README.md").write_text("x\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "init")
    main_tip = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    _git(root, "checkout", "-q", "-b", "feature")
    (root / "fix.txt").write_text("the fix\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "the fix")
    return main_tip


def _ticket(kind: Any) -> Any:  # noqa: ANN401
    """A minimal in-progress ticket of the given `kind`, evidence-bearing
    enough for the mutation-evidence/BUG002 channel to run against it."""
    from frob.tickets import Origin, Ticket, TicketState

    return Ticket(
        id="T-1438-sample",
        title="sample",
        state=TicketState.IN_PROGRESS,
        kind=kind,
        origin=Origin.HUMAN,
        created=date(2026, 1, 1),
        scope=("m.py",),
        evidence=("tests/fake/test_m.py::test_add",),
        body="## Description\nx\n",
    )


class TestCloseMutationEvidenceBaseRef:
    """T-1438: `_close_mutation_evidence_for_ticket` must diff/repro
    against the merge-base with `base_ref`, not `current_branch(root)`."""

    def test_uses_merge_base_not_own_branch_tip(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_ticket_close_bug002_t1438.py::TestCloseMutationEvidenceBaseRef.test_uses_merge_base_not_own_branch_tip  # noqa: E501
        from frob.tickets._models import TicketKind

        main_tip = _init_repo_with_feature_branch(tmp_path)

        seen_refs: list[str] = []

        def _fake_mutation_violations(root: Path, ticket: Any, base_ref: str) -> tuple:  # noqa: ANN401
            seen_refs.append(base_ref)
            return ()

        def _fake_bug_violations(root: Path, ticket: Any, base_ref: str) -> tuple:  # noqa: ANN401
            seen_refs.append(base_ref)
            return ()

        monkeypatch.setattr(
            "frob.gates.mutation_evidence_violations", _fake_mutation_violations
        )
        monkeypatch.setattr("frob.gates.bug_repro_violations", _fake_bug_violations)

        from frob.app import ticket_runner

        result = ticket_runner._close_mutation_evidence_for_ticket(
            tmp_path, _ticket(TicketKind.BUG), "main"
        )

        # No violations reported (both stubs return empty) -- the point of
        # this test is which ref was passed in, not the verdict.
        assert result is None
        assert seen_refs, "mutation/bug-repro violation checks were never called"
        for ref in seen_refs:
            assert ref == main_tip, (
                f"expected the merge-base with main ({main_tip}), got "
                f"{ref!r} -- this is the feature branch's own tip if the "
                "T-1438 regression has come back"
            )
            # The old, buggy behavior passed `current_branch(root)` -- on
            # this fixture that resolves to the literal string "feature",
            # never a real commit sha. Assert the new value is NOT that.
            assert ref != "feature"

    def test_still_skips_when_merge_base_unresolvable(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_ticket_close_bug002_t1438.py::TestCloseMutationEvidenceBaseRef.test_still_skips_when_merge_base_unresolvable  # noqa: E501
        # tmp_path is NOT a git work tree at all -- the merge-base
        # resolution must fail, and the whole check degrades to "skip"
        # (None), never a false ERROR/OK verdict.
        from frob.app import ticket_runner
        from frob.tickets._models import TicketKind

        result = ticket_runner._close_mutation_evidence_for_ticket(
            tmp_path, _ticket(TicketKind.BUG), "main"
        )
        assert result is None
