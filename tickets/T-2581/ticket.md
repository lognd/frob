---
id: T-2581
title: 'M6: REL001 extension -- refuse release cut with open milestone-X tickets'
state: queued
kind: feature
origin: human
created: '2026-08-18'
priority: high
blocked_by:
- T-2574
- T-2576
parent: T-2573
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_debt_deprecated.py
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
Extend REL001 (src/frob/gates/_debt_deprecated.py, `release_gate`/its
callers -- REL001 currently refuses a release over open `frob:debt` and
open `frob:deprecated`; verify the exact call shape before extending it,
same file already carries two REL001-reporting checks side by side as a
precedent for how to add a third finding kind under the same rule id).

New rule: refuse to cut release X while OPEN tickets carry milestone X.
Must name WHICH tickets block the cut in the refusal message, not just
that something does -- follow the existing REL001 finding shape (each
finding already names the specific edge/ticket that blocks; match that
precedent, do not report a bare count).

Depends on M1 (T-2574, milestone field) and M2 (T-2576, MILE003 +
backfill -- without every open ticket actually carrying a milestone,
this check cannot meaningfully compare "milestone X" against the
release version being cut). Does not depend on M3/M4/M4b/M5.
