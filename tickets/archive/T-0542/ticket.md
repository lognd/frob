---
id: T-0542
title: 'gates: COV002 satisfied by ANY open ticket whose scope glob covers the file
  (B10)'
state: done
kind: bug
origin: auditor
created: '2026-07-21'
priority: medium
parent: T-0403
tier: ticket
sprint: null
scope:
- src/frob/gates/
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestCov002ScopeCoverage::test_open_ticket_scope_covers_changed_symbol
- tests/test_gates.py::TestCov002ScopeCoverage::test_ambiguous_overlapping_open_scopes_do_not_cover
- tests/test_gates.py::TestCov002ScopeCoverage::test_active_ticket_own_scope_wins_over_a_broader_open_ticket
designated_repro_test: null
threat: null
component: null
---
docs/audits/gates-accounting.md B10. _cov002 uses _open_scopes = every open ticket's scope glob, matched via _scope_covers against ANY of them. One broad-scope open ticket (e.g. src/frob/**) makes every changed symbol under it accounted for regardless of relation to that ticket. Fix direction: prefer the ACTIVE ticket's own scope first, and require a narrower/more-specific glob match (or an explicit frob:ticket edge) when multiple open tickets' scopes could cover the same file, rather than accepting the first match found.