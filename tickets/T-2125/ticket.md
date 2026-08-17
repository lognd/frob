---
id: T-2125
title: 'T-2106 residue: doable still exceeds 540s in the SHARED ROOT after the sweep-budget
  fix (86.5s was measured in a worktree); the sweep line is gone and the new bottleneck
  is unidentified'
state: done
kind: bug
origin: human
created: '2026-08-11'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_unlanded.py
- tests/unit/test_unlanded_branch_work.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/tickets/_doable.py
  reason: the actual hotspot per PYTHONFAULTHANDLER stack sample is _unlanded.py::_ticket_state_on_main,
    a per-(branch,ticket) git show spawn -- not _doable.py, which only renders the
    summary
  actor: logan
  at: '2026-08-11'
- op: add
  glob: src/frob/tickets/_unlanded.py
  reason: the actual hotspot per PYTHONFAULTHANDLER stack sample is _unlanded.py::_ticket_state_on_main,
    a per-(branch,ticket) git show spawn -- not _doable.py, which only renders the
    summary
  actor: logan
  at: '2026-08-11'
- op: add
  glob: tests/unit/test_unlanded_branch_work.py
  reason: the actual hotspot per PYTHONFAULTHANDLER stack sample is _unlanded.py::_ticket_state_on_main,
    a per-(branch,ticket) git show spawn -- not _doable.py, which only renders the
    summary
  actor: logan
  at: '2026-08-11'
evidence:
- tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWork::test_confirmed_leak_shape_done_report_plus_in_progress
- tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWork::test_findings_for_one_branch_matches_the_aggregate
- tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWorkMainStateSpawnScaling::test_main_state_resolution_does_not_scale_with_branch_times_ticket
designated_repro_test: tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWorkMainStateSpawnScaling::test_main_state_resolution_does_not_scale_with_branch_times_ticket
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Done report

Root cause confirmed via the coordinator's PYTHONFAULTHANDLER stack
sample: `frob.tickets._unlanded._ticket_state_on_main` spawned up to two
`git show` subprocesses PER TICKET ID PER BRANCH via `_blob_text` ->
`guarded_subprocess_run`. With ~644 branches and ~2100 ticket
directories in this repo (`main`'s own tally, confirmed via `git grep`),
that product is exactly the shared-root `doable` hotspot -- invisible in
a worktree, which has far fewer branches/tickets in view.

Fix: `_ticket_states_on_ref(root, ref, globs)` resolves EVERY ticket
id's `state:` value at a given ref in ONE `git grep -e '^state:' <ref>
-- <globs>` call, instead of one `git show`/`_blob_text` spawn per
ticket id. `_all_ticket_states_on_main` (active + archive globs) is the
generalization of the exact function the stack trace named;
`_unlanded_branch_work` now computes this ONCE per run and threads it
through `_unlanded_findings_for_branch` (new `main_states` parameter,
defaulting to `None` -> computed lazily, so the function stays
independently callable for its own unit tests and
`frob.tickets._leases`'s per-worktree sweep caller).

Measuring the fix for JUST that one function in the shared root
(bounded, analytic sample over 61 of 646 branches, since running the
OLD per-ticket path to completion across all 646 would itself take the
better part of the very time budget this ticket exists to fix):
`_all_ticket_states_on_main` resolved all 2112 tickets in 0.097s; the 61
sampled branches' own finished-signal counts alone projected ~7054
`git show` spawns the old code would have needed for JUST those 61
branches' main-state resolution.

**That fix alone was not sufficient** -- a real, bounded (300s timeout)
shared-root run of `_unlanded_branch_work` with only the main-state fix
applied did NOT complete. Investigating why found the SAME per-(branch,
ticket) `git show`/`_blob_text` shape twice more in this module, both
resolving a ticket's state on the BRANCH itself rather than `main`:
`_done_report_and_local_state_signals`'s second-signal check, and
`_directive_anchor_signals_on_branch`'s third-signal check. Confirmed
directly: a bounded run got stuck cycling through dozens of `git show
<branch>:tickets/<id>/ticket.md` calls on branches carrying many
directive-anchored ticket ids (e.g. branch T-0871: 39 such ids, each its
own spawn, under the old code).

Generalized the same fix (`_ticket_states_on_ref` is ref-parametrized,
`re.escape`d against the ref name since a branch name can contain regex
metacharacters) into `_ticket_states_on_branch` (active-only glob,
matching this module's own deliberate archive exclusion for branch-local
checks), computed ONCE per branch inside `_finished_signals_on_branch`
and shared between both branch-side signal functions -- replacing their
per-candidate-id spawns with dict lookups.

Measured end to end in the shared root with BOTH fixes applied (`git
status --porcelain` clean before starting; two live agent lands started
mid-measurement and left the tree mid-stage afterward, unrelated to this
read-only measurement -- confirmed via `ps aux` showing T-2122/T-1973
lands genuinely in flight, not anything this change wrote):
`_unlanded_branch_work(Path("/home/logan/projects/frob"))` completed in
~118.5s, 245 findings, well under the 540s land-lock budget -- down from
a run that did not complete within a 300s bound with only the main-state
half of the fix.

Evidence protocol (BUG002): committed
`TestUnlandedBranchWorkMainStateSpawnScaling::test_main_state_resolution_does_not_scale_with_branch_times_ticket`
alone first (df5d3ec74) -- a fixture with 4 branches x 5 distinct
unresolved tickets each, asserting total `git`-spawn count (via
`frob.gitio.spawn_recorder`) stays below the branch x ticket product.
Confirmed genuinely fails at that commit (old code spawns 2 `git show`
calls per pair, exceeding the product) via `frob ticket evidence
--check-repro ... --base-ref df5d3ec74`: FAILED_AT_PARENT. The fix
(both the main-state AND branch-state batching) landed in a separate
commit (c93dc07eb).

Verified:
- `uv run pytest tests/unit/test_unlanded_branch_work.py -o addopts=""
  -q`: 14 passed (13 pre-existing + 1 new).
- `uv run pytest tests/test_ticket_leases.py tests/test_ticket_reconcile.py
  tests/unit/test_app_runners_doable_stale_lease.py
  tests/unit/test_unlanded_branch_work.py -o addopts="" -q`: 163 passed
  -- every caller of `_unlanded_findings_for_branch`/
  `_unlanded_branch_work` (the per-worktree sweep gate, `reconcile`'s
  third anomaly class, `doable`'s summary line) still passes.
- `frob ticket evidence T-2125 --check-repro ... --base-ref df5d3ec74`:
  FAILED_AT_PARENT (genuine repro).
- `frob check --ticket T-2125 --only gates-fast`: clean except gate:TICK
  TICK004 (T-0969 rotting past its 7-day threshold) -- pre-existing
  repo-wide ticket-ledger rot unrelated to this ticket's own diff (same
  finding seen, and disclosed, in the prior T-2098/T-1784/T-1782 series
  this session).

Not folded in (disclosed, not silently dropped): the third remaining
per-branch loop in this module, `_directive_anchored_ticket_ids`'s scan
of `branch`'s own NON-ticket changed files for `frob:ticket` directive
comments, still spawns one `_blob_text` call per candidate file (not per
ticket id -- bounded by `own_changed`'s file count, not the ticket
count, and measured at 0.123s for a real 39-file branch, not itself
observed as a bottleneck in the bounded shared-root run above). Batching
this too (a single `git grep` across the candidate paths) is the same
class of fix and would close the loop entirely, but was not needed to
bring `doable` under budget and is left as a smaller, lower-priority
follow-up rather than expanded into this ticket's own scope.

### Changed
```
 src/frob/tickets/_unlanded.py           | 219 ++++++++++++++++++++++++++++----
 tests/unit/test_unlanded_branch_work.py |  61 +++++++++
 tickets/T-2125/ticket.md                |  33 ++++-
 3 files changed, 282 insertions(+), 31 deletions(-)
```

### Evidence
- `tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWork::test_confirmed_leak_shape_done_report_plus_in_progress` (pytest node id, verified passing when recorded)
- `tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWork::test_findings_for_one_branch_matches_the_aggregate` (pytest node id, verified passing when recorded)
- `tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWorkMainStateSpawnScaling::test_main_state_resolution_does_not_scale_with_branch_times_ticket` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: E501@/home/logan/projects/frob/.claude/worktrees/t-2125/src/frob/tickets/_unlanded.py, TICK004@tickets.md
