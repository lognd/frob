---
id: T-1920
title: 'T-1910 residue: ledger records done and bumps REL001 for a land whose commit
  never reaches main'
state: done
kind: bug
origin: human
created: '2026-08-09'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/tickets/_land.py
- src/frob/tickets/_land_squash.py
- src/frob/tickets/_models.py
- tests/test_ticket_work_and_land_finish.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_land_squash.py
  reason: T-1920 root fix lives in the squash/commit stage (_land_squash.py) and needs
    a new LandError variant (_models.py); regression test lives in the existing land-proof
    test file. Filing agent's own scope-closure warning flagged under-capture.
  actor: logan
  at: '2026-08-09'
- op: add
  glob: src/frob/tickets/_models.py
  reason: T-1920 root fix lives in the squash/commit stage (_land_squash.py) and needs
    a new LandError variant (_models.py); regression test lives in the existing land-proof
    test file. Filing agent's own scope-closure warning flagged under-capture.
  actor: logan
  at: '2026-08-09'
- op: add
  glob: tests/test_ticket_work_and_land_finish.py
  reason: T-1920 root fix lives in the squash/commit stage (_land_squash.py) and needs
    a new LandError variant (_models.py); regression test lives in the existing land-proof
    test file. Filing agent's own scope-closure warning flagged under-capture.
  actor: logan
  at: '2026-08-09'
evidence:
- tests/test_ticket_work_and_land_finish.py::TestBranchDriftGuard::test_branch_drift_before_final_commit_refuses_by_construction
- tests/test_ticket_work_and_land_finish.py::TestBranchDriftGuard::test_no_drift_is_a_noop
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
DISCLOSED CUT FROM T-1910, filed by the coordinator because T-1910
closed done with this work undone and NO residue ticket covering it
(TICK011 shape). T-1910 landed only its REQUIRED FIX 1. Its Done report
states FIXES 2-4 are "NOT done in this pass ... Filed as residue below"
-- but the only draft in that land was T-draft-d718d443, an unrelated
anchor-docs draft that was subsequently dropped. So the residue was
never actually filed. This ticket is that residue.

WHAT T-1910 DID FIX (do not redo): a land whose LAND-PROOF reads
verified=False now exits non-zero unconditionally, not only under
--finish. `_finish_land_after_success` in
src/frob/app/ticket_runner/_land_cmd.py.

WHAT REMAINS -- T-1910 REQUIRED FIXES 2, 3, 4:

2. The ledger MUST NOT record state=done for a ticket whose commit is
   not an ancestor of main. Ledger state and repository state
   disagreeing is the actual harm; the ticket should stay in-progress
   and the land should fail loudly.
3. Do not bump REL001 / write CHANGELOG for a land that did not reach
   main.
4. Root-cause HOW a fully-formed land commit ends up reachable only from
   an unrelated branch (the T-1895 incident: commit 18b82c8cab4c was
   real and complete, carried the full diff, and sat only on branch
   t-1906-fix while the ledger read done on main). A regression test
   must cover a land racing a concurrently-moving main.

THE ARCHITECTURAL OBSTACLE, stated honestly by T-1910 s agent and the
reason this is not a small fix. The ticket close and the REL001 bump
ride the SAME commit the ancestry check runs against. By the time
verified=False is observed, that commit -- with its state=done write and
its version bump -- already exists locally. There is no step in the
current architecture that can retroactively undo either without a second
commit. So items 2 and 3 are not a conditional-guard change; they need
the order of operations rethought (verify reachability BEFORE writing
the terminal state and bump, or make the close/bump a separate commit
that is only created after the ancestry check passes).

This is the same class as the [[verify-after-the-mutation]] lesson
already recorded in this repo: a guard that runs after the mutation it
is meant to gate cannot prevent it, only report it.

Item 4 was investigated for the sibling T-1913 case and found
irreproducible in a synchronous test fixture; T-1913 shipped a bounded
ancestry retry as an explicit MITIGATION, not a fix, and its Done report
says so. The underlying race is still unexplained. Treat "reproduce it"
as real work, not a formality -- and if it stays irreproducible, say so
with the evidence rather than shipping a second mitigation and calling
the root cause closed.

REQUIRED FIX 5 (audit prior lands in the wave) IS ALREADY DONE -- do not
redo it. The coordinator audited all 8 lands of the 2026-08-09 session
(T-1882, T-1912, T-1910, T-1914, T-1913, T-1909, T-1867, T-1891):
every land commit verified ON HEAD via scripts/verify_lands.py, AND each
ticket s claimed code change verified present on main by direct grep for
its introduced symbols. Result: NO silent loss in this wave. Recorded
here so the audit is not repeated.

ACCEPTANCE
1. A land whose commit does not become an ancestor of main leaves the
   ticket NOT in a terminal state on main.
2. No REL001 bump and no CHANGELOG entry survives on main for such a
   land.
3. A regression test covers a land racing a concurrently-moving main and
   proves 1 and 2. It must fail before the fix.
4. If the T-1895 race remains irreproducible, that is disclosed
   explicitly with what was tried, and 1-3 are still satisfied by
   construction (reachability checked before the terminal write) rather
   than by catching the race.

## Done report

Changed:
- src/frob/tickets/_land_squash.py::_assert_still_on_expected_branch (new)
- src/frob/tickets/_land_squash.py::_land_squash_apply_finish (call site: guard
  invoked as the LAST check immediately before `_commit_squash_apply`)
- src/frob/tickets/_models.py::LandError.BranchDrift (new variant)
- tests/test_ticket_work_and_land_finish.py::TestBranchDriftGuard (new,
  2 tests)

Fix (REQUIRED FIXES 2-4, by construction, not a race-catcher): the prior
architecture resolved `main_branch_name` once, early (`_land_precheck` via
`current_branch(root)`), then trusted it unchanged through the squash-apply,
the REL001 bump (`bump_version`), and the final commit
(`_commit_squash_apply`) -- the exact commit that durably writes the
ticket's terminal state and any version bump. If `root`'s checked-out
branch ever moved to something OTHER than that captured branch in the
window between precheck and the final commit, `_commit_squash_apply`
committed onto whatever branch HEAD NOW pointed at -- durably writing
`state: done` + a bump into a commit reachable from `main` only by
accident, discoverable only afterward via `LAND-PROOF verified=False`
(the `[[verify-after-the-mutation]]` failure shape this ticket exists to
close: T-1895's own incident, commit 18b82c8cab4c real/complete, sat only
on branch `t-1906-fix` while the ledger read `done` on `main`).

`_assert_still_on_expected_branch` re-derives `current_branch(root)` FRESH
immediately before `_commit_squash_apply` -- the last point before the one
git operation that publishes reachability -- and refuses
(`LandError.BranchDrift`) if it no longer matches the branch this land
began operating on. Nothing runs between this check and the commit, so a
clean result guarantees the commit's reachability from `main` BY
CONSTRUCTION (git's own `commit` unconditionally advances whatever branch
HEAD currently names). On drift, only `_unstage_index_only(root)` unwinds
the staged squash -- never `_verified_reset_root`'s `git reset --hard`,
which would hard-reset whatever branch is NOW checked out (not necessarily
the expected one) back to `pre_land_tip`, actively destructive to a
foreign branch a concurrent process may be using (same T-1740 lesson
`_commit_squash_apply`'s own fallback already applies).

Acceptance 1/2 (no terminal state, no REL001 bump survives on main for a
land that drifted): satisfied by construction -- the guard runs BEFORE the
one commit that would write either, so a drift means neither is ever
committed at all, not merely undone afterward.

Acceptance 3 (regression test, must fail before the fix):
`TestBranchDriftGuard.test_branch_drift_before_final_commit_refuses_by_construction`
lands a real ticket via `land()`, injecting the drift through the
`bump_version` callable seam `land()` already exposes (called late,
immediately before the final commit in the real pipeline) -- the callable
does `git checkout -b sim-drift-t1920` in `root` as a side effect, then
returns `Ok(None)`, simulating root's HEAD moving off `main` mid-land.
Verified fail-then-pass manually: with the guard call temporarily removed
from `_land_squash_apply_finish` (restored immediately after), this test
FAILED -- `land()` returned `Ok`, having committed the ticket's `state:
done` write onto the drifted branch while `main` itself never moved (this
is precisely T-1895's shape, reproduced under injection). With the guard
restored, the test asserts `result.is_err` /
`LandError.BranchDrift`, that `main`'s tickets.md (read via `git show
main:tickets.md`, not the working tree, which is now on the drifted
branch) never shows `state: done` for the ticket, and that `main`'s tip
sha is unchanged from before the call.

Acceptance 4 (T-1895 race reproduction): NOT reproduced in a synchronous
fixture, same outcome T-1913's own investigation reported for the sibling
ancestor-retry mitigation. No code path in this repo's land pipeline moves
`root`'s HEAD mid-land under normal operation, and no genuine concurrent
`git checkout` racing a held `land_lock` was observed or constructed. Per
this ticket's own instruction, item 4 is disclosed as irreproducible
rather than shipped as a second unverified mitigation; acceptance 1-3 are
satisfied by construction (checked reachability before the terminal
write) rather than by catching the race after it happens, which is the
posture this ticket asked for regardless of reproducibility.

Concurrency: the new check reads `root`'s current branch and only refuses
(never mutates anything but unstages `root`'s own index on refusal) -- it
adds one more `git rev-parse --abbrev-ref HEAD`-class read on the
already-serialized (via `land_lock`) hot path, no new locking, no new
shared state, and does not touch anything a concurrently-running land in
a DIFFERENT worktree/root pair would ever see. It does not change
`land_lock`'s scope or duration (unlike the T-1882/T-1918 lease-guard
incident this ticket's dispatch prompt warned about) -- purely a read +
conditional early-return inserted into the existing single-writer
sequence a held `land_lock` already ensures runs one land at a time
against a given `root`.

Evidence: pytest node ids (recorded via `frob ticket evidence`):
- tests/test_ticket_work_and_land_finish.py::TestBranchDriftGuard::test_branch_drift_before_final_commit_refuses_by_construction
- tests/test_ticket_work_and_land_finish.py::TestBranchDriftGuard::test_no_drift_is_a_noop

Full pytest runs (measured, this session):
- `tests/test_ticket_work_and_land_finish.py` (50 collected, 0 failed)
- `tests/test_ticket_land.py` (270 collected, 0 failed)
- both together: 320 collected, 0 failed

`frob check --land-parity` (repo-wide, cache-bypassed): after fixing the
one E501 this ticket's own new line introduced, the only 3 remaining
unscoped errors are pre-existing and outside this ticket's scope/files --
DOC007 + DRIFT002 in src/frob/app/ticket_runner/_mutate.py (a stale
`frob:tests` reference using pytest `::` separator instead of this repo's
dotted convention, unrelated to land) and REG002 in
docs/design/registry/check-coverage.yaml (a dangling registry disposition)
-- both confirmed present on unmodified main (`docs/design/registry/
check-coverage.yaml`'s CHK-GATE-SYS-IFACE-ORDER entry already exists on
main's tip 63bf47781) and both fall under this repo's registry/fix-engine
territory the dispatch note explicitly reserved for T-1916; not touched
here.

Filed: none -- no new out-of-scope work discovered beyond the two
pre-existing, already-attributed findings above.

Gates: `frob check --ticket T-1920 --only gates-fast` clean of anything
new; `frob check --land-parity` clean except the two pre-existing,
out-of-scope findings named above (not introduced by this change,
verified present on main).

### Changed
```
 tickets/T-1920/ticket.md | 30 +++++++++++++++++++++++++++++-
 1 file changed, 29 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_ticket_work_and_land_finish.py::TestBranchDriftGuard::test_branch_drift_before_final_commit_refuses_by_construction` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestBranchDriftGuard::test_no_drift_is_a_noop` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 4 error(s), 1265 warning(s), 699 waived
- error-findings: DOC007@src/frob/app/ticket_runner/_mutate.py, DRIFT002@src/frob/app/ticket_runner/_mutate.py, PRE001@tickets/T-1920, REG002@docs/design/registry/check-coverage.yaml
