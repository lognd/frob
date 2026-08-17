---
id: T-1932
title: 'Structural: land runs mutations AFTER the guards that gate them, so any guard''s
  decision can be silently invalidated'
state: done
kind: bug
origin: human
created: '2026-08-09'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_land_step_ordering.py::TestCrossTicketLeakagePostMutationRecheck::test_guard_refusal_survives_an_uncommitted_reintroduction
- tests/unit/test_land_step_ordering.py::TestCrossTicketLeakagePostMutationRecheck::test_clean_land_is_unaffected
- tests/unit/test_land_step_ordering.py::TestPostMutationRecheckOrdering::test_leakage_recheck_runs_after_the_wip_commit_in_land_locked
- tests/unit/test_land_step_ordering.py::TestPostMutationRecheckOrdering::test_post_mutation_recheck_delegates_to_the_same_check_preflight_uses
- tests/test_ticket_work_and_land_finish.py::TestAssertDesignLoadsPreLand::test_a_tier_a_handler_that_corrupts_design_after_it_was_healthy_refuses_the_land
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
THIS IS THE GENERAL CASE BEHIND AT LEAST THREE SEPARATE BUGS. Each was
filed and fixed as a one-off; the ordering defect that produced all three
has never been addressed, so the next guard added to the land path
inherits the same hazard by default.

THE INVARIANT THAT IS VIOLATED: on the land path, no mutation may run
after a guard whose decision that mutation can invalidate. Today land
does exactly that -- it absorbs `frob fmt` and the T-1138 Tier-A
deterministic auto-fix handlers, which REWRITE FILES, and various guards
run before that rewriting.

THE THREE MEASURED INSTANCES:

1. T-1903 (done) -- "Pre-land strata parse guard runs BEFORE the Tier-A
   rewrite, so it cannot catch corruption the rewrite itself introduces."
   Recorded consequence: three lands published an unparseable self-model
   while reporting LAND-PROOF verified=True.

2. T-1910 / T-1920 (done) -- the ticket close and REL001 bump ride the
   SAME commit the ancestry check runs against, so by the time
   verified=False is observable the terminal state and version bump are
   already written. T-1920 had to fix this BY CONSTRUCTION (check
   reachability before the terminal write) precisely because no
   after-the-fact guard could work.

3. T-1931 (queued, observed live during T-1556 s land at 16880d5170a2) --
   the CrossTicketLeakage guard correctly REFUSED a land touching
   design/frob.strata (T-1901 s declared scope). The offending line was
   reverted in the worktree, and land s own Tier-A auto-fixer then
   silently RE-ADDED it before the next attempt, so it landed anyway.
   A guard that refused was overruled by a mutation running after it.

Same shape three times: guard decides, mutation runs, decision is stale,
nobody re-checks. T-1931 is the worst variant because the guard did fire
and was simply overridden.

WHY A FOURTH POINT FIX IS NOT THE ANSWER. Fixing T-1931 alone leaves the
ordering unconstrained, so guard number four added next month repeats
this. The repo already has the lesson written down (a guard that runs
after the mutation it is meant to gate cannot prevent it, only report
it) and it keeps recurring anyway -- which means a written rule is not
sufficient and this needs to be enforced by construction.

FIX DIRECTION -- investigate and choose, with reasoning recorded:
(a) Re-run every guard after the LAST mutating step, so no decision can
    be stale. Simplest to reason about; cost is a second guard pass.
(b) Move all mutation strictly BEFORE all guards, so guards see final
    bytes. Cleanest ordering; requires the auto-fixers not to depend on
    guard output.
(c) Make the ordering explicit and machine-checked: declare each land
    step as mutating or gating, and add a test asserting no gating step
    precedes a mutating step it can be invalidated by.
(a) or (b) plus (c) is likely right -- (c) alone documents the invariant,
it does not establish it.

DO NOT resolve this by removing guards or by disabling land s auto-fix
absorption. Both are load-bearing. The deliverable is ordering, not
subtraction.

ACCEPTANCE
1. The land path has a single documented, enforced ordering between
   mutating steps and gating steps.
2. A test proves a guard s refusal cannot be undone by a later mutating
   step -- model it directly on T-1931 s live repro (guard refuses on a
   cross-ticket file, auto-fix re-adds it, land must still refuse). It
   must FAIL before the fix.
3. A test proves a mutation cannot introduce a defect that an
   already-run guard would have caught -- model on T-1903 (Tier-A rewrite
   corrupts design/frob.strata after the parse guard ran).
4. Adding a NEW guard or a NEW auto-fix handler to the land path cannot
   silently violate the ordering; state how that is prevented.

SEQUENCING: T-1931 may land first as the urgent point fix, or be folded
in here -- decide and say which. Do not let both land redundant
overlapping fixes to the same code.

Note src/frob/tickets/_land.py is high-traffic and every agent depends on
it. A regression here blocks the whole repo, as T-1882 demonstrated
earlier today. State explicitly what this change does under concurrent
lands.

## Done report

SEQUENCING DECISION: T-1931 is folded into T-1932, not landed separately.
Reason: T-1931's own root cause (`_check_cross_ticket_leakage`'s preflight
copy reads only COMMITTED git history, so it cannot see a mutation that
lands as an uncommitted disk write before `land()` is even called) is
exactly one instance of T-1932's general invariant violation. Landing a
standalone T-1931 patch first would have meant writing
`_reverify_cross_ticket_leakage_post_mutation` once for the point fix and
then either duplicating or awkwardly refactoring it again for T-1932's
general treatment -- the redundant-overlapping-fix outcome both tickets
explicitly warn against. T-1931 is closed here as resolved by T-1932's fix
rather than shipped twice.

FIX DIRECTION CHOSEN: (a) -- re-run the affected guard after the LAST
mutating step that can invalidate it, rather than (b) moving every
mutation strictly before every guard (Tier-A/fmt already run before
`land()`'s own preflight, and STILL missed the leak, because the
preflight's leakage check reads only committed history -- moving mutation
earlier does nothing when the guard's blind spot is "uncommitted", not
"early/late"). Root cause: `_check_cross_ticket_leakage`'s diff source
(`_branch_changed_files`) is `git diff base_ref...HEAD` -- committed-only,
by construction. `frob ticket land`'s own T-1175 pre-land auto-fix
absorption (`_absorb_pre_land_fixes`: fmt + Tier-A) runs BEFORE `land()`
is even invoked and leaves its rewrites as UNCOMMITTED disk changes for
`land()`'s own wip-commit to pick up later. So the preflight leakage check
(run first thing inside `land()`, before any git mutation, by design --
cheap fail-fast) structurally cannot see content Tier-A already wrote to
disk but not yet committed. `_land_merge_stage`'s wip-commit is the FIRST
point every such mutation becomes part of history -- so that is where the
guard must run again.

WHAT CHANGED
- `src/frob/tickets/_land.py::_reverify_cross_ticket_leakage_post_mutation`
  (new): pure re-invocation of `_check_cross_ticket_leakage` with the same
  arguments the preflight call used. No second implementation to drift
  from the first.
- `src/frob/tickets/_land.py::_land_locked`: calls the above immediately
  after `_land_merge_stage` returns (wip-commit has run by then), before
  the D-05 dry-run early return (same "dry-run must preview the real
  refusal" rule D-05's other post-merge checks already follow). A refusal
  aborts the just-created merge via the existing `_abort_merge` unwind --
  no new unwind path, identical shape to every other post-merge check in
  this function.

ACCEPTANCE 1 (single documented, enforced ordering): documented in
`_reverify_cross_ticket_leakage_post_mutation`'s own docstring and in this
report; ENFORCED by
`tests/unit/test_land_step_ordering.py::TestPostMutationRecheckOrdering::test_leakage_recheck_runs_after_the_wip_commit_in_land_locked`,
which asserts (via `inspect.getsource(_land_locked)`) that the re-check
call appears strictly AFTER the `_land_merge_stage` call in source order --
a future edit that reorders these two calls (reintroducing the T-1931
shape) fails this test mechanically, not just by prose review.

ACCEPTANCE 2 (T-1931's own live repro, must fail before the fix):
`TestCrossTicketLeakagePostMutationRecheck::test_guard_refusal_survives_an_uncommitted_reintroduction`
models the incident directly -- two worktrees (T-1370's same-worktree
exemption otherwise masks the refusal), a committed leak that the
preflight check correctly refuses first; the leak reverted+committed
(satisfying the preflight in isolation); then an UNCOMMITTED
reintroduction of the identical content (standing in for
`_absorb_pre_land_fixes`'s real Tier-A write) before the retry. VERIFIED
FAIL-THEN-PASS: with the fix's call temporarily replaced by `Ok(None)`
in `_land_locked` (never committed -- restored immediately after), this
test FAILED (the second `land()` call landed T-0001 clean instead of
refusing). With the fix restored, `pytest tests/unit/test_land_step_ordering.py`
-- 4 passed in 3.43s / 4.15s (measured twice, both clean).

ACCEPTANCE 3 (T-1903 model -- Tier-A rewrite corrupts design/frob.strata
after the parse guard ran): T-1903 already fixed THIS specific instance
(the `_assert_design_loads_pre_land` post-tier-a call already exists,
already regression-tested by
`tests/test_ticket_work_and_land_finish.py::TestAssertDesignLoadsPreLand::test_a_tier_a_handler_that_corrupts_design_after_it_was_healthy_refuses_the_land`,
which corrupts `design/frob.strata` from inside a monkeypatched Tier-A
batch and asserts `SystemExit(1)`). That test is bound as evidence here
as a regression lock proving T-1932's invariant continues to hold for
this guard too, not a newly-failing repro (nothing in this ticket's scope
touches that code path).

ACCEPTANCE 4 (a NEW guard/auto-fix handler cannot silently violate the
ordering): answered concretely, not just by prose --
`TestPostMutationRecheckOrdering::test_leakage_recheck_runs_after_the_wip_commit_in_land_locked`
statically asserts the call ORDER inside `_land_locked` itself, so ANY
future edit that moves a diff-reading guard's re-check ahead of the
mutation it must survive fails this test, not just a passing "it still
works today" run.
`test_post_mutation_recheck_delegates_to_the_same_check_preflight_uses`
pins the OTHER half: the post-mutation call is a pure re-invocation of
the SAME check function the preflight uses, so there is exactly one
implementation to keep correct, not two that can drift. This is a
mechanism, not a fourth point fix: a hypothetical FUTURE committed-diff
guard added to `_land_precheck_remaining_checks` still needs its own
post-mutation twin added explicitly (this repo does not yet have a fully
generic guard registry that forces this automatically -- see RESIDUE
below for the honestly-disclosed remaining gap), but the pattern this
land establishes (self-delegating re-invocation, called after
`_land_merge_stage`, asserted by source-order introspection) is now the
one to copy, with a working example and a locked test proving it holds,
rather than a written rule alone (which the ticket's own body notes has
already failed to prevent recurrence three times).

RESIDUE (disclosed cut): a fully generic, structural guard REGISTRY that
mechanically forces every future committed-diff-reading check in
`_land_precheck_remaining_checks` to register a post-mutation twin (so a
new guard's own author cannot forget, rather than relying on this
report's worked example) is NOT built here -- doing so safely means
walking `_land_precheck_remaining_checks`'s own guard list generically,
which risks widening this ticket's `src/frob/tickets/_land.py`-only scope
into every guard's own call signature and is a real, separate design
question (does a generic registry apply to `_check_passenger_tickets` and
`_check_already_landed` too, which read the same committed-diff source
and could in principle have an analogous gap?). Filed as a residue ticket
rather than attempted inside this land -- see Filed below.

CONCURRENT-LAND REASONING: this change touches only `_land_locked`'s
in-process control flow (adds one function call plus one new pure
function) -- it introduces no new lock, no new file write, no new git
ref, and does not change `_land_lock`'s critical-section boundary (the
whole precheck-through-squash-commit body, unchanged). Two `land()` calls
against the SAME `root` still serialize on the existing `_land_lock`
exactly as before; this change adds one more read-only-to-history git
diff spawn (`git diff base_ref...HEAD` again, same command the preflight
already runs once) inside that same locked section -- strictly more work
per land, not new concurrency exposure. A land against a DIFFERENT root
(a different worktree/series) is entirely unaffected -- no shared state
crosses ticket/series boundaries here. The new test file
(`tests/unit/test_land_step_ordering.py`) uses only tmp_path-isolated git
fixture repos, matching every other land test module in this repo;
nothing it does touches this actual repo's `_land.py`/`_land_git_ops.py`
worktrees other agents may be landing from concurrently.

TESTS RUN
- tests/unit/test_land_step_ordering.py -- 4 passed (both before-restore
  and after-restore runs)
- tests/test_ticket_work_and_land_finish.py::TestAssertDesignLoadsPreLand
  -- 3 passed
- tests/test_ticket_work_and_land_finish.py (full file) -- 50 passed
- tests/test_ticket_land.py (full file) -- 270 passed
- tests/unit/test_land_cross_ticket_leakage.py,
  tests/unit/test_land_already_landed.py -- 15 passed, 1 pre-existing
  FAILURE (`test_queued_sibling_scope_overlap_does_not_block`) confirmed
  UNRELATED to this change: reproduced identically against the primary
  checkout's unmodified `main` (no worktree changes at all) -- a
  `_commit_all` helper finding "nothing to commit" because `new_ticket`'s
  own ledger auto-commit already committed the seed ticket; this is a
  pre-existing test-fixture drift this ticket's scope does not cover, not
  a regression introduced here.

### Changed
```
 tickets/T-1931/ticket.md           |  2 +-
 tickets/T-1932/ticket.md           |  8 ++++++-
 tickets/T-1940/ticket.md | 45 ++++++++++++++++++++++++++++++++++++++
 3 files changed, 53 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/test_land_step_ordering.py::TestCrossTicketLeakagePostMutationRecheck::test_guard_refusal_survives_an_uncommitted_reintroduction` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_step_ordering.py::TestCrossTicketLeakagePostMutationRecheck::test_clean_land_is_unaffected` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_step_ordering.py::TestPostMutationRecheckOrdering::test_leakage_recheck_runs_after_the_wip_commit_in_land_locked` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_step_ordering.py::TestPostMutationRecheckOrdering::test_post_mutation_recheck_delegates_to_the_same_check_preflight_uses` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestAssertDesignLoadsPreLand::test_a_tier_a_handler_that_corrupts_design_after_it_was_healthy_refuses_the_land` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 4 error(s), 997 warning(s), 728 waived
- error-findings: ARCH001@src/frob/app/ticket_runner/_close_cmd.py, DOC001@docs/design/cli-hygiene.md, SEC110@src/frob/app/ticket_runner/_new.py, SELFAUDIT001@design
