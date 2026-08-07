---
id: T-0804
title: 'gates: rebind T-0580''s four frob:deprecated directives off the now-closed
  T-0580 (DEPR002)'
state: dropped
kind: bug
origin: human
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/xref_runner.py
- src/frob/app/outline_runner.py
- src/frob/app/docs_runner.py
- src/frob/app/map_runner.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
found while working T-0797 (registering the deprecated gate in _ALL_GATES). T-0580 deprecated the four navigation commands (map/outline/xref/docs-search) with frob:deprecated ticket=T-0580, but T-0580 itself is now closed/done -- so a real frob check --only deprecated run reports DEPR002 (bound to a non-open ticket) on all four, not the DEPR003 in-window warning the T-0797 dispatch predicted. Rebind each directive's ticket= to a new open removal-tracking ticket (or reopen/track differently) so the sunset lifecycle is enforceable again.

## Drop reason
- 2026-07-23: absorbed: rebind folded into T-0797 land (absorbed by T-0797)