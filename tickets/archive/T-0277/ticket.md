---
id: T-0277
title: Model src/frob/deploy in design/frob.strata self-model (SYS102)
state: done
kind: bug
origin: human
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant
designated_repro_test: null
threat: null
component: null
---
T-0257 added src/frob/deploy/ (frob deploy generate, DEPLOY001). design/frob.strata's self-model has no code/may declaration covering it, so tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant now fails with SYS102 unmodeled code src/frob/deploy. design/frob.strata was out of T-0257's declared scope (src/frob/deploy/**, src/frob/app/**, src/frob/__main__.py, src/frob/strata/**, docs/**, tests/**, tickets.md), so it was not touched there. Fix: add a code "src/frob/deploy/**" declaration (new node or extend the existing cli/stratamod node, whichever the reviewer of T-0257 judges architecturally correct) plus the may capabilities frob.vet's capability scan observes across that tree.