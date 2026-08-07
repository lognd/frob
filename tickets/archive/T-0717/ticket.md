---
id: T-0717
title: 'capability taxonomy: mode-qualified names (fs.read/fs.write, net.connect/net.listen),
  one vocabulary with T-0700 modes, deprecated-alias migration'
state: done
kind: security
origin: human
created: '2026-07-22'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/vet/**
- src/frob/strata/**
- docs/design/registry/**
- docs/strata/**
- tests/unit/vet/**
- tests/unit/strata/test_effects.py
- tests/unit/strata/test_selfconform.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/vet/**
  reason: T-0717's new capability-mode vocabulary lives in src/frob/vet/_capability_modes.py;
    its own unit tests need a home, and tests/unit/vet/ did not exist yet
  actor: logan
  at: '2026-07-22'
- op: add
  glob: tests/unit/strata/test_effects.py
  reason: existing SYS100/THREAT004 tests assert the old ambiguous fs-kind spelling
    and need updating; new legacy-alias/mode-precision tests belong alongside them
  actor: logan
  at: '2026-07-22'
- op: add
  glob: tests/unit/strata/test_selfconform.py
  reason: existing SYS100/SYS101 tests assert the old fs-kind spelling; new fs.read
    narrow-discharge acceptance test belongs alongside them
  actor: logan
  at: '2026-07-22'
evidence:
- tests/unit/vet/test_capability_modes.py::TestModeQualified::test_joins_family_and_mode
- tests/unit/vet/test_capability_modes.py::TestModeQualified::test_capability_mode_kinds_includes_fs_read_write
- tests/unit/vet/test_capability_modes.py::TestExpandDeclaredKind::test_precise_kind_covers_only_itself
- tests/unit/vet/test_capability_modes.py::TestExpandDeclaredKind::test_coarse_fs_covers_union_of_modes
- tests/unit/vet/test_capability_modes.py::TestExpandDeclaredKind::test_unwired_family_stays_coarse
- tests/unit/vet/test_capability_modes.py::TestExpandDeclaredKind::test_kind_with_no_modes_defined_stays_itself
- tests/unit/vet/test_capability_modes.py::TestResolveCapabilityKind::test_precise_kind_passes_through
- tests/unit/vet/test_capability_modes.py::TestResolveCapabilityKind::test_coarse_family_is_never_deprecated
- tests/unit/vet/test_capability_modes.py::TestResolveCapabilityKind::test_legacy_alias_in_window_resolves_and_warns
- tests/unit/vet/test_capability_modes.py::TestResolveCapabilityKind::test_legacy_alias_past_sunset_is_gate_error
- tests/unit/vet/test_capability_modes.py::TestResolveCapabilityKind::test_sunset_date_itself_is_already_expired
- tests/unit/vet/test_capability_modes.py::TestCanonicalAndNormalize::test_canonical_declared_kind_resolves_alias_regardless_of_sunset
- tests/unit/vet/test_capability_modes.py::TestCanonicalAndNormalize::test_normalize_observed_kind_matches_canonical
- tests/unit/strata/test_effects.py::TestModeQualifiedFsConformance::test_fs_read_declaration_discharges_read_only_code
- tests/unit/strata/test_effects.py::TestModeQualifiedFsConformance::test_fs_read_declaration_fails_conformance_on_a_write
- tests/unit/strata/test_effects.py::TestLegacyCapabilityAliases::test_legacy_alias_in_window_is_a_warning_not_an_error
- tests/unit/strata/test_effects.py::TestLegacyCapabilityAliases::test_legacy_alias_past_sunset_is_an_error
- tests/unit/strata/test_effects.py::TestLegacyCapabilityAliases::test_non_legacy_declaration_is_not_flagged
- tests/unit/strata/test_selfconform.py::TestModeQualifiedFsStaleDesign::test_fs_read_declaration_discharges_on_read_only_code
- tests/unit/strata/test_selfconform.py::TestModeQualifiedFsStaleDesign::test_fs_read_declaration_stays_stale_when_only_writes_observed
designated_repro_test: null
acceptance:
- text: GIVEN a node whose code only reads files WHEN it declares may fs.read THEN
    SYS101 discharges narrowly and a write observation fails conformance; GIVEN a
    legacy may fs declaration THEN it works with a deprecation warning naming the
    sunset and migration target; GIVEN the alias sunset passes THEN legacy spellings
    are gate errors
  evidence:
  - tests/unit/strata/test_effects.py::TestModeQualifiedFsConformance::test_fs_read_declaration_discharges_read_only_code
  - tests/unit/strata/test_effects.py::TestModeQualifiedFsConformance::test_fs_read_declaration_fails_conformance_on_a_write
  - tests/unit/strata/test_effects.py::TestLegacyCapabilityAliases::test_legacy_alias_in_window_is_a_warning_not_an_error
  - tests/unit/strata/test_effects.py::TestLegacyCapabilityAliases::test_legacy_alias_past_sunset_is_an_error
threat: null
component: null
---
User mandate 2026-07-22: capability names conflate mode -- measured in src/frob/vet/_capability_registry.py: scanner emits fs-write, _KIND_MAP normalizes it to bare fs for the may vocabulary, fs-read was added later as a separate kind, and SYS101 backward-compatibly satisfies bare may-fs with EITHER observed kind -- so fs is ambiguous (write-derived history, read-satisfiable present). net has no mode split at all. DESIGN MANDATE (think the declarations through, do not just rename): (1) ONE mode vocabulary shared with T-0700's resource modes (read|append|alpha|write|exclusive where meaningful) -- capability families get family.mode ids: fs.read/fs.append/fs.write, net.connect/net.listen, env.read/env.write, proc.spawn, ffi.call...; not every family has every mode (define each family's valid mode set explicitly). (2) COARSE DECLARATIONS STAY LEGAL, INTERPRETED FAIL-CLOSED: may fs means the UNION of fs modes for obligation purposes (a coarse declarer answers for everything), while observed effects always map to the most precise mode; conformance = observed subset-of declared; precision is rewarded (narrower declarations discharge narrower obligations) never required by fiat. (3) MIGRATION: alias table old->new; old spellings keep working but carry frob:deprecated (T-0576 machinery -- sunset date, ticket) so they warn now and error at sunset; mechanical sweep of this repo's .strata models, DEFAULT_BENIGN_CAPABILITIES, registry yamls; ESTATE: the 8 sibling repos' declarations migrate via fleet-routed per-repo tickets (T-0573 routing) -- file them at close, do not hand-edit siblings from here. (4) SYS101's either-satisfies compatibility join becomes an explicit alias-table lookup, not a special case, and dies with the aliases at sunset. Coordinate: T-0701 mode-conformance consumes this vocabulary; T-0339 resolvers classify into it; do not fork a second mode enum anywhere (no-duplication rule).