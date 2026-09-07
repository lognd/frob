---
id: T-4170
title: 'a bug ticket whose only honest evidence is a pre-existing test cannot close:
  the rule asks whether the test file is in scope, not whether its binding reaches
  in-scope code'
state: done
kind: bug
origin: agent
created: '2026-09-07'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_evidence.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/test_evidence_integrity.py::TestT4170PreExistingTestOutsideScopeBoundViaDirective::test_directive_bound_pre_existing_test_covers_scope
- tests/test_evidence_integrity.py::TestT4170PreExistingTestOutsideScopeBoundViaDirective::test_directive_bound_pre_existing_test_closes_cleanly
- tests/test_evidence_integrity.py::TestT4170PreExistingTestOutsideScopeBoundViaDirective::test_unconnected_pre_existing_test_still_refused
- tests/test_evidence_integrity.py::TestT4170PreExistingTestOutsideScopeBoundViaDirective::test_scope_widened_without_a_touching_diff_remains_detectable
designated_repro_test: null
acceptance:
- text: given a bug-kind ticket binding a pre-existing test whose own directive names
    a symbol inside the ticket's scope, when the ticket closes, then it closes cleanly
  evidence:
  - tests/test_evidence_integrity.py::TestT4170PreExistingTestOutsideScopeBoundViaDirective::test_directive_bound_pre_existing_test_covers_scope
  - tests/test_evidence_integrity.py::TestT4170PreExistingTestOutsideScopeBoundViaDirective::test_directive_bound_pre_existing_test_closes_cleanly
- text: given a bug-kind ticket binding a test with no connection to its scope, when
    it attempts to close, then it is still refused
  evidence:
  - tests/test_evidence_integrity.py::TestT4170PreExistingTestOutsideScopeBoundViaDirective::test_unconnected_pre_existing_test_still_refused
- text: given a ticket that widens scope to a file its diff never touched, when the
    ledger is checked, then that remains detectable
  evidence:
  - tests/test_evidence_integrity.py::TestT4170PreExistingTestOutsideScopeBoundViaDirective::test_scope_widened_without_a_touching_diff_remains_detectable
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
A BUG TICKET WHOSE ONLY HONEST EVIDENCE IS A TEST THAT PREDATES IT HAS NO WAY TO
CLOSE CLEANLY. Reported as logand.app-v2 F-367, and their enumeration of the
available exits is what makes it a no-exit rather than friction:

  - The evidence IS the pytest test that verifies the behaviour. That test file
    predates the ticket and was never touched by it, so it sits outside the
    ticket's scope and ledger hygiene reports evidence-out-of-scope.
  - Citing the land commit against the in-scope file instead -- the pattern
    allowed for docs and ux kinds -- trips COV003, because a non-docs kind must
    bind a collected pytest node.
  - Widening scope to include the test file WOULD BE A LIE, and they can prove it:
    the diff shows the file was never touched.

So the three available actions are: report false evidence, declare a false scope,
or leave the ticket unclean. Their agent chose the third and left a note. That is
the correct choice and it is the one the system should not have forced.

THEIR PROPOSED FIX IS BETTER THAN A NEW EXEMPTION AND SHOULD BE THE STARTING
POINT: let a bug or feature ticket bind a pytest node whose FILE is outside scope
WHEN THAT TEST'S OWN `frob:tests` DIRECTIVE NAMES AN IN-SCOPE SYMBOL.

That is elegant because it invents nothing. The test already declares what it
covers, and that declaration is exactly the edge frob's obligation graph exists to
track. A test outside scope that declares an in-scope symbol is not weaker
evidence -- it is the SAME evidence, reached through the binding rather than
through file adjacency. The current rule ignores the edge and asks a proximity
question instead.

THIS IS THE SAME SUBJECT ERROR AS T-4144, and the pair should be read together
before either is fixed. There, command evidence is refused because a ticket's
SCOPE CONTAINS a python file even though its DIFF touched none. Here, evidence is
refused because a test's FILE is outside scope even though its BINDING reaches
in-scope code. Both rules take "the ticket's scope" as a proxy for a question
scope does not answer. If a shared helper is warranted -- something that answers
"is this evidence connected to what this ticket changed" -- both should use it.

DO NOT ADOPT THE SECOND SUGGESTION AS THE PRIMARY FIX. They offer, as an
alternative, accepting a commit-diff entry as supplementary scope proof on any
kind. That widens the docs and ux escape hatch to every kind, which would let a
code ticket close with no test binding at all -- the exact thing the kind
restriction exists to prevent. If it is adopted, it must be IN ADDITION to a real
binding, never instead of one, and the ticket should say so explicitly.

VERIFY THE PREMISE FIRST, since I have not: confirm that a test file outside scope
whose directive names an in-scope symbol is genuinely refused today, and confirm
which check refuses it. The report names both ledger hygiene and COV003, which are
different surfaces; if two separate checks refuse the same legitimate shape, both
need fixing and only one may be obvious.

MUST-FIRE FIXTURE:   a bug-kind ticket binds a pre-existing test whose own
                     directive names a symbol inside the ticket's scope, and it
                     closes cleanly.
MUST-STAY-QUIET:     a bug-kind ticket binding a test with NO connection to its
                     scope is still refused -- the binding must do real work.
THIRD FIXTURE:       a ticket cannot satisfy the requirement by widening scope to
                     a file its diff never touched; that remains detectable.

ACCEPTANCE
- The premise verified and the refusing check or checks identified by name.
- Evidence accepted through the declared binding rather than through file
  adjacency.
- The unconnected-test case proven still refused.
- The relationship to T-4144's identical subject error stated, and a shared
  helper used if one is warranted.
- All three fixtures committed.