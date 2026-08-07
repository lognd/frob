---
id: T-0993
title: gate:TEST TEST003 natives package needs a real integration-kind test or reasoned
  waiver
state: done
kind: bug
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/natives/**
- tests/unit/test_natives_build.py
- tests/system/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_natives_build.py::TestBuildNatives::test_builds_declared_rust_natives
- tests/system/test_natives_build_integration.py::test_build_natives_compiles_and_imports_real_crate
designated_repro_test: null
threat: null
component: null
---
T-0875 accounting sub-finding. gate:TEST TEST003 (WARN) fires for the
src/frob/natives package: 0 integration-kind test edges, below
min_integration=1. This is the ONE remaining unwaived TEST003 finding
after T-0875's edge-wiring pass (doctor.py and registry are already
disposed via existing frob:waive TEST003 notes).

tests/unit/test_natives_build.py::TestNativesRunner exercises
natives_runner.run with build_natives monkeypatched (unit-kind, already
bound), so this is a genuine gap, not an accounting artifact -- there is
no test that exercises the real cargo/maturin build path end to end.

Real cargo/maturin builds are slow (minutes, see this ticket's `frob
natives build` timing) and this repo's playbook explicitly forbids a
dispatched agent from running `make coverage`-class slow builds inline;
an "integration" kind test for this package needs a deliberate design
(e.g. a system test gated behind an opt-in marker/env var that actually
invokes `build_natives` against a tiny fixture crate, or an explicit
per-symbol disposition/waiver with a stated reason) rather than a quick
patch. Scope this to design + land exactly one integration-kind
frob:tests edge (or a reasoned frob:waive TEST003) for src/frob/natives.