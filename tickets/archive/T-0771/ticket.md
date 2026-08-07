---
id: T-0771
title: 'capability taxonomy: wire net/env/proc/ffi mode split + sibling-repo migration
  (T-0717 follow-up)'
state: done
kind: feature
origin: human
created: '2026-07-22'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/vet/**
- src/frob/strata/**
- docs/design/registry/**
- docs/strata/**
- tests/test_capability_registry.py
- tests/test_vet.py
- tests/unit/vet/test_capability_modes.py
- tests/unit/strata/test_effects.py
- tests/unit/strata/test_selfconform.py
- tests/unit/strata/test_threat.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_capability_registry.py
  reason: T-0771 net-connect/net-listen + env-read/env-write reclassification and
    net's WIRED_MODE_FAMILIES join break existing fixtures/assertions bound to the
    old bare-net/bare-env behavior in these files -- structurally necessary follow-through,
    not scope creep (docs/modules/tickets.md accountable SCOPE001 replacement)
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/test_vet.py
  reason: T-0771 net-connect/net-listen + env-read/env-write reclassification and
    net's WIRED_MODE_FAMILIES join break existing fixtures/assertions bound to the
    old bare-net/bare-env behavior in these files -- structurally necessary follow-through,
    not scope creep (docs/modules/tickets.md accountable SCOPE001 replacement)
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/unit/vet/test_capability_modes.py
  reason: T-0771 net-connect/net-listen + env-read/env-write reclassification and
    net's WIRED_MODE_FAMILIES join break existing fixtures/assertions bound to the
    old bare-net/bare-env behavior in these files -- structurally necessary follow-through,
    not scope creep (docs/modules/tickets.md accountable SCOPE001 replacement)
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/unit/strata/test_effects.py
  reason: T-0771 net-connect/net-listen + env-read/env-write reclassification and
    net's WIRED_MODE_FAMILIES join break existing fixtures/assertions bound to the
    old bare-net/bare-env behavior in these files -- structurally necessary follow-through,
    not scope creep (docs/modules/tickets.md accountable SCOPE001 replacement)
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/unit/strata/test_selfconform.py
  reason: T-0771 net-connect/net-listen + env-read/env-write reclassification and
    net's WIRED_MODE_FAMILIES join break existing fixtures/assertions bound to the
    old bare-net/bare-env behavior in these files -- structurally necessary follow-through,
    not scope creep (docs/modules/tickets.md accountable SCOPE001 replacement)
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/unit/strata/test_threat.py
  reason: T-0771 net-connect/net-listen + env-read/env-write reclassification and
    net's WIRED_MODE_FAMILIES join break existing fixtures/assertions bound to the
    old bare-net/bare-env behavior in these files -- structurally necessary follow-through,
    not scope creep (docs/modules/tickets.md accountable SCOPE001 replacement)
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_capability_registry.py::TestMatrixExhaustiveness::test_no_unexcused_empty_cells
- tests/test_capability_registry.py::TestValidateRegistryKinds::test_known_kinds_pass
- tests/unit/strata/test_effects.py::TestLegacyCapabilityAliases::test_legacy_alias_in_window_is_a_warning_not_an_error
- tests/unit/strata/test_effects.py::TestNodeMayKinds::test_kinds
- tests/unit/strata/test_selfconform.py::TestExtendedKindsDriftLock::test_observed_all_kinds_by_node_normalizes_through_kind_map
- tests/unit/strata/test_selfconform.py::TestExtendedKindsDriftLock::test_observed_extended_kinds_by_node_only_ever_yields_extended_kinds
- tests/unit/vet/test_capability_modes.py::TestExpandDeclaredKind::test_coarse_net_covers_union_of_modes
- tests/unit/vet/test_capability_modes.py::TestExpandDeclaredKind::test_unwired_family_stays_coarse
designated_repro_test: null
threat: null
component: null
---
T-0717 shipped the shared mode-qualified capability vocabulary
(frob.vet._capability_modes: FAMILY_MODES, CAPABILITY_MODE_KINDS,
LEGACY_CAPABILITY_ALIASES, resolve_capability_kind/expand_declared_kind/
canonical_declared_kind/normalize_observed_kind) and wired it live for the
fs family only (fs.read/fs.write, WIRED_MODE_FAMILIES={"fs"}) -- the one
family the acceptance tests exercised. net.connect/net.listen,
env.read/env.write, proc.spawn, and ffi.call are DEFINED in FAMILY_MODES
but deliberately NOT exploded by expand_declared_kind/normalize_observed_
kind yet (a bare may "net" stays exactly {"net"}), because the vet
scanner has no connect/listen (or env-read/write, proc, ffi-call)
distinction to normalize observations against -- exploding the
declaration side without a matching observation side would make every
existing bare "net"/"env"/etc. declaration spuriously SYS101-stale.

Follow-up work, explicitly not done in T-0717:
1. Extend frob.vet._capability's per-language needle tables with a real
   connect-vs-listen split for net (e.g. socket.connect vs socket.bind+
   listen; net.connect vs net.listen in TS/Rust equivalents), and an
   env read-vs-write split, before adding those families to
   WIRED_MODE_FAMILIES.
2. Mechanical sweep of this repo's own design/frob.strata declarations
   and DEFAULT_BENIGN_CAPABILITIES (src/frob/strata/_threat.py) once a
   family is wired, mirroring what T-0717 did for fs (BenignCapability
   entries + CAPABILITY_KINDS registration would be needed for fs.read/
   fs.write too if any node ever declares them precisely -- currently
   design/frob.strata only uses the still-legal coarse "fs"/"fs-read"
   spellings, so this was deferred).
3. ESTATE migration (mandate point 3): once net/env/proc/ffi are wired,
   file per-repo tickets (T-0573 fleet routing) for the 8 sibling repos'
   own capability declarations to adopt the precise family.mode spellings
   ahead of the T-0717 alias sunset (fs-write/fs-read, 2026-10-20).