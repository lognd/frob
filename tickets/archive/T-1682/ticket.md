---
id: T-1682
title: Add a dedicated docs section for frob coverage (T-1516/T-1525)
state: done
kind: docs
origin: human
created: '2026-08-06'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/modules/testing.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
designated_repro_test: null
threat: null
component: null
---
`frob coverage` (T-1516/T-1525, touched-set incremental coverage.xml
refresh) exists in the CLI verb tree and docs/modules/cli.md's verb
table, but has no dedicated ## section of its own describing its flags
and behavior -- the only substantive prose about it is a passing aside
inside docs/modules/testing.md (~line 440) about `make coverage-fast`'s
own delegation to it, not about the command itself.

Found during T-1610's docs completeness sweep
(docs/audits/docs-completeness-2026-08-06.md item 3). Every other
top-level verb of comparable weight (frob clean, frob vet, frob release)
has its own module-doc section; this one should too. Read the actual CLI
wiring in src/frob/_cli_parsers/** and native_coverage_refresh's
implementation before writing it, to avoid a stale/guessed description.