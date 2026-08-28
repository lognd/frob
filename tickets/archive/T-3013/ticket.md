---
id: T-3013
title: 'post-land sweep regression from an unattributed source (sweep spawned by T-2990):
  1 new (rule, file) identit(ies), 0 finding(s) (DOC006)'
state: done
kind: docs
origin: agent
created: '2026-08-26'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/strata/graph.md
findings:
- - DOC006
  - docs/strata/graph.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: kind
  old_value: bug
  new_value: docs
  reason: T-3013's finding (DOC006 on docs/strata/graph.md) is a doc-lint identity,
    not a code defect; scope is doc-only. Reclassifying to docs-kind so the docs-kind
    --evidence-cmd channel applies, matching the pre-existing-residue disposition
  actor: logan
  at: '2026-08-28'
body_changes:
- mode: append
  reason: record re-verification for series-DC disposition
  actor: logan
  at: '2026-08-28'
  old_length: 967
  new_length: 1361
- mode: append
  reason: 'BUG002 front door (T-2393): DOC006 identity on docs/strata/graph.md does
    not reproduce on current main; independent re-measurement (gates-fast) found the
    only two DOC006 hits repo-wide are on tickets/T-2962/ticket.md, unrelated. Pre-existing
    residue the rolling baseline had not recorded; no fix required.'
  actor: logan
  at: '2026-08-28'
  old_length: 1361
  new_length: 1673
evidence:
- cmd:git grep -L DOC006 -- docs/strata/graph.md exit=0 sha256=aed3729dd11c
kind_history:
- 2026-08-28 bug->docs evidence=0 done_report=yes
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: ad5e80be07249ce52218e9c70e01edcbc9cca267
---
The deferred post-land unscoped sweep (T-1684) for an unattributed source (sweep spawned by T-2990) at commit 3e7ec9013238a16a5c3c40b3ad40014349fb6503 found 1 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (1), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 0 actual finding(s) across those 1 identit(ies).

New (rule, file) identit(ies) filed here:

- DOC006  docs/strata/graph.md

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

Re-verified on current main (2026-08-28): ran gates-fast; DOC006 does not fire on docs/strata/graph.md at all -- the only two DOC006 hits repo-wide are on tickets/T-2962/ticket.md, an unrelated file. This confirms the ticket's own independent re-measurement (0 findings). Disposition: pre-existing/stale residue from the rolling baseline gap, not a live defect. Closing without a code change.

frob:no-behavior-change reason="DOC006 identity on docs/strata/graph.md does not reproduce on current main; independent re-measurement (gates-fast) found the only two DOC006 hits repo-wide are on tickets/T-2962/ticket.md, unrelated. Pre-existing residue the rolling baseline had not recorded; no fix required."