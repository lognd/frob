---
id: T-0193
title: 'R1.5 exact-region kernel: generalized suffix automaton over normalized token
  stream'
state: done
kind: feature
origin: agent
created: '2026-07-18'
priority: medium
parent: T-0187
tier: ticket
sprint: null
scope:
- tickets.md
- frob-core/**
- src/frob/dup/**
- tests/**
- docs/modules/dup.md
- CHANGELOG.md
- src/frob/gates/__init__.py
- pyproject.toml
- .frob-release.json
- uv.lock
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_dup_region.py::TestRegionKernelFindsPartialClone::test_enabled_finds_shared_region_between_otherwise_different_functions
- tests/test_dup_region.py::TestRegionKernelOffByDefault::test_whole_symbol_rungs_miss_the_partial_clone
designated_repro_test: null
threat: null
component: null
---
Survey item 16 ADOPT: R1/R2 hash whole symbol bodies only, so partial copy-paste regions inside otherwise-different functions are invisible today. New frob-core kernel; region output feeds the existing CloneRegion model; cargo tests + python-side fixtures.

Scope widened mid-implementation (round 1): `CHANGELOG.md` (REL001's remediation for the
new public `frob_core.exact_regions`/`frob.dup._core.exact_regions` exports and
`DupConfig` fields) and `src/frob/gates/__init__.py` (the `[dup].region_kernel`/
`region_min_tokens` knob has to be read and threaded into `DupConfig` somewhere, and
`dup_gate`/`_dup_config` in `frob.gates` is that one call site -- the ticket's Plan
implies this wiring but the original scope globs did not cover it). `pyproject.toml`
(REL001's version bump, 0.4.0 -> 0.5.0, for the same new public-API surface);
`.frob-release.json`/`uv.lock` (mechanical side effects of `frob release stamp`
and the version bump, not hand-edited).