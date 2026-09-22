"""Tests for T-3092/T-3899: TICK014 (`frob.gates._empty_diff_close`) --
warn when a FEATURE/BUG ticket closes done with a diff touching only
ticket bookkeeping (tickets/tickets.md/tickets-archive.md).

Positive controls (per the ticket's own acceptance criteria): a BUG-kind
ticket with no scope exemption that closes with a diff touching only
`tickets/` MUST fire (`test_bug_warns`); the symmetric
FEATURE-kind case also fires. A docs-kind, epic-tier, or
no_scope_declared ticket that closes with an empty code diff MUST stay
quiet (one fixture per exemption, per the acceptance criteria's own "each
exemption needs its own must-stay-quiet fixture" instruction). A ticket
with a REAL code diff, an open (non-done) ticket, and a Done report with
no parsable Changed block at all are additional must-stay-quiet controls
this module's own docstring commits to.

T-3899 DRIFT-LOCK additions (`TestTick014LandCommit`): a ticket recording
`land_commit` is judged by THAT commit's own `git show --stat` diff, not
the stored done-report Changed block -- reproducing, then locking the
fix for, the exact false-positive class the ticket reports: a
`feat:`/`fix:` code commit followed by a separate `chore(tickets): close
T-####` commit, later squashed by `frob ticket land` into one
`land_commit`. These use a REAL temporary git repo (`_git_repo`) rather
than a hand-typed `git show --stat` string, so the fixture cannot drift
from what git itself actually emits.
"""

from __future__ import annotations

import subprocess
from datetime import date
from pathlib import Path

from frob.gates._empty_diff_close import empty_code_diff_violations
from frob.tickets import (
    Origin,
    Priority,
    Ticket,
    TicketKind,
    TicketQueue,
    TicketState,
    TicketTier,
)

#: Any path works for `root` when a ticket has no `land_commit` -- that
#: branch never touches git at all (falls straight to the stored Changed
#: block), so tests exercising only that branch pass this rather than
#: paying for a real repo fixture.
_UNUSED_ROOT = Path(".")


def _changed_block(*lines: str) -> str:
    """Render lines as the exact `### Changed` fenced shape
    `frob.tickets._evidence.render_changed_block` produces, so fixtures
    exercise the real parse target rather than a hand-approximated one."""
    body = "\n".join(lines)
    return f"### Changed\n```\n{body}\n```\n"


def _ticket(
    *,
    ticket_id: str,
    kind: TicketKind = TicketKind.BUG,
    state: TicketState = TicketState.DONE,
    tier: TicketTier = TicketTier.TICKET,
    no_scope_declared: bool = False,
    body: str = "",
    land_commit: str | None = None,
) -> Ticket:
    """Minimal Done-ticket fixture, same shape `test_gates_milestone.py::
    _ticket` uses (kept as its own local copy for the same "two unrelated
    test modules should not couple on a tiny constructor" reasoning that
    file's docstring gives)."""
    return Ticket(
        id=ticket_id,
        title=f"ticket {ticket_id}",
        state=state,
        kind=kind,
        origin=Origin.HUMAN,
        created=date(2026, 1, 1),
        priority=Priority.MEDIUM,
        blocked_by=(),
        parent=None,
        tier=tier,
        scope=(),
        evidence=(),
        attachments=(),
        acceptance=(),
        threat=None,
        body=body,
        no_scope_declared=no_scope_declared,
        land_commit=land_commit,
    )


def _git_repo(tmp_path: Path) -> Path:
    """Init a real, throwaway git repo at `tmp_path` -- `git show --stat`
    needs an actual commit to read, so `_tick014_changed_paths`'s
    `land_commit` branch is exercised against real git output, never a
    hand-typed approximation of it."""
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"], cwd=root, check=True
    )
    subprocess.run(["git", "config", "user.name", "test"], cwd=root, check=True)
    (root / "README.md").write_text("seed\n")
    subprocess.run(["git", "add", "README.md"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "seed"], cwd=root, check=True)
    return root


def _commit(root: Path, *files: tuple[str, str]) -> str:
    """Write `files` (relative path, content) and commit them, returning
    the new commit's sha."""
    for rel, content in files:
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        subprocess.run(["git", "add", rel], cwd=root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "change"], cwd=root, check=True)
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


class TestTick014:
    """`empty_code_diff_violations(_UNUSED_ROOT, queue)` -- TICK014."""

    # frob:tests src/frob/gates/_empty_diff_close.py::empty_code_diff_violations
    def test_bug_warns(self) -> None:
        """MUST-FIRE: a done BUG-kind ticket whose Changed block lists
        only a `tickets/` path fires TICK014."""
        t = _ticket(
            ticket_id="T-9001",
            kind=TicketKind.BUG,
            body=_changed_block(
                " tickets/T-9001/ticket.md | 12 +++++++",
                " 1 file changed, 12 insertions(+)",
            ),
        )
        queue = TicketQueue(tickets={t.id: t})
        violations = empty_code_diff_violations(_UNUSED_ROOT, queue)
        assert len(violations) == 1
        assert violations[0].rule == "TICK014"
        assert "T-9001" in violations[0].message
# frob:tests src/frob/gates/_empty_diff_close.py::empty_code_diff_violations

    def test_feature_warns(self) -> None:
        """MUST-FIRE: the symmetric FEATURE-kind case, and the exact
        `(no changed files detected)` sentinel (a ticket with a Done
        report but literally zero diff, `render_changed_block`'s other
        output shape)."""
        t = _ticket(
            ticket_id="T-9002",
            kind=TicketKind.FEATURE,
            body="### Changed\n(no changed files detected)\n",
        )
        queue = TicketQueue(tickets={t.id: t})
        violations = empty_code_diff_violations(_UNUSED_ROOT, queue)
        assert len(violations) == 1
        # frob:tests src/frob/gates/_empty_diff_close.py::empty_code_diff_violations
        assert violations[0].rule == "TICK014"

    def test_docs_kind_quiet(self) -> None:
        """MUST-STAY-QUIET: a docs-kind ticket legitimately closes with
        only a ledger-touching diff -- no code was ever expected."""
        t = _ticket(
            ticket_id="T-9003",
            kind=TicketKind.DOCS,
            body=_changed_block(" tickets/T-9003/ticket.md | 5 +++"),
        )
        # frob:tests src/frob/gates/_empty_diff_close.py::empty_code_diff_violations
        queue = TicketQueue(tickets={t.id: t})
        assert empty_code_diff_violations(_UNUSED_ROOT, queue) == ()

    def test_epic_tier_quiet(self) -> None:
        """MUST-STAY-QUIET: an epic-tier rollup ticket legitimately closes
        without its own code diff (its descendants carry the code)."""
        t = _ticket(
            ticket_id="T-9004",
            kind=TicketKind.BUG,
            tier=TicketTier.EPIC,
            body=_changed_block(" tickets/T-9004/ticket.md | 3 +"),
        # frob:tests src/frob/gates/_empty_diff_close.py::empty_code_diff_violations  # noqa: E501
        )
        queue = TicketQueue(tickets={t.id: t})
        assert empty_code_diff_violations(_UNUSED_ROOT, queue) == ()

    def test_no_scope_quiet(self) -> None:
        """MUST-STAY-QUIET: a ticket with an explicit `no_scope_declared`
        opt-out (a decision record, per this module's own docstring) --
        the ticket already told the ledger it never expected a code
        diff."""
        t = _ticket(
            ticket_id="T-9005",
            kind=TicketKind.BUG,
            no_scope_declared=True,
            # frob:tests src/frob/gates/_empty_diff_close.py::empty_code_diff_violations  # noqa: E501
            body=_changed_block(" tickets/T-9005/ticket.md | 8 ++++"),
        )
        queue = TicketQueue(tickets={t.id: t})
        assert empty_code_diff_violations(_UNUSED_ROOT, queue) == ()

    # frob:tests src/frob/gates/_empty_diff_close.py::empty_code_diff_violations  # noqa: E501
    def test_real_diff_quiet(self) -> None:
        """MUST-STAY-QUIET: a done BUG ticket whose Changed block touches
        a real source file alongside the ticket file -- the normal,
        expected shape."""
        t = _ticket(
            ticket_id="T-9006",
            kind=TicketKind.BUG,
            body=_changed_block(
                " src/frob/gitio.py | 4 ++--",
                " tickets/T-9006/ticket.md | 12 +++++++",
                " 2 files changed, 14 insertions(+), 2 deletions(-)",
            ),
        )
        queue = TicketQueue(tickets={t.id: t})
        assert empty_code_diff_violations(_UNUSED_ROOT, queue) == ()

    def test_no_block_quiet(self) -> None:
        """MUST-STAY-QUIET: a Done report with no parsable `### Changed`
        block at all (predates T-0458, or a hand-written narrative) is a
        disclosed "cannot tell" gap, not a claimed empty diff -- silent,
        never a false-positive finding."""
        t = _ticket(
            ticket_id="T-9007",
            kind=TicketKind.BUG,
            body="## Done report\n\nDid the thing.\n",
        )
        queue = TicketQueue(tickets={t.id: t})
        assert empty_code_diff_violations(_UNUSED_ROOT, queue) == ()

    def test_open_never_fires(self) -> None:
        """MUST-STAY-QUIET: a non-done ticket (queued here) never fires --
        it has not closed yet, so there is nothing to check."""
        t = _ticket(
            ticket_id="T-9008",
            kind=TicketKind.BUG,
            state=TicketState.QUEUED,
            body=_changed_block(" tickets/T-9008/ticket.md | 2 ++"),
        )
        queue = TicketQueue(tickets={t.id: t})
        assert empty_code_diff_violations(_UNUSED_ROOT, queue) == ()


class TestTick014LandCommit:
    """T-3899 drift-lock: `land_commit`'s own diff, not the stored
    done-report Changed block, is what TICK014 judges a closed ticket by
    when a `land_commit` is recorded."""

    def test_land_commit_with_real_code_quiet(self, tmp_path: Path) -> None:
        """MUST-STAY-QUIET, reproducing the ticket's reported false
        positive: `land_commit` is a squash of a `feat:` code commit
        followed by a `chore(tickets): close T-####` bookkeeping commit
        (this project's mandated one-logical-change-per-commit
        convention) -- its OWN diff touches a real source file, so
        TICK014 must stay quiet even though the STORED Changed block
        (composed earlier, before the squash) claims bookkeeping-only."""
        root = _git_repo(tmp_path)
        sha = _commit(
            root,
            ("src/frob/widget.py", "def widget(): ...\n"),
            ("tickets/T-9101/ticket.md", "state: done\n"),
        )
        t = _ticket(
            ticket_id="T-9101",
            kind=TicketKind.BUG,
            land_commit=sha,
            # Stale/wrong on purpose: proves land_commit, not this block,
            # decides the outcome.
            body=_changed_block(" tickets/T-9101/ticket.md | 1 +"),
        )
        queue = TicketQueue(tickets={t.id: t})
        assert empty_code_diff_violations(root, queue) == ()

    def test_land_commit_bookkeeping_only_warns(self, tmp_path: Path) -> None:
        """MUST-FIRE: `land_commit`'s own diff touches ONLY `tickets/` --
        the true-positive case (T-3064's own incident) survives the
        land_commit-based rewrite unchanged."""
        root = _git_repo(tmp_path)
        sha = _commit(root, ("tickets/T-9102/ticket.md", "state: done\n"))
        t = _ticket(ticket_id="T-9102", kind=TicketKind.BUG, land_commit=sha)
        queue = TicketQueue(tickets={t.id: t})
        violations = empty_code_diff_violations(root, queue)
        assert len(violations) == 1
        assert "T-9102" in violations[0].message

    def test_land_commit_overrides_stale_empty_changed_block(
        self, tmp_path: Path
    ) -> None:
        """MUST-STAY-QUIET: the stored Changed block reads as the literal
        `(no changed files detected)` sentinel (as it would if `done-
        report` ran against an already-merged base, T-3899's diagnosis),
        but `land_commit` proves real code landed -- land_commit wins."""
        root = _git_repo(tmp_path)
        sha = _commit(
            root,
            ("src/frob/other.py", "x = 1\n"),
            ("tickets/T-9103/ticket.md", "state: done\n"),
        )
        t = _ticket(
            ticket_id="T-9103",
            kind=TicketKind.BUG,
            land_commit=sha,
            body="### Changed\n(no changed files detected)\n",
        )
        queue = TicketQueue(tickets={t.id: t})
        assert empty_code_diff_violations(root, queue) == ()

    def test_unresolvable_land_commit_falls_back_to_changed_block(
        self, tmp_path: Path
    ) -> None:
        """MUST-FIRE (fallback, edge case 3 -- effectively "no usable
        land_commit"): a `land_commit` sha this clone cannot resolve (a
        shallow clone, a corrupt/rewritten value) falls back to the
        stored Changed block instead of silently passing -- the original
        true-positive detection path stays intact when git cannot answer
        for land_commit."""
        root = _git_repo(tmp_path)
        t = _ticket(
            ticket_id="T-9104",
            kind=TicketKind.BUG,
            land_commit="0" * 40,
            body=_changed_block(" tickets/T-9104/ticket.md | 1 +"),
        )
        queue = TicketQueue(tickets={t.id: t})
        violations = empty_code_diff_violations(root, queue)
        assert len(violations) == 1
        assert "T-9104" in violations[0].message
