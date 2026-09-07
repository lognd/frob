"""Discriminating tests for T-0398 (evidence integrity, D-01..D-12,
docs/audits/tickets-testing.md). Each test is written to FAIL against the
pre-T-0398 behavior (verified by reverting the relevant fix locally) and
PASS after it -- not a vacuous "does it still import" smoke test.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from frob.gates import evidence_covers_scope
from frob.gitio import Diff, Hunk
from frob.graph._models import (
    Digests,
    Edge,
    EdgeKind,
    GraphSnapshot,
    SymbolId,
    SymbolRecord,
)
from frob.lang._models import SymbolKind
from frob.testing import SelectConfig, select_tests
from frob.tickets import (
    Origin,
    Ticket,
    TicketError,
    TicketKind,
    TicketState,
    add_evidence,
    land,
    new_ticket,
    reverify_cmd_evidence,
    run_cmd_evidence,
    transition,
)
from frob.tickets._land import splice_ledger
from frob.tickets._land_ledger_merge import _newer
from frob.tickets._models import (
    TicketSpec,
    has_substantive_done_report,
    replace_done_report_section,
)
from frob.tickets._store import (
    _serialize_ticket,
    atomic_write,
    ledger_path,
    write_ticket,
)


def _digests(seed: str) -> Digests:
    return Digests(sig=seed, body=seed, doc=seed)


def _symbol(path: str, qualname: str, span: tuple[int, int]) -> SymbolRecord:
    return SymbolRecord(
        id=SymbolId(path=path, qualname=qualname),
        kind=SymbolKind.FUNCTION,
        public=True,
        digests=_digests(f"{path}:{qualname}"),
        span=span,
    )


# frob:ticket T-0995
def _assert_transition_to_done_allows(
    tmp_path: Path, **transition_kwargs: bool
) -> None:
    """A single IN_PROGRESS ticket, written then transitioned to DONE with
    the given `transition()` override kwarg(s), succeeds (T-0995): the
    shared arrange/act/assert `TestD02ScopeBinding.
    test_transition_allows_when_covers_scope_true` and
    `TestT0417ReverifyEvidenceOnClose.
    test_transition_allows_when_evidence_reverified_true` used to duplicate
    byte-for-byte, differing only in which override kwarg they passed --
    extracted here since both live in this same file, testing two closely
    related evidence-transition safety overrides side by side, not two
    distinct domains whose ownership dedup would blur."""
    ticket = _ticket(
        state=TicketState.IN_PROGRESS,
        evidence=("tests/test_thing.py::test_x",),
        body="## Description\nx\n\n## Done report\nDone.\n",
    )
    _write(tmp_path, ticket)
    result = transition(tmp_path, "T-0001", TicketState.DONE, **transition_kwargs)
    assert result.is_ok


def _ticket(
    *,
    ticket_id: str = "T-0001",
    state: TicketState = TicketState.IN_PROGRESS,
    kind: TicketKind = TicketKind.FEATURE,
    scope: tuple[str, ...] = (),
    evidence: tuple[str, ...] = (),
    body: str = "## Description\nsomething\n",
) -> Ticket:
    return Ticket(
        id=ticket_id,
        title="sample",
        state=state,
        kind=kind,
        origin=Origin.HUMAN,
        created=date(2026, 1, 1),
        scope=scope,
        evidence=evidence,
        body=body,
    )


def _write(root: Path, ticket: Ticket, slug: str = "sample") -> Path:
    tickets_dir = root / "tickets"
    tickets_dir.mkdir(parents=True, exist_ok=True)
    path = tickets_dir / f"{ticket.id}-{slug}.md"
    path.write_text(_serialize_ticket(ticket), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# D-01: evidence must PASS, not merely resolve/collect
# ---------------------------------------------------------------------------
class TestD01PassVerification:
    def test_red_evidence_rejected_when_passed_supplied(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_evidence_integrity.py::TestD01PassVerification.test_red_evidence_r\
        # ejected_when_passed_supplied
        ticket = _ticket(state=TicketState.IN_PROGRESS)
        _write(tmp_path, ticket)
        node = "tests/test_x.py::test_it"
        # collected (exists) but NOT in passed (it failed on the actual run)
        result = add_evidence(
            tmp_path,
            "T-0001",
            [node],
            collected=frozenset({node}),
            passed=frozenset(),
        )
        assert result.is_err
        assert result.danger_err == TicketError.EvidenceNotPassing

    def test_green_evidence_recorded_when_passed_supplied(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_evidence_integrity.py::TestD01PassVerification.test_green_evidence\
        # _recorded_when_passed_supplied
        ticket = _ticket(state=TicketState.IN_PROGRESS)
        _write(tmp_path, ticket)
        node = "tests/test_x.py::test_it"
        result = add_evidence(
            tmp_path,
            "T-0001",
            [node],
            collected=frozenset({node}),
            passed=frozenset({node}),
        )
        assert result.is_ok
        assert node in result.danger_ok.evidence

    def test_passed_none_preserves_old_permissive_behavior(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/test_evidence_integrity.py::TestD01PassVerification.test_passed_none_pr\
        # eserves_old_permissive_behavior
        ticket = _ticket(state=TicketState.IN_PROGRESS)
        _write(tmp_path, ticket)
        node = "tests/test_x.py::test_it"
        result = add_evidence(tmp_path, "T-0001", [node], collected=frozenset({node}))
        assert result.is_ok


# ---------------------------------------------------------------------------
# D-02: evidence must bind to a touched/scope symbol
# ---------------------------------------------------------------------------
# frob:ticket T-3156
class TestD02ScopeBinding:
    def test_transition_rejects_when_covers_scope_false(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_evidence_integrity.py::TestD02ScopeBinding.test_transition_rejects\
        # _when_covers_scope_false
        ticket = _ticket(
            state=TicketState.IN_PROGRESS,
            evidence=("tests/test_unrelated.py::test_x",),
            body="## Description\nx\n\n## Done report\nDone.\n",
        )
        _write(tmp_path, ticket)
        result = transition(tmp_path, "T-0001", TicketState.DONE, covers_scope=False)
        assert result.is_err
        assert result.danger_err == TicketError.EvidenceScopeUnbound

    def test_transition_allows_when_covers_scope_true(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_evidence_integrity.py::TestD02ScopeBinding.test_transition_allows_\
        # when_covers_scope_true
        _assert_transition_to_done_allows(tmp_path, covers_scope=True)

    def test_evidence_covers_scope_true_for_bound_test(self) -> None:
        # frob:tests \
        # tests/test_evidence_integrity.py::TestD02ScopeBinding.test_evidence_covers_sc\
        # ope_true_for_bound_test
        ticket = _ticket(
            scope=("src/pkg/",),
            evidence=("tests/test_thing.py::test_it",),
        )
        snapshot = GraphSnapshot(
            root=".",
            symbols={},
            edges=(
                Edge(
                    src="src/pkg/thing.py::do_thing",
                    kind=EdgeKind.TESTS,
                    target="tests/test_thing.py::test_it",
                    origin="src/pkg/thing.py:1",
                ),
            ),
        )
        assert evidence_covers_scope(ticket, snapshot) is True

    def test_evidence_covers_scope_false_for_unrelated_test(self) -> None:
        # frob:tests \
        # tests/test_evidence_integrity.py::TestD02ScopeBinding.test_evidence_covers_sc\
        # ope_false_for_unrelated_test
        ticket = _ticket(
            scope=("src/pkg/",),
            evidence=("tests/test_logging.py::test_levels",),
        )
        snapshot = GraphSnapshot(
            root=".",
            symbols={},
            edges=(
                Edge(
                    src="src/other/thing.py::do_other",
                    kind=EdgeKind.TESTS,
                    target="tests/test_logging.py::test_levels",
                    origin="src/other/thing.py:1",
                ),
            ),
        )
        assert evidence_covers_scope(ticket, snapshot) is False

    def test_evidence_covers_scope_true_for_docs_kind_with_cmd_evidence(
        self,
    ) -> None:
        # frob:tests \
        # tests/test_evidence_integrity.py::TestD02ScopeBinding.test_evidence_covers_sc\
        # ope_true_for_docs_kind_with_cmd_evidence
        # frob:ticket T-0444
        # A docs-kind ticket scoped to doc files has no coverable code
        # symbol; T-0215 sanctions it closing on a --evidence-cmd exit
        # status, so covers_scope must accept it (else docs tickets are
        # unclosable). No graph edge exists for the cmd evidence.
        ticket = _ticket(
            kind=TicketKind.DOCS,
            scope=("docs/modules/thing.md",),
            evidence=("cmd:grep -q foo src/x.py exit=0 sha256=0123456789ab",),
        )
        snapshot = GraphSnapshot(root=".", symbols={}, edges=())
        assert evidence_covers_scope(ticket, snapshot) is True

    def test_evidence_covers_scope_false_for_code_kind_with_cmd_shaped_evidence(
        self,
    ) -> None:
        # frob:tests \
        # tests/test_evidence_integrity.py::TestD02ScopeBinding.test_evidence_covers_sc\
        # ope_false_for_code_kind_with_cmd_shaped_evidence
        # frob:ticket T-0444
        # The docs exemption must NOT loophole a code-kind ticket: even a
        # cmd-shaped evidence entry on a bug ticket does not satisfy
        # covers_scope (code kinds cannot legitimately carry cmd evidence).
        ticket = _ticket(
            kind=TicketKind.BUG,
            scope=("src/pkg/",),
            evidence=("cmd:grep -q foo src/x.py exit=0 sha256=0123456789ab",),
        )
        snapshot = GraphSnapshot(root=".", symbols={}, edges=())
        assert evidence_covers_scope(ticket, snapshot) is False

    # frob:ticket T-3156
    def test_evidence_covers_scope_true_for_bug_kind_with_no_python_surface(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/test_evidence_integrity.py::TestD02ScopeBinding.test_evidence_covers_sc\
        # ope_true_for_bug_kind_with_no_python_surface
        # T-3156: a `bug`-kind ticket whose ENTIRE declared scope is a real,
        # existing non-Python file (a docs/ledger-only investigation, the
        # T-3147-audit shape) has no OTHER legitimate D-02 route -- cmd:
        # evidence now covers it, same as a docs/ux-kind ticket already
        # could.
        (tmp_path / "notes.md").write_text("investigation notes\n")
        ticket = _ticket(
            kind=TicketKind.BUG,
            scope=("notes.md",),
            evidence=("cmd:printf ok exit=0 sha256=0123456789ab",),
        )
        snapshot = GraphSnapshot(root=str(tmp_path), symbols={}, edges=())
        assert evidence_covers_scope(ticket, snapshot) is True

    # frob:ticket T-3156
    def test_evidence_covers_scope_false_for_bug_kind_with_real_python_surface(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/test_evidence_integrity.py::TestD02ScopeBinding.test_evidence_covers_sc\
        # ope_false_for_bug_kind_with_real_python_surface
        # Must-stay-quiet: a `bug`-kind ticket whose scope has a REAL,
        # existing Python file must NOT get the new exemption -- cmd:
        # evidence still cannot loophole an actual code change, exactly
        # like the pre-existing sibling test above (fictional scope).
        pkg = tmp_path / "src" / "pkg"
        pkg.mkdir(parents=True)
        (pkg / "x.py").write_text("def f():\n    pass\n")
        ticket = _ticket(
            kind=TicketKind.BUG,
            scope=("src/pkg/",),
            evidence=("cmd:printf ok exit=0 sha256=0123456789ab",),
        )
        snapshot = GraphSnapshot(root=str(tmp_path), symbols={}, edges=())
        assert evidence_covers_scope(ticket, snapshot) is False


# frob:ticket T-4170
class TestT4170PreExistingTestOutsideScopeBoundViaDirective:
    """F-367: a bug/feature-kind ticket's ONLY honest evidence is a
    pre-existing test that predates it -- that test's FILE sits outside
    the ticket's scope (it was never touched), but the test's own
    `frob:tests` binding names a symbol INSIDE scope. VERIFIED PREMISE
    FIRST (the ticket's own instruction): `evidence_covers_scope`'s route
    1 (a `TESTS`-edge walk, `_evidence_binds_to_scope`) ALREADY accepts
    this shape at the unit level (`TestD02ScopeBinding.test_evidence_
    covers_scope_true_for_bound_test`, pre-existing, unchanged) -- the
    premise as literally stated (this shape is refused today) is FALSE
    for `evidence_covers_scope` itself. These tests additionally prove it
    against a REAL graph build (not a hand-constructed `GraphSnapshot`,
    which cannot catch a directive-PARSING gap the unit-level test is
    blind to), and bug-kind specifically (the reported ticket kind)."""

    def _bug_kind_repo_with_directive_bound_test(
        self, tmp_path: Path
    ) -> tuple[Ticket, "GraphSnapshot"]:  # noqa: F821
        """A real git repo: `src/pkg/thing.py` (in scope) carries a
        directive comment naming `tests/test_thing.py::test_it` on its
        one public function; that test file (NOT in scope, pre-existing,
        never touched by this ticket) is what the directive names.
        Returns a bug-kind ticket citing that test as its only evidence,
        plus the REAL `GraphSnapshot` built over this repo."""
        import subprocess

        from frob.graph import build_graph

        (tmp_path / "src" / "pkg").mkdir(parents=True)
        (tmp_path / "tests").mkdir()
        (tmp_path / "src" / "pkg" / "thing.py").write_text(
            "# frob:tests tests/test_thing.py::test_it\n"
            "def do_thing() -> int:\n"
            "    return 1\n"
        )
        (tmp_path / "tests" / "test_thing.py").write_text(
            "def test_it():\n    assert True\n"
        )
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "config", "user.email", "t@example.com"],
            cwd=tmp_path,
            check=True,
        )
        subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "pre-existing source + test"],
            cwd=tmp_path,
            check=True,
        )
        snapshot = build_graph(tmp_path, tmp_path / ".frob" / "cache.db").danger_ok
        ticket = _ticket(
            kind=TicketKind.BUG,
            # Only the SOURCE file is in scope -- the pre-existing test
            # file is deliberately NOT, matching F-367's exact repro
            # (widening scope to include it would be the lie the ticket
            # names).
            scope=("src/pkg/thing.py",),
            evidence=("tests/test_thing.py::test_it",),
        )
        return ticket, snapshot

    def test_directive_bound_pre_existing_test_covers_scope(
        self, tmp_path: Path
    ) -> None:
        """MUST-FIRE fixture: a bug-kind ticket's evidence is a
        pre-existing, out-of-scope test bound via a REAL `frob:tests`
        directive to an in-scope symbol -- `evidence_covers_scope`
        accepts it against a REAL (not hand-built) graph."""
        # frob:tests tests/test_evidence_integrity.py::TestT4170PreExistingTestOutsideScopeBoundViaDirective.test_directive_bound_pre_existing_test_covers_scope  # noqa: E501
        ticket, snapshot = self._bug_kind_repo_with_directive_bound_test(tmp_path)
        assert evidence_covers_scope(ticket, snapshot) is True

    def test_directive_bound_pre_existing_test_closes_cleanly(
        self, tmp_path: Path
    ) -> None:
        """MUST-FIRE fixture, end to end: the same ticket actually
        CLOSES through `transition(..., DONE, covers_scope=...)` once a
        substantive Done report is attached -- the real close path, not
        only the coverage predicate in isolation."""
        # frob:tests tests/test_evidence_integrity.py::TestT4170PreExistingTestOutsideScopeBoundViaDirective.test_directive_bound_pre_existing_test_closes_cleanly  # noqa: E501
        ticket, snapshot = self._bug_kind_repo_with_directive_bound_test(tmp_path)
        ticket = ticket.model_copy(
            update={
                "id": "T-0001",
                "title": "sample",
                "state": TicketState.IN_PROGRESS,
                "body": "## Description\nx\n\n## Done report\nFixed do_thing; "
                "verified via the pre-existing test_it.\n",
            }
        )
        _write(tmp_path, ticket)
        covers = evidence_covers_scope(ticket, snapshot)
        result = transition(tmp_path, "T-0001", TicketState.DONE, covers_scope=covers)
        assert result.is_ok, result.err

    def test_unconnected_pre_existing_test_still_refused(self, tmp_path: Path) -> None:
        """MUST-STAY-QUIET: a pre-existing, out-of-scope test with NO
        `frob:tests` connection to anything in scope is still refused --
        the binding must do real work, not merely "the evidence file
        predates the ticket"."""
        # frob:tests tests/test_evidence_integrity.py::TestT4170PreExistingTestOutsideScopeBoundViaDirective.test_unconnected_pre_existing_test_still_refused  # noqa: E501
        ticket, snapshot = self._bug_kind_repo_with_directive_bound_test(tmp_path)
        unconnected = ticket.model_copy(
            update={"evidence": ("tests/test_unrelated.py::test_z",)}
        )
        assert evidence_covers_scope(unconnected, snapshot) is False

    def test_scope_widened_without_a_touching_diff_remains_detectable(
        self, tmp_path: Path
    ) -> None:
        """THIRD FIXTURE: WHAT TO DO explicitly forbids adopting "a
        commit-diff entry as scope proof" as the PRIMARY fix, since it
        would let any kind close with no real test binding at all. This
        proves the alternative it warns against remains independently
        checkable rather than silently accepted: a ticket whose `scope`
        includes a file `working_diff` shows was never touched is a
        detectable mismatch using EXISTING primitives (`Ticket.scope` vs.
        `working_diff(root, base).hunks`) -- no new escape hatch was
        added, and none is needed for this to stay visible."""
        # frob:tests tests/test_evidence_integrity.py::TestT4170PreExistingTestOutsideScopeBoundViaDirective.test_scope_widened_without_a_touching_diff_remains_detectable  # noqa: E501
        from frob.gitio import working_diff

        ticket, _snapshot = self._bug_kind_repo_with_directive_bound_test(tmp_path)
        # Widen scope (as the rejected alternative fix would encourage)
        # to also cover the pre-existing test file this diff never
        # touched at all -- everything here predates "main"'s only commit.
        widened = ticket.model_copy(
            update={"scope": ticket.scope + ("tests/test_thing.py",)}
        )
        diff = working_diff(tmp_path, "main")
        touched = {h.file for h in diff.danger_ok.hunks} if diff.is_ok else set()
        untouched_but_scoped = [g for g in widened.scope if g not in touched]
        assert "tests/test_thing.py" in untouched_but_scoped


# ---------------------------------------------------------------------------
# D-03: Done report must be substantive, not a bare heading
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# T-0844: `frob ticket close` (transition's own mutation_evidence
# parameter) refuses on the same TEST016 confirmatory-only-evidence
# finding `frob ticket land` already refuses on, instead of being exempt.
# ---------------------------------------------------------------------------
class TestT0844MutationEvidenceOnClose:
    def test_transition_rejects_when_mutation_evidence_false(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_evidence_integrity.py::TestT0844MutationEvidenceOnClose.test_transition_rejects_when_mutation_evidence_false  # noqa: E501
        ticket = _ticket(
            state=TicketState.IN_PROGRESS,
            kind=TicketKind.SECURITY,
            evidence=("tests/test_thing.py::test_x",),
            body="## Description\nx\n\n## Done report\nDone.\n",
        )
        _write(tmp_path, ticket)
        result = transition(
            tmp_path, "T-0001", TicketState.DONE, mutation_evidence=False
        )
        assert result.is_err
        assert result.danger_err == TicketError.EvidenceConfirmatoryOnly

    def test_transition_allows_when_mutation_evidence_true(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_evidence_integrity.py::TestT0844MutationEvidenceOnClose.test_transition_allows_when_mutation_evidence_true  # noqa: E501
        ticket = _ticket(
            state=TicketState.IN_PROGRESS,
            kind=TicketKind.SECURITY,
            evidence=("tests/test_thing.py::test_x",),
            body="## Description\nx\n\n## Done report\nDone.\n",
        )
        _write(tmp_path, ticket)
        result = transition(
            tmp_path, "T-0001", TicketState.DONE, mutation_evidence=True
        )
        assert result.is_ok

    def test_transition_permissive_when_mutation_evidence_none(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_evidence_integrity.py::TestT0844MutationEvidenceOnClose.test_transition_permissive_when_mutation_evidence_none  # noqa: E501
        ticket = _ticket(
            state=TicketState.IN_PROGRESS,
            kind=TicketKind.SECURITY,
            evidence=("tests/test_thing.py::test_x",),
            body="## Description\nx\n\n## Done report\nDone.\n",
        )
        _write(tmp_path, ticket)
        result = transition(tmp_path, "T-0001", TicketState.DONE)
        assert result.is_ok


# ---------------------------------------------------------------------------
# T-0417 N-02: `frob ticket close` must re-verify evidence against the
# CURRENT tree, not trust the pass status recorded at evidence-record time
# (docs/audits/tickets-testing-round2.md).
# ---------------------------------------------------------------------------
# frob:ticket T-0417
class TestT0417ReverifyEvidenceOnClose:
    def test_transition_rejects_when_evidence_reverified_false(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_evidence_integrity.py::TestT0417ReverifyEvidenceOnClose.test_transition_rejects_when_evidence_reverified_false  # noqa: E501
        ticket = _ticket(
            state=TicketState.IN_PROGRESS,
            evidence=("tests/test_thing.py::test_x",),
            body="## Description\nx\n\n## Done report\nDone.\n",
        )
        _write(tmp_path, ticket)
        result = transition(
            tmp_path, "T-0001", TicketState.DONE, evidence_reverified=False
        )
        assert result.is_err
        assert result.danger_err == TicketError.EvidenceNotPassing

    def test_transition_allows_when_evidence_reverified_true(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_evidence_integrity.py::TestT0417ReverifyEvidenceOnClose.test_transition_allows_when_evidence_reverified_true  # noqa: E501
        _assert_transition_to_done_allows(tmp_path, evidence_reverified=True)

    def test_transition_permissive_when_evidence_reverified_none(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_evidence_integrity.py::TestT0417ReverifyEvidenceOnClose.test_transition_permissive_when_evidence_reverified_none  # noqa: E501
        ticket = _ticket(
            state=TicketState.IN_PROGRESS,
            evidence=("tests/test_thing.py::test_x",),
            body="## Description\nx\n\n## Done report\nDone.\n",
        )
        _write(tmp_path, ticket)
        result = transition(tmp_path, "T-0001", TicketState.DONE)
        assert result.is_ok


class TestD03SubstantiveDoneReport:
    def test_empty_section_rejected(self) -> None:
        # frob:tests \
        # tests/test_evidence_integrity.py::TestD03SubstantiveDoneReport.test_empty_sec\
        # tion_rejected
        assert (
            has_substantive_done_report("## Description\nx\n\n## Done report\n")
            is False
        )

    def test_blank_lines_only_rejected(self) -> None:
        # frob:tests \
        # tests/test_evidence_integrity.py::TestD03SubstantiveDoneReport.test_blank_lin\
        # es_only_rejected
        body = "## Description\nx\n\n## Done report\n\n   \n\n"
        assert has_substantive_done_report(body) is False

    def test_real_content_accepted(self) -> None:
        # frob:tests \
        # tests/test_evidence_integrity.py::TestD03SubstantiveDoneReport.test_real_cont\
        # ent_accepted
        body = "## Description\nx\n\n## Done report\nAll good.\n"
        assert has_substantive_done_report(body) is True

    def test_close_rejects_empty_done_report(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_evidence_integrity.py::TestD03SubstantiveDoneReport.test_close_rej\
        # ects_empty_done_report
        # T-4167: this ticket HAS evidence -- an empty Done report is the
        # ONLY missing precondition, so the refusal must name THAT
        # (`MissingDoneReport`), not the unrelated `MissingEvidence` the
        # pre-T-4167 disjunction collapsed onto regardless of which half
        # actually failed.
        ticket = _ticket(
            state=TicketState.IN_PROGRESS,
            evidence=("tests/test_thing.py::test_it",),
            body="## Description\nx\n\n## Done report\n",
        )
        _write(tmp_path, ticket)
        result = transition(tmp_path, "T-0001", TicketState.DONE)
        assert result.is_err
        assert result.danger_err == TicketError.MissingDoneReport


# frob:ticket T-4167
class TestT4167SplitMissingEvidenceDisjunction:
    """F-363: `close`'s `MissingEvidence` used to be ONE error name for
    TWO unrelated preconditions (no evidence bound; no Done report
    recognised) -- split so each reports itself."""

    def test_done_report_present_no_evidence_names_missing_evidence(
        self, tmp_path: Path
    ) -> None:
        """MUST-FIRE fixture: a ticket with a real Done report but no
        bound evidence refuses naming the missing evidence."""
        # frob:tests tests/test_evidence_integrity.py::TestT4167SplitMissingEvidenceDisjunction.test_done_report_present_no_evidence_names_missing_evidence  # noqa: E501
        ticket = _ticket(
            state=TicketState.IN_PROGRESS,
            evidence=(),
            body="## Description\nx\n\n## Done report\nAll good.\n",
        )
        _write(tmp_path, ticket)
        result = transition(tmp_path, "T-0001", TicketState.DONE)
        assert result.is_err
        assert result.danger_err == TicketError.MissingEvidence

    def test_heading_without_preceding_blank_line_is_not_missing_evidence(
        self, tmp_path: Path
    ) -> None:
        """MUST-STAY-QUIET: a ticket WITH bound evidence, whose `## Done
        report` heading is not preceded by a blank line (T-0853's
        impersonation guard correctly does not recognise it as a real
        heading here -- see that guard's own docstring for why loosening
        it is the wrong fix), refuses -- but as `MissingDoneReport`,
        naming the blank-line requirement, never as `MissingEvidence`."""
        # frob:tests tests/test_evidence_integrity.py::TestT4167SplitMissingEvidenceDisjunction.test_heading_without_preceding_blank_line_is_not_missing_evidence  # noqa: E501
        ticket = _ticket(
            state=TicketState.IN_PROGRESS,
            evidence=("tests/test_thing.py::test_it",),
            # No blank line before "## Done report" -- it reads as a
            # continuation of the prior paragraph, not a real heading.
            body="## Description\nx\n## Done report\nAll good.\n",
        )
        _write(tmp_path, ticket)
        result = transition(tmp_path, "T-0001", TicketState.DONE)
        assert result.is_err
        assert result.danger_err == TicketError.MissingDoneReport
        assert result.danger_err != TicketError.MissingEvidence

    def test_stale_prework_sweep_never_surfaces_as_missing_evidence(
        self, tmp_path: Path
    ) -> None:
        """THIRD FIXTURE: WHAT TO DO item 3 asked where the stale
        pre-work-sweep precondition the F-363 reporter also hit (cause
        (a)) reaches `MissingEvidence` at all. TRACED, NOT FOUND: `frob
        ticket close`'s own guard chain (`_done_transition_structural_
        guard`/`_done_transition_evidence_kind_and_scope_guard`) never
        reads pre-work-sweep state at all -- PRE001 (a stale sweep) is
        exclusively a `frob check` gate finding, a wholly separate
        command from `close`. This fixture proves it directly: a ticket
        with real evidence and a real Done report closes successfully
        even though nothing here ever refreshed its pre-work sweep --
        there is no code path in `close` for a stale sweep to be
        misreported as `MissingEvidence` (or anything else) through,
        because `close` never consults sweep state in the first place."""
        # frob:tests tests/test_evidence_integrity.py::TestT4167SplitMissingEvidenceDisjunction.test_stale_prework_sweep_never_surfaces_as_missing_evidence  # noqa: E501
        ticket = _ticket(
            state=TicketState.IN_PROGRESS,
            evidence=("tests/test_thing.py::test_it",),
            body="## Description\nx\n\n## Done report\nAll good.\n",
        )
        _write(tmp_path, ticket)
        # No `frob ticket sweep` was ever run for this ticket -- its
        # pre-work sweep record does not exist at all, the most extreme
        # form of "stale." `close`'s own guard chain must be entirely
        # unaffected by that.
        result = transition(tmp_path, "T-0001", TicketState.DONE)
        assert result.is_ok


# ---------------------------------------------------------------------------
# T-0848: a Done-report narrative with its own `## ` sub-headings must be
# fully replaced on a second `done-report` call, not duplicated alongside
# a surviving stale copy of the first-round narrative.
# ---------------------------------------------------------------------------
class TestDoneReportSectionEndStructuralSentinel:
    def test_narrative_h2_subheadings_do_not_end_the_section(self) -> None:
        # frob:tests tests/test_evidence_integrity.py::TestDoneReportSectionEndStructuralSentinel.test_narrative_h2_subheadings_do_not_end_the_section  # noqa: E501
        body = "## Description\nx\n"
        round_one = (
            "## Done report\n\n"
            "Some intro paragraph.\n\n"
            "## Per-pattern decision\n\n"
            "the two hallmarks are structurally disjoint per-method.\n\n"
            "## Evidence\n\n"
            "tests/test_x.py::test_y\n"
        )
        after_round_one = replace_done_report_section(body, round_one)
        assert "structurally disjoint per-method" in after_round_one

        round_two = (
            "## Done report\n\n"
            "Corrected intro paragraph.\n\n"
            "## Per-pattern decision\n\n"
            "## Reviewer round 1\n\n"
            "the disjointness claim above was WRONG; see corrected analysis.\n\n"
            "## Evidence\n\n"
            "tests/test_x.py::test_y\n"
        )
        after_round_two = replace_done_report_section(after_round_one, round_two)

        # The corrected narrative is present...
        assert "Corrected intro paragraph" in after_round_two
        assert "was WRONG" in after_round_two
        # ...and the stale, disproven round-one narrative must NOT survive
        # anywhere in the ticket body (this is the exact T-0848 failure: a
        # naive "stop at any '## '" boundary left it duplicated verbatim
        # just past the new report).
        assert "structurally disjoint per-method" not in after_round_two
        # Exactly one '## Done report' heading and one '## Evidence'
        # heading -- no duplicated section survives.
        assert after_round_two.count("## Done report") == 1
        assert after_round_two.count("## Evidence") == 1


# frob:ticket T-0853
class TestDoneReportHeadingImpersonation:
    """A narrative/description line that merely READS like the `## Done
    report` heading (a line-wrapped quoted phrase, T-0853) must never be
    mistaken for a genuine section start."""

    # frob:ticket T-0853
    def test_lookalike_heading_before_real_report_ignored(self) -> None:
        # frob:tests tests/test_evidence_integrity.py::TestDoneReportHeadingImpersonation.test_lookalike_heading_before_real_report_ignored  # noqa: E501
        # Description prose written BEFORE any real Done report exists,
        # containing a line-wrapped quoted phrase that happens to read as
        # exactly the heading text on its own physical line.
        body = (
            "## Description\n"
            "A narrative quoting the heading in isolation on its own line "
            "reads as\n"
            "## Done report\n"
            "and looks structural even though it is just prose.\n"
        )
        round_one = (
            "## Done report\n\n"
            "Some intro.\n\n"
            "### Changed\n(none)\n\n"
            "### Evidence\n\n"
            "tests/test_x.py::test_y\n"
        )
        after = replace_done_report_section(body, round_one)
        # The pre-fix bug: the lookalike line was mistaken for the section
        # start, silently dropping everything that followed it in the body.
        assert "and looks structural even though it is just prose." in after
        # And the real report was still appended, not lost.
        assert "Some intro." in after

    # frob:ticket T-0853
    def test_lookalike_heading_without_changed_marker_not_real(self) -> None:
        # frob:tests tests/test_evidence_integrity.py::TestDoneReportHeadingImpersonation.test_lookalike_heading_without_changed_marker_not_real  # noqa: E501
        # A second `done-report` call must still correctly replace the
        # real, prior section even when a lookalike heading line precedes
        # it in the ticket's own Description.
        body = (
            "## Description\n"
            "See also the heading text on its own line:\n"
            "## Done report\n"
            "-- that is just an example, not a real section.\n"
        )
        round_one = (
            "## Done report\n\n"
            "Round one narrative.\n\n"
            "### Changed\n(none)\n\n"
            "### Evidence\n\ntests/test_x.py::test_y\n"
        )
        after_one = replace_done_report_section(body, round_one)
        round_two = (
            "## Done report\n\n"
            "Round two narrative, corrected.\n\n"
            "### Changed\n(none)\n\n"
            "### Evidence\n\ntests/test_x.py::test_y\n"
        )
        after_two = replace_done_report_section(after_one, round_two)
        assert "Round two narrative, corrected." in after_two
        assert "Round one narrative." not in after_two
        assert "-- that is just an example, not a real section." in after_two


# ---------------------------------------------------------------------------
# D-04: unknown-language file changes must not silently select 0 tests
# ---------------------------------------------------------------------------
class TestD04UnknownLanguageFallback:
    def test_config_file_change_selects_something(self) -> None:
        # frob:tests \
        # tests/test_evidence_integrity.py::TestD04UnknownLanguageFallback.test_config_\
        # file_change_selects_something
        snapshot = GraphSnapshot(
            root=".",
            symbols={
                "src/pkg/thing.py::do_thing": _symbol(
                    "src/pkg/thing.py", "do_thing", (1, 3)
                )
            },
            edges=(),
        )
        diff = Diff(base="deadbeef", hunks=(Hunk(file="frob.toml", span=(1, 2)),))
        report = select_tests(snapshot, diff, SelectConfig(fallback="package"))
        assert report.selected != {}
        assert "python" in report.selected
        assert report.selected["python"] == ("*",)


# ---------------------------------------------------------------------------
# D-06: module-level (no-symbol-span) edits must not silently select 0
# tests even under fallback=warn
# ---------------------------------------------------------------------------
class TestD06ModuleLevelEdits:
    def test_module_level_edit_forces_selection_under_warn(self) -> None:
        # frob:tests \
        # tests/test_evidence_integrity.py::TestD06ModuleLevelEdits.test_module_level_e\
        # dit_forces_selection_under_warn
        snapshot = GraphSnapshot(
            root=".",
            symbols={
                "src/pkg/thing.py::do_thing": _symbol(
                    "src/pkg/thing.py", "do_thing", (10, 20)
                )
            },
            edges=(),
        )
        # hunk at line 1-2, well outside the only symbol's span (10-20):
        # a module-level edit (e.g. an import line).
        diff = Diff(
            base="deadbeef", hunks=(Hunk(file="src/pkg/thing.py", span=(1, 2)),)
        )
        report = select_tests(snapshot, diff, SelectConfig(fallback="warn"))
        assert report.selected != {}
        assert report.selected["python"] == ("src/pkg",)

    def test_symbol_touched_still_respects_warn(self) -> None:
        # frob:tests \
        # tests/test_evidence_integrity.py::TestD06ModuleLevelEdits.test_symbol_touched\
        # _still_respects_warn
        snapshot = GraphSnapshot(
            root=".",
            symbols={
                "src/pkg/thing.py::do_thing": _symbol(
                    "src/pkg/thing.py", "do_thing", (1, 3)
                )
            },
            edges=(),
        )
        diff = Diff(
            base="deadbeef", hunks=(Hunk(file="src/pkg/thing.py", span=(1, 3)),)
        )
        report = select_tests(snapshot, diff, SelectConfig(fallback="warn"))
        assert report.selected == {}


# ---------------------------------------------------------------------------
# D-07: ripple horizon widened beyond one hop
# ---------------------------------------------------------------------------
class TestD07RippleHorizon:
    def test_two_hop_dependent_is_selected(self) -> None:
        # frob:tests \
        # tests/test_evidence_integrity.py::TestD07RippleHorizon.test_two_hop_dependent\
        # _is_selected
        # C is touched; B uses-contract C; A uses-contract B; a test covers A.
        snapshot = GraphSnapshot(
            root=".",
            symbols={
                "src/pkg/c.py::c_fn": _symbol("src/pkg/c.py", "c_fn", (1, 3)),
                "src/pkg/b.py::b_fn": _symbol("src/pkg/b.py", "b_fn", (1, 3)),
                "src/pkg/a.py::a_fn": _symbol("src/pkg/a.py", "a_fn", (1, 3)),
            },
            edges=(
                Edge(
                    src="src/pkg/b.py::b_fn",
                    kind=EdgeKind.USES_CONTRACT,
                    target="src/pkg/c.py::c_fn",
                    origin="src/pkg/b.py:1",
                ),
                Edge(
                    src="src/pkg/a.py::a_fn",
                    kind=EdgeKind.USES_CONTRACT,
                    target="src/pkg/b.py::b_fn",
                    origin="src/pkg/a.py:1",
                ),
                Edge(
                    src="src/pkg/a.py::a_fn",
                    kind=EdgeKind.TESTS,
                    target="tests/test_a.py::test_a",
                    origin="src/pkg/a.py:1",
                ),
            ),
        )
        diff = Diff(base="deadbeef", hunks=(Hunk(file="src/pkg/c.py", span=(1, 3)),))
        report = select_tests(snapshot, diff, SelectConfig(fallback="warn"))
        assert "src/pkg/a.py::a_fn" in report.ripple
        assert report.selected.get("python") == ("tests/test_a.py::test_a",)


# ---------------------------------------------------------------------------
# D-08: collected=None evidence is explicitly marked unresolved (not silent)
# ---------------------------------------------------------------------------
class TestD08UnresolvedMarking:
    def test_new_ticket_resolves_when_collected_supplied(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_evidence_integrity.py::TestD08UnresolvedMarking.test_new_ticket_re\
        # solves_when_collected_supplied
        spec = TicketSpec(
            title="t",
            kind=TicketKind.FEATURE,
            origin=Origin.HUMAN,
            evidence=("tests/ghost.py::test_x",),
        )
        result = new_ticket(
            tmp_path, spec, collected=frozenset({"tests/real.py::test_y"})
        )
        assert result.is_err
        assert result.danger_err == TicketError.UnknownEvidence

    def test_new_ticket_accepts_resolving_evidence(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_evidence_integrity.py::TestD08UnresolvedMarking.test_new_ticket_ac\
        # cepts_resolving_evidence
        spec = TicketSpec(
            title="t",
            kind=TicketKind.FEATURE,
            origin=Origin.HUMAN,
            evidence=("tests/real.py::test_y",),
        )
        result = new_ticket(
            tmp_path, spec, collected=frozenset({"tests/real.py::test_y"})
        )
        assert result.is_ok

    def test_new_ticket_collected_none_still_stores_schema_valid_evidence(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/test_evidence_integrity.py::TestD08UnresolvedMarking.test_new_ticket_co\
        # llected_none_still_stores_schema_valid_evidence
        spec = TicketSpec(
            title="t",
            kind=TicketKind.FEATURE,
            origin=Origin.HUMAN,
            evidence=("tests/ghost.py::test_x",),
        )
        result = new_ticket(tmp_path, spec)
        assert result.is_ok
        assert "tests/ghost.py::test_x" in result.danger_ok.evidence


# ---------------------------------------------------------------------------
# D-09: land splice must union evidence, never drop one side's
# ---------------------------------------------------------------------------
class TestD09EvidenceUnionOnSplice:
    def test_newer_unions_disjoint_evidence_on_tie(self) -> None:
        # frob:tests \
        # tests/test_evidence_integrity.py::TestD09EvidenceUnionOnSplice.test_newer_uni\
        # ons_disjoint_evidence_on_tie
        common_body = "## Description\nx\n\n## Done report\nDone.\n"
        a = _ticket(
            state=TicketState.DONE,
            evidence=("tests/a.py::test_a",),
            body=common_body,
        )
        b = _ticket(
            state=TicketState.DONE,
            evidence=("tests/b.py::test_b",),
            body=common_body,
        )
        winner = _newer(a, b)
        assert "tests/a.py::test_a" in winner.evidence
        assert "tests/b.py::test_b" in winner.evidence

    def test_splice_ledger_preserves_both_sides_evidence(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_evidence_integrity.py::TestD09EvidenceUnionOnSplice.test_splice_le\
        # dger_preserves_both_sides_evidence
        common_body = "## Description\nx\n\n## Done report\nDone.\n"
        ours = _ticket(
            state=TicketState.DONE,
            evidence=("tests/a.py::test_a",),
            body=common_body,
        )
        theirs = ours.model_copy(update={"evidence": ("tests/b.py::test_b",)})

        ours_root = tmp_path / "ours"
        theirs_root = tmp_path / "theirs"
        atomic_write(ledger_path(ours_root), "# Tickets\n\n")
        atomic_write(ledger_path(theirs_root), "# Tickets\n\n")
        assert write_ticket(ours_root, ours).is_ok
        assert write_ticket(theirs_root, theirs).is_ok
        ours_text = ledger_path(ours_root).read_text()
        theirs_text = ledger_path(theirs_root).read_text()

        merged = splice_ledger(ours_text, theirs_text)
        assert merged.is_ok
        assert "tests/a.py::test_a" in merged.danger_ok
        assert "tests/b.py::test_b" in merged.danger_ok


# ---------------------------------------------------------------------------
# D-10: cmd: evidence reproducibility is re-checkable
# ---------------------------------------------------------------------------
class TestD10CmdEvidenceReverify:
    def test_reverify_true_when_command_still_reproduces(self) -> None:
        # frob:tests \
        # tests/test_evidence_integrity.py::TestD10CmdEvidenceReverify.test_reverify_tr\
        # ue_when_command_still_reproduces
        recorded = run_cmd_evidence("echo hello")
        assert recorded.is_ok
        result = reverify_cmd_evidence(recorded.danger_ok)
        assert result.is_ok
        assert result.danger_ok is True

    def test_reverify_false_when_output_changed(self) -> None:
        # frob:tests \
        # tests/test_evidence_integrity.py::TestD10CmdEvidenceReverify.test_reverify_fa\
        # lse_when_output_changed
        # Fabricate an entry claiming a digest the command will never produce.
        entry = "cmd:echo hello exit=0 sha256=000000000000"
        result = reverify_cmd_evidence(entry)
        assert result.is_ok
        assert result.danger_ok is False

    def test_reverify_false_when_command_now_fails(self) -> None:
        # frob:tests \
        # tests/test_evidence_integrity.py::TestD10CmdEvidenceReverify.test_reverify_fa\
        # lse_when_command_now_fails
        entry = "cmd:exit 1 exit=0 sha256=aaaaaaaaaaaa"
        result = reverify_cmd_evidence(entry)
        assert result.is_ok
        assert result.danger_ok is False

    def test_reverify_rejects_malformed_entry(self) -> None:
        # frob:tests \
        # tests/test_evidence_integrity.py::TestD10CmdEvidenceReverify.test_reverify_re\
        # jects_malformed_entry
        result = reverify_cmd_evidence("not-a-cmd-entry")
        assert result.is_err
        assert result.danger_err == TicketError.MalformedEvidence


# ---------------------------------------------------------------------------
# D-11: collected-match rule is a single shared implementation
# ---------------------------------------------------------------------------
class TestD11DedupedMatchRule:
    def test_tickets_and_gates_share_matches_collected(self) -> None:
        # frob:tests \
        # tests/test_evidence_integrity.py::TestD11DedupedMatchRule.test_tickets_and_ga\
        # tes_share_matches_collected
        import frob.gates as gates_mod
        import frob.tickets._models as tickets_models

        assert gates_mod.matches_collected is tickets_models.matches_collected


# ---------------------------------------------------------------------------
# D-12: deletion filter must not trust an over-broad scope
# ---------------------------------------------------------------------------
class TestD12DeletionFilterBroadScope:
    def test_deletion_owned_rejects_bare_top_level_scope(self) -> None:
        # frob:tests \
        # tests/test_evidence_integrity.py::TestD12DeletionFilterBroadScope.test_deleti\
        # on_owned_rejects_bare_top_level_scope
        from frob.tickets._land_merge import _deletion_owned

        assert _deletion_owned("src/frob/other/mod.py", ("src/",)) is False

    def test_deletion_owned_accepts_narrow_scope(self) -> None:
        # frob:tests \
        # tests/test_evidence_integrity.py::TestD12DeletionFilterBroadScope.test_deleti\
        # on_owned_accepts_narrow_scope
        from frob.tickets._land_merge import _deletion_owned

        assert (
            _deletion_owned("src/frob/tickets/foo.py", ("src/frob/tickets/",)) is True
        )

    def test_deletion_owned_rejects_whole_tree_scope(self) -> None:
        # frob:tests \
        # tests/test_evidence_integrity.py::TestD12DeletionFilterBroadScope.test_deleti\
        # on_owned_rejects_whole_tree_scope
        from frob.tickets._land_merge import _deletion_owned

        assert _deletion_owned("anything/at/all.py", (".",)) is False

    # frob:ticket T-1680
    def test_exact_root_level_file_authorizes_its_own_deletion(self) -> None:
        """T-1680 REGRESSION LOCK: an exact literal path is the NARROWEST
        authorization there is and must be trusted, at the repo root as
        much as anywhere else.

        The old rule asked whether the pattern contained a '/', so every
        root-level file read as an over-broad glob. That made deleting any
        root-level file unlandable, and the refusal printed the scope entry
        that already authorized the file while insisting it was missing."""
        from frob.tickets._land_merge import _deletion_owned

        assert _deletion_owned("FROBLEMS.md", ("FROBLEMS.md",)) is True
        assert _deletion_owned("tickets.md", ("tickets.md", "docs/**")) is True
        # An exact path authorizes ONLY itself -- narrow, not permissive.
        assert _deletion_owned("README.md", ("FROBLEMS.md",)) is False

    # frob:ticket T-1680
    def test_wildcard_breadth_rules_are_unchanged(self) -> None:
        """T-1680 must not loosen the D-12 guard it fixes: a bare
        top-level directory glob still authorizes nothing, while a
        sufficiently deep glob is still trusted."""
        from frob.tickets._land_git_ops import _deletion_glob_too_broad

        assert _deletion_glob_too_broad("src/**") is True
        assert _deletion_glob_too_broad("docs/**") is True
        assert _deletion_glob_too_broad("*") is True
        assert _deletion_glob_too_broad(".") is True
        assert _deletion_glob_too_broad("src/frob/tickets/**") is False
        # Exact paths, wildcard-free, at any depth.
        assert _deletion_glob_too_broad("FROBLEMS.md") is False
        assert _deletion_glob_too_broad("src/frob/tickets/_land.py") is False


# ---------------------------------------------------------------------------
# D-05: land() re-verifies evidence against the post-merge worktree tree
# ---------------------------------------------------------------------------
class TestD05LandReverification:
    def test_land_rejects_evidence_that_no_longer_resolves_post_merge(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/test_evidence_integrity.py::TestD05LandReverification.test_land_rejects\
        # _evidence_that_no_longer_resolves_post_merge
        import subprocess

        def git(root: Path, *args: str) -> None:
            subprocess.run(
                ["git", "-C", str(root), *args],
                check=True,
                capture_output=True,
                text=True,
            )

        root = tmp_path / "main"
        root.mkdir()
        git(root, "init", "-q")
        git(root, "config", "user.email", "t@example.com")
        git(root, "config", "user.name", "T")
        git(root, "checkout", "-q", "-b", "main")
        (root / "README.md").write_text("root\n")
        git(root, "add", "-A")
        git(root, "commit", "-q", "-m", "init")

        wt = tmp_path / "wt"
        git(root, "worktree", "add", "-b", "feature", str(wt))

        ticket = _ticket(
            ticket_id="T-0002",
            state=TicketState.IN_PROGRESS,
            evidence=("tests/x.py::test_stale",),
            scope=("src/",),
            body="## Description\nx\n\n## Done report\nDone.\n",
        )
        _write(wt, ticket)
        git(wt, "add", "-A")
        git(wt, "commit", "-q", "-m", "wip ticket")

        result = land(
            root,
            "T-0002",
            wt,
            dry_run=True,
            collected=lambda: frozenset(),  # evidence id no longer resolves
        )
        assert result.is_err
