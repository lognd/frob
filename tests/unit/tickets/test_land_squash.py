"""Tests for T-3067's curated-landing primitives
(`frob.tickets._land_squash.classify_ticket_commits`/`_is_bookkeeping_commit`).

UNWIRED, same posture as T-3546's `classify_test_then_impl_paths`: these
are pure, no-git-I/O classification helpers a future land-path caller
will use to curate a ticket's own commit history (keep real work commits,
squash bookkeeping ones) -- this test file proves the classification
logic in isolation.
"""

from __future__ import annotations

from frob.tickets._land_squash import (
    _is_bookkeeping_commit,
    classify_ticket_commits,
)


class TestIsBookkeepingCommit:
    # frob:tests \
    # tests/unit/tickets/test_land_squash.py::TestIsBookkeepingCommit.test_pure_ticket_ledger_paths_are_bookkeeping  # noqa: E501
    def test_pure_ticket_ledger_paths_are_bookkeeping(self) -> None:
        """A commit touching only tickets/*.md is bookkeeping."""
        assert _is_bookkeeping_commit(["tickets/T-1234/ticket.md"]) is True

    def test_pure_frob_cache_paths_are_bookkeeping(self) -> None:
        """A commit touching only .frob/* (e.g. a cache/lock artifact) is
        also bookkeeping."""
        assert _is_bookkeeping_commit([".frob/cache.db"]) is True

    def test_mixed_ledger_and_real_paths_is_not_bookkeeping(self) -> None:
        """A commit that ALSO touches a real source file is real work,
        even if it touches a ticket ledger file in the same commit."""
        assert (
            _is_bookkeeping_commit(["tickets/T-1234/ticket.md", "src/frob/x.py"])
            is False
        )

    def test_pure_source_change_is_not_bookkeeping(self) -> None:
        """A commit touching only source is real work."""
        assert _is_bookkeeping_commit(["src/frob/x.py"]) is False

    def test_empty_path_set_is_not_bookkeeping(self) -> None:
        """An empty changed-path set (a no-op commit) is never classified
        away as bookkeeping -- nothing to classify, so it must not be
        silently dropped by a caller trusting this function."""
        assert _is_bookkeeping_commit([]) is False


class TestClassifyTicketCommits:
    # frob:tests \
    # tests/unit/tickets/test_land_squash.py::TestClassifyTicketCommits.test_partitions_real_work_from_bookkeeping_preserving_order  # noqa: E501
    # frob:tests src/frob/tickets/_land_squash.py::classify_ticket_commits
    def test_partitions_real_work_from_bookkeeping_preserving_order(self) -> None:
        """T-3067's exact shape: a handful of real-work commits
        interleaved with several bookkeeping ones, in commit order."""
        commits = [
            ("sha-start", ["tickets/T-1234/ticket.md"]),
            ("sha-code-1", ["src/frob/x.py"]),
            ("sha-scope", ["tickets/T-1234/ticket.md"]),
            ("sha-code-2", ["src/frob/x.py", "tests/test_x.py"]),
            ("sha-evidence", ["tickets/T-1234/ticket.md"]),
            ("sha-done-report", ["tickets/T-1234/done-report.md"]),
        ]
        real_work, bookkeeping = classify_ticket_commits(commits)
        assert real_work == ("sha-code-1", "sha-code-2")
        assert bookkeeping == (
            "sha-start",
            "sha-scope",
            "sha-evidence",
            "sha-done-report",
        )

    def test_empty_input_returns_two_empty_tuples(self) -> None:
        """No commits at all -- both groups empty, never an error."""
        assert classify_ticket_commits([]) == ((), ())

    def test_all_real_work_no_bookkeeping(self) -> None:
        """A ticket branch with zero ledger-only commits (unusual, but
        legal) -- everything lands in real_work."""
        commits = [("sha-1", ["src/frob/x.py"]), ("sha-2", ["docs/x.md"])]
        real_work, bookkeeping = classify_ticket_commits(commits)
        assert real_work == ("sha-1", "sha-2")
        assert bookkeeping == ()

    def test_all_bookkeeping_no_real_work(self) -> None:
        """A ticket branch that is pure ledger churn (e.g. a `frob ticket
        scope`-only sequence with no code committed yet)."""
        commits = [
            ("sha-1", ["tickets/T-1234/ticket.md"]),
            ("sha-2", ["tickets/T-1234/ticket.md"]),
        ]
        real_work, bookkeeping = classify_ticket_commits(commits)
        assert real_work == ()
        assert bookkeeping == ("sha-1", "sha-2")
