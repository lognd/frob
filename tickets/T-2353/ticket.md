---
id: T-2353
title: priority/kind/component/tier mutations have no --reason audit trail
state: queued
kind: bug
origin: human
created: '2026-08-17'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: tickets
anchor: false
anchor_reason: null
land_commit: null
---
frob ticket priority <id> <level> accepts NO --reason flag, so a priority
change leaves no audit trail of why it happened. Meanwhile frob ticket
scope and frob ticket accept --amend BOTH require a --reason (recorded in
scope_changes / acceptance_amendments audit trails) and refuse without
one. That is an inconsistency in the ledger's own accountability model:
in a repo whose premise is that unaccounted work is a build failure,
silently re-triaging a ticket's priority is exactly the kind of
unrecorded decision the ledger exists to prevent. Hit this raising
T-2351 from medium to critical -- the change is now in the ledger with
no recorded justification.

Survey ALL the frob ticket mutation verbs before designing the fix
(priority, kind, component, label, tier, sprint, runs-last, block,
...) and report which do and do not require a reason. Then make the
ones that change triage-relevant state consistent, following the
existing --reason/--reason-file pattern (T-0737 precedent) and
recording into a per-ticket audit trail like the existing ones
(scope_changes, acceptance_amendments). Do not invent a new audit
mechanism if one already fits.

POSITIVE CONTROLS: a reason-less invocation of a newly-guarded verb is
REFUSED; a reasoned one records into the audit trail; and verbs that
legitimately need no reason (pure queries) are untouched.
