---
id: T-3006
title: 'Multi-modal strata redesign: behaviour/implementation/configuration split,
  VHDL entity-architecture model (T-3004 section 5)'
state: in-progress
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
- strata-core/src/parse/**
- tests/unit/strata/entity_arch/**
- docs/strata/entity_architecture.md
- tests/unit/test_lang_strata_entity_arch.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: strata-core/src/parse/**
  reason: 'Entity/architecture/configuration redesign (T-3004 section 5): new grammar

    constructs live in strata-core''s parser and a small worked-example fixture

    plus docs. Kept narrow deliberately -- no gates/_sys.py or gates/__init__.py

    (owned by a concurrent live agent this session), no ticket-ledger migration

    (deferred by the epic), no cross-file entity resolution (single-file scope

    for this first slice).

    '
  actor: logan
  at: '2026-08-26'
- op: add
  glob: design/entity_arch/**
  reason: 'Entity/architecture/configuration redesign (T-3004 section 5): new grammar

    constructs live in strata-core''s parser and a small worked-example fixture

    plus docs. Kept narrow deliberately -- no gates/_sys.py or gates/__init__.py

    (owned by a concurrent live agent this session), no ticket-ledger migration

    (deferred by the epic), no cross-file entity resolution (single-file scope

    for this first slice).

    '
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/unit/strata/entity_arch/**
  reason: 'Entity/architecture/configuration redesign (T-3004 section 5): new grammar

    constructs live in strata-core''s parser and a small worked-example fixture

    plus docs. Kept narrow deliberately -- no gates/_sys.py or gates/__init__.py

    (owned by a concurrent live agent this session), no ticket-ledger migration

    (deferred by the epic), no cross-file entity resolution (single-file scope

    for this first slice).

    '
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/strata/entity_architecture.md
  reason: 'Entity/architecture/configuration redesign (T-3004 section 5): new grammar

    constructs live in strata-core''s parser and a small worked-example fixture

    plus docs. Kept narrow deliberately -- no gates/_sys.py or gates/__init__.py

    (owned by a concurrent live agent this session), no ticket-ledger migration

    (deferred by the epic), no cross-file entity resolution (single-file scope

    for this first slice).

    '
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/unit/test_lang_strata_entity_arch.py
  reason: 'Entity/architecture/configuration redesign (T-3004 section 5): new grammar

    constructs live in strata-core''s parser and a small worked-example fixture

    plus docs. Kept narrow deliberately -- no gates/_sys.py or gates/__init__.py

    (owned by a concurrent live agent this session), no ticket-ledger migration

    (deferred by the epic), no cross-file entity resolution (single-file scope

    for this first slice).

    '
  actor: logan
  at: '2026-08-26'
- op: remove
  glob: design/entity_arch/**
  reason: moved worked-example fixtures under tests/unit/strata/entity_arch instead
    -- design/ is rglob-scanned live by frob check sys stages against the real repo,
    and a fixture with a nonexistent code= path would pollute that floor
  actor: logan
  at: '2026-08-26'
triage_changes:
- field: parent
  old_value: null
  new_value: T-3004
  reason: T-3004 decomposition per the owner design decision
  actor: logan
  at: '2026-08-26'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
