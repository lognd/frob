"""T-0537: TICK005 -- post-merge terminal-state-regression lint.

Reproduces the exact incident class: a `tickets.md` conflict resolved BY
HAND (not through `splice_ledger`/the merge driver) that keeps a stale
non-terminal state for a ticket main had already closed. Uses a real git
repository and a real merge commit -- the whole point of TICK005 is that
it inspects git history, not a mock.
"""

from __future__ import annotations

import subprocess
from datetime import date
from pathlib import Path

from frob.gates import tickets_gate
from frob.tickets import Origin, TicketKind, TicketState, load_queue
from frob.tickets._models import Ticket
from frob.tickets._store import atomic_write, ledger_path, write_ticket


def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        argv, cwd=str(cwd), check=True, capture_output=True, text=True
    )


def _git_init(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    _run(["git", "init", "-q", "-b", "main"], root)
    _run(["git", "config", "user.email", "test@example.com"], root)
    _run(["git", "config", "user.name", "Test"], root)


def _commit_all(root: Path, message: str) -> None:
    _run(["git", "add", "-A"], root)
    _run(["git", "commit", "-q", "-m", message], root)


def _head(root: Path) -> str:
    return _run(["git", "rev-parse", "HEAD"], root).stdout.strip()


def _make_merge_commit_with_content(
    root: Path, *, parent1: str, parent2: str, message: str
) -> None:
    """Build a real two-parent merge commit on `root`'s current branch
    whose resulting TREE is exactly whatever is on disk right now (already
    staged/committed as a normal commit at `parent1`) -- this is how a
    HAND-resolved conflict actually lands: git records a merge commit with
    two parents no matter how the conflict was resolved, and the tree it
    commits is whatever the human left in the working copy. Building it via
    `commit-tree` (rather than driving git's own merge/conflict machinery,
    which only conflicts when BOTH sides diverge from the merge-base on the
    same line) makes the "which side won" outcome deterministic and
    independent of git's merge heuristics, while still producing a
    genuinely-shaped 2-parent commit TICK005 inspects."""
    tree = _run(["git", "rev-parse", "HEAD^{tree}"], root).stdout.strip()
    merge_sha = _run(
        [
            "git",
            "commit-tree",
            tree,
            "-p",
            parent1,
            "-p",
            parent2,
            "-m",
            message,
        ],
        root,
    ).stdout.strip()
    _run(["git", "reset", "--hard", merge_sha], root)


def _ticket(ticket_id: str, state: TicketState) -> Ticket:
    return Ticket(
        id=ticket_id,
        title=f"{ticket_id} ticket",
        state=state,
        kind=TicketKind.BUG,
        origin=Origin.HUMAN,
        created=date(2026, 1, 1),
        body="## Description\nsomething\n## Done report\n\nevidence attached\n",
        evidence=("tests/test_x.py::test_ok",),
    )


class TestTick005MergeStateRegression:
    """`tickets_gate` -- TICK005."""

    # frob:tests tests/test_gates_tick005.py::TestTick005MergeStateRegression.test_hand_resolved_conflict_resurrecting_done_ticket_is_flagged  # noqa: E501
    def test_hand_resolved_conflict_resurrecting_done_ticket_is_flagged(
        self, tmp_path: Path
    ) -> None:
        """Main closed T-0001 (done); a stale branch still remembers it as
        queued. A `tickets.md` merge conflict resolved by hand in favor of
        the stale side (git's default line-level conflict, `checkout
        --theirs`, no splice at all) produces exactly the T-0537 7-ticket
        resurrection incident for this one ticket -- TICK005 must flag it."""
        repo = tmp_path / "repo"
        _git_init(repo)
        atomic_write(ledger_path(repo), "# Tickets\n\n")
        assert write_ticket(repo, _ticket("T-0001", TicketState.DONE)).is_ok
        _commit_all(repo, "T-0001 closed on main")
        main_sha = _head(repo)

        _run(["git", "checkout", "-q", "-b", "feature"], repo)
        assert write_ticket(repo, _ticket("T-0001", TicketState.QUEUED)).is_ok
        _commit_all(repo, "stale branch still thinks T-0001 is queued")
        feature_sha = _head(repo)

        # Hand-resolve a would-be conflict by keeping the stale (feature)
        # side's content -- the exact human mistake the incident
        # reproduces, modeled as a real 2-parent merge commit whose tree
        # is the stale, still-queued content.
        _run(["git", "checkout", "-q", "main"], repo)
        _make_merge_commit_with_content(
            repo, parent1=main_sha, parent2=feature_sha, message="merge (hand-resolved)"
        )
        assert write_ticket(repo, _ticket("T-0001", TicketState.QUEUED)).is_ok
        _run(["git", "add", "-A"], repo)
        _run(["git", "commit", "--amend", "--no-edit"], repo)

        queue = load_queue(repo).danger_ok
        assert queue.tickets["T-0001"].state == TicketState.QUEUED

        violations = tickets_gate(repo, queue)
        tick005 = [v for v in violations if v.rule == "TICK005"]
        assert len(tick005) == 1
        assert "T-0001" in tick005[0].message
        assert "done" in tick005[0].message

    # frob:tests tests/test_gates_tick005.py::TestTick005MergeStateRegression.test_forward_progress_across_a_merge_is_clean  # noqa: E501
    def test_forward_progress_across_a_merge_is_clean(self, tmp_path: Path) -> None:
        """A merge where the ticket makes ordinary FORWARD progress (queued
        -> planned) never fires TICK005 -- only a terminal-state regression
        does."""
        repo = tmp_path / "repo"
        _git_init(repo)
        atomic_write(ledger_path(repo), "# Tickets\n\n")
        assert write_ticket(repo, _ticket("T-0001", TicketState.QUEUED)).is_ok
        _commit_all(repo, "T-0001 queued")

        _run(["git", "checkout", "-q", "-b", "feature"], repo)
        assert write_ticket(repo, _ticket("T-0001", TicketState.PLANNED)).is_ok
        _commit_all(repo, "T-0001 planned on feature")

        _run(["git", "checkout", "-q", "main"], repo)
        _run(["git", "merge", "--no-ff", "-m", "merge", "feature"], repo)

        queue = load_queue(repo).danger_ok
        violations = tickets_gate(repo, queue)
        assert not any(v.rule == "TICK005" for v in violations)

    # frob:tests tests/test_gates_tick005.py::TestTick005MergeStateRegression.test_non_merge_commit_never_checked  # noqa: E501
    def test_non_merge_commit_never_checked(self, tmp_path: Path) -> None:
        """An ordinary single-parent commit (no merge in play at all) is
        never inspected by TICK005 -- there is no "first parent before this
        merge" to diff against, so it must not false-positive on a plain
        requeue of a done ticket done outside any merge context."""
        repo = tmp_path / "repo"
        _git_init(repo)
        atomic_write(ledger_path(repo), "# Tickets\n\n")
        assert write_ticket(repo, _ticket("T-0001", TicketState.DONE)).is_ok
        _commit_all(repo, "T-0001 closed")

        assert write_ticket(repo, _ticket("T-0001", TicketState.QUEUED)).is_ok
        _commit_all(repo, "ordinary requeue, no merge")

        queue = load_queue(repo).danger_ok
        violations = tickets_gate(repo, queue)
        assert not any(v.rule == "TICK005" for v in violations)

    # frob:tests tests/test_gates_tick005.py::TestTick005MergeStateRegression.test_archived_ticket_is_not_flagged  # noqa: E501
    def test_archived_ticket_is_not_flagged(self, tmp_path: Path) -> None:
        """A ticket that legitimately moved from the active ledger into
        `tickets-archive.md` (still terminal, just relocated) must not be
        mistaken for a state regression."""
        repo = tmp_path / "repo"
        _git_init(repo)
        atomic_write(ledger_path(repo), "# Tickets\n\n")
        assert write_ticket(repo, _ticket("T-0001", TicketState.DONE)).is_ok
        _commit_all(repo, "T-0001 closed on main")
        main_sha = _head(repo)

        _run(["git", "checkout", "-q", "-b", "feature"], repo)
        assert write_ticket(repo, _ticket("T-0001", TicketState.QUEUED)).is_ok
        _commit_all(repo, "stale branch")
        feature_sha = _head(repo)

        _run(["git", "checkout", "-q", "main"], repo)
        _make_merge_commit_with_content(
            repo, parent1=main_sha, parent2=feature_sha, message="merge (archived)"
        )

        # Resolve by archiving T-0001 out of the active ledger entirely
        # (its terminal state is preserved, just relocated) -- fold that
        # resolution into the same merge commit, same as the incident's
        # own hand-resolution step would.
        atomic_write(ledger_path(repo), "# Tickets\n\n")
        archive_path = repo / "tickets-archive.md"
        archive_path.write_text(
            "# Archive\n\n<!-- ticket:T-0001 -->\n```yaml\nid: T-0001\ntitle: T-0001 "
            "ticket\nstate: done\nkind: bug\norigin: human\ncreated: '2026-01-01'\n"
            "```\narchived.\n"
        )
        _run(["git", "add", "-A"], repo)
        _run(["git", "commit", "--amend", "--no-edit"], repo)

        # `load_queue` merges active+archive (T-0001 resolves via the
        # archive, still DONE) -- the archived id is never "missing" to a
        # gate join, only relocated out of the active ledger file.
        queue = load_queue(repo).danger_ok
        assert queue.tickets["T-0001"].state == TicketState.DONE

        violations = tickets_gate(repo, queue)
        assert not any(v.rule == "TICK005" for v in violations)
