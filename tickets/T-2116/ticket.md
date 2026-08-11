---
id: T-2116
title: Add frob:doc anchor for detect_duplicate_ticket_id_collisions once docs/modules/tickets.md
  frees
state: queued
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
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
T-2105 added detect_duplicate_ticket_id_collisions (src/frob/tickets/_land_git_ops.py) as a public COV001-obligated symbol. docs/modules/tickets.md is this module's doc home but was under live-lease contention (T-1780's own subject) at fix time, so COV001 is waived there citing this ticket per the T-2003/T-1999 precedent (src/frob/tickets/_leases.py::is_effectively_in_progress). Add the frob:doc anchor once the file frees, and remove the waiver.