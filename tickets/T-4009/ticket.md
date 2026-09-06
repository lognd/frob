---
id: T-4009
title: 'F-223: a brand-new test is NO_VERDICT at the parent commit, so --designate-repro-force
  is required every time and becomes ceremony'
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
- src/frob/tickets/_bug_repro.py
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
Consumer logand.app-v2 F-223, 2026-09-06:

  "A new test cannot exist at the parent commit, so the repro designation always
   reports NO_VERDICT and needs the force flag; treat 'test file absent at
   parent' as a red verdict by construction."

THEY ARE RIGHT, AND THE ARGUMENT IS AIRTIGHT. A test that does not exist cannot
pass. "Absent at the parent commit" and "failing at the parent commit" are the
same fact for the purpose this check serves -- the fix genuinely came after the
test. Reporting NO_VERDICT there is not caution; it is refusing to draw the one
conclusion the situation permits.

THE HARM IS THAT IT TURNS A DELIBERATE OVERRIDE INTO CEREMONY. Because EVERY
brand-new test hits it, `--designate-repro-force` must be passed on essentially
every TDD-shaped ticket. A force flag that is always required stops being a
considered override and becomes a keystroke people add reflexively -- and once it
is reflexive it will be used in the cases where it genuinely matters, which is
exactly what a force flag exists to prevent. The rule is not just noisy; it is
actively destroying its own escape hatch's meaning.

CONFIRMED INDEPENDENTLY INSIDE THIS REPO, TODAY. While landing T-3940, one of my
own implementer agents reported: "the designated BUG002 repro test was lost across
the land ... re-verified the repro by hand against the pre-fix commit (confirmed
it genuinely fails there), re-designated it with --designate-repro-force". A
careful agent did the right thing manually and then still had to force. That is
the reported pattern, from a second and unrelated direction, on the same day.

THIS ALSO COMPLETES A KNOWN PINCER. Already recorded here: TDD001 pushes tests
first, --check-repro requires them red, and DRIFT002 then fires on the red test's
own directive. F-223 is the missing piece -- the test-first ordering the other
rules DEMAND is precisely the ordering this check cannot verdict on. The rules
are not merely unaligned; one requires the state another cannot evaluate.

THE FIX: treat "test file (or test node) absent at the parent commit" as RED by
construction, and say so in the output -- "absent at parent, treated as red"
rather than NO_VERDICT. The reasoning should be visible, not implicit, so a
reader can tell this apart from a test that ran and failed.

BE PRECISE ABOUT WHAT "ABSENT" MEANS -- this is the part to get right:
  - The FILE absent at parent is unambiguous.
  - The file present but the NODE ID absent (a new test added to an existing
    file) is the same argument and is the more common case; make sure it is
    covered.
  - The file present, node present, but not COLLECTIBLE at parent (e.g. an
    import error) is NOT the same thing -- that is a genuine no-verdict and must
    stay one. Do not collapse a broken parent tree into a red verdict; that would
    manufacture false repro proof, which is worse than the friction being fixed.

MUST-FIRE FIXTURE: a test absent at the parent commit yields a RED verdict with
no force flag, and the output states why.
MUST-STAY-QUIET: a test that EXISTS and PASSES at the parent commit is still
refused as confirmatory-only -- the whole point of the check survives.
THIRD FIXTURE: a parent commit where collection genuinely fails still reports
NO_VERDICT, not red.

ACCEPTANCE
- Absent-at-parent treated as red, for both missing file and missing node id.
- Uncollectible-at-parent still NO_VERDICT, with a fixture proving the split.
- --designate-repro-force no longer required for an ordinary new test.
- All three fixtures committed.