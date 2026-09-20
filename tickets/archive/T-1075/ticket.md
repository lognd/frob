---
id: T-1075
title: wire env.read/env.write tier-2 join (_KIND_MAP + WIRED_MODE_FAMILIES)
state: done
kind: feature
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/strata/_effects.py
- src/frob/vet/_capability_modes.py
- src/frob/strata/_selfconform.py
- src/frob/strata/_threat.py
- tests/unit/strata/test_selfconform.py
- tests/unit/strata/test_effects.py
- tests/unit/strata/test_threat.py
- tests/unit/vet/test_capability_modes.py
- src/frob/vet/_capability_registry.py
- tests/test_capability_registry.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/strata/_selfconform.py
  reason: removing _UNWIRED_ENV_MODE_ALIASES's transitional fold is the point of this
    ticket's tier-2 join, per the ticket's own plan point 2
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/strata/_threat.py
  reason: 'T-0771 mandate point 2 / ticket plan point 3: sweep DEFAULT_BENIGN_CAPABILITIES/CWE_CATALOG
    for env.read/env.write entries the new join requires'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/unit/strata/test_selfconform.py
  reason: existing litmus tests for _EXTENDED_KINDS/_KIND_MAP that this ticket's env
    wiring changes
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/unit/strata/test_effects.py
  reason: existing litmus tests for _KIND_MAP this ticket extends
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/unit/strata/test_threat.py
  reason: existing litmus tests for DEFAULT_BENIGN_CAPABILITIES this ticket extends
    with env.read/env.write
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/unit/vet/test_capability_modes.py
  reason: existing litmus tests for WIRED_MODE_FAMILIES this ticket extends
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/vet/_capability_registry.py
  reason: CAPABILITY_KINDS must register the new mode-qualified env.read/env.write
    spellings DEFAULT_BENIGN_CAPABILITIES now excuses, mirroring net.connect/net.listen's
    own T-0771 registration
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/test_capability_registry.py
  reason: existing litmus tests for CAPABILITY_KINDS this ticket extends
  actor: logan
  at: '2026-07-28'
body_changes:
- mode: append
  reason: 'T-4718 sweep: move narrative out of over-length comment run in _capability_modes.py'
  actor: logan
  at: '2026-09-19'
  old_length: 759
  new_length: 1843
evidence:
- tests/unit/vet/test_capability_modes.py::TestExpandDeclaredKind::test_coarse_env_covers_union_of_modes
- tests/unit/strata/test_effects.py::TestDeployServeMutateNodeSplitConformance::test_mutate_declares_every_real_effect_it_exercises
- tests/unit/strata/test_selfconform.py::TestExtendedKindsDriftLock::test_extended_kinds_is_disjoint_from_kind_map
- tests/test_capability_registry.py::TestMatrixExhaustiveness::test_no_unexcused_empty_cells
- tests/test_capability_registry.py::TestValidateRegistryKinds::test_every_threat_catalog_kind_is_registered
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-0771 gave env a real read-vs-write needle split (frob.vet._capability_registry env-read/env-write, per language) but deliberately left env OUT of WIRED_MODE_FAMILIES and _effects.py::_KIND_MAP -- env has no tier-2 (THREAT004/SYS100/SYS101) may-declaration join at all today, so there is nothing to feed. This ticket: (1) decide whether env gets its own THREAT004-delegated join like net/fs, or stays a SYS100-extended-only kind; (2) if wired, add env-read/env-write to _KIND_MAP and WIRED_MODE_FAMILIES, remove _selfconform.py's _UNWIRED_ENV_MODE_ALIASES transitional fold; (3) sweep frob.strata._threat.DEFAULT_BENIGN_CAPABILITIES / CWE_CATALOG for any env.read/env.write entries the new join would require (T-0717 mandate point 2's sweep, applied to env).

T-4718 sweep (condensed from src/frob/vet/_capability_modes.py:159-172,
trimmed for DOCARCH002's 12-line cap): the trimmed block's full original
text, kept verbatim below.

#: Families whose mode split is WIRED into a live join this pass (module
#: docstring's "wiring status"): `expand_declared_kind`/`normalize_
#: observed_kind` only ever explode a bare family name from THIS set into
#: its `FAMILY_MODES` union -- a family present in `FAMILY_MODES` but NOT
#: here (proc/ffi today) has its vocabulary DEFINED but its
#: scanner/declaration join still coarse (a bare `may "proc"` stays exactly
#: `{"proc"}`, never silently exploded into a mode set that no
#: scanner-observed kind could ever match, which would make every
#: existing bare `may "proc"` declaration spuriously go SYS101-stale).
#: T-1075 adds `env` (module docstring's wiring-status update): env-read/
#: env-write now has a real tier-2 join (`_effects.py::_KIND_MAP`), so a
#: coarse `may "env"` declaration can safely explode too. Extending this
#: set further (`proc`/`ffi`) is the next sibling ticket's job.