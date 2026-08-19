---
id: T-2622
title: unify lease-premise and follow-up-ticket-promise waiver checks (coordinate
  with T-2606)
state: queued
kind: feature
origin: human
created: '2026-08-19'
priority: medium
blocked_by:
- T-2606
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_waive.py
- src/frob/gates/_waive_comments.py
- tests/test_waive_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: docs/modules/gates.md
  reason: T-2377 still holds live lease on docs/modules/gates.md; narrowing to code
    files only, will disclose doc-catalog gap in Done report rather than force the
    add
  actor: logan
  at: '2026-08-19'
- op: add
  glob: src/frob/gates/_waive_comments.py
  reason: the shared parser + lease-premise phrase extension lives in _waive_comments.py
    (WAIVE006/007's own home); tests/test_waive_gate.py already covers this file's
    WAIVE006/007/WAIVE009 tests
  actor: logan
  at: '2026-08-19'
- op: add
  glob: tests/test_waive_gate.py
  reason: the shared parser + lease-premise phrase extension lives in _waive_comments.py
    (WAIVE006/007's own home); tests/test_waive_gate.py already covers this file's
    WAIVE006/007/WAIVE009 tests
  actor: logan
  at: '2026-08-19'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2612's audit measured 0 of the (originally cited) lease-holding tickets
named in `frob:waive` reasons still holding a live lease -- every one had
gone terminal, and the waiver's justification silently outlived it. Of
the 5 distinct holder-tickets whose waiver text could still be found in
today's tree (12 individual waiver sites across 8 files), 3 sites were
confirmed removable (the deferred doc work had actually been done) and 9
sites were confirmed still-owed work (now individually ticketed:
T-2621, T-2619, T-2618, T-2620 --
these renumber at land).

This is a mechanically checkable class and nothing currently checks it.
T-2606 covers the adjacent case (a waiver reason promising a follow-up
ticket that is never filed at all). Both are instances of the same
underlying gap: a waiver reason's free-text prose makes a claim about
another ticket's state or existence, and nothing keeps that claim honest
over time. Proposed unified design (do NOT build two parallel checkers):

1. A waiver-reason parser (shared with T-2606's follow-up-ticket-promise
   detection) that extracts every `T-\d+` token a reason mentions, plus a
   coarse classification of WHY it's mentioned: "holds a live lease
   blocking this waiver" vs "a follow-up ticket will do the deferred
   work" vs incidental context (e.g. "T-1733 added this field").
2. For the "live lease" class: when the named ticket's current state is
   terminal (done/archived/dropped/failed), surface the waiver for
   review -- a new WAIVE-family rule (or an extension of an existing one)
   rather than a silent pass. It should NOT auto-remove the waiver (T-2612's
   own explicit instruction: an expired premise does not mean the finding
   is dead) -- just force a human/agent re-check, the same posture T-2606
   already proposes for its own case.
3. For the "follow-up ticket promised" class: T-2606's own detection
   (a real ticket id token near "follow-up"/"once ... clears"/similar
   phrasing) plus a check that the named id actually exists and, ideally,
   is not itself terminal-with-the-work-undone.

Both classes share the parser and the "waiver reason cites a ticket ->
check that ticket's current state against the claim the prose makes"
shape; only the specific claim being checked differs. Implement as one
gate (or one shared helper feeding two gate rules) rather than two
independently-maintained regex sets -- avoid the exact duplication NO
DUPLICATION forbids.

Coordinate with T-2606 before starting; this ticket's scope is naming the
unified design, not landing it standalone if T-2606 is already in
progress by the time this is picked up.

Filed by T-2612 (deliverable 2: "make it enforceable").
