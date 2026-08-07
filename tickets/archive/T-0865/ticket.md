---
id: T-0865
title: 'natives build estate conformance: scaffold Makefile shim template + drift
  check for per-repo cache logic'
state: done
kind: feature
origin: human
created: '2026-07-23'
priority: high
blocked_by:
- T-0864
parent: T-0735
tier: ticket
sprint: null
scope:
- src/frob/scaffold/**
- tests/unit/test_scaffold_natives_shim.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_scaffold_natives_shim.py::TestMakefileCoreShimTemplate::test_applying_to_fresh_repo_installs_one_line_shim
- tests/unit/test_scaffold_natives_shim.py::TestLegacyCoreCacheDrift::test_legacy_unmanaged_core_target_reports_stale
designated_repro_test: null
acceptance:
- text: GIVEN a scaffolded frob-enabled repo WHEN `frob scaffold apply` runs THEN
    the Makefile core target is the one-line `uv run frob natives build` shim
  evidence:
  - tests/unit/test_scaffold_natives_shim.py::TestMakefileCoreShimTemplate::test_applying_to_fresh_repo_installs_one_line_shim
- text: GIVEN a repo whose Makefile core target contains its own native-build cache
    logic WHEN the conformance check runs THEN it reports the drift naming the shim
    as the remedy
  evidence:
  - tests/unit/test_scaffold_natives_shim.py::TestLegacyCoreCacheDrift::test_legacy_unmanaged_core_target_reports_stale
threat: null
component: natives
---
T-0735 child 2 (estate conformance). Scaffold template: `frob scaffold apply` emits/updates the Makefile `core` target as the one-line `uv run frob natives build` shim in adopter repos. Add a conformance drift check that flags a frob-enabled repo whose Makefile core target carries its own native-build/cache logic instead of the shim (the drift that motivated the parent: per-repo cache hacks at the wrong layer). Estate rollout of the shim across sibling repos happens via fleet at parent close, not in this ticket.

Resynced the scaffold-owned `makefile-core-shim` template to T-0864's landed one-line `uv run frob natives build` delegate (it was still the pre-T-0864 literal CARGO_TARGET_DIR/maturin-develop recipe, verbatim T-0732 -- exactly the drift T-0865's parent named). Added a conformance check: a repo whose Makefile has a `core:` recipe with NO managed-block markers but still carries the legacy per-repo cache assignment/invocation shapes (`CARGO_TARGET_DIR :=`, `maturin develop --uv --release`) is reported present+stale by `scaffold_conformance_status` (doctor's existing remediation already names `makefile-core-shim`/`frob scaffold apply` as the fix) instead of silently reading as "nothing here yet". A Makefile with no `core:` recipe at all still reports plain absent, unchanged.