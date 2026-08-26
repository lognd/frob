---
id: T-3019
title: frob check fires spurious REF001/PRE001/SCOPE001 on any clean project; frob
  check is not repo-clean on main
state: queued
kind: bug
origin: human
created: '2026-08-26'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_refs.py
- tests/unit/gates/test_refs.py
- tests/test_refs_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/gates/__init__.py
  reason: T-3014 holds lease on this file; fix confined to _refs.py and design/frob.strata
  actor: logan
  at: '2026-08-26'
- op: remove
  glob: design/frob.strata
  reason: T-2989 lease still recorded on this file; cluster A fix (REF001/PRE001/SCOPE001
    spurious findings) needs only _refs.py, cluster B self-conformance strata work
    deferred to a follow-up ticket
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/unit/gates/test_refs.py
  reason: scope closure requires test edge for ref_gate
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/test_refs_gate.py
  reason: scope closure requires test edge for _native_stub_pairs/ref_gate
  actor: logan
  at: '2026-08-26'
triage_changes:
- field: priority
  old_value: medium
  new_value: high
  reason: os.kill(pid,0) can TerminateProcess a live process on Windows under PID
    reuse, and the unfixed sibling copies are in _land.py and _leases.py -- the land
    machinery itself, where killing a live process corrupts a land in flight
  actor: logan
  at: '2026-08-26'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
`frob check` fires spurious REF001/PRE001/SCOPE001 errors on any trivial
synthetic project fixture, unrelated to Windows -- surfaced while
investigating T-3003's "19 Windows pytest failures" list.

Six of that list's tests/system/test_cli_check.py failures, and
tests/unit/strata/test_selfconform.py::TestRealGateGreen's failure, ALSO
reproduce identically on Linux (verified by running them directly in a
Linux worktree against current main, no code changes applied):

  tests/system/test_cli_check.py::TestCheckCleanProject::test_clean_code_exits_zero
  tests/system/test_cli_check.py::TestCheckSkipFlags::test_skip_ruff
  tests/system/test_cli_check.py::TestCheckSkipFlags::test_skip_exports
  tests/system/test_cli_check.py::TestCheckGatesStage::test_only_gates_passes_once_bound_and_tested
  tests/system/test_cli_check.py::TestCheckStageGroups::test_available_stages_cover_every_gate_and_tool
  tests/system/test_cli_check.py::TestCheckTicketLeasePinRefusal::test_ticket_lease_recorded_elsewhere_refuses
  tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant

These are NOT Windows portability defects: they are a pre-existing
main-branch regression that happens to also show up in the Windows job
log, inflating the reported Windows failure count from 19 to effectively
~13 genuinely Windows-related failures.

Cluster A (5 of the 6 test_cli_check.py failures): a synthetic project
fixture (just pyproject.toml + frob.toml + one src file, freshly
git-committed) now fails `frob check` with:

  [gate:PRE] uv.lock:0 PRE001 diff against merge-base ... touches 1 file(s)
    but no active ticket is derivable
  [gate:REF] frob.toml:0 REF001 frob.toml has no inbound references ...
  [gate:REF] pyproject.toml:0 REF001 pyproject.toml has no inbound references ...
  [gate:REF] src/mypkg/__init__.py:0 REF001 ... has no inbound references ...
  [gate:SCOPE] uv.lock:0 SCOPE001 diff against merge-base ... touches 1 file(s) ...

Reproduced with NO uv.lock ever created by the fixture -- worth checking
whether `frob check` is somehow resolving to the wrong root, or whether
REF001's entrypoint exemption for frob.toml/pyproject.toml regressed (it
used to treat a project's own root config files as exempt from "no
inbound references"). Suspect a recent REF001/PRE001/SCOPE001 change;
`git log` on `src/frob/gates/_refs.py` and the PRE/SCOPE gate modules
around the time these gates were last touched is the fastest way in.

Cluster B (test_selfconform, 1 test): the real repo's SYS100/SYS102/
SYS107 self-conformance scan is NOT clean on current main -- 23 real
violations (not flaky, not environment-specific), e.g.:

  SYS100 cli capability 'env.read' observed at src/frob/__main__.py:651 but not declared
  SYS102 src/frob/ci_report.py has no node's code= glob binding it
  SYS102 src/frob/ci_validity.py has no node's code= glob binding it
  SYS102 src/frob/ghio.py has no node's code= glob binding it
  SYS107 testsuite node binds 622 file(s) (> 20), via-less 'fs.read'/'fs.write' may grants

`src/frob/ci_report.py`, `src/frob/ci_validity.py`, and `src/frob/ghio.py`
look like genuinely new/renamed files with no `design/frob.strata` node
binding them yet (SYS102) -- likely just needs a `.strata` update to
match. The env.read/env.write/ffi/eval capability gaps (SYS100) are
smaller, mechanical additions to existing node declarations.

Severity: HIGH. This is not a Windows-only gap -- `frob check` is
currently NOT clean-repo-safe on ANY platform for a plain new project,
and the repo's own self-conformance gate is red on main. This should be
picked up ahead of most other backlog items since it affects every
platform's baseline, not just the Windows matrix leg.

Filed while working T-3003 (Windows Test-stage triage); out of that
ticket's declared Windows-portability scope.
