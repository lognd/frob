---
id: T-1934
title: Nothing detects finished-but-unlanded ticket work on a branch, and sweep's
  remove heuristic is inverted against it
state: queued
kind: bug
origin: human
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
MEASURED 2026-08-09. Exactly one confirmed leak right now, plus two
near-misses recovered by hand this session. The count is small only
because I went looking manually; nothing in the toolchain would have
told me.

THE CONFIRMED LEAK: T-1315. A complete done-report, the design doc
(docs/design/test005-ratchet-schedule.md) and the frob.toml change are
committed on branch `runner-wiring`. The branch copy of
tickets/T-1315/ticket.md reads `state: in-progress`. None of it is on
main. T-1315 reads `queued` on main right now, so the next agent
dispatched to it would redo the whole thing from scratch.

THE NEAR-MISSES: T-1851 and T-1556 sat finished on branch
`gate-internals` behind dead-agent leases for an entire session. They
were recovered today ONLY because I manually noticed the branch was 59
commits ahead and dispatched someone to survey it. Both landed
(f4a0e5032c3e, 16880d5170a2). That recovery was luck, not process.

HOW THE LEAK HAPPENS -- the full chain, all five steps observed:
1. An agent finishes, COMMITS its work (done-report + code) in its
   worktree.
2. It dies before `frob ticket land` -- session end, context exhaustion,
   or the OOM kills this environment is known for.
3. Because everything is committed, the working tree is CLEAN.
4. The lease survives, so the ticket reads in-progress and
   `frob ticket doable` renders it under "already being worked".
   Nobody picks it up. T-1876 improved this (holder-dead leases are now
   flagged) but that surfaces the LEASE, never the WORK.
5. Nothing anywhere compares branch state against main. The work is
   invisible to every command in the toolchain.

THE INVERTED HEURISTIC, and this is the sharp edge:
`frob worktree sweep` decides removability from WORKING-TREE
DIRTINESS. So a worktree full of uncommitted junk is KEPT (kept:dirty),
while a worktree whose agent did everything right -- committed clean,
died before landing -- is marked `removed`. The better an agent behaved,
the more likely its worktree is swept. Today s sweep marked all 13
clean worktrees removable; I only checked them by hand because I was
being cautious, and every one turned out to be superseded. Next time one
will not be.

(Mitigating fact, verified: `git worktree remove` does NOT delete the
branch -- I confirmed no `branch -D` on the sweep path and all 13 branch
refs survived. So this is invisibility plus a bad heuristic, not
immediate data loss. It is still a leak, because nothing ever looks at
those branches again.)

THE DETECTOR IS CHEAP -- pure git plumbing, no test runs, no checkout.
This prototype found the leak in seconds and is the whole idea:

    for b in $(git branch --format="%(refname:short)" | grep -v "^main$"); do
      for f in $(git ls-tree -r --name-only $b | grep -E "^tickets/T-[0-9]+/done-report\.md$"); do
        t=$(echo $f | cut -d/ -f2)
        # flag when $t is NOT terminal on main
      done
    done

Keying on ticket STATE is essential. My first attempt keyed on whether
the done-report path existed on main and returned 186 false positives,
because a done ticket is ARCHIVED to tickets/archive/<id>/ on main. Do
not repeat that mistake -- resolve the ticket s state through the ledger,
including the archive, not through a path test.

REQUIRED
A. A first-class way to ask "what finished work is not on main?" --
   report every branch carrying a done-report, or a branch-local ticket
   state of done, for a ticket that is not terminal on main. Read-only,
   fast, no checkout.
B. `frob worktree sweep` must NOT mark a worktree removable while its
   branch carries unlanded ticket work. Unlanded work outranks
   working-tree cleanliness; today it is not consulted at all.
C. Ideally surfaced where a coordinator already looks --
   `frob ticket doable` already grew a stale-lease warning in T-1876;
   an "N branches carry unlanded work" line belongs in the same place.

DO NOT implement A by auto-landing anything. Landing a dead agent s
branch unattended is how unreviewed work reaches main. Report and let a
human or a dispatched agent decide.

ACCEPTANCE
1. The detector reports T-1315/runner-wiring today. It must FAIL (find
   nothing, or not exist) before the fix.
2. It does NOT report a ticket that is done or dropped on main,
   including archived ones -- assert the 186-false-positive shape
   explicitly as a regression test.
3. It does NOT report a ticket currently being worked by a live agent
   (T-1923/sweep-1919 was correctly excluded from my manual run only
   because I recognised the name -- the tool must key on something real,
   e.g. lease liveness via T-1876 s `lease_staleness_reason`).
4. `frob worktree sweep --dry-run` reports kept, not removed, for a
   clean worktree whose branch has unlanded ticket work.

FOLLOW-ON, do not fold in: T-1315 itself needs recovering from
`runner-wiring`. Do not delete that branch.