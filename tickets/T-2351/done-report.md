## Done report

ROOT CAUSE (independent of T-2328's fix, per coordinator's narrowing --
did not assume T-2328's stale-declared-scope fix moved this defect, and
confirmed it did not): apply_tier_a_fixes (src/frob/gates/_fix_engine.py)
always runs BEFORE frob ticket land's own pre-land wip-commit step
(_land_cmd.py::_absorb_pre_land_fixes/_land_core_prepare, its own
comment: "any file rewritten here becomes an ordinary uncommitted change
land()'s own wip-commit step already picks up, so this needs no separate
commit"). When a Tier-A handler (SYS100) writes its own rewrite to
design/frob.strata and that fix is then disqualified (correctly OR
incorrectly, per T-2328) by filter_fixes_by_scope_and_lease,
_revert_fix_file ran an unconditional `git checkout -- <file>`, which
restores to HEAD -- and at this point in the pipeline HEAD is still the
PRE-TICKET branch tip, since the ticket's own work is still entirely
uncommitted. This silently discarded the ticket's own real, in-scope,
uncommitted edit to that file along with the handler's disqualified
rewrite, with no error, no refusal, and a log line ("SKIPPED SYS100
... under T-2303's live lease") that reads as "the sync fixer didn't
touch this", not "your own edit is being thrown away".

This explains all three live reproductions already on record (T-2328's
own attachments):
  T-2194  edit uncommitted at land time              -> dropped
  T-2329  same edit, re-applied, uncommitted          -> dropped again
  T-2323  same edit, committed to the branch FIRST    -> survived
A pre-committed edit was always safe because HEAD already contained it;
an uncommitted one was destroyed because HEAD did not yet.

FIX:
1. src/frob/gates/_fix_engine.py::_snapshot_dirty_files(root) -- new,
   captures the exact on-disk bytes of every TRACKED file `git status
   --porcelain` shows as dirty (modified/staged), right now. Untracked
   files are deliberately excluded (a Tier-A handler only ever acts on
   tracked source).
2. apply_tier_a_fixes calls this ONCE, before its handler loop runs any
   Tier-A rewrite, and threads the resulting dict to
   filter_fixes_by_scope_and_lease as a new `pre_fix_snapshot` parameter
   (default None, preserving old behavior for every direct caller that
   doesn't pass one -- e.g. every pre-existing unit test).
3. _revert_fix_file (src/frob/gates/_fix_engine_scope.py): when
   `pre_fix_snapshot` has an entry for the disqualified file, restores
   those exact bytes (the ticket's own pre-handler state) instead of
   running `git checkout --`. Falls back to the old checkout-to-HEAD
   behavior when there is no snapshot entry (nothing was dirty before
   Tier-A touched the file -- HEAD and pre-handler state are identical,
   so checkout-to-HEAD is provably correct there) or `pre_fix_snapshot`
   is None. Never a loud refusal in this implementation -- capture is
   always possible (reading current on-disk bytes cannot fail short of
   an OSError, logged and swallowed exactly like the pre-existing
   checkout-failure path), so the "refuse loudly if it cannot capture
   safely" branch the dispatch allowed for was not needed.

The one pre-existing incorrect assumption this also corrects (removed
from _revert_fix_file's own docstring): "a file scope/lease disqualifies
can never also carry the landing ticket's own legitimate uncommitted
work" -- false exactly in the live-lease-wins-over-declared-scope case
this module exists for, which is what made the bug reachable.

POSITIVE CONTROLS (all three required, non-negotiable per dispatch):
1. In-scope file with UNCOMMITTED edits reaches the land commit:
   test_uncommitted_in_scope_edit_survives_a_disqualified_tier_a_revert
   reproduces the incident directly (real uncommitted edit, not a
   pre-committed false-green) and confirms it survives a disqualified
   Tier-A revert.
2. Must-still-pass, genuinely out-of-scope excluded:
   test_out_of_scope_fix_is_reverted_and_reported (unchanged, T-2284's
   own test) still passes -- this fix changes WHAT a revert restores to,
   never WHETHER an out-of-scope/leased fix gets reverted.
3. Must-still-pass, SYS100/live-lease behavior still functions:
   test_live_leased_file_skipped_even_when_in_landing_scope and
   test_narrowed_live_lease_wins_over_stale_declared_scope (T-2328's own
   test) both still pass -- a genuinely live lease still wins over the
   landing ticket's own broader scope.
   test_committed_edit_is_unaffected_by_a_disqualified_tier_a_revert
   additionally reproduces T-2323's own discriminating comparison as a
   permanent regression test.

MUST-FAIL-THEN-PASS, verified manually (not --check-repro, which cannot
produce a verdict pre-land -- no committed parent sha without the fix
exists yet): committed the fix+tests as a checkpoint
(cd0744cf8), then `git checkout HEAD~1 -- src/frob/gates/_fix_engine.py
src/frob/gates/_fix_engine_scope.py` to restore the pre-fix code with
the new tests still present -- all three new tests failed with
ImportError (the pre-fix module has no _snapshot_dirty_files symbol at
all, let alone the pre_fix_snapshot-aware revert). Restored the fix
(`git checkout HEAD -- ...`) and reran: all 43 tests in
TestFixEngineScopeLease+TestFixEngineTierA pass.

BOOKKEEPING: added a clarifying attachment to T-2328 (already `done`)
stating plainly that its landed fix closed an adjacent, real bug but did
NOT close the work-loss defect named in its own title -- this ticket
(T-2351) carries that forward and closes it.

### Changed
```
 src/frob/gates/_fix_engine.py       |  59 ++++++++++++-
 src/frob/gates/_fix_engine_scope.py |  81 +++++++++++++++---
 tests/test_gates.py                 | 165 ++++++++++++++++++++++++++++++++++++
 tickets/T-2351/ticket.md            | 113 +++++++++++++++++++++++-
 4 files changed, 402 insertions(+), 16 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestFixEngineTierA::test_pre_fix_dirty_snapshot_captures_uncommitted_content` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineScopeLease::test_uncommitted_in_scope_edit_survives_a_disqualified_tier_a_revert` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineScopeLease::test_committed_edit_is_unaffected_by_a_disqualified_tier_a_revert` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineScopeLease::test_out_of_scope_fix_is_reverted_and_reported` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineScopeLease::test_live_leased_file_skipped_even_when_in_landing_scope` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineScopeLease::test_in_scope_fix_is_kept_unchanged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineScopeLease::test_narrowed_live_lease_wins_over_stale_declared_scope` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, AFFECT001@src/frob/gates/_fix_engine.py, AFFECT001@src/frob/gates/_fix_engine_scope.py, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/release/_cli.py, COV001@scripts/fleet_status.py, COV001@src/frob/tickets/_land_git_ops.py, COV001@src/frob/tickets/_leases.py, COV001@src/frob/verify/_drain.py, COV001@src/frob/verify/_quarantine.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, DOC001@docs/commands/release.md, DOC002@scripts/fleet_status.py, DOC002@src/frob/app/verify_runner.py, DOC002@src/frob/verify/_drain.py, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, E501@/home/logan/projects/frob/.claude/worktrees/t-2351/src/frob/verify/_worker.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_new.py, PRE001@tickets/T-2351, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/tickets/_leases.py, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md
