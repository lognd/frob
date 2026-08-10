---
id: T-1920
title: 'T-1910 residue: ledger records done and bumps REL001 for a land whose commit
  never reaches main'
state: queued
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
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
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