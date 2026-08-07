---
id: T-0081
title: 'strata self-hosting: design/frob.strata models frob itself'
state: done
kind: feature
origin: human
created: '2026-07-17'
priority: medium
blocked_by:
- T-0052
parent: T-0053
tier: ticket
sprint: null
scope:
- design/**
- frob.toml
- src/frob/vet/_registry.py
- src/frob/app/ticket_runner.py
- docs/strata/roadmap.md
- tests/system/test_frob_self_model.py
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_parses_and_elaborates
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_every_claim_proves
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations
designated_repro_test: null
threat: null
component: null
---
frob declares its own components (lang/graph/gates/tickets/check), trust levels, and module-dependency architecture in strata and gates on it. Phase-4 exit criterion; supersedes the informal docs/rework.md dependency diagram as enforced truth.

Scope extended beyond the original `design/**, frob.toml` during
implementation: proving `frob check --only sys` gates on the model at
zero violations required a couple of real `frob:channel`/`frob:boundary`
code anchors (`src/frob/vet/_registry.py`, `src/frob/app/ticket_runner.py`),
a CI-locking system test (`tests/system/test_frob_self_model.py`), and the
roadmap doc update -- all explicitly called for by this ticket's own
dispatch instructions.
## Done report

design/frob.strata models frob itself: 10 nodes (8 roadmap components
+ tickets ledger store + graph cache), 27 flows every one derived from
real cross-package imports, 1 boundary, 3 claims all PROVED (registry
noflow to ledger, cache age bound, gates reach tickets). Reviewer
spot-verified 8 flows against real imports, confirmed 3 candidate
omissions genuinely absent, and ran the negative check (synthetic
registry->ledger flow flips the claim to REFUTED -- load-bearing, not
vacuous). Two sparse directives anchor the vet endorsement boundary
and the cli->tickets channel. CI-locked by a 4-test system suite.
Grammar gap filed as T-0132 (code=/may unreachable from surface text).
Landing surfaced two integration incidents fixed alongside: the
standalone tool crashed on the hard strata_core import (guarded,
T-0133 tracks bundling; global tool now installed --with both crates)
and three DOC002 anchor mismatches got explicit anchors. Verified at
close: frob check exit 0 with the bundled tool, self-model suite 4/4.