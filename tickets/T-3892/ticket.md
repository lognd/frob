---
id: T-3892
title: the scope-mirror writes a ticket to main without its evidence block, so merging
  main back conflicts or leaves conflict markers inside the ledger YAML
state: queued
kind: bug
origin: human
created: '2026-09-05'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Reported as logand.app-v2 FROBLEMS F-048, "real bug: every multi-ticket land
needs a manual ledger repair". This is frob corrupting its own ledger.

THE MECHANISM, as reported and reproduced across seven of their tickets
(T-0019, T-0020, T-0025, T-0011/12, T-0039..T-0042):

  1. A worktree binds evidence to its ticket.
  2. main receives a `chore(tickets): mirror scope T-nnnn from worktree` commit
     that carries the ticket record WITHOUT that evidence list.
  3. Merging main back into the worktree produces a conflict on `evidence:` --
     HEAD has the ids, main has nothing.
  4. TWICE, git auto-merged and left `<<<<<<<` markers INSIDE THE YAML
     FRONTMATTER.
  5. Every `frob ticket` command in that worktree then failed with
     MalformedFrontmatter, and `frob ticket land` reported
     "NotFound: ticket not found in the worktree's store".

THIS REPO DOES THE SAME THING. `git log` on main here carries the identical
commit shape -- "chore(tickets): mirror scope T-3260 from worktree",
"chore(tickets): mirror body T-3820 from worktree" -- so the mirror path is not
specific to their setup.

WHY THIS IS CRITICAL RATHER THAN FRICTION. The standing rule in this repo is
never to hand-edit the ledger, because a single malformed character in
frontmatter takes every gate down -- that has happened here before. This defect
produces exactly that outcome WITHOUT anyone hand-editing anything: frob writes
the partial record, git does the merge, and the ledger ends up syntactically
broken. The guard rule cannot protect against the tool.

AND THE WORSE HALF IS THE QUIET ONE. Conflict markers at least fail loudly. The
report also says "or silently corrupts" -- a git auto-merge of two YAML blocks
can produce a file that PARSES but is wrong: evidence silently dropped, or a
field taking main's value when the worktree's was correct. A ticket that loses
its evidence block and still loads is a done-report waiting to be written
against nothing, which is the exact failure the evidence requirement exists to
prevent.

TWO SEPARATE FIXES ARE NEEDED. Do not conflate them; the second is worth doing
even if the first is delayed.

  A. THE MIRROR MUST NOT WRITE A PARTIAL RECORD. Either carry the whole ticket
     record, or write only the fields it actually changed. Decide which and say
     why. "Only the changed fields" is more surgical but needs the merge to be
     field-aware; "the whole record" is simpler but means main can carry a
     record staler than the worktree's in other fields. Consider whether the
     mirror should refuse when the worktree's record has fields main's copy does
     not, rather than silently narrowing.

  B. THE TICKET LOADER MUST DETECT CONFLICT MARKERS AND SAY SO. A file
     containing `<<<<<<<`, `=======`, `>>>>>>>` at line starts is not malformed
     YAML in any interesting sense -- it is an unresolved merge, and saying that
     turns a mystifying MalformedFrontmatter (and a nonsense "NotFound: ticket
     not found in the worktree's store") into a ten-second fix. This is cheap,
     independent of A, and would have saved the reporter two manual repairs.
     Include the file path and the conflicting field.

MEASURE THE BLAST RADIUS BEFORE FIXING: scan this repo's ledger history for
mirror commits that dropped an evidence block, and report how many tickets on
main currently carry fewer evidence ids than their worktree branch did. If any
LANDED ticket lost evidence this way, its done report cites evidence the ledger
no longer records -- that is a silent integrity failure in closed work, and it
outranks the merge friction.

DO NOT fix this by teaching agents to resolve the conflict by hand. The report
already shows what that costs, and hand-editing the ledger is the thing this
repo forbids.

MUST-FIRE FIXTURES:
  - a ticket file containing merge-conflict markers is reported as an
    unresolved merge, naming the file and field -- not as MalformedFrontmatter
    and not as NotFound
  - a mirror that would drop a field present in the worktree record is caught
MUST-STAY-QUIET:
  - an ordinary mirror of an unchanged ticket still works and produces no
    conflict on merge

ACCEPTANCE
- The A/B split implemented, with the partial-vs-whole-record decision stated.
- The historical scan reported: how many tickets lost evidence to this, and
  whether any of them are closed.
- All fixtures committed.
