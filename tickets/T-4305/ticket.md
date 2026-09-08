---
id: T-4305
title: Rebind stranded WIRE001 waiver whose follow-up ticket closed
state: in-progress
kind: bug
origin: human
created: '2026-09-08'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_ci_workflow_timeout.py
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
CLOSING A TICKET CAN STRAND A WAIVER THAT NAMES IT, AND ONE IS STRANDING THE
INTEGRATION RUN RIGHT NOW.

THE IMMEDIATE FAILURE, REPRODUCED LOCALLY AND IN CI. The live-repo WIRE002 test
reports exactly one finding: a WIRE001 waiver in the CI-workflow timeout test file
names a follow-up ticket that is already done, and the rule requires a WIRE001
waiver to bind to a real, OPEN follow-up ticket. That named ticket was closed
earlier today, which is what turned a passing waiver into a failing one without
anyone touching the waived code.

DO NOT SIMPLY DELETE THE WAIVER. Read its recorded reason first: it argues the
helper is genuinely wired, called by named sibling test methods, and that a
workflow-YAML-inspection helper has no production caller to reach it through BY
CONSTRUCTION. That reasoning does not expire when the ticket that prompted it
closes -- it is structural. If you agree with it after checking the callers named
in the reason actually exist and call it, the waiver should persist; what is wrong
is only which ticket it points at.

DECIDE WHAT A PERMANENT-SHAPED WAIVER SHOULD BIND TO. A rule that demands an open
follow-up ticket is designed for waivers that mean "not yet"; this one means "not
ever, by construction". Those are different claims and the rule currently cannot
tell them apart. Work out which the codebase already supports -- look for sibling
waivers of the same permanent shape in this same file and elsewhere and see what
they bind to, since the reason text itself claims pre-existing helpers in this
file are in the same shape. Follow that precedent rather than inventing a
mechanism.

THEN ASK WHETHER THIS CAN HAPPEN AGAIN, because it will. Any close of any ticket
can strand any waiver naming it, and nothing warned at close time. Whatever you
conclude, record it -- if the right answer is a check at close time that names
waivers pointing at the ticket being closed, file that rather than building it
here; this ticket is the unblock, not the redesign.

VERIFY by running the live-repo WIRE002 test to zero findings, and quote the
result. Expect other unrelated failures in the same suite; they are not yours.
