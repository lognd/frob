---
id: T-draft-615d0118-stale-mirror
title: CI stamp-baseline --only chunk list desynced from _stamp_baseline_gate_chunks,
  .frob/baseline never written
state: dropped
kind: bug
origin: human
created: '2026-09-03'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .github/workflows/ci.yml
- tests/test_ci_workflow_matrix.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: add description and plan for stamp-baseline chunk-desync fix
  actor: logan
  at: '2026-09-03'
  old_length: 0
  new_length: 2511
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Description

CI run 33748098172 ubuntu+macos both FAILED the "coverage stamp + delta
baseline must be freshly measurable and clean (T-1366)" step with:

    .frob/baseline is missing after a fresh frob check --stamp-baseline run

This was latent, just unmasked now that the Test step passes (T-3740).

Root cause (measured): that step (ci.yml ~1602-1616) stamps the baseline in
chunks via a hardcoded list of `uv run frob check --stamp-baseline --only
<group>` commands. The real `.frob/baseline` is only written when the union
of gate-ids covered by all --only invocations is a SUPERSET of
`_stamp_baseline_gate_chunks()` (see
src/frob/app/_check_chunking_baseline.py:224 `if covered < expected_union:
return`). The CI --only list has drifted: it covers only 40 of 68 expected
gate-ids. 28 are uncovered (win32_kill_signal, gates_schema, arch_schema,
capability_conformance, vmodel, suppress, land_parity, docseverity,
docstatus, milestone, lexcheck, and ~17 more schema/misc gates), so
covered<expected forever, stamp_baseline is never called, every frob
command exits 0, and only the python assertion catches the missing file.

## Plan

1. In ci.yml, replace the FOUR chunked `uv run frob check --stamp-baseline
   --only ...` commands (the gates-native / gates-security / test / big-list
   block) with a SINGLE bare command: `uv run frob check --stamp-baseline`.
   Keep the surrounding `uv run frob ticket reconcile --apply`, `uv run frob
   doctor`, `uv run frob coverage --full`, the `--only test --json` recheck,
   and the python verification block unchanged. Comment explaining: the
   hand-maintained --only enumeration duplicates
   _stamp_baseline_gate_chunks() and silently desyncs whenever a gate is
   added (this failure); a bare --stamp-baseline runs all chunks in one
   process and always stamps. Chunking only existed for the agent
   foreground cap, which does not apply in CI (the documented
   coordinator-only path, T-0751).
2. Update tests/test_ci_workflow_matrix.py's TestCoverageStepUsesFrobNotMake
   (and any assertion pinning the chunked --only groups) to instead assert
   the step contains a bare `frob check --stamp-baseline` (no --only on the
   stamp-baseline command). Drop any assertion pinning the specific --only
   list -- that pin is the desync source.
3. Run `uv run pytest tests/test_ci_workflow_matrix.py -q` green.
4. Land together with T-3740 (win32 budget fix) in one land -- same files,
   filed to avoid a lease collision per the coordinator's instruction.

## Drop reason
- 2026-09-03: stale mirrored ticket-body artifact from the mirror-body write feature, superseded by the worktree's own finalized T-draft-615d0118 record (renamed to avoid a T-2105 duplicate-id collision at T-3740's land)
