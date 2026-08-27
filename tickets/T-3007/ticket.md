---
id: T-3007
title: 'V-model spec graph as strata instances: requirement/spec/design/component
  nodes with paired verification levels (T-3004 sections 1-2)'
state: done
kind: feature
origin: human
created: '2026-08-26'
priority: high
parent: T-3004
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- strata-core/src/graph/vmodel.rs
- strata-core/src/graph/mod.rs
- strata-core/src/lib.rs
- strata-core/Cargo.toml
- docs/strata/graph.md
- docs/strata/vmodel.md
- docs/strata/kernel.md
evidence_scope:
- tests/unit/strata/test_parse.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: strata-core/src/graph/vmodel.rs
  reason: 'T-3007: V-model schema+closure rules as a strata-core graph consumer, plus
    the PyO3 surface it needs'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: strata-core/src/graph/mod.rs
  reason: 'T-3007: V-model schema+closure rules as a strata-core graph consumer, plus
    the PyO3 surface it needs'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: strata-core/src/lib.rs
  reason: 'T-3007: V-model schema+closure rules as a strata-core graph consumer, plus
    the PyO3 surface it needs'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: strata-core/Cargo.toml
  reason: 'T-3007: V-model schema+closure rules as a strata-core graph consumer, plus
    the PyO3 surface it needs'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/strata/graph.md
  reason: 'T-3007: V-model schema+closure rules as a strata-core graph consumer, plus
    the PyO3 surface it needs'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/strata/vmodel.md
  reason: 'T-3007: V-model schema+closure rules as a strata-core graph consumer, plus
    the PyO3 surface it needs'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/strata/kernel.md
  reason: 'AFFECT001: strata_core pymodule fn touched, its affects-closure doc is
    docs/strata/kernel.md#strata-core'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/strata/kernel.md
  reason: 'AFFECT001: strata_core pymodule fn touched, its affects-closure doc is
    docs/strata/kernel.md#strata-core'
  actor: logan
  at: '2026-08-26'
triage_changes:
- field: parent
  old_value: null
  new_value: T-3004
  reason: T-3004 decomposition per the owner design decision
  actor: logan
  at: '2026-08-26'
evidence:
- tests/unit/strata/test_parse.py::TestParseModule::test_parses_bare_module
- tests/unit/strata/test_parse.py::TestParseModule::test_round_trip_small_design
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
