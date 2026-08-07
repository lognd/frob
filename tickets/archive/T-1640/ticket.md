---
id: T-1640
title: INV006 fires on waiver-reason prose, penalising precise justifications
state: done
kind: bug
origin: human
created: '2026-08-06'
priority: medium
blocked_by:
- T-1663
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_inv.py
- src/frob/dsl.py
- tests/**
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestInv003Gate::test_markdown_waive_marker_with_reason_is_silent
- tests/test_gates.py::TestInv003Gate::test_exclusivity_claim_without_marker_warns
designated_repro_test: null
evidence_changes:
- old_node: tests/test_gates.py::TestInv006Gate::test_exclusivity_claim_inside_a_waiver_reason_is_not_flagged
  new_node: tests/test_gates.py::TestInv003Gate::test_markdown_waive_marker_with_reason_is_silent
  reason: T-1763 deleted INV006 and its whole _strip_directive_reason_prose mechanism
    -- no functional equivalent exists; rebinding to the nearest still-live waiver-related
    test in INV003
  actor: logan
  at: '2026-08-07'
- old_node: tests/test_gates.py::TestInv006Gate::test_exclusivity_claim_outside_a_reason_attribute_still_warns
  new_node: tests/test_gates.py::TestInv003Gate::test_exclusivity_claim_without_marker_warns
  reason: T-1763 deleted INV006 and its whole _strip_directive_reason_prose mechanism
    -- no functional equivalent exists; rebinding to the nearest still-live test in
    INV003
  actor: logan
  at: '2026-08-07'
threat: null
component: null
---
INV006 flags a file that "makes an exclusivity/normative claim" -- a bare `only`, `never`, `always` -- with no `frob:invariant INV-###` edge anchored anywhere in it. That is a good rule for a docstring or a design comment stating how the system behaves.

It also fires on WAIVER REASON text. Observed 2026-08-06: a `frob:waive EXHAUST002 reason="..."` justification read "int(str) can only ever raise ValueError, never TypeError", and INV006 turned main red with 1 error until the sentence was reworded.

The question this ticket must settle: should a waiver's reason count as a normative claim?

The case for YES (current behavior): the sentence really does assert an invariant about int()'s behavior, and if that assertion is wrong the waiver is unjustified. Waiver reasons are exactly where unproven claims hide -- which is the whole premise of the waiver audit (T-1614).

The case for NO: a waiver reason is an ARGUMENT about why a finding does not apply, not a specification of system behavior. Demanding an INV-### binding for every explanatory sentence makes reasons worse: the cheapest way to satisfy the gate is to write a vaguer reason, and a vaguer reason is precisely what the waiver audit will later condemn. A rule that penalises precise justification is pointed the wrong way.

My read is NO for waiver reasons specifically, but the decision should be deliberate and documented either way, not left as an accident of which prose the scanner happens to reach.

Note the pattern: this is the third detector this drive found reading PROSE as if it were a declaration (TICK006 on a marker quoted mid-sentence, T-1541; the live-tracker scan on Done-report narrative, T-1633; now INV006 on a waiver reason). Consider whether these want a shared notion of "this span is explanatory text, not a declaration" rather than three independent fixes -- the DSL already knows where directive attributes end and free text begins.

Whatever is decided, add the case to the test suite so the behavior is pinned rather than incidental.

## Done report

INV006's claim scan ran over a source file's whole raw text, including
every directive's `reason="..."` attribute string -- so a `frob:waive
EXHAUST002 reason="int(str) can only ever raise ValueError, never
TypeError"` justification tripped INV006 on its own (the live incident:
that sentence genuinely uses "only"/"never"), demanding an unrelated
`frob:invariant` binding for a sentence that ARGUES why a different
finding does not apply, not a specification of this file's behavior.
Read the wrong way, the gate rewards a vaguer reason (the cheapest way
to dodge it) over a precise one -- the wrong direction for the waiver
audit (T-1614).

Decision made per the ticket's own framing: NO, a waiver reason (or any
directive's `reason=` attribute value) does not count as a normative
claim for INV006's purposes.

Fix: `_strip_directive_reason_prose` (src/frob/gates/_inv.py) removes
every `reason="..."` directive-attribute span (any verb, not just
`frob:waive`; DOTALL so a folded, backslash-continued multi-line reason
is stripped as one span) from the text INV006's source-side scan
(`_inv006_src_violations`) passes to `find_exclusivity_claims`. Scoped
narrowly to INV006's source scan only -- INV003/INV004's doc-side scans
are unchanged, since the ticket's own incident and this drive's scope
are both source-file-specific.

Two regression tests pin the decision: a waiver reason containing
exclusivity vocabulary no longer fires INV006 (verified to fail without
the fix by reverting it locally and re-running); a genuine claim living
outside any `reason=` span in the same file still fires normally, so the
strip cannot be used to smuggle a real, unwaived claim past the gate.

docs/modules/gates.md's INV006 section documents the decision and its
scope.

Not addressed (explicitly out of scope, noted per the ticket's closing
suggestion): the shared "this span is explanatory text, not a
declaration" abstraction the ticket floats across TICK006/live-tracker/
INV006 was not built -- this fix is INV006-local, matching the other two
detectors' own independent fixes rather than generalizing three
different scanners' notion of prose into one shared primitive in the
same change.

### Changed
```
 tickets.md | 3 +--
 1 file changed, 1 insertion(+), 2 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 0 error(s), 6217 warning(s), 715 waived
- error-findings: none (measured, zero errors)
