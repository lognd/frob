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
body_changes:
- mode: append
  reason: 'second sighting F-068 plus the root cause: the ledger merge driver was
    retired on a v2-disjointness premise that concurrent edits to one ticket falsify;
    driver still registered but unrouted'
  actor: logan
  at: '2026-09-05'
  old_length: 4381
  new_length: 8872
- mode: append
  reason: 'F-100 broadens part B: any malformed ledger file reports not-found, not
    just conflict markers; three states are collapsed into one wrong message'
  actor: logan
  at: '2026-09-05'
  old_length: 8872
  new_length: 10842
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



SECOND SIGHTING AND A ROOT CAUSE, 2026-09-05. logand.app-v2 F-068 is F-048 with
a different field set, and chasing it found the mechanism.

F-068's report: `git merge main` into worktree t-0068 conflicted in
tickets/T-0068/ticket.md because MAIN carried the coordinator's `scope` and
`accept` mirror commits while the BRANCH carried the agent's start/evidence/done
edits. The land then aborted with "frontmatter is not valid YAML" and "ticket
not found in the worktree's store". Resolved by hand, keeping the branch side.

So it is not specifically the evidence block (F-048's field): it is ANY
concurrent edit to one ticket's own frontmatter from two sides.

THE ROOT CAUSE IS A RETIRED MERGE DRIVER, AND ITS RETIREMENT RESTED ON A
PREMISE THESE TWO REPORTS FALSIFY. From this repo's .gitattributes:

    # T-1258/T-2356: this repo cut over to ledger v2 (disjoint tickets/T-####/
    # directories, ordinary git objects git's native per-file 3-way merge
    # already resolves correctly). tickets.md/tickets-archive.md and the
    # frob-ledger merge driver they needed are gone ...
    # The merge driver itself (`frob ticket merge-driver`, splice_ledger) is
    # NOT removed from frob's own source -- other repos using frob may still
    # be on v1/monofile mode ...; only THIS repo's now-inert data files and
    # the .gitattributes lines that routed them through the driver are
    # retired here.

The v2 argument was that per-ticket directories are disjoint, so git's native
3-way merge suffices. That holds for disjointness BETWEEN tickets. It does not
hold for TWO SIDES EDITING ONE TICKET'S OWN FILE -- which is the fleet's normal
operating mode: the coordinator mirrors scope/accept on main while an agent
edits state/evidence in its worktree. Git then line-merges YAML frontmatter and
can leave conflict markers inside it, which is how a structured record becomes
unparseable.

MEASURED HERE 2026-09-05: the driver still exists and is still REGISTERED --
    merge.frob-ledger.driver        uv run frob ticket merge-driver %O %A %B
    merge.frob-ticket-ledger.driver uv run frob ticket merge-driver %O %A %B %P
-- only the .gitattributes routing was retired. So the machinery is present and
unwired.

DO NOT SIMPLY RE-ADD THE ROUTING. Two reasons, and the second is already
documented in the same file:
  1. `splice_ledger` was written for the v1 MONOFILE. Whether it handles a v2
     per-ticket file at all is unverified -- check before assuming.
  2. The T-1873 note directly below argues AGAINST a custom driver for exactly
     this class: git's built-in `merge=union` was preferred over a new frob
     driver because a driver "needs per-clone `git config` registration -- a
     worktree that skipped that one-time setup silently falls back to the
     default (conflicting) driver, which is exactly the failure mode this
     ticket exists to close." That argument applies here in full, and it is
     sharper than it looks: a fresh clone or a new worktree that missed the
     registration gets the CONFLICTING behaviour silently, so the fix would
     work on the machine that installed it and fail everywhere else.

SO EVALUATE, IN THIS ORDER:
  (a) a built-in git strategy that needs no registration (union is wrong here
      -- frontmatter is not append-only -- but check whether an attribute-level
      option covers the structured case)
  (b) making the conflict IMPOSSIBLE rather than merge-able: if the coordinator
      never wrote scope/accept mirrors to main while a branch held the ticket,
      there would be nothing to conflict. F-068's own suggestion -- "union of
      evidence, branch wins on state" -- is a semantic rule that could equally
      be enforced by WHO WRITES WHAT, WHEN, instead of by a merge driver.
  (c) re-routing through a v2-aware driver, accepting the registration
      fragility and mitigating it (fail loudly when unregistered rather than
      falling back silently).
State which and why. (b) deserves real consideration: it removes the failure
mode instead of resolving it, and this repo already has the mirror commits as a
distinct, controllable code path.

WHATEVER IS CHOSEN, THE LOADER FIX FROM THE MAIN BODY STILL STANDS
INDEPENDENTLY: a ticket file containing conflict markers must be reported as an
unresolved merge naming the file and field, never as "frontmatter is not valid
YAML" and never as "ticket not found in the worktree's store". Both of those
messages sent this reporter looking in the wrong place.



BROADENED BY F-100, 2026-09-05: "a malformed ledger file makes frob report
'ticket not found in the worktree's store'".

Part B of this ticket already required that CONFLICT MARKERS be reported as an
unresolved merge rather than as MalformedFrontmatter or as "ticket not found in
the worktree's store". F-100 shows the misdiagnosis is not specific to conflict
markers: ANY malformed ledger file produces the not-found message.

SO PART B IS BROADER THAN FILED, AND SHOULD BE IMPLEMENTED THAT WAY. The ticket
file EXISTS; frob can see it; it simply cannot parse it. Reporting that as "not
found" tells the operator the opposite of the truth and sends them looking for a
missing file, a wrong id, or a wrong worktree -- none of which is the problem.
Three distinct states are being collapsed into one message:
    the file is absent
    the file is present and unparseable (malformed, for any reason)
    the file is present and parseable but holds no such ticket
Only the first is "not found". The second is the one that occurs after a bad
merge, a truncated write, or a killed process, and it is exactly when a
misleading message costs the most, because the repository is already in a state
the operator did not intend.

MINIMUM FIX, independent of the mirror work in part A and worth landing on its
own: distinguish the three states and name the file and the parse failure. If
conflict markers are present, say so specifically -- that detail turns a
mystifying error into a ten-second fix, and it is why part B was separated from
part A in the first place.

MEASURED CONTEXT FROM THIS DRIVE: this repo's own memory records that a single
malformed character in ledger frontmatter has taken every gate down before,
which is why hand-editing the ledger is forbidden. The tool's own recovery path
therefore has to be legible: an operator hitting a malformed ledger is, by
definition, already having a bad day and cannot afford a message that points
away from the cause.
