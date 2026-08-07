---
id: T-1356
title: Scope-lease deadlock between two tickets sharing one worktree
state: done
kind: bug
origin: agent
created: '2026-07-31'
priority: medium
parent: T-1344
tier: ticket
sprint: null
scope:
- src/frob/tickets/_scope.py
- docs/modules/tickets.md
- tests/unit/test_scope_lease_deadlock.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_scope_lease_deadlock.py
  reason: regression tests for T-1356 scope-lease deadlock fixes
  actor: logan
  at: '2026-08-01'
evidence:
- tests/unit/test_scope_lease_deadlock.py::TestRemoveKeepsEvidenceCoveredByRemainingScope::test_remove_permitted_when_narrower_glob_still_covers_evidence
- tests/unit/test_scope_lease_deadlock.py::TestRemoveKeepsEvidenceCoveredByRemainingScope::test_remove_still_refused_when_evidence_would_be_orphaned
- tests/unit/test_scope_lease_deadlock.py::TestRemoveKeepsEvidenceCoveredByRemainingScope::test_unit_helper_directly_permits_when_remaining_covers
- tests/unit/test_scope_lease_deadlock.py::TestSameWorktreeLeaseIsNotAConflict::test_add_into_sibling_scope_same_worktree_is_permitted
- tests/unit/test_scope_lease_deadlock.py::TestSameWorktreeLeaseIsNotAConflict::test_add_into_different_worktree_sibling_scope_still_refused
designated_repro_test: null
acceptance:
- text: given a glob whose recorded evidence stays covered by a remaining narrower
    glob, when scope --remove runs, then it is permitted
  evidence:
  - tests/unit/test_scope_lease_deadlock.py::TestRemoveKeepsEvidenceCoveredByRemainingScope::test_remove_permitted_when_narrower_glob_still_covers_evidence
  - tests/unit/test_scope_lease_deadlock.py::TestRemoveKeepsEvidenceCoveredByRemainingScope::test_remove_still_refused_when_evidence_would_be_orphaned
  - tests/unit/test_scope_lease_deadlock.py::TestRemoveKeepsEvidenceCoveredByRemainingScope::test_unit_helper_directly_permits_when_remaining_covers
- text: given two tickets in the same worktree, when one adds a scope glob the other
    holds, then the operation is not refused as a lease conflict
  evidence:
  - tests/unit/test_scope_lease_deadlock.py::TestSameWorktreeLeaseIsNotAConflict::test_add_into_sibling_scope_same_worktree_is_permitted
  - tests/unit/test_scope_lease_deadlock.py::TestSameWorktreeLeaseIsNotAConflict::test_add_into_different_worktree_sibling_scope_still_refused
threat: null
component: tickets
---
Leaf of T-1344. Discovered 2026-07-31 during the batched parallel drive.

THE DEFECT: two tickets living in one worktree can deadlock on scope leases in a way that cannot be resolved through the CLI.

OBSERVED: T-1276 held the glob `tests/unit/**`. A sibling ticket T-1352, in the SAME worktree, needed `tests/unit/test_app_lazy_exports.py` in scope. `frob ticket scope T-1352 --add ...` was refused with ScopeLeaseConflict because T-1276's broader glob covered it. The obvious remedy -- narrow T-1276's glob -- was ALSO refused: `frob ticket scope --remove` will not release any glob still covering recorded evidence, even when a narrower duplicate glob would remain in place and keep that evidence covered.

So the two refusals compose into a deadlock with no CLI exit. The agent worked around it by recording evidence against the test files WITHOUT adding them to T-1352's declared scope (evidence recording has no scope-membership requirement, only a soft SCOPE002 warning). That worked, but it means the ticket's declared scope now understates what it actually touched -- the workaround erodes exactly the scope-accuracy guarantee the lease system exists to provide.

WHAT TO FIX (assess each, do not assume):
1. `scope --remove` should permit releasing a glob when the remaining globs still cover every recorded evidence path. The current check appears to test "is this glob covering evidence?" rather than "would removing it leave evidence uncovered?" -- the latter is the property that actually matters.
2. Lease conflicts between tickets sharing a worktree are arguably not conflicts at all: the lease exists to stop CONCURRENT AGENTS colliding, and two tickets in one worktree have exactly one agent. Consider scoping lease checks to distinct worktrees/agents rather than distinct ticket ids.
3. If the deadlock is genuinely unresolvable in some cases, the refusal message must say so and name the escape hatch, instead of leaving an agent to invent a workaround that quietly degrades scope accuracy.

This matters more now that SERIES dispatch is standing policy -- multiple tickets per worktree is the normal case, not the exception, so this deadlock will recur.