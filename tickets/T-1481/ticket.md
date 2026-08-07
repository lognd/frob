---
id: T-1481
title: wire frob check --fix CLI flag to the tiered fix engine
state: queued
kind: feature
origin: human
created: '2026-08-03'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/_cli_parsers/_check.py
- src/frob/app/check_runner.py
- docs/design/check-fix-engine.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
docs/design/check-fix-engine.md's "Status quo" section states
apply_tier_a_fixes has no CLI entry point: src/frob/app/check_runner.py
and src/frob/_cli_parsers/_check.py have no --fix/Fix reference, so
`frob check --fix` does not exist as a runnable command. Wire a --fix
flag through _cli_parsers/_check.py and check_runner.py that invokes
apply_tier_a_fixes (and, once T-1262/T-1263 land, the Tier-B/Tier-C
paths). Found while draining NEGEXIST001 (T-1477): the doc's
absence-claim had no frob:until binding.