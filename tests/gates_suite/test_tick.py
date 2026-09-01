from datetime import date
from pathlib import Path

import pytest

from frob.gates import (
    Severity,
    tickets_gate,
)
from frob.tickets import Origin, Priority, Ticket, TicketKind, TicketQueue, TicketState
from tests.conftest import (
    _by_rule,
    _ticket,
)


# frob:ticket T-0726
class TestTick006PhantomFiling:
    """TICK006 (T-0726): a Done report's affirmative "filed" claim whose
    id resolves to no ledger block, distinguished from prose that merely
    mentions another ticket's id and from explicit filing negations."""

    def _queue(self, *tickets: Ticket) -> TicketQueue:
        """A `TicketQueue` of `tickets`, keyed by id."""
        return TicketQueue(tickets={t.id: t for t in tickets})

    # frob:tests \
    # tests/gates_suite/test_tick.py::TestTick006PhantomFiling.test_phantom_filed_colon\
    # _fires
    def test_phantom_filed_colon_fires(self, tmp_path: Path) -> None:
        """`Filed: T-draft-deadbeef` (a real T-0726/T-0577-class draft-loss
        shape) resolving to no block, active or archived, is TICK006."""
        ticket = _ticket(
            ticket_id="T-0001",
            body=(
                "## Description\nsome bug\n\n"
                "## Done report\n\n"
                "Filed: `T-draft-deadbeef` (a follow-up bug, scope foo.py "
                "-- renumbers to a real T-#### id when this worktree "
                "merges to main).\n"
            ),
        )
        violations = tickets_gate(tmp_path, self._queue(ticket))
        tick006 = [v for v in violations if v.rule == "TICK006"]
        assert len(tick006) == 1
        assert "T-draft-deadbeef" in tick006[0].message
        assert tick006[0].severity == Severity.ERROR

    # frob:tests \
    # tests/gates_suite/test_tick.py::TestTick006PhantomFiling.test_phantom_filed_as_fi\
    # res
    def test_phantom_filed_as_fires(self, tmp_path: Path) -> None:
        """The T-0707 incident class: `filed as T-0999` where T-0999 was
        never actually filed anywhere -- an invented filing trail."""
        ticket = _ticket(
            ticket_id="T-0002",
            body=(
                "## Done report\n\n"
                "The out-of-scope discovery above was filed as T-0999 "
                "(never actually created).\n"
            ),
        )
        violations = tickets_gate(tmp_path, self._queue(ticket))
        tick006 = [v for v in violations if v.rule == "TICK006"]
        assert len(tick006) == 1
        assert "T-0999" in tick006[0].message

    # frob:tests tests/gates_suite/test_tick.py::TestTick006PhantomFiling.test_filed_colon_real_active_id_is_silent  # noqa: E501
    def test_filed_colon_real_active_id_is_silent(self, tmp_path: Path) -> None:
        """`Filed: T-0003` where T-0003 is a real block in the ACTIVE
        queue does not fire -- this is exactly what a correct filing
        claim looks like."""
        followup = _ticket(ticket_id="T-0003", body="## Description\nx\n")
        # Real Done-report grammar, verbatim shape from tickets-archive.md
        # (T-0077's own Done report): "Filed: T-0129 (wire `.strata`
        # into frob.graph/outline/... -- out of T-0077's scope)."
        reporter = _ticket(
            ticket_id="T-0004",
            body=(
                "## Done report\n\n"
                "Filed: T-0003 (wire `.strata` into frob.graph/outline/"
                "xref/testing/policy/cycle_runner/arch's raw_tree call so "
                "map/outline/xref/COV obligations reach `.strata` symbols "
                "end to end -- out of T-0004's scope).\n"
            ),
        )
        violations = tickets_gate(tmp_path, self._queue(followup, reporter))
        assert not any(v.rule == "TICK006" for v in violations)

    # frob:tests \
    # tests/gates_suite/test_tick.py::TestTick006PhantomFiling.test_filed_colon_none_is\
    # _silent
    def test_filed_colon_none_is_silent(self, tmp_path: Path) -> None:
        """`Filed: none` -- the common "nothing to file" Done-report
        shape -- names no id at all and must never fire."""
        ticket = _ticket(
            ticket_id="T-0005",
            body=(
                "## Done report\n\n"
                "Filed: none (no out-of-scope work found; the change was "
                "entirely inside T-0005's declared scope).\n"
            ),
        )
        violations = tickets_gate(tmp_path, self._queue(ticket))
        assert not any(v.rule == "TICK006" for v in violations)

    # frob:tests tests/gates_suite/test_tick.py::TestTick006PhantomFiling.test_filed_as_real_archived_id_is_silent  # noqa: E501
    def test_filed_as_real_archived_id_is_silent(self, tmp_path: Path) -> None:
        """`filed as **T-0137**` resolves against `tickets-archive.md`,
        not only the active queue -- an id archived long ago is still a
        real filing, never a phantom."""
        from frob.tickets._store import write_archive

        archived = _ticket(ticket_id="T-0137", body="## Description\narchived\n")
        write_archive(tmp_path, {"T-0137": archived}).danger_ok
        ticket = _ticket(
            ticket_id="T-0006",
            body=(
                "## Done report\n\n"
                "`strata-core/**` is outside this ticket's scope, so this "
                "was filed as **T-0137** rather than patched around.\n"
            ),
        )
        violations = tickets_gate(tmp_path, self._queue(ticket))
        assert not any(v.rule == "TICK006" for v in violations)

    # frob:tests tests/gates_suite/test_tick.py::TestTick006PhantomFiling.test_code_spanned_filed_claim_does_not_fire  # noqa: E501
    def test_code_spanned_filed_claim_does_not_fire(self, tmp_path: Path) -> None:
        """T-1700's own incident, reproduced exactly: a Done report
        EXPLAINS that a code-spanned mention is DOC011's illustrative-
        example exemption, not a claim -- `` `Filed: T-0104` `` and
        `` `waive ... ticket "T-9999";` `` both sit inside inline code
        spans, and neither T-0104 nor T-9999 resolves to any ledger
        block. Before T-1700, the bare `\\bfiled\\b` scan had no code-span
        awareness and fired TICK006 on the explanation of the exemption
        the neighbouring gate (DOC011) correctly applies -- this is the
        exact shape that turned main red on T-1542's land."""
        ticket = _ticket(
            ticket_id="T-0011",
            body=(
                "## Done report\n\n"
                "The remaining citations are inline-code-span examples "
                "illustrating the id syntax itself (`Filed: T-0104`, "
                '`waive ... ticket "T-9999";`) -- DOC011\'s own scan '
                "already blanks fenced/inline code spans before "
                "matching, so these were never real findings.\n"
            ),
        )
        violations = tickets_gate(tmp_path, self._queue(ticket))
        assert not any(v.rule == "TICK006" for v in violations)

    # frob:tests \
    # tests/gates_suite/test_tick.py::TestTick006PhantomFiling.test_prose_quoting_another_tickets_criterion_does_not_fire  # noqa: E501
    def test_prose_quoting_another_tickets_criterion_does_not_fire(
        self, tmp_path: Path
    ) -> None:
        """T-2243, the measured T-2226/T-2238 incident reproduced exactly
        (archaeology: `git show 3a688f28b:tickets/T-2226/done-report.md`,
        confirmed against the real `T-2238` phantom ticket's own quoted
        excerpt). A genuine `Filed T-draft-...` claim sits in plain prose
        earlier in the SAME sentence/list item as an ASCII-double-quoted
        clause that echoes a DIFFERENT ticket's own acceptance-criterion
        text, which happens to name a THIRD, unrelated id
        (`T-draft-0bd874ac`) that resolves to nothing. Before this fix,
        the 300-char claim window swept that unrelated id in as a second
        phantom "filed" claim -- MUST FAIL FIRST, this is the repro."""
        ticket = _ticket(
            ticket_id="T-0013",
            body=(
                "## Done report\n\n"
                "1. Running the backfill against this repo's REAL "
                "T-2195/T-2197 ledger data in THIS environment refuses "
                "rather than relocating, correctly, by design. This is "
                'ALSO why 2 of the ticket\'s "4 COV004" findings are '
                "purely environmental. Filed T-draft-76b5731f (high) "
                "for the .gitattributes glob fix; acceptance [3] there "
                "is \"T-2226's two still-unresolved T-draft-0bd874ac "
                "records are re-attempted and confirmed relocated once "
                'this lands".\n'
            ),
        )
        violations = tickets_gate(tmp_path, self._queue(ticket))
        tick006 = [v for v in violations if v.rule == "TICK006"]
        # The genuine claim (T-draft-76b5731f) still fires ...
        assert any("T-draft-76b5731f" in v.message for v in tick006)
        # ... but the quoted-prose id never becomes a second phantom.
        assert not any("T-draft-0bd874ac" in v.message for v in tick006)

    # frob:tests \
    # tests/gates_suite/test_tick.py::TestTick006PhantomFiling.test_genuine_dangling_citation_outside_any_quote_still_fires  # noqa: E501
    def test_genuine_dangling_citation_outside_any_quote_still_fires(
        self, tmp_path: Path
    ) -> None:
        """T-2243 MUST-STILL-PASS CONTROL: a genuine dangling citation
        that is NOT inside any quoted/code/blockquote range must still
        trigger TICK006 -- the T-2243 fix narrows WHICH ids count as
        claims, it must never stop detecting a real one. Two ids appear
        near "filed" here (mirroring the T-2226 shape) and NEITHER is
        quoted -- both must fire, proving the fix did not silently widen
        into a blanket "skip everything after the first id" rule."""
        ticket = _ticket(
            ticket_id="T-0014",
            body=(
                "## Done report\n\n"
                "Filed T-draft-aaaaaaaa (high) for the first issue, and "
                "separately filed T-draft-bbbbbbbb (medium) for the "
                "second, unrelated issue found while investigating.\n"
            ),
        )
        violations = tickets_gate(tmp_path, self._queue(ticket))
        tick006 = [v for v in violations if v.rule == "TICK006"]
        assert any("T-draft-aaaaaaaa" in v.message for v in tick006)
        assert any("T-draft-bbbbbbbb" in v.message for v in tick006)

    # frob:tests tests/gates_suite/test_tick.py::TestTick006PhantomFiling.test_backtick_styled_id_in_a_real_claim_still_fires  # noqa: E501
    def test_backtick_styled_id_in_a_real_claim_still_fires(
        self, tmp_path: Path
    ) -> None:
        """The T-1700 fix must stay NARROW: when "filed" itself is plain
        prose and only the id happens to be backtick-styled (a common,
        legitimate Done-report convention -- see
        `test_phantom_filed_colon_fires` above), TICK006 must still fire.
        Only a "filed" occurrence that is ITSELF inside a code span is
        illustrative; an id styled in backticks next to plain-prose
        "Filed:" is still a real, checkable claim."""
        ticket = _ticket(
            ticket_id="T-0012",
            body=("## Done report\n\nFiled: `T-9998` (never actually created).\n"),
        )
        violations = tickets_gate(tmp_path, self._queue(ticket))
        tick006 = [v for v in violations if v.rule == "TICK006"]
        assert len(tick006) == 1
        assert "T-9998" in tick006[0].message

    # frob:tests \
    # tests/gates_suite/test_tick.py::TestTick006PhantomFiling.test_negation_not_filed_\
    # is_silent
    def test_negation_not_filed_is_silent(self, tmp_path: Path) -> None:
        """ "not filed as a new ticket" (verbatim phrase used repeatedly in
        this repo's ledger) is an explicit negation and must never fire,
        even when a phantom-shaped id sits nearby in the same sentence."""
        ticket = _ticket(
            ticket_id="T-0007",
            body=(
                "## Done report\n\n"
                "That is out of T-0007's scope; not filed as a new ticket "
                "this pass because the discovery T-draft-deadbeef "
                "duplicates existing tracked work.\n"
            ),
        )
        violations = tickets_gate(tmp_path, self._queue(ticket))
        assert not any(v.rule == "TICK006" for v in violations)

    # frob:tests tests/gates_suite/test_tick.py::TestTick006PhantomFiling.test_negation_no_ticket_filed_is_silent  # noqa: E501
    def test_negation_no_ticket_filed_is_silent(self, tmp_path: Path) -> None:
        """ "no new ticket filed" is an explicit negation and must never
        fire."""
        ticket = _ticket(
            ticket_id="T-0008",
            body=(
                "## Done report\n\n"
                "Tracked under T-0008's own pattern (no new ticket filed; "
                "T-draft-deadbeef is only a scratch note, not a real id).\n"
            ),
        )
        violations = tickets_gate(tmp_path, self._queue(ticket))
        assert not any(v.rule == "TICK006" for v in violations)

    # frob:tests tests/gates_suite/test_tick.py::TestTick006PhantomFiling.test_description_prose_mentioning_other_ticket_is_silent  # noqa: E501
    def test_description_prose_mentioning_other_ticket_is_silent(
        self, tmp_path: Path
    ) -> None:
        """Ordinary narrative in a ticket's Description -- BEFORE any Done
        report heading -- routinely names another (possibly phantom-
        shaped) ticket id in prose; this is extremely common and must
        never fire, since it is not a filing claim about this ticket's
        own work at all."""
        ticket = _ticket(
            ticket_id="T-0009",
            body=(
                "## Description\n\n"
                "NOTE: T-0570's Done report references this as "
                "T-draft-1327a057 (and mislabels it as T-0571); the draft "
                "did not survive land, so this ticket is its real "
                "replacement.\n\n"
                "## Done report\n\nFiled: none.\n"
            ),
        )
        violations = tickets_gate(tmp_path, self._queue(ticket))
        assert not any(v.rule == "TICK006" for v in violations)

    # frob:tests tests/gates_suite/test_tick.py::TestTick006PhantomFiling.test_no_done_report_heading_is_silent  # noqa: E501
    def test_no_done_report_heading_is_silent(self, tmp_path: Path) -> None:
        """A ticket with no Done report at all (still in progress) has
        nothing for TICK006 to scan, regardless of what its Description
        says."""
        ticket = _ticket(
            ticket_id="T-0010",
            state=TicketState.IN_PROGRESS,
            body="## Description\nFiled: T-draft-deadbeef (not real).\n",
        )
        violations = tickets_gate(tmp_path, self._queue(ticket))
        assert not any(v.rule == "TICK006" for v in violations)

    # frob:tests tests/gates_suite/test_tick.py::TestTick006PhantomFiling.test_filed_bare_draft_without_colon_fires  # noqa: E501
    def test_filed_bare_draft_without_colon_fires(self, tmp_path: Path) -> None:
        """The T-0577 draft-loss shape: `Filed T-draft-<hex> (mints a real
        T-#### id at land)` with no colon after "Filed" -- a real filing
        grammar used repeatedly in this ledger -- still fires when the
        draft never survived land, since that is TICK006's whole point
        (a currently-unresolvable phantom, to be waived per-instance if
        it is a disclosed historical draft-loss case)."""
        ticket = _ticket(
            ticket_id="T-0011",
            body=(
                "## Done report\n\n"
                "Filed T-draft-deadbeef (mints a real T-#### id at land) "
                "for a follow-up entity kind.\n"
            ),
        )
        violations = tickets_gate(tmp_path, self._queue(ticket))
        tick006 = [v for v in violations if v.rule == "TICK006"]
        assert len(tick006) == 1
        assert "T-draft-deadbeef" in tick006[0].message

    # frob:ticket T-2722
    # frob:tests tests/gates_suite/test_tick.py::TestTick006PhantomFiling.test_renumbered_draft_corrected_to_real_id_is_silent  # noqa: E501
    def test_renumbered_draft_corrected_to_real_id_is_silent(
        self, tmp_path: Path
    ) -> None:
        """T-2722: a Done report that ORIGINALLY named a pre-renumber
        draft id (`T-draft-...`) but was corrected, post-land, to name
        the real id it was renumbered to at land -- the fix this ticket
        applied to T-1614's own Done report. Unlike the T-0577 draft-loss
        shape (`test_filed_bare_draft_without_colon_fires` above), the
        draft here DID survive land as a real ticket; only the Done
        report's own prose was stale. Naming the real id, not the draft
        id, is silent -- exactly TICK006's own error-message remedy
        ("correct the Done report to name the real id")."""
        followup = _ticket(ticket_id="T-2719", body="## Description\nx\n")
        reporter = _ticket(
            ticket_id="T-1614",
            body=(
                "## Done report\n\n"
                "Filed: T-2719 (renumbered at land from the draft id "
                "this pass originally filed).\n"
            ),
        )
        violations = tickets_gate(tmp_path, self._queue(followup, reporter))
        assert not any(v.rule == "TICK006" for v in violations)

    # frob:ticket T-2722
    # frob:tests tests/gates_suite/test_tick.py::TestTick006PhantomFiling.test_stale_draft_id_after_renumber_still_fires  # noqa: E501
    def test_stale_draft_id_after_renumber_still_fires(self, tmp_path: Path) -> None:
        """T-2722's own regression, reproduced directly: a Done report
        that STILL names the pre-renumber draft id after the draft was
        renumbered to a real ticket (the real id exists in the queue,
        but the Done report text was never updated) still fires -- this
        is the exact shape T-1614's Done report had before this
        ticket's fix, and confirms the bug this ticket closes was real
        (not stale-baseline noise): the fix is in the Done report's own
        prose, not in TICK006 itself."""
        followup = _ticket(ticket_id="T-2719", body="## Description\nx\n")
        reporter = _ticket(
            ticket_id="T-1614",
            body=(
                "## Done report\n\n"
                "Filed: T-draft-07669f4e (RENDER001 exemption-list "
                "extension). Real-ticket id to be confirmed post-land.\n"
            ),
        )
        violations = tickets_gate(tmp_path, self._queue(followup, reporter))
        tick006 = [v for v in violations if v.rule == "TICK006"]
        assert len(tick006) == 1
        assert "T-draft-07669f4e" in tick006[0].message
# frob:ticket T-1129
class TestTick011DisclosedCutWithoutTicket:
    """TICK011 (T-1129, active-window-narrowed T-1402): a Done report's
    prose disclosing deferred/cut work with no ticket id cited nearby and
    no explicit no-ticket-needed reason -- the T-1085/T-0321/T-1140/
    T-1150 incident class. Full strength inside `_TICK011_ACTIVE_WINDOW`
    of the ledger's current highest ticket id; silent by default outside
    it (a historical report nobody can honestly reconstruct context for),
    unless `FROB_TICK011_INCLUDE_HISTORY` is set."""

    def _queue(self, *tickets: Ticket) -> TicketQueue:
        """A `TicketQueue` of `tickets`, keyed by id."""
        return TicketQueue(tickets={t.id: t for t in tickets})

    # frob:tests tests/gates_suite/test_tick.py::TestTick011DisclosedCutWithoutTicket.test_disclosed_follow_up_with_no_citation_fires  # noqa: E501
    def test_disclosed_follow_up_with_no_citation_fires(self, tmp_path: Path) -> None:
        """The real T-1085 shape: "deliberately left for a follow-up
        pass" with no `T-####` anywhere nearby -- must fire."""
        ticket = _ticket(
            ticket_id="T-0001",
            body=(
                "## Done report\n\n"
                "`check_runner.py`'s two `ToolResult`-builder groups were "
                "NOT touched -- deliberately left for a follow-up pass "
                "rather than expanding this ticket's scope further.\n"
            ),
        )
        violations = tickets_gate(tmp_path, self._queue(ticket))
        tick011 = [v for v in violations if v.rule == "TICK011"]
        assert len(tick011) == 1
        assert tick011[0].severity == Severity.ERROR
        assert "T-0001" in tick011[0].message

    def test_not_yet_ticketed_with_no_citation_fires(self, tmp_path: Path) -> None:
        """The real T-0321 close shape: "not yet ticketed as its own
        item" with no id nearby -- must fire."""
        ticket = _ticket(
            ticket_id="T-0002",
            body=(
                "## Done report\n\n"
                "The serve RPC gap is not yet ticketed as its own item.\n"
            ),
        )
        violations = tickets_gate(tmp_path, self._queue(ticket))
        tick011 = [v for v in violations if v.rule == "TICK011"]
        assert len(tick011) == 1

    def test_disclosure_with_a_real_citing_id_is_silent(self, tmp_path: Path) -> None:
        """The correct shape -- a disclosure immediately followed by a
        real ticket id that resolves in the active queue -- must not
        fire."""
        followup = _ticket(ticket_id="T-0004", body="## Description\nx\n")
        reporter = _ticket(
            ticket_id="T-0003",
            body=(
                "## Done report\n\n"
                "This was deliberately left for a follow-up pass, filed "
                "as T-0004.\n"
            ),
        )
        violations = tickets_gate(tmp_path, self._queue(followup, reporter))
        assert not any(v.rule == "TICK011" for v in violations)

    def test_explicit_no_ticket_needed_reason_is_silent(self, tmp_path: Path) -> None:
        """The T-1129 acceptance criterion's own escape hatch: an
        explicit no-ticket-needed disposition near the disclosure must
        suppress the finding."""
        ticket = _ticket(
            ticket_id="T-0005",
            body=(
                "## Done report\n\n"
                "The docs-only residue here is cosmetic; no ticket "
                "needed.\n"
            ),
        )
        violations = tickets_gate(tmp_path, self._queue(ticket))
        assert not any(v.rule == "TICK011" for v in violations)

    def test_no_disclosure_phrase_is_silent(self, tmp_path: Path) -> None:
        """An ordinary Done report with none of the disclosure phrases at
        all must never fire (the common case)."""
        ticket = _ticket(
            ticket_id="T-0006",
            body="## Done report\n\nAll planned work landed cleanly.\n",
        )
        violations = tickets_gate(tmp_path, self._queue(ticket))
        assert not any(v.rule == "TICK011" for v in violations)

    def test_one_finding_per_ticket_not_per_phrase(self, tmp_path: Path) -> None:
        """Two uncited disclosure phrases in the same Done report still
        produce exactly ONE TICK011 finding -- conservative-on-noise for
        a WARN-tier first turn-on (this rule's own docstring)."""
        ticket = _ticket(
            ticket_id="T-0007",
            body=(
                "## Done report\n\nLeft for a follow-up pass. Also some residue here.\n"
            ),
        )
        violations = tickets_gate(tmp_path, self._queue(ticket))
        assert len([v for v in violations if v.rule == "TICK011"]) == 1

    # frob:ticket T-2372
    def test_ordinary_prose_residue_preceded_by_non_technical_word_is_not_a_disclosure(
        self, tmp_path: Path
    ) -> None:
        """T-2372's designated repro: the real T-2552 shape ("...26 of
        26, no residue -- but they were NOT one idiom") is ordinary
        prose with NO technical token before "residue" at all (just the
        word "no") -- the OLD bare-word pattern plus its technical-token
        lookback could not exclude this, and it fired as a false
        positive; the narrowed colon-labeled-heading pattern never
        matches a mid-sentence, non-labeled occurrence like this one at
        all, fixing it structurally rather than by extending the
        lookback's own token-shape list."""
        ticket = _ticket(
            ticket_id="T-0013",
            body=(
                "## Done report\n\n"
                "26 of 26 call sites were reachable, no residue -- but "
                "they were NOT one idiom.\n"
            ),
        )
        violations = tickets_gate(tmp_path, self._queue(ticket))
        assert not any(v.rule == "TICK011" for v in violations)

    def test_numeric_count_residual_is_not_a_disclosure(self, tmp_path: Path) -> None:
        """T-1111's real Done report shape, found while calibrating this
        rule against the live ledger: "7 residual, not the filed 2" is a
        FINDING-COUNT ("N residual"), not disclosed deferred work -- must
        not fire. T-2372: the bare word "residual" mid-sentence never
        matches `_TICK011_DISCLOSURE_PATTERNS`'s colon-labeled-heading
        form at all any more, so this is now a no-op at the pattern
        level rather than the technical-token lookback T-1111 originally
        added (deleted, T-2372, once measurement showed the lookback
        itself was not enough -- see the module-level T-2372 note above
        `_tick011_disclosure_hits`)."""
        ticket = _ticket(
            ticket_id="T-0008",
            body=(
                "## Done report\n\n"
                "REG -> 0 (7 residual, not the filed 2 -- re-measured "
                "fresh): all filled.\n"
            ),
        )
        violations = tickets_gate(tmp_path, self._queue(ticket))
        assert not any(v.rule == "TICK011" for v in violations)

    def test_rule_id_shaped_residue_is_not_a_disclosure(self, tmp_path: Path) -> None:
        """Another real T-1111 shape: "gate:WAIVE residue" -- a
        rule-id/namespace-shaped word directly before "residue", not a
        bare number -- must also not fire. T-2372: same as the sibling
        test above, this is a mid-sentence bare occurrence with no
        trailing colon, so the narrowed pattern never matches it in the
        first place."""
        ticket = _ticket(
            ticket_id="T-0009",
            body=(
                "## Done report\n\n"
                "each one individually shows a nonzero gate:WAIVE residue "
                "that is inflated by the other groups.\n"
            ),
        )
        violations = tickets_gate(tmp_path, self._queue(ticket))
        assert not any(v.rule == "TICK011" for v in violations)

    # frob:ticket T-2372
    def test_residue_heading_label_with_no_citation_still_fires(
        self, tmp_path: Path
    ) -> None:
        """T-2372's must-still-fire control: "Residue:" used as a
        genuine paragraph-leading disclosure label (this ledger's own
        real convention, see the T-2556 archived incident this ticket
        found and repaired) with no citation nearby -- the narrowed
        pattern must still catch the real disclosure shape, not just
        stop matching everything."""
        ticket = _ticket(
            ticket_id="T-0010",
            body=(
                "## Done report\n\n"
                "Residue: the hook's own header comment still names a "
                "subcommand that does not exist.\n"
            ),
        )
        violations = tickets_gate(tmp_path, self._queue(ticket))
        tick011 = [v for v in violations if v.rule == "TICK011"]
        assert len(tick011) == 1
        assert tick011[0].severity == Severity.ERROR

    # frob:ticket T-2372
    def test_residue_heading_label_with_citation_immediately_after_is_silent(
        self, tmp_path: Path
    ) -> None:
        """The same label shape as above, but with a real citation
        immediately after the colon (this ticket's own repair shape for
        T-2556) -- must not fire."""
        followup = _ticket(ticket_id="T-0012", body="## Description\nx\n")
        reporter = _ticket(
            ticket_id="T-0011",
            body=(
                "## Done report\n\n"
                "Residue: filed as T-0012 (done). The hook's own header "
                "comment still names a subcommand that does not exist.\n"
            ),
        )
        violations = tickets_gate(tmp_path, self._queue(followup, reporter))
        assert not any(v.rule == "TICK011" for v in violations)

    # frob:tests \
    # tests/gates_suite/test_tick.py::TestTick011DisclosedCutWithoutTicket.test_histori\
    # cal_ticket_outside_active_window_is_silent_by_default
    def test_historical_ticket_outside_active_window_is_silent_by_default(
        self, tmp_path: Path
    ) -> None:
        """T-1402: an old ticket's Done report (numerically far below the
        ledger's current highest id) discloses the exact same uncited
        follow-up shape `test_disclosed_follow_up_with_no_citation_fires`
        proves still fires INSIDE the window -- but here the ledger also
        has a much later ticket, pushing the old one outside
        `_TICK011_ACTIVE_WINDOW`, so it must NOT fire by default. This is
        the precision fix: 50 pre-fix findings were all exactly this
        shape (14 below T-0500), unfixable without reconstructing
        long-gone context."""
        old = _ticket(
            ticket_id="T-0001",
            body=(
                "## Done report\n\n"
                "`check_runner.py`'s two `ToolResult`-builder groups were "
                "NOT touched -- deliberately left for a follow-up pass "
                "rather than expanding this ticket's scope further.\n"
            ),
        )
        recent = _ticket(ticket_id="T-1400", body="## Description\nx\n")
        violations = tickets_gate(tmp_path, self._queue(old, recent))
        assert not any(v.rule == "TICK011" for v in violations)

    # frob:tests \
    # tests/gates_suite/test_tick.py::TestTick011DisclosedCutWithoutTicket.test_recent_\
    # ticket_outside_old_window_still_fires_exactly_as_today
    def test_recent_ticket_outside_old_window_still_fires_exactly_as_today(
        self, tmp_path: Path
    ) -> None:
        """T-1402 regression: a Done report written NOW (a high ticket
        number, inside the active window even with a much-later sibling
        ticket also on the ledger) with the exact T-1085 uncited-
        disclosure shape must still fire EXHAUST-style -- er, TICK011 --
        exactly as before this ticket's narrowing. This is the case the
        narrowing must NOT silence."""
        recent = _ticket(
            ticket_id="T-1400",
            body=(
                "## Done report\n\n"
                "`check_runner.py`'s two `ToolResult`-builder groups were "
                "NOT touched -- deliberately left for a follow-up pass "
                "rather than expanding this ticket's scope further.\n"
            ),
        )
        newer = _ticket(ticket_id="T-1401", body="## Description\nx\n")
        violations = tickets_gate(tmp_path, self._queue(recent, newer))
        tick011 = [v for v in violations if v.rule == "TICK011"]
        assert len(tick011) == 1
        assert "T-1400" in tick011[0].message

    # frob:tests \
    # tests/gates_suite/test_tick.py::TestTick011DisclosedCutWithoutTicket.test_include\
    # _history_env_opt_in_restores_the_historical_finding
    def test_include_history_env_opt_in_restores_the_historical_finding(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-1402: the explicit opt-in escape hatch
        (`FROB_TICK011_INCLUDE_HISTORY`) restores the historical finding
        `test_historical_ticket_outside_active_window_is_silent_by_default`
        proves is silent by default -- the capability is not deleted, only
        gated behind a deliberate choice."""
        monkeypatch.setenv("FROB_TICK011_INCLUDE_HISTORY", "1")
        old = _ticket(
            ticket_id="T-0001",
            body=(
                "## Done report\n\n"
                "`check_runner.py`'s two `ToolResult`-builder groups were "
                "NOT touched -- deliberately left for a follow-up pass "
                "rather than expanding this ticket's scope further.\n"
            ),
        )
        recent = _ticket(ticket_id="T-1400", body="## Description\nx\n")
        violations = tickets_gate(tmp_path, self._queue(old, recent))
        tick011 = [v for v in violations if v.rule == "TICK011"]
        assert len(tick011) == 1
        assert "T-0001" in tick011[0].message
# frob:ticket T-0820
class TestTick007UndispatchedStale:
    """TICK007 (T-0820): the `frob check` half of T-0752's undispatched-
    stale-CRITICAL/HIGH alarm -- `tickets_gate` reuses
    `frob.tickets.undispatched_stale` verbatim over the dispatchable
    (unblocked, unleased) set and WARNs per alarmed ticket, mirroring
    `frob ticket doable`'s UNDISPATCHED row marker as a mechanical gate
    finding instead of a display-only nicety."""

    # frob:ticket T-0820
    def _queue(self, *tickets: Ticket) -> TicketQueue:
        """A `TicketQueue` of `tickets`, keyed by id."""
        return TicketQueue(tickets={t.id: t for t in tickets})

    # frob:ticket T-0820
    def _priority_ticket(
        self,
        *,
        ticket_id: str,
        priority: Priority,
        created: date,
        state: TicketState = TicketState.QUEUED,
        blocked_by: tuple[str, ...] = (),
    ) -> Ticket:
        """A minimal queued `Ticket` at `priority`/`created`, optionally
        `blocked_by` an id, no scope -- the shape `undispatched_stale`
        needs, with every other field defaulted the same way
        `test_tickets_priority.py`'s `_ticket` helper does. `Ticket` is
        frozen (`model_config = ConfigDict(frozen=True, ...)`), so
        `blocked_by` must be set here, not assigned after construction."""
        return Ticket(
            id=ticket_id,
            title=f"ticket {ticket_id}",
            state=state,
            kind=TicketKind.FEATURE,
            origin=Origin.HUMAN,
            created=created,
            priority=priority,
            blocked_by=blocked_by,
            parent=None,
            scope=(),
            evidence=(),
            attachments=(),
            acceptance=(),
            threat=None,
            body="",
        )

    # frob:ticket T-0820
    # frob:tests \
    # tests/gates_suite/test_tick.py::TestTick007UndispatchedStale.test_stale_critical_\
    # fires
    def test_stale_critical_fires(self, tmp_path: Path) -> None:
        """A CRITICAL ticket filed long ago (far past the 4h default
        threshold), still queued and unblocked, is TICK007."""
        ticket = self._priority_ticket(
            ticket_id="T-4001",
            priority=Priority.CRITICAL,
            created=date(2026, 1, 1),
        )
        violations = tickets_gate(tmp_path, self._queue(ticket))
        tick007 = [v for v in violations if v.rule == "TICK007"]
        assert len(tick007) == 1
        assert "T-4001" in tick007[0].message
        assert tick007[0].severity == Severity.WARN

    # frob:ticket T-0820
    # frob:tests \
    # tests/gates_suite/test_tick.py::TestTick007UndispatchedStale.test_fresh_critical_\
    # is_silent
    def test_fresh_critical_is_silent(self, tmp_path: Path) -> None:
        """A CRITICAL ticket filed today has not crossed the 4h threshold
        yet (whole-day granularity means same-day is 0h elapsed) -- no
        TICK007."""
        ticket = self._priority_ticket(
            ticket_id="T-4002",
            priority=Priority.CRITICAL,
            created=date.today(),
        )
        violations = tickets_gate(tmp_path, self._queue(ticket))
        assert not any(v.rule == "TICK007" for v in violations)

    # frob:ticket T-0820
    # frob:tests \
    # tests/gates_suite/test_tick.py::TestTick007UndispatchedStale.test_medium_priority\
    # _never_fires
    def test_medium_priority_never_fires(self, tmp_path: Path) -> None:
        """MEDIUM/LOW carry no default threshold (T-0752: "a queue always
        has some") -- an ancient MEDIUM ticket never alarms TICK007."""
        ticket = self._priority_ticket(
            ticket_id="T-4003",
            priority=Priority.MEDIUM,
            created=date(2020, 1, 1),
        )
        violations = tickets_gate(tmp_path, self._queue(ticket))
        assert not any(v.rule == "TICK007" for v in violations)

    # frob:ticket T-0820
    # frob:tests \
    # tests/gates_suite/test_tick.py::TestTick007UndispatchedStale.test_blocked_ticket_\
    # is_silent
    def test_blocked_ticket_is_silent(self, tmp_path: Path) -> None:
        """A CRITICAL ticket blocked on an open blocker is not in the
        dispatchable set at all (`doable()` excludes it), so it never
        reaches `undispatched_stale` and cannot fire TICK007."""
        blocker = self._priority_ticket(
            ticket_id="T-4004",
            priority=Priority.HIGH,
            created=date(2026, 1, 1),
        )
        blocked = self._priority_ticket(
            ticket_id="T-4005",
            priority=Priority.CRITICAL,
            created=date(2026, 1, 1),
            blocked_by=(blocker.id,),
        )
        violations = tickets_gate(tmp_path, self._queue(blocker, blocked))
        tick007 = [v for v in violations if v.rule == "TICK007"]
        assert not any("T-4005" in v.message for v in tick007)

    # frob:ticket T-0820
    # frob:tests tests/gates_suite/test_tick.py::TestTick007UndispatchedStale.test_real_repo_scan_runs_end_to_end_without_crashing  # noqa: E501
    def test_real_repo_scan_runs_end_to_end_without_crashing(self) -> None:
        """The honest "real repo scan" smoke test (T-0813 precedent): runs
        `tickets_gate` over this repo's OWN live `tickets.md`, not a
        fabricated fixture, and just proves TICK007's `doable()` +
        `has_live_lease()` + `undispatched_stale()` plumbing completes
        without crashing against real ticket data (blockers, leases,
        scopes, every priority) -- it deliberately does NOT assert
        fires-or-not, since the live queue's staleness state churns
        between sessions (a CRITICAL/HIGH ticket dispatched an hour before
        this test runs vs. one left sitting are both legitimate states);
        every violation, if any, must simply carry the TICK007 rule id and
        a WARN severity."""
        from frob.tickets import load_queue

        root = Path(__file__).resolve().parents[2]
        queue = load_queue(root).danger_ok
        violations = tickets_gate(root, queue)
        tick007 = [v for v in violations if v.rule == "TICK007"]
        for v in tick007:
            assert v.severity == Severity.WARN
            assert v.rule == "TICK007"
# frob:ticket T-0842
class TestTick008UnknownLedgerFields:
    """TICK008 (T-0842): the T-0838 typo-hazard follow-up -- a ticket
    carrying unknown/extra ledger field(s) (`extra="allow"` captured them
    into `__pydantic_extra__` instead of hard-failing `MalformedFrontmatter`)
    must be a mechanical `frob check` finding on the checked ledger, not
    just a WARNING log line nothing gates on. WARN severity, not ERROR --
    an initial ERROR pass was rejected in adversarial review: `frob ticket
    land`'s claim re-verification spawns `frob check` from the ROOT
    checkout's OLD `src` tree (playbook section 2), so while a schema-
    extending ticket is itself landing, root's stale `Ticket` model
    captures that ticket's own new field as an extra and an ERROR would
    red the land via `ClaimDivergence` -- a `frob:waive` cannot route
    around it either, since the same stale binary evaluates the waiver.
    See `_tick008_unknown_ledger_fields`'s docstring for the full trace."""

    def _queue(self, *tickets: Ticket) -> TicketQueue:
        """A `TicketQueue` of `tickets`, keyed by id."""
        return TicketQueue(tickets={t.id: t for t in tickets})

    def _ticket_with_extra(self, ticket_id: str, **extra: object) -> Ticket:
        """A minimal valid `Ticket` plus arbitrary unknown `extra` fields --
        `Ticket.model_config` is `extra="allow"`, so these land in
        `__pydantic_extra__` rather than raising. Goes through
        `model_validate` (a single `dict[str, object]` argument) rather than
        keyword-splatting into the constructor, so the mypy/ty-visible
        signature stays exact for every known field."""
        data: dict[str, object] = {
            "id": ticket_id,
            "title": f"ticket {ticket_id}",
            "state": TicketState.QUEUED,
            "kind": TicketKind.FEATURE,
            "origin": Origin.HUMAN,
            "created": date(2026, 1, 1),
            **extra,
        }
        return Ticket.model_validate(data)

    # frob:tests \
    # tests/gates_suite/test_tick.py::TestTick008UnknownLedgerFields.test_fires_on_unkn\
    # own_field
    def test_fires_on_unknown_field(self, tmp_path: Path) -> None:
        """A ticket with a genuinely unknown field fires TICK008, naming
        both the ticket id and the unknown field, at WARN (not ERROR --
        see the class docstring for why ERROR was rejected)."""
        ticket = self._ticket_with_extra("T-9001", not_a_real_field="x")
        violations = tickets_gate(tmp_path, self._queue(ticket))
        tick008 = _by_rule(violations, "TICK008")
        assert len(tick008) == 1
        assert "T-9001" in tick008[0].message
        assert "not_a_real_field" in tick008[0].message
        assert tick008[0].severity == Severity.WARN

    # frob:tests tests/gates_suite/test_tick.py::TestTick008UnknownLedgerFields.test_fuzzy_hint_on_near_miss_typo  # noqa: E501
    def test_fuzzy_hint_on_near_miss_typo(self, tmp_path: Path) -> None:
        """A near-miss typo of a known field name (`priorty` for
        `priority`, the exact incident T-0838's reviewer flagged) gets a
        fuzzy-match hint naming the likely intended field."""
        ticket = self._ticket_with_extra("T-9002", priorty="low")
        violations = tickets_gate(tmp_path, self._queue(ticket))
        tick008 = _by_rule(violations, "TICK008")
        assert len(tick008) == 1
        assert "priorty" in tick008[0].message
        assert "did you mean 'priority'" in tick008[0].message

    # frob:tests \
    # tests/gates_suite/test_tick.py::TestTick008UnknownLedgerFields.test_silent_on_cle\
    # an_ledger
    def test_silent_on_clean_ledger(self, tmp_path: Path) -> None:
        """A ticket with only known fields carries no `__pydantic_extra__`
        and never fires TICK008."""
        ticket = self._ticket_with_extra("T-9003")
        violations = tickets_gate(tmp_path, self._queue(ticket))
        assert not any(v.rule == "TICK008" for v in violations)

    # frob:tests tests/gates_suite/test_tick.py::TestTick008UnknownLedgerFields.test_real_repo_ledger_is_tick008_clean  # noqa: E501
    def test_real_repo_ledger_is_tick008_clean(self) -> None:
        """The real-repo smoke test the ticket demands: this repo's own
        live `tickets.md`/`tickets-archive.md` must produce ZERO TICK008
        findings today -- a nonzero result here means a genuinely stale
        known field somewhere in the live ledger, which this ticket's
        Description says to STOP and report rather than calibrate around."""
        from frob.tickets import load_queue

        root = Path(__file__).resolve().parents[2]
        queue = load_queue(root).danger_ok
        violations = tickets_gate(root, queue)
        tick008 = _by_rule(violations, "TICK008")
        assert tick008 == []

    # frob:tests \
    # tests/gates_suite/test_tick.py::TestTick008UnknownLedgerFields.test_waivable
    def test_waivable(self) -> None:
        """TICK008 is waivable like TICK004/TICK006/TICK007 (not added to
        `_UNWAIVABLE_RULES`) -- a genuinely temporary, disclosed exception
        (`frob:waive TICK008 reason=...`) stays available, matching the
        rest of the TICK family."""
        from frob.gates import _UNWAIVABLE_RULES

        assert "TICK008" not in _UNWAIVABLE_RULES
