---
id: T-3629
title: 'ARCH102: split src/frob/tickets/_land_squash.py (38 exports, 3 clusters)'
state: in-progress
kind: feature
origin: human
created: '2026-09-01'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land_squash.py
- tests/unit/test_land_squash_residue_reclaim.py
- tests/unit/test_land_squash_stage.py
- src/frob/tickets/_land_splice.py
- docs/design/land-splice-test-then-impl.md
- tests/unit/test_land_splice_test_then_impl.py
- tickets/T-3566/ticket.md
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: tests/**/*land_squash*
  reason: narrow overbroad glob that phantom-matches T-1661s live lease on tests/unit/strata/**;
    the real test files live in tests/unit/
  actor: logan
  at: '2026-09-01'
- op: add
  glob: tests/unit/test_land_squash_residue_reclaim.py
  reason: narrow overbroad glob that phantom-matches T-1661s live lease on tests/unit/strata/**;
    the real test files live in tests/unit/
  actor: logan
  at: '2026-09-01'
- op: add
  glob: tests/unit/test_land_squash_stage.py
  reason: narrow overbroad glob that phantom-matches T-1661s live lease on tests/unit/strata/**;
    the real test files live in tests/unit/
  actor: logan
  at: '2026-09-01'
- op: add
  glob: src/frob/tickets/_land_splice.py
  reason: new module created by the split
  actor: logan
  at: '2026-09-01'
- op: add
  glob: docs/design/land-splice-test-then-impl.md
  reason: moved symbols frob:doc anchor lives there; may need AFFECT001/DRIFT002 re-verification
  actor: logan
  at: '2026-09-01'
- op: add
  glob: tests/unit/test_land_splice_test_then_impl.py
  reason: refactor split auto-updated this tests import statement and an unrelated
    tickets historical-attribution reference to the moved symbols path
  actor: logan
  at: '2026-09-01'
- op: add
  glob: tickets/T-3566/ticket.md
  reason: refactor split auto-updated this tests import statement and an unrelated
    tickets historical-attribution reference to the moved symbols path
  actor: logan
  at: '2026-09-01'
- op: add
  glob: design/frob.strata
  reason: need to declare fs.write/env.read capability via-list entries for the new
    _land_splice.py module (SELFAUDIT001)
  actor: logan
  at: '2026-09-01'
body_changes:
- mode: append
  reason: record split plan before coding, per ticket instruction
  actor: logan
  at: '2026-09-01'
  old_length: 779
  new_length: 2706
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
ARCH102: src/frob/tickets/_land_squash.py has 38 exports clustering
into roughly 3 concerns -- split it along those clusters. Write the
split plan (which exports go into which new module, and why) in this
ticket's body BEFORE coding. MUST use `uv run frob refactor split` /
`uv run frob refactor move-module` to perform the actual split, never
a hand-copy (standing user directive) -- append any tool gaps
encountered to T-3596. After the split, run a repo-wide import check
and `ty` type-check.

Scope: src/frob/tickets/_land_squash.py + its test file + any direct
importers whose import statement must be updated.

Previously specified but never filed (LandInProgress starvation
during a prior agent's ~45 min of retries); refiled now as part of
draining that starved backlog.


## Split plan (T-3629, ARCH102, 38 exports / 3 clusters)

Cluster 1 -- test-then-impl commit splicing (splits a worktree's staged
diff into a separate "test" commit and "impl" commit pair):
  classify_test_then_impl_paths
  _apply_pathset_diff_to_scratch_index
  _write_and_commit_pathset_index
  _compose_pathset_commit
  compose_test_then_impl_commits
-> new module `frob.tickets._land_splice`

Cluster 2 -- squash-conflict/ledger-v2 scope checking (pre-flight over
the v2 ledger before a squash-apply is attempted):
  _check_squash_conflicted
  _v2_effective_scope
  _check_squash_conflicted_v2
  _squash_and_splice_ledger_v2
  _squash_and_splice_ledger
  _unwind_squash_apply
-> stays in `_land_squash.py` for this ticket (tool-risk note below)

Cluster 3 -- squash-apply/publish/commit-record machinery (the large
core: land-commit-record derivation, absorption reporting, the
squash-apply pipeline itself, pre-commit sweep, native rebuild, land
report):
  everything else (~27 functions)
-> stays in `_land_squash.py` for this ticket (tool-risk note below)

EXECUTION NOTE (T-3628 tool-gap precedent, T-3596): `frob refactor
split` was found to drop a moved function's own module-level free-
variable dependencies (T-3596 gap 3/4) when the destination module
never had that dependency (e.g. this file's `_log = get_logger(
__name__)`). Cluster 1 is the smallest, most clearly self-contained,
least state-coupled subset (only `_log` as a free variable, no
decorators, no cross-cluster call edges back into clusters 2/3) and is
attempted first via the tool with full post-move verification (actual
pytest run, not just the tool's own success report, per the T-3628
incident). Clusters 2/3 remain undivided in `_land_squash.py` pending
either a T-3596 fix or a follow-up ticket, rather than risk a repeat of
T-3628's tool-corrupted split on this much larger, more state-coupled
file within this same ticket's time budget.
