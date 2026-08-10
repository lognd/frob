---
id: T-1910
title: frob ticket land can report 'landed as <sha>' for a commit that never reaches
  main, silently losing the work
state: queued
kind: bug
origin: agent
created: '2026-08-09'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
MEASURED 2026-08-09, coordinator, on main. THIS IS A DATA-LOSS BUG.

'frob ticket land T-1895 --worktree .../t1895-t1893' printed:

  land T-1895: landed as T-1895 at 18b82c8cab4c74d2f5457b738486a129321602e8 (14 file(s) changed)
  land T-1895: REL001 bumped to 0.419.0
  LAND-PROOF: ticket=T-1895 commit=18b82c8... is_ancestor_of_main=False state_on_main=done verified=False

The commit 18b82c8cab4c was REAL and complete -- 'git show' confirms it carries the full diff. But it never became an ancestor of main. 'git branch --contains 18b82c8cab4c' places it on the UNRELATED branch 't-1906-fix' only. Meanwhile the ledger was updated: tickets/T-1895/ticket.md read 'state: done' on main while main's source still had the duplicate the ticket existed to delete and lacked the extraction it existed to create.

Net effect: a ticket marked DONE, a real commit object, a CHANGELOG entry, a REL001 version bump to 0.419.0 -- and ZERO of the actual code change on main. The work was silently lost. I recovered it by cherry-picking 18b82c8cab4c back onto main (commit 53ab0d671); without that it would have stayed lost behind a done ticket, which is the worst possible state: the queue says the problem is solved and it is not.

WHAT SAVED IT, AND WHAT ALMOST DID NOT. LAND-PROOF printed the truth (is_ancestor_of_main=False, verified=False). I initially DISBELIEVED it -- I ran an immediate ancestry check and grep, read a transient state as confirmation, and recorded a 'false negative' note against T-1884 (since retracted). The signal was correct and the operator overrode it. That is precisely why the next fix matters more than the diagnosis.

REQUIRED FIXES:
1. A land whose LAND-PROOF is verified=False MUST NOT report success. It must exit non-zero and say the work did not reach main, in the same breath as 'landed as <sha>' -- currently those two lines contradict each other and the optimistic one comes first.
2. The ledger MUST NOT record state=done for a ticket whose commit is not an ancestor of main. Ledger state and repository state disagreeing is the actual harm here; the ticket should stay in-progress and the land should fail loudly.
3. Do not bump REL001 / write CHANGELOG for a land that did not reach main.
4. Root-cause the mechanism: determine HOW the land commit ended up reachable only from t-1906-fix. Likely candidates are the shared-branch/worktree handling and the concurrent lands running during this wave (several lands were in flight against sibling worktrees cut from different main tips). A regression test must cover a land racing a concurrently-moving main.
5. AUDIT: I cannot rule out that OTHER tickets in this wave landed the same way. Every ticket closed during this session should have its landed commit checked with 'git merge-base --is-ancestor <sha> main' and its claimed code change verified present. Report the audit result -- a second silent loss is more likely than not.

Related: T-1884 (LAND-PROOF correctness), T-1903 (post-mutation verification), T-1907 (unknown read as clean).