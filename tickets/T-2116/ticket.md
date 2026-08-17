---
id: T-2116
title: Add frob:doc anchor for detect_duplicate_ticket_id_collisions once docs/modules/tickets.md
  frees
state: done
kind: docs
origin: human
created: '2026-08-11'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- docs/modules/tickets.md
- src/frob/tickets/_land_git_ops.py
evidence_scope:
- tests/unit/test_land_duplicate_ticket_id.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: docs/modules/tickets.md
  reason: 'T-1780: docs/modules/tickets.md was split by subject; this ticket''s own
    touched code lives in the lifecycle cluster (filing, review, scope/lease), so
    its scope now names docs/modules/tickets-lifecycle.md instead of the monofile
    every other unrelated ticket also held a lease on'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: docs/modules/tickets-lifecycle.md
  reason: 'T-1780: docs/modules/tickets.md was split by subject; this ticket''s own
    touched code lives in the lifecycle cluster (filing, review, scope/lease), so
    its scope now names docs/modules/tickets-lifecycle.md instead of the monofile
    every other unrelated ticket also held a lease on'
  actor: logan
  at: '2026-08-16'
- op: remove
  glob: docs/modules/tickets-lifecycle.md
  reason: T-1780 split docs/modules/tickets.md into subject files after this ticket
    was filed; the doc home for the Public API reference (where this anchor belongs)
    is docs/modules/tickets.md itself, not tickets-lifecycle.md; also need to touch
    the source file to remove the now-satisfied COV001 waiver
  actor: logan
  at: '2026-08-17'
- op: add
  glob: docs/modules/tickets.md
  reason: T-1780 split docs/modules/tickets.md into subject files after this ticket
    was filed; the doc home for the Public API reference (where this anchor belongs)
    is docs/modules/tickets.md itself, not tickets-lifecycle.md; also need to touch
    the source file to remove the now-satisfied COV001 waiver
  actor: logan
  at: '2026-08-17'
- op: add
  glob: src/frob/tickets/_land_git_ops.py
  reason: T-1780 split docs/modules/tickets.md into subject files after this ticket
    was filed; the doc home for the Public API reference (where this anchor belongs)
    is docs/modules/tickets.md itself, not tickets-lifecycle.md; also need to touch
    the source file to remove the now-satisfied COV001 waiver
  actor: logan
  at: '2026-08-17'
evidence:
- tests/unit/test_land_duplicate_ticket_id.py::TestDetectDuplicateTicketIdCollisions::test_ignores_the_landing_tickets_own_id
- tests/unit/test_land_duplicate_ticket_id.py::TestDetectDuplicateTicketIdCollisions::test_ignores_identical_content_on_both_sides
- tests/unit/test_land_duplicate_ticket_id.py::TestDetectDuplicateTicketIdCollisions::test_ignores_an_id_that_already_existed_at_the_merge_base
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: f05d6ae9da2dcac5063858e3ca8b2a11d85494c3
---
T-2105 added detect_duplicate_ticket_id_collisions (src/frob/tickets/_land_git_ops.py) as a public COV001-obligated symbol. docs/modules/tickets.md is this module's doc home but was under live-lease contention (T-1780's own subject) at fix time, so COV001 is waived there citing this ticket per the T-2003/T-1999 precedent (src/frob/tickets/_leases.py::is_effectively_in_progress). Add the frob:doc anchor once the file frees, and remove the waiver.