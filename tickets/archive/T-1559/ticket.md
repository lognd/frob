---
id: T-1559
title: 'land/close guard: refuse or auto-migrate open frob:waive directives bound
  to the closing ticket (WIRE002 orphan prevention)'
state: done
kind: feature
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_live_tracker.py
- tests/test_tickets_live_tracker.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_live_tracker.py
  reason: 'T-1559: extend the existing T-0854 live-tracker-citation preflight (already
    wired into close+land) to WIRE001''s follow_up= binding'
  actor: logan
  at: '2026-08-05'
- op: add
  glob: tests/test_tickets_live_tracker.py
  reason: 'T-1559: extend the existing T-0854 live-tracker-citation preflight (already
    wired into close+land) to WIRE001''s follow_up= binding'
  actor: logan
  at: '2026-08-05'
- op: add
  glob: docs/modules/tickets.md
  reason: 'T-1559: extend the existing T-0854 live-tracker-citation preflight (already
    wired into close+land) to WIRE001''s follow_up= binding'
  actor: logan
  at: '2026-08-05'
evidence:
- tests/test_tickets_live_tracker.py::TestLiveTrackerCitations::test_finds_comment_waiver_follow_up_attribute
designated_repro_test: null
acceptance:
- text: GIVEN a ticket close/land WHEN any frob:waive directive in the repo names
    the closing ticket id THEN the close refuses with the waiver list and the exact
    rebind command, OR a Tier-A auto-fix rebinds them to a named open successor --
    closing a waiver-bound ticket can never silently red main again
  evidence:
  - tests/test_tickets_live_tracker.py::TestLiveTrackerCitations::test_finds_comment_waiver_follow_up_attribute
- text: GIVEN the guard fires THEN the refusal message names each waiver file:line
    and the successor-ticket flag to pass
  evidence:
  - tests/test_tickets_live_tracker.py::TestLiveTrackerCitations::test_finds_comment_waiver_follow_up_attribute
threat: null
component: null
---
2026-08-05 incident: T-1490/T-1488 landed and closed while 16 frob:waive WIRE001 directives bound them; the next full check showed 16 WIRE002 errors on main with no gate having warned at close time. The WIRE002 rule (waivers must bind an open ticket) is only enforced at check time, after the close already happened. Tier-A auto-fix family (T-1544..T-1549 precedent).