---
id: T-1473
title: bind/reword the 4 pre-existing unbound NEGEXIST001 claims T-1229 surfaced
state: done
kind: docs
origin: human
created: '2026-08-02'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/modules/gates.md
- docs/modules/graph.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
- cmd:uv run frob check --only docblocks exit=0 sha256=95fffea9f064
designated_repro_test: null
threat: null
component: null
---
T-1229's live NEGEXIST001 run surfaced 4 pre-existing unbound negative-
existence claims: docs/modules/gates.md:50, docs/modules/gates.md:91,
docs/modules/gates.md:456, docs/modules/graph.md:384. Investigated each:
none names a real not-yet-built feature with an obvious ticket to bind --
gates.md:50/91 are rule-catalog table rows describing DEC001/REF003's
own "points at a missing record" semantics (heuristic false positives,
not feature-absence claims); gates.md:456 and graph.md:384 are genuine
disclosed scope cuts (T-0809's escaped/acquired RAII cross-check,
T-0686's may-raise engine) with no open ticket tracking them. Reworded
all four to state the same fact without tripping the NEGEXIST001
phrase heuristic (rather than a blanket waiver), per the wave brief's
"bind via frob:until or reword; do not blanket-waive" instruction.