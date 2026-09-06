---
id: T-4100
title: 'F-300: a correct fix broke out-of-scope tests, so scope discipline left the
  branch red for every later ticket to inherit'
state: queued
kind: bug
origin: human
created: '2026-09-06'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_land_cmd.py
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
Consumer logand.app-v2 F-300, 2026-09-06:

  "T-0262's hasPointer fix made two matrix-rain.test.tsx cases fail because they
   never mocked a container rect; THE FILE WAS OUTSIDE THE TICKET'S SCOPE, so the
   agent LEFT THE BRANCH RED (133/135) and filed T-0268. Scope discipline is
   right, but A RED BRANCH BETWEEN TWO TICKETS IS A WINDOW WHERE EVERY OTHER
   ENGINE TICKET INHERITS FAILURES."

SCOPE DISCIPLINE PRODUCED A KNOWINGLY BROKEN BRANCH. The agent did everything
correctly: it made a correct fix, discovered the consequence, did not edit outside
its declared scope, and filed a follow-up. The result is a red branch that every
subsequent ticket on that branch inherits -- so the next agent starts from a
failing baseline and cannot tell its own breakage from the inherited kind.

THIS IS THE SAME STRUCTURAL GAP AS T-4054, from a third direction. There, a
refactor invalidated doc anchors in a file another ticket owned; here, a fix
invalidates TESTS in a file outside scope. In both cases THE TICKET CREATES AN
OBLIGATION IT IS FORBIDDEN TO DISCHARGE. T-4054 records the doc case and the
false-ack it forced; this adds the test case and the red-branch window it forces.
Read them together -- one answer about "work my change creates in a file I do not
own" resolves both.

THEIR TWO PROPOSALS ARE GENUINELY DIFFERENT AND SHOULD NOT BE BLURRED:
  (a) ALLOW A NARROW SCOPE-ADD for a test file the ticket's own diff broke, with
      a reason -- "it is a consequence of the ticket, not new work". This is the
      permissive answer and it is well-argued: fixing a test your change broke is
      not scope creep, it is completing your change.
  (b) LAND SHOULD REFUSE until the follow-up is dispatched. This is the strict
      answer: it keeps scope inviolate and prevents the red-branch window by
      blocking rather than widening.
(a) is cheaper and matches how a careful human would behave. (b) is safer for
multi-agent branches, which is precisely the situation that produced the report.
DECIDE DELIBERATELY AND SAY WHY; do not implement whichever is easier to code.

WHAT MUST BE DETERMINED FIRST, because it decides between them: CAN FROB TELL
THAT THIS TICKET'S DIFF CAUSED THAT TEST'S FAILURE? Option (a) requires
attributing a newly-failing out-of-scope test TO the diff -- otherwise it becomes
a general licence to widen scope by claiming causation. If that attribution is not
reliably computable, (a) is unsafe and (b) is the honest choice. frob already
reasons about which commits belong to a ticket (the land path squashes them, and
verify has an attribution engine), so check what exists before assuming either
way.

NOTE THE INTERACTION WITH TDD001 AND THE FLAKE WORK: a red baseline also poisons
the flake population measurement (T-4055) -- a test failing for an inherited
reason is indistinguishable from a load-sensitive flake in a CI summary. So the
red-branch window has a second cost beyond the next agent's confusion.

DO NOT resolve this by weakening scope enforcement generally. The consumer
explicitly says "scope discipline is right", and this queue has five tickets open
about scope being computed over the wrong SET (T-4050 and children) -- widening
what a ticket may touch is a different and more dangerous change than fixing what
it is measured against.

MUST-FIRE FIXTURE: a ticket whose diff breaks an out-of-scope test cannot land
silently leaving the branch red.
MUST-STAY-QUIET: a ticket whose diff breaks nothing outside its scope lands
normally, with no new friction.
THIRD FIXTURE: a test that was ALREADY failing before the ticket's diff does not
block it -- the attribution must distinguish inherited from caused.

ACCEPTANCE
- Whether frob can attribute an out-of-scope test failure to this ticket's diff,
  answered by measurement first.
- (a) or (b) chosen deliberately with the reason recorded.
- Read jointly with T-4054 as one "obligations I cannot discharge" question.
- All three fixtures committed.