---
id: T-3010
title: 'Incremental releases: milestone-scoped closure over a configuration binding
  partial architectures with declared gaps (T-3004 section 6)'
state: done
kind: feature
origin: human
created: '2026-08-26'
priority: high
parent: T-3004
tier: ticket
sprint: strata-vmodel
runs_last: false
milestone: 0.535.0
points: 8
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-3010
branch: t-3010
scope:
- strata-core/src/graph/vmodel/closure.rs
- src/frob/gates/_strata_milestone_closure.py
- tests/unit/strata/test_vmodel_check.py
- tests/gates/test_milestone_closure.py
- docs/strata/vmodel.md
- strata-core/src/lib.rs
- src/frob/gates/__init__.py
- src/frob/gates/_waive.py
- design/frob.strata
- docs/design/registry/check-coverage.yaml
- docs/design/registry/capability-via-ratchet.lock.json
- strata-core/strata_core.pyi
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: strata-core/src/graph/vmodel/closure.rs
  reason: milestone-scoped closure over configuration binding
  actor: logan
  at: '2026-09-23'
- op: add
  glob: src/frob/gates/_strata_milestone_closure.py
  reason: milestone-scoped closure over configuration binding
  actor: logan
  at: '2026-09-23'
- op: add
  glob: tests/unit/strata/test_vmodel_check.py
  reason: milestone-scoped closure over configuration binding
  actor: logan
  at: '2026-09-23'
- op: add
  glob: tests/gates/test_milestone_closure.py
  reason: milestone-scoped closure over configuration binding
  actor: logan
  at: '2026-09-23'
- op: add
  glob: docs/strata/vmodel.md
  reason: milestone-scoped closure over configuration binding
  actor: logan
  at: '2026-09-23'
- op: add
  glob: strata-core/src/lib.rs
  reason: milestone closure needs a PyO3 export mirroring vmodel_check's pattern for
    the Python gate to call the new rule-6 Rust engine
  actor: logan
  at: '2026-09-23'
- op: add
  glob: strata-core/src/graph/vmodel/mod.rs
  reason: check_milestone_closure needs the same pub use re-export mod.rs already
    gives every other closure.rs rule function
  actor: logan
  at: '2026-09-24'
- op: add
  glob: src/frob/gates/__init__.py
  reason: wire the new milestone_closure_gate into _ALL_GATES and the gates-fast stage
    group, same wiring VMOD001 needed
  actor: logan
  at: '2026-09-24'
- op: add
  glob: src/frob/gates/_waive.py
  reason: MSCLOSE001 needs registering in _KNOWN_GATE_RULES, same REG002 step VMOD001/TDD001
    needed
  actor: logan
  at: '2026-09-24'
- op: add
  glob: design/frob.strata
  reason: MSCLOSE001's _repo_milestone helper opens frob.toml directly (Path.open('rb')),
    a new fs.read site under src/frob/gates/**
  actor: logan
  at: '2026-09-24'
- op: add
  glob: docs/design/registry/check-coverage.yaml
  reason: MSCLOSE001 needs a CHK-GATE-MSCLOSE001 registry entry, same REG002 step
    VMOD001 needed
  actor: logan
  at: '2026-09-24'
- op: add
  glob: docs/design/registry/capability-via-ratchet.lock.json
  reason: SYS111 gates::fs.read ratchet needs bumping 62->63 for _strata_milestone_closure.py's
    new frob.toml read site
  actor: logan
  at: '2026-09-24'
- op: add
  glob: strata-core/strata_core.pyi
  reason: milestone_closure_check needs a type stub, same as vmodel_check's, for ty
    check to resolve the new PyO3 export
  actor: logan
  at: '2026-09-24'
- op: remove
  glob: strata-core/src/graph/vmodel/mod.rs
  reason: T-3010's own mod.rs work (the check_milestone_closure re-export) is complete
    and committed; freeing the lease so T-3047 (same agent, sequencing-only blocked_by)
    can extend the schema further
  actor: logan
  at: '2026-09-24'
triage_changes:
- field: parent
  old_value: null
  new_value: T-3004
  reason: T-3004 decomposition per the owner design decision
  actor: logan
  at: '2026-08-26'
- field: milestone
  old_value: 1.1.0
  new_value: 0.535.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-23'
- field: sprint
  old_value: null
  new_value: strata-vmodel
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-23'
- field: points
  old_value: null
  new_value: '8'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
- field: points
  old_value: '8'
  new_value: '8'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
evidence:
- tests/gates/test_milestone_closure.py::TestMilestoneGapNodeIds::test_refuses_a_blank_reason
- tests/gates/test_milestone_closure.py::TestMilestoneClosureGate::test_quiet_on_no_design_dir
- tests/gates/test_milestone_closure.py::TestMilestoneClosureGate::test_quiet_no_vmodel_declarations
- tests/unit/strata/test_vmodel_check.py::TestMilestoneClosureCheck::test_fires_on_an_ungapped_uncovered_obligation
- tests/unit/strata/test_vmodel_check.py::TestMilestoneClosureCheck::test_quiet_when_gap_is_declared
- tests/unit/strata/test_vmodel_check.py::TestMilestoneClosureCheck::test_quiet_when_covered_by_a_verifying_test
- tests/unit/strata/test_vmodel_check.py::TestMilestoneClosureCheck::test_partial_coverage_three_of_five_with_two_gaps_passes
- tests/unit/strata/test_vmodel_check.py::TestMilestoneClosureCheck::test_same_configuration_with_an_undeclared_missing_obligation_fails
- tests/gates/test_milestone_closure.py::TestMilestoneClosureGate::test_fires_msclose001_on_an_ungapped_uncovered_obligation
- tests/gates/test_milestone_closure.py::TestMilestoneClosureGate::test_quiet_when_gap_is_declared
- tests/gates/test_milestone_closure.py::TestMilestoneClosureGate::test_partial_milestone_with_gap_passes_the_ungapped_case_still_fires
- tests/gates/test_milestone_closure.py::TestMilestoneClosureGate::test_default_milestone_reads_frob_toml
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
