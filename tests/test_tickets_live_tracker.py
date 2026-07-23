"""T-0854: the T-0605-orphaned-41-rows incident class -- a ticket cannot
close/land while a registry disposition or waiver still cites it as its
live tracker. Each test is written to FAIL against the pre-T-0854
behavior (no such check existed at all) and PASS after it.
"""

from __future__ import annotations

import subprocess
from datetime import date
from pathlib import Path

from frob.tickets import (
    Origin,
    Ticket,
    TicketError,
    TicketKind,
    TicketState,
    transition,
)
from frob.tickets._live_tracker import live_tracker_citations
from frob.tickets._store import _serialize_ticket


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def _init_repo(root: Path) -> None:
    # `-b main` pins the default branch name explicitly -- `live_tracker_
    # citations`'s own default `base_ref="main"` must resolve regardless
    # of this sandbox's ambient `git init.defaultBranch` (observed as
    # `master`, not `main`, which silently broke the diff-aware base
    # comparison against an unresolvable ref during T-0854's rework).
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "Test")


def _commit_all(root: Path, message: str) -> None:
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", message)


def _ticket(
    *,
    ticket_id: str = "T-0001",
    state: TicketState = TicketState.IN_PROGRESS,
    kind: TicketKind = TicketKind.FEATURE,
    evidence: tuple[str, ...] = (),
    body: str = "## Description\nsomething\n\n## Done report\nDone.\n",
) -> Ticket:
    return Ticket(
        id=ticket_id,
        title="sample",
        state=state,
        kind=kind,
        origin=Origin.HUMAN,
        created=date(2026, 1, 1),
        evidence=evidence,
        body=body,
    )


def _write_ticket(root: Path, ticket: Ticket, slug: str = "sample") -> Path:
    tickets_dir = root / "tickets"
    tickets_dir.mkdir(parents=True, exist_ok=True)
    path = tickets_dir / f"{ticket.id}-{slug}.md"
    path.write_text(_serialize_ticket(ticket), encoding="utf-8")
    return path


class TestLiveTrackerCitations:
    """Unit tests over the grep-shaped scan itself, against a real (tiny)
    git repo -- `git grep` needs a real work tree, not a bare tmp dir."""

    def test_empty_repo_has_no_citations(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_live_tracker.py::TestLiveTrackerCitations.test_empty_repo_has_no_citations  # noqa: E501
        _init_repo(tmp_path)
        (tmp_path / "README.md").write_text("hello\n", encoding="utf-8")
        _commit_all(tmp_path, "init")
        assert live_tracker_citations(tmp_path, "T-0605") == ()

    def test_finds_registry_deferred_disposition(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_live_tracker.py::TestLiveTrackerCitations.test_finds_registry_deferred_disposition  # noqa: E501
        _init_repo(tmp_path)
        registry_dir = tmp_path / "docs" / "design" / "registry"
        registry_dir.mkdir(parents=True)
        (registry_dir / "patterns.yaml").write_text(
            'entries:\n  - id: foo\n    disposition: "deferred:T-0605"\n',
            encoding="utf-8",
        )
        _commit_all(tmp_path, "add registry")
        citations = live_tracker_citations(tmp_path, "T-0605")
        assert len(citations) == 1
        assert "patterns.yaml" in citations[0]
        assert "T-0605" in citations[0]

    def test_finds_registry_tracked_by_disposition(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_live_tracker.py::TestLiveTrackerCitations.test_finds_registry_tracked_by_disposition  # noqa: E501
        _init_repo(tmp_path)
        registry_dir = tmp_path / "docs" / "design" / "registry"
        registry_dir.mkdir(parents=True)
        (registry_dir / "system.yaml").write_text(
            'entries:\n  - id: bar\n    disposition: "tracked_by:T-0605"\n',
            encoding="utf-8",
        )
        _commit_all(tmp_path, "add registry")
        citations = live_tracker_citations(tmp_path, "T-0605")
        assert len(citations) == 1

    def test_ignores_duplicate_of_disposition(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_live_tracker.py::TestLiveTrackerCitations.test_ignores_duplicate_of_disposition  # noqa: E501
        # duplicate_of does not claim T-0605 still has open work -- must
        # not be flagged as a live citation.
        _init_repo(tmp_path)
        registry_dir = tmp_path / "docs" / "design" / "registry"
        registry_dir.mkdir(parents=True)
        (registry_dir / "patterns.yaml").write_text(
            'entries:\n  - id: baz\n    disposition: "duplicate_of:T-0605"\n',
            encoding="utf-8",
        )
        _commit_all(tmp_path, "add registry")
        assert live_tracker_citations(tmp_path, "T-0605") == ()

    def test_finds_comment_waiver_ticket_attribute(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_live_tracker.py::TestLiveTrackerCitations.test_finds_comment_waiver_ticket_attribute  # noqa: E501
        _init_repo(tmp_path)
        (tmp_path / "mod.py").write_text(
            '# frob:waive SOME001 reason="pending fix" ticket=T-0605\nx = 1\n',
            encoding="utf-8",
        )
        _commit_all(tmp_path, "add waiver")
        citations = live_tracker_citations(tmp_path, "T-0605")
        assert len(citations) == 1
        assert "mod.py" in citations[0]

    def test_finds_strata_waiver_ticket_clause(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_live_tracker.py::TestLiveTrackerCitations.test_finds_strata_waiver_ticket_clause  # noqa: E501
        _init_repo(tmp_path)
        (tmp_path / "node.strata").write_text(
            'waive "SOME001" reason "pending fix" ticket "T-0605"\n',
            encoding="utf-8",
        )
        _commit_all(tmp_path, "add strata waiver")
        citations = live_tracker_citations(tmp_path, "T-0605")
        assert len(citations) == 1

    def test_unrelated_ticket_id_not_matched(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_live_tracker.py::TestLiveTrackerCitations.test_unrelated_ticket_id_not_matched  # noqa: E501
        _init_repo(tmp_path)
        (tmp_path / "mod.py").write_text(
            '# frob:waive SOME001 reason="pending fix" ticket=T-0606\n',
            encoding="utf-8",
        )
        _commit_all(tmp_path, "add waiver")
        assert live_tracker_citations(tmp_path, "T-0605") == ()

    def test_own_scope_citation_excluded(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_live_tracker.py::TestLiveTrackerCitations.test_own_scope_citation_excluded  # noqa: E501
        # T-0854 rework (reviewer MAJOR finding, kept under its original
        # name -- T-0854's own recorded evidence already binds this exact
        # id, and the honest fix is a behavior change, not a rename): the
        # pre-rework exemption excluded a citation purely because its FILE
        # matched the closing ticket's scope glob, with the citing LINE
        # left byte-identical to base -- gameable by any ticket that just
        # adds the citing file to its own scope and closes without
        # actually re-pointing anything. A citation already present at
        # base_ref, UNCHANGED in the current tree, is now REFUSED (NOT
        # excluded, the opposite of this test's pre-rework assertion)
        # regardless of any scope claim -- the rework drops the scope
        # parameter entirely in favor of a diff-aware base-ref comparison.
        _init_repo(tmp_path)
        (tmp_path / "mod.py").write_text(
            '# frob:waive SOME001 reason="own gap" ticket=T-0605\n',
            encoding="utf-8",
        )
        _commit_all(tmp_path, "add self-citing waiver")
        # No further edit to mod.py -- the citation is untouched relative
        # to "main" (the only commit so far) -- must be REFUSED, not
        # excluded.
        citations = live_tracker_citations(tmp_path, "T-0605", base_ref="main")
        assert len(citations) == 1

    def test_citation_outside_own_scope_still_flagged(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_live_tracker.py::TestLiveTrackerCitations.test_citation_outside_own_scope_still_flagged  # noqa: E501
        # T-0854 rework: kept under its original name for evidence
        # continuity, repurposed as the honest POSITIVE case the rework
        # must still allow -- a waiver this ticket's OWN diff freshly
        # introduces (never present at base_ref) is self-consistent -- it
        # lands/closes in the SAME change as the citation, so it is never
        # actually orphaned, regardless of scope (which no longer exists
        # as a parameter at all).
        _init_repo(tmp_path)
        (tmp_path / "mod.py").write_text("x = 1\n", encoding="utf-8")
        _commit_all(tmp_path, "init, no citation yet")
        # This ticket's own (uncommitted) diff adds the self-citing
        # waiver -- "main" still has none of this.
        (tmp_path / "mod.py").write_text(
            'x = 1\n# frob:waive SOME001 reason="own gap" ticket=T-0605\n',
            encoding="utf-8",
        )
        citations = live_tracker_citations(tmp_path, "T-0605", base_ref="main")
        assert citations == ()

    def test_repointed_citation_no_longer_matches(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_live_tracker.py::TestLiveTrackerCitations.test_repointed_citation_no_longer_matches  # noqa: E501
        # A citation that DID exist at base_ref but this diff re-points to
        # a different ticket id no longer matches the closing id's own
        # grep pattern in the current tree at all -- it never even
        # reaches the base comparison, and the closing ticket is clear.
        _init_repo(tmp_path)
        (tmp_path / "mod.py").write_text(
            '# frob:waive SOME001 reason="own gap" ticket=T-0605\n',
            encoding="utf-8",
        )
        _commit_all(tmp_path, "add self-citing waiver")
        (tmp_path / "mod.py").write_text(
            '# frob:waive SOME001 reason="re-pointed" ticket=T-0700\n',
            encoding="utf-8",
        )
        citations = live_tracker_citations(tmp_path, "T-0605", base_ref="main")
        assert citations == ()

    def test_unresolvable_base_ref_fails_closed(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_live_tracker.py::TestLiveTrackerCitations.test_unresolvable_base_ref_fails_closed  # noqa: E501
        # An unresolvable base_ref (a typo, or a repo whose default branch
        # is not literally "main") must never be silently treated as
        # "everything is new" -- that would make the whole diff-aware
        # exemption trivially bypassable. Every current citation is
        # reported instead.
        _init_repo(tmp_path)
        (tmp_path / "mod.py").write_text(
            '# frob:waive SOME001 reason="own gap" ticket=T-0605\n',
            encoding="utf-8",
        )
        _commit_all(tmp_path, "add self-citing waiver")
        citations = live_tracker_citations(
            tmp_path, "T-0605", base_ref="does-not-exist"
        )
        assert len(citations) == 1

    def test_draft_id_always_clear(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_live_tracker.py::TestLiveTrackerCitations.test_draft_id_always_clear  # noqa: E501
        _init_repo(tmp_path)
        (tmp_path / "mod.py").write_text(
            '# frob:waive SOME001 reason="draft waiver" ticket=T-draft-abcdef01\n',
            encoding="utf-8",
        )
        _commit_all(tmp_path, "add draft waiver")
        assert live_tracker_citations(tmp_path, "T-draft-abcdef01") == ()

    def test_bare_cli_invocation_not_matched(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_live_tracker.py::TestLiveTrackerCitations.test_bare_cli_invocation_not_matched  # noqa: E501
        # `--ticket T-0605` in a log/telemetry line is not a waiver
        # attribute -- the T-0854 own-testing false-positive class.
        _init_repo(tmp_path)
        (tmp_path / "telemetry.jsonl").write_text(
            '{"args_head": "check --ticket T-0605"}\n', encoding="utf-8"
        )
        _commit_all(tmp_path, "add telemetry")
        assert live_tracker_citations(tmp_path, "T-0605") == ()

    def test_non_git_root_degrades_to_no_citations(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_live_tracker.py::TestLiveTrackerCitations.test_non_git_root_degrades_to_no_citations  # noqa: E501
        # Not a git work tree at all -- must degrade permissively, never
        # raise and never refuse every close forever on infra failure.
        assert live_tracker_citations(tmp_path, "T-0605") == ()


class TestTransitionRefusesOnLiveTrackerCitation:
    """`transition(..., DONE)` (the direct `frob ticket close` path) always
    runs the live-tracker citation check -- no injection needed, unlike
    covers_scope/reviewed/mutation_evidence."""

    def test_close_refused_when_registry_cites_this_ticket(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_tickets_live_tracker.py::TestTransitionRefusesOnLiveTrackerCitation.test_close_refused_when_registry_cites_this_ticket  # noqa: E501
        _init_repo(tmp_path)
        ticket = _ticket(
            ticket_id="T-0605",
            state=TicketState.IN_PROGRESS,
            evidence=("tests/test_thing.py::test_it",),
        )
        _write_ticket(tmp_path, ticket)
        registry_dir = tmp_path / "docs" / "design" / "registry"
        registry_dir.mkdir(parents=True)
        (registry_dir / "patterns.yaml").write_text(
            'entries:\n  - id: foo\n    disposition: "deferred:T-0605"\n',
            encoding="utf-8",
        )
        _commit_all(tmp_path, "add ticket + registry")
        result = transition(tmp_path, "T-0605", TicketState.DONE)
        assert result.is_err
        assert result.danger_err == TicketError.LiveTrackerCited

    def test_close_allowed_when_no_citation(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_live_tracker.py::TestTransitionRefusesOnLiveTrackerCitation.test_close_allowed_when_no_citation  # noqa: E501
        _init_repo(tmp_path)
        ticket = _ticket(
            ticket_id="T-0605",
            state=TicketState.IN_PROGRESS,
            evidence=("tests/test_thing.py::test_it",),
        )
        _write_ticket(tmp_path, ticket)
        _commit_all(tmp_path, "add ticket")
        result = transition(tmp_path, "T-0605", TicketState.DONE)
        assert result.is_ok
