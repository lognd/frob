---
id: T-2397
title: Wire find_dropped_cli_flags into frob check as a gate (T-2387 visibility gap)
state: in-progress
kind: bug
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/check/**
- docs/modules/gates.md
- src/frob/gates/_flag_coverage.py
- src/frob/gates/_docblocks_shared.py
- src/frob/gates/_docblocks_refs.py
- src/frob/gates/_waive.py
- src/frob/gates/__init__.py
- src/frob/check/__init__.py
- frob.toml
- tests/unit/test_flag_coverage_gate.py
- docs/design/registry/check-coverage.yaml
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/gates/**
  reason: 'narrowing the umbrella glob to the actual files this gate touches: new
    gate module + shared resolver + registration + this repo self-declaration + docs
    + tests'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/gates/_flag_coverage.py
  reason: 'narrowing the umbrella glob to the actual files this gate touches: new
    gate module + shared resolver + registration + this repo self-declaration + docs
    + tests'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/gates/_docblocks_shared.py
  reason: 'narrowing the umbrella glob to the actual files this gate touches: new
    gate module + shared resolver + registration + this repo self-declaration + docs
    + tests'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/gates/_docblocks_refs.py
  reason: 'narrowing the umbrella glob to the actual files this gate touches: new
    gate module + shared resolver + registration + this repo self-declaration + docs
    + tests'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/gates/_waive.py
  reason: 'narrowing the umbrella glob to the actual files this gate touches: new
    gate module + shared resolver + registration + this repo self-declaration + docs
    + tests'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/gates/__init__.py
  reason: 'narrowing the umbrella glob to the actual files this gate touches: new
    gate module + shared resolver + registration + this repo self-declaration + docs
    + tests'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/check/__init__.py
  reason: 'narrowing the umbrella glob to the actual files this gate touches: new
    gate module + shared resolver + registration + this repo self-declaration + docs
    + tests'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: frob.toml
  reason: 'narrowing the umbrella glob to the actual files this gate touches: new
    gate module + shared resolver + registration + this repo self-declaration + docs
    + tests'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: docs/modules/gates.md
  reason: 'narrowing the umbrella glob to the actual files this gate touches: new
    gate module + shared resolver + registration + this repo self-declaration + docs
    + tests'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/unit/test_flag_coverage_gate.py
  reason: 'narrowing the umbrella glob to the actual files this gate touches: new
    gate module + shared resolver + registration + this repo self-declaration + docs
    + tests'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: docs/design/registry/check-coverage.yaml
  reason: frob registry audit --sync-gate-rules writes the CHK-GATE-FLAGCOV001 entry
    here as part of registering the new rule
  actor: logan
  at: '2026-08-18'
evidence:
- tests/unit/test_flag_coverage_gate.py::TestFlagCoverageGate::test_must_now_fire_reports_the_genuinely_dropped_flag
- tests/unit/test_flag_coverage_gate.py::TestFlagCoverageGate::test_must_still_pass_when_everything_is_forwarded
- tests/unit/test_flag_coverage_gate.py::TestFlagCoverageGate::test_this_repos_own_frob_toml_reports_zero
- tests/unit/test_flag_coverage_gate.py::TestFlagCoverageGate::test_no_declared_sources_is_unresolved_not_empty
- tests/unit/test_flag_coverage_gate.py::TestFlagCoverageGate::test_missing_config_key_is_unresolved
- tests/unit/test_flag_coverage_gate.py::TestFlagCoverageGate::test_missing_forwarded_key_is_unresolved
- tests/unit/test_flag_coverage_gate.py::TestFlagCoverageGate::test_unresolvable_parser_is_unresolved_not_a_crash
- tests/unit/test_flag_coverage_gate.py::TestFlagCoverageGate::test_non_callable_non_set_forwarded_is_unresolved
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2387 fixed the second occurrence of the "argparse dest has a matching
AppConfig field but is missing from a forwarding tuple" bug class
(T-0749 fixed the first, --accepts). Both times the only thing that
caught it was a human noticing broken behavior -- the detector that
would have caught it mechanically, find_dropped_cli_flags (T-2004,
src/frob/app/_config_external.py), already existed both times and was
never wrong; it was simply never wired to run anywhere except its own
unit test (tests/unit/test_app_config_flag_coverage.py::
TestFindDroppedCliFlags::test_current_tree_has_zero_dropped_flags).

A unit test nobody runs outside `pytest tests/unit/` is not an
enforcement surface -- it does not fire in `frob check`, so an agent or
operator who runs the gate-oriented workflow this repo standardizes on
never sees it. Wire find_dropped_cli_flags into frob check as its own
gate (or fold it into an existing app/config-consuming gate family)
so a new dropped-flag regression shows up the same way COV/WIRE/DEAD
findings do, not only when someone happens to run the full unit suite
or hits the bug manually in production use.

Filed per T-2387's coordinator instruction: "ask what would have made
this visible within a day, and if the answer is a frob check gate
rather than a unit test nobody runs, say so ... even if wiring it is a
separate ticket."
