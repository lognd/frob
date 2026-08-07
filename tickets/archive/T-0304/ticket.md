---
id: T-0304
title: 'vet capability scanner: fs-read/fs-write split for read-only nodes (graphite
  T-0018)'
state: done
kind: feature
origin: agent
created: '2026-07-19'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/vet/_capability_registry.py
- src/frob/strata/_selfconform.py
- src/frob/strata/_threat.py
- design/frob.strata
- docs/strata/selfconform.md
- docs/modules/vet.md
- tests/unit/strata/test_selfconform.py
- tests/test_capability_registry.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_selfconform.py::TestStaleDesign::test_legacy_fs_declaration_discharges_on_read_only_observation
- tests/unit/strata/test_selfconform.py::TestStaleDesign::test_fs_read_declaration_discharges_on_read_only_observation
- tests/unit/strata/test_selfconform.py::TestStaleDesign::test_fs_read_declaration_stays_stale_when_only_writes_observed
- tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant
designated_repro_test: null
acceptance:
- text: A new fs-read capability kind is patterned in python/typescript/rust/c-cpp,
    added to _EXTENDED_KINDS, and given a DEFAULT_BENIGN_CAPABILITIES excuse
  evidence: []
- text: A pre-existing bare may 'fs' declaration is not marked SYS101-stale when only
    fs-read (read-only) observations exist; a node declaring may 'fs-read' specifically
    stays stale if only writes are observed
  evidence: []
threat: null
component: null
---
graphite's frob-adoption sweep found SYS101 firing 'declared but never observed' for a node node core declaring may 'fs' for genuinely-real read-only access (Path.read_text()/json.loads(), no writes) -- the scanner only ever emitted the write-derived fs kind. Adds a distinct fs-read kind plus a one-directional backward-compat alias (_alias_legacy_fs_observations) so a pre-existing bare 'fs' declaration is not called stale by a read-only observation, while a node declaring 'fs-read' specifically gets the honest, narrower signal.