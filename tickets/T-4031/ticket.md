---
id: T-4031
title: 'F-238: a ticket with zero acceptance criteria passes the acceptance check
  vacuously and lands'
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
- src/frob/tickets/_evidence.py
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
Consumer logand.app-v2 F-238, 2026-09-06:

  "T-0206 landed with an evidence list but NO ACCEPTANCE CRITERIA; frob's
   close/land did not object, the repo's ledger hygiene test then blocked the
   next land. `close` should require at least one criterion for feature/bug/
   security kinds."

A TICKET WITH NO ACCEPTANCE CRITERIA CANNOT FAIL ITS ACCEPTANCE CHECK. That is
the whole finding, and it is the silent-zero shape in its purest form: the gate
that verifies criteria are satisfied iterates an empty list, finds no
violations, and reports success. Zero criteria and zero unmet criteria are
indistinguishable in the output.

Note this repo ALREADY HAS the machinery that would catch it: `unbound_acceptance`
in src/frob/tickets/_models.py:768 checks that each criterion has resolving
evidence. It correctly returns nothing for a ticket with no criteria -- which is
right for what it was asked, and useless for what actually matters. The missing
check is one level up: whether there were any criteria to bind AT ALL.

THE DETECTION ARRIVED, BUT IN THE WRONG PLACE AND ONE LAND TOO LATE. Their
repo-side ledger hygiene ratchet caught it -- and blocked the NEXT land, not the
offending one. So the ticket with no acceptance is already permanently in the
history, and the cost landed on an unrelated piece of work. A check that fires
one land late punishes the wrong change and leaves the defect in place.

THEIR PROPOSED SCOPE IS RIGHT AND WORTH KEEPING NARROW: require at least one
criterion for feature/bug/security kinds. Do NOT extend it to every kind. A
docs or chore ticket may legitimately have nothing to state as given/when/then,
and forcing a criterion there would produce ceremonial text -- which is worse
than none, because it looks like verification and is not. Say explicitly which
kinds are exempt and why.

WHAT TO DETERMINE FIRST: is there already a rule intended to cover this that is
not firing? "Nothing enforces X" is a claim about our code -- four items across
the recent audit epics turned out to be already implemented. Check MILE/TICK and
the close gate before adding a new rule; if a rule exists and is silent, the fix
is different and smaller.

CROSS-REFERENCE T-3985 (the subject-count primitive). This is precisely a gate
reporting a verdict over zero subjects, and the primitive would make it visible
without a dedicated rule. Say in the Done report whether T-3985 subsumes this; if
it does, the narrow close-time refusal is still worth having, because a refusal
at close is more useful than a finding at check.

MUST-FIRE FIXTURE: closing a feature/bug/security ticket with zero acceptance
criteria is refused, naming the ticket kind.
MUST-STAY-QUIET: (a) a ticket WITH criteria closes normally; (b) an exempt kind
with zero criteria still closes -- the carve-out is deliberate and tested, not
incidental.
THIRD FIXTURE: the refusal happens on the OFFENDING close, not on a later
unrelated land.

ACCEPTANCE
- Whether an existing rule already intends to cover this, answered by grep
  first.
- At-least-one-criterion required for feature/bug/security at close time.
- The exempt kinds named and justified.
- All three fixtures committed.