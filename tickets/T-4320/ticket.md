---
id: T-4320
title: LiveTrackerCited can permanently refuse close/land against a land-owned file
state: in-progress
kind: bug
origin: human
created: '2026-09-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_live_tracker.py
- tests/test_tickets_live_tracker.py
- docs/modules/tickets-landing.md#live-tracker-citation-preflight-t-0854
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_tickets_live_tracker.py
  reason: tests and doc target for the live_tracker_citations fix
  actor: logan
  at: '2026-09-08'
- op: add
  glob: docs/modules/tickets-landing.md
  reason: tests and doc target for the live_tracker_citations fix
  actor: logan
  at: '2026-09-08'
- op: remove
  glob: docs/modules/tickets-landing.md
  reason: narrow to the single anchor this diff actually touches, not the whole landing
    doc
  actor: logan
  at: '2026-09-08'
- op: add
  glob: docs/modules/tickets-landing.md#live-tracker-citation-preflight-t-0854
  reason: narrow to the single anchor this diff actually touches, not the whole landing
    doc
  actor: logan
  at: '2026-09-08'
- op: add
  glob: docs/modules/tickets-landing.md
  reason: SCOPE001 requires the whole file in scope even though only one anchor is
    edited; the file-level closure warnings this pulls in (TestAnchorMarker's pre-existing
    frob:tests bindings into _land.py) predate this ticket and are addressed below
  actor: logan
  at: '2026-09-08'
- op: remove
  glob: docs/modules/tickets-landing.md
  reason: 'revert: whole-file scope pulls in 100+ unrelated closure obligations; keep
    only the anchor this diff touches'
  actor: logan
  at: '2026-09-08'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Discovered while closing T-4303. frob.tickets._live_tracker.live_tracker_citations (the T-0854 close/land preflight) found a citation of 'follow_up=T-4303' inside changelog.d/T-4299.md's own historical narrative text (T-4299's Done-report prose, verbatim-copied into the changelog fragment during T-4299's own land) and CHANGELOG.md's generated aggregate of it. Both are refused as LiveTrackerCited, with the stated remedy 'file a successor ticket and re-point the citing rows, or re-point them in this same change'. Neither remedy is reachable: both files are land-owned -- 'git commit' on either is refused outright ('CHANGELOG.md is land-owned (T-0731)' / 'changelog.d/T-4299.md is land-owned', both citing frob ticket land as the only writer) -- so no worktree, including T-4303's own, can ever edit them to re-point the citation, and 'file a successor' does not help either: a successor ticket's own id would just become a NEW live-tracker citation the moment it's mentioned, without ever clearing the original site's text. Practical effect: T-4303 -- the exact ticket whose own follow-up this citation names, the one ticket for which closing is the CORRECT and EXPECTED outcome -- cannot close through the normal path at all. Likely root cause: live_tracker_citations's regex-based scan does not distinguish a REAL, still-live directive (frob:waive ... follow_up="T-4303" in tracked source) from a HISTORICAL, already-resolved narrative mention of the same text pattern inside a changelog entry -- changelog prose routinely quotes a diff's own directives verbatim as part of describing what the diff did, which is exactly the false-positive shape here. Fix options: (1) exclude CHANGELOG.md/changelog.d/**/*.md from the scan entirely, matching their land-owned/generated-historical-record status (they are never a live directive, only ever a quotation of one); (2) require the match to be inside an actual frob:waive-shaped comment/registry-yaml line, not free-form markdown prose (the WAIVE006/WIRE002 machinery this preflight mirrors already parses real directives instead of grepping loosely); (3) give frob ticket close/land a documented override for a citation proven land-owned-unfixable. T-4303 worked around this by rewording the two citing lines in an UNCOMMITTABLE worktree edit (immediately reverted, since the land-owned refusal makes it pointless) and is otherwise blocked on this bug for a normal close.