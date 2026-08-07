---
id: T-1078
title: land REL001 bump updates pyproject/CHANGELOG but can leave .frob-release.json
  version stale -- quartet desync makes every later land refuse on the T-0992 guard
state: done
kind: bug
origin: human
created: '2026-07-28'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land.py
- src/frob/release.py
- tests/test_ticket_land.py
- src/frob/release/__init__.py
- docs/modules/release.md
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/release/__init__.py
  reason: release.py is a package (actual module release/__init__.py); AFFECT001 doc
    anchors for set_manifest_version and _apply_release_bump
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/modules/release.md
  reason: release.py is a package (actual module release/__init__.py); AFFECT001 doc
    anchors for set_manifest_version and _apply_release_bump
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/modules/tickets.md
  reason: release.py is a package (actual module release/__init__.py); AFFECT001 doc
    anchors for set_manifest_version and _apply_release_bump
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_ticket_land.py::TestReleaseBumpQuartetAtomicity::test_manifest_version_written_same_step_as_pyproject
- tests/test_ticket_land.py::TestReleaseBumpQuartetAtomicity::test_incoherent_quartet_refusal_names_desync
designated_repro_test: null
acceptance:
- text: given a land whose REL001 bump succeeds, when the land commit is inspected,
    then .frob-release.json's version field equals pyproject.toml's version (quartet
    coherent) in that same commit
  evidence:
  - tests/test_ticket_land.py::TestReleaseBumpQuartetAtomicity::test_manifest_version_written_same_step_as_pyproject
- text: given a repo whose manifest version lags pyproject (the desync this ticket
    fixes), when frob ticket land runs, then the refusal message names the desync
    explicitly and points at frob release sync, instead of the bare monotonicity refusal
  evidence:
  - tests/test_ticket_land.py::TestReleaseBumpQuartetAtomicity::test_incoherent_quartet_refusal_names_desync
threat: null
component: null
---
Observed 2026-07-28 ~04:30: T-1073's land bumped pyproject/CHANGELOG to 0.211.0 but left .frob-release.json's version at 0.210.0. Every subsequent land then derived baseline 0.210.0 -> computed 0.211.0 -> refused on the T-0992 monotonicity guard against pyproject's 0.211.0 -- three lands (T-1075/T-1069/T-1072) blocked until the coordinator hand-reconciled the manifest (commit b7fa63d9) and ran frob release sync. T-1007 fixed the baseline DERIVATION side; this is the WRITE side: the bump callback (or land's finalize) must write the manifest version in the same atomic step as pyproject/CHANGELOG, and land's refusal diagnostics should detect an incoherent quartet and prescribe the sync.