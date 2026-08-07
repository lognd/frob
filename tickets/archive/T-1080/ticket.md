---
id: T-1080
title: 'tickets: T-0666 evidence names stale _not_detected variants that were renamed
  to _detected in tests/test_vet.py'
state: dropped
kind: bug
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tickets-archive.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
COV003 fires on main (independent of any in-progress worktree): T-0666's archived evidence in tickets-archive.md names tests/test_vet.py::TestCapabilityScanRustTaxonomyClosureResolution::test_struct_update_field_rebind_not_detected, TestCapabilityScanKotlinTaxonomyClosureResolution::test_destructuring_declaration_not_detected, and ::test_default_parameter_forwarding_callable_not_detected -- none of these resolve; the live tests are named test_struct_update_field_rebind_detected, test_destructuring_declaration_detected, and test_default_parameter_forwarding_callable_detected (opposite suffix). Fix the archived evidence ids to match the live test names, or waive COV003 with an honest reason if this is intentional historical drift.

## Drop reason
- 2026-07-28: premise stale: tickets-archive.md T-0666 evidence already names the _detected variants (verified at lines 70507-70530, 70714-70722, 114198-114322), not the _not_detected ones described; frob check --only coverage shows zero COV003 findings for T-0666 on current main