---
id: T-4014
title: 'F-227: TDD001 names the wrong side as the verifying test (observed printing
  the SAME symbol on both sides), making the finding unactionable'
state: queued
kind: bug
origin: human
created: '2026-09-06'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Consumer logand.app-v2 F-227, 2026-09-06:

  "Sixteen WARN-only TDD001 lines on T-0185's dry run read 'X was not committed
   strictly after its verifying test Y' where Y is the impl symbol from a
   frob:tests directive. Swap the roles in the message and say which commit each
   side was first seen in."

I OBSERVED THIS MYSELF TODAY AND DID NOT ACT ON IT, which is worth recording as
much as the defect. Landing T-3934 produced TDD001 lines of this exact shape, and
in our case the two sides were LITERALLY THE SAME STRING:

  TDD001: tests/test_ticket_land_proof_claims.py::TestLandProofClaimsOutcome.
  test_no_recorded_outcome_leaves_verified_unaffected was not committed strictly
  after its verifying test tests/test_ticket_land_proof_claims.py::
  TestLandProofClaimsOutcome.test_no_recorded_outcome_leaves_verified_unaffected

A message asserting a symbol was not committed after ITSELF is self-evidently
wrong, I read it, noted it as odd, and moved on because the rule is WARN-only and
the land succeeded. That is the failure mode this queue exists to prevent: a
nonsensical diagnostic tolerated because it did not block anything. The consumer
had to report it for it to get a ticket.

WHY IT MATTERS BEYOND TIDINESS. TDD001 exists to enforce test-first ordering,
which is a discipline the whole T-3004 section-7 workflow rests on. A message
that names the wrong side -- or the same side twice -- makes the finding
unactionable: the reader cannot tell which artifact is supposed to move, so the
only available responses are to ignore it or to waive it. Sixteen such lines in
one dry run is a strong training signal that TDD001 output is noise.

IT ALSO INTERACTS WITH A KNOWN PINCER already recorded here: TDD001 pushes tests
first, --check-repro requires them red, DRIFT002 then fires on the red test's own
directive, and T-4009 (F-223) shows a brand-new test is NO_VERDICT at the parent
commit so the force flag is always required. TDD001's message being wrong on top
of that makes the whole cluster harder to reason about. Whoever takes this should
read T-4009 first.

WHAT TO FIX, both halves:
  1. THE ROLES. Determine which side of a frob:tests edge is the test and which
     is the implementation AT THE POINT THE MESSAGE IS BUILT. Note the codebase
     already knows this is ambiguous: gates/__init__.py documents that "two
     frob:tests conventions coexist -- src is the test and target is the tested
     symbol, or src is the tested symbol and target is the test", and checks
     e.src first with e.target as fallback. A message that assumes one
     convention will be wrong for the other. THAT AMBIGUITY IS THE LIKELY ROOT
     CAUSE -- start there rather than swapping the two format arguments.
  2. THE EVIDENCE. The consumer's second ask is the more useful half: say which
     commit each side was first seen in. TDD001 is an ORDERING claim; printing
     the two commits makes it checkable by the reader instead of asserted. It
     also makes the same-symbol-twice case impossible to print silently.

MUST-FIRE FIXTURE: a genuine implementation-first pair is still flagged, with the
test and the implementation named on the correct sides.
MUST-STAY-QUIET: a genuine test-first pair is not flagged.
THIRD FIXTURE: a message can never name the same symbol on both sides -- assert
it, so the observed nonsense output cannot recur.
FOURTH FIXTURE: both conventions of the frob:tests edge produce correctly-oriented
messages.

ACCEPTANCE
- Root-caused through the two-convention ambiguity, not patched at the format
  string.
- Each side's first-seen commit printed.
- All four fixtures committed.