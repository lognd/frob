---
id: T-1040
title: Wire ffi_boundary gate into a check --only stage-group alias
state: done
kind: ux
origin: agent
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/check/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/system/test_cli_check.py::TestCheckStageGroups::test_available_stages_cover_every_gate_and_tool
designated_repro_test: null
threat: null
component: null
---
T-0690 landed frob.gates._ffi_boundary.ffi_boundary_gate (FFI001/FFI002)
registered in frob.gates's _ALL_GATES/_CANONICAL_GATE_ORDER/process_jobs,
runnable today via its own bare name (--only ffi_boundary), but
src/frob/check/__init__.py's _STAGE_GROUPS was out of T-0690's declared
scope (src/frob/gates/** does not cover src/frob/check/__init__.py) so no
existing --only alias (gates-native/gates-fast/...) bundles it yet. Add
ffi_boundary to the appropriate _STAGE_GROUPS entry (it is a fast process
job, ~0.4s measured) so a normal --budget/--only gates-native run picks
it up without the caller needing to name it explicitly.

This is a REFILE: the original draft (T-draft-93f13251) was filed during
the T-0690 dispatch but did not survive land -- the same draft-loss class
T-0637 tracks and T-1036 (this dispatch's CLI-churn-under-fast-land
ticket) also documents. Re-filing here so the work item is not lost a
second time.