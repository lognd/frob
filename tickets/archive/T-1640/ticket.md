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
- tests/test_gates.py::TestInv006Gate::test_exclusivity_claim_inside_a_waiver_reason_is_not_flagged
- tests/test_gates.py::TestInv006Gate::test_exclusivity_claim_outside_a_reason_attribute_still_warns
designated_repro_test: null
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