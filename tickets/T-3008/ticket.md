---
id: T-3008
title: 'Multi-level invariants: an invariant declared at level L must be verified
  at Ls paired test level (T-3004 section 7)'
state: in-progress
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
worktree: /home/logan/projects/frob/.claude/worktrees/t-3008
branch: t-3008
scope:
- src/frob/gates/_invariant_level.py
- tests/gates/test_invariant_level.py
- src/frob/gates/invariants.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/strata/_selfconform_models.py
  reason: invariant level field + level-mismatch rule (INVLVL001)
  actor: logan
  at: '2026-09-23'
- op: add
  glob: strata-core/src/graph/vmodel/mod.rs
  reason: invariant level field + level-mismatch rule (INVLVL001)
  actor: logan
  at: '2026-09-23'
- op: add
  glob: src/frob/gates/_invariant_level.py
  reason: invariant level field + level-mismatch rule (INVLVL001)
  actor: logan
  at: '2026-09-23'
- op: add
  glob: tests/gates/test_invariant_level.py
  reason: invariant level field + level-mismatch rule (INVLVL001)
  actor: logan
  at: '2026-09-23'
- op: add
  glob: docs/strata/vmodel.md
  reason: invariant level field + level-mismatch rule (INVLVL001)
  actor: logan
  at: '2026-09-23'
- op: add
  glob: docs/modules/gates.md
  reason: invariant level field + level-mismatch rule (INVLVL001)
  actor: logan
  at: '2026-09-23'
- op: remove
  glob: strata-core/src/graph/vmodel/mod.rs
  reason: no Rust kernel change needed -- the level field/pairing lives entirely in
    Python (frob.gates.invariants), avoiding a collision with T-3010's live lease
    on this file
  actor: logan
  at: '2026-09-24'
- op: remove
  glob: src/frob/strata/_selfconform_models.py
  reason: declared scope named the wrong module -- INV001/INV002/Invariant actually
    live in src/frob/gates/invariants.py (SYS100-102 self-conformance is unrelated);
    swapping to the correct file
  actor: logan
  at: '2026-09-24'
- op: add
  glob: src/frob/gates/invariants.py
  reason: the real location of Invariant/INV001/INV002 this ticket adds a level field
    and paired-level check to
  actor: logan
  at: '2026-09-24'
- op: remove
  glob: docs/strata/vmodel.md
  reason: T-3010 holds a live lease on this file; document INVLVL001 in docs/modules/gates.md
    only for now to avoid collision, cross-link can follow once T-3010 lands
  actor: logan
  at: '2026-09-24'
- op: remove
  glob: docs/modules/gates.md
  reason: T-3008's own INVLVL001 doc section is complete and committed; freeing the
    lease so T-3068 (same agent, sequencing-only blocked_by) can extend it further
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
  at: '2026-09-24'
evidence:
- tests/gates/test_invariant_level.py::TestInvariantLevelGate::test_quiet_when_no_level_declared
- tests/gates/test_invariant_level.py::TestInvariantLevelGate::test_fires_on_a_level_mismatch
- tests/gates/test_invariant_level.py::TestInvariantLevelGate::test_quiet_when_verified_at_the_paired_level
- tests/gates/test_invariant_level.py::TestInvariantLevelGate::test_quiet_for_untagged_evidence
- tests/gates/test_invariant_level.py::TestInvariantLevelGate::test_multiple_invariants_only_mismatched_one_fires
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
