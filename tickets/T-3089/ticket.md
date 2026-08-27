---
id: T-3089
title: Wire out-of-tree compose+CAS publish into the squash-apply land stage
state: in-progress
kind: feature
origin: human
created: '2026-08-27'
priority: high
blocked_by:
- T-3088
- T-3095
- T-3107
parent: T-3053
tier: story
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land_squash.py
- tests/test_ticket_land.py
- docs/modules/tickets-landing.md
- frob.lock
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_ticket_land.py
  reason: 'T-3089''s fixtures live in tests/test_ticket_land.py because the v2-mode
    land

    fixtures they need (v2_repo, _seed_v2_ticket, _make_closeable, _commit_all)

    are module-local there, and the existing _absorbed_land_report mutation-

    coverage test in that file calls the helper positionally, so the new `stage`

    parameter changes that one call site. src/frob/tickets/_land_compose.py is

    dropped: the compose primitives it holds are already landed (T-3088/T-3107/

    T-3114) and this ticket''s landed subset does not modify them.

    '
  actor: logan
  at: '2026-08-27'
- op: remove
  glob: src/frob/tickets/_land_compose.py
  reason: 'T-3089''s fixtures live in tests/test_ticket_land.py because the v2-mode
    land

    fixtures they need (v2_repo, _seed_v2_ticket, _make_closeable, _commit_all)

    are module-local there, and the existing _absorbed_land_report mutation-

    coverage test in that file calls the helper positionally, so the new `stage`

    parameter changes that one call site. src/frob/tickets/_land_compose.py is

    dropped: the compose primitives it holds are already landed (T-3088/T-3107/

    T-3114) and this ticket''s landed subset does not modify them.

    '
  actor: logan
  at: '2026-08-27'
- op: add
  glob: docs/modules/tickets-landing.md
  reason: 'T-3089''s fixtures live in tests/test_ticket_land.py because the v2-mode
    land

    fixtures they need (v2_repo, _seed_v2_ticket, _make_closeable, _commit_all)

    are module-local there, and the existing _absorbed_land_report mutation-

    coverage test in that file calls the helper positionally, so the new `stage`

    parameter changes that one call site. src/frob/tickets/_land_compose.py is

    dropped: the compose primitives it holds are already landed (T-3088/T-3107/

    T-3114) and this ticket''s landed subset does not modify them.

    '
  actor: logan
  at: '2026-08-27'
- op: add
  glob: frob.lock
  reason: frob ack (AFFECT001 re-verification of the two v2-mode helpers whose parameter
    this ticket renamed) writes its digests into frob.lock; the file is a required
    artifact of this ticket's own doc-drift acknowledgement, not an unrelated edit
  actor: logan
  at: '2026-08-27'
body_changes:
- mode: append
  reason: 'series BM re-scope: the wire-up as planned loses three-way conflict semantics
    and leaves six index-consuming stages unfed; git 2.34.1 has no merge-tree --write-tree'
  actor: logan
  at: '2026-08-27'
  old_length: 2574
  new_length: 4298
- mode: append
  reason: 'series BM: record the post-publish root-resync problem (root is a checked-out
    worktree, so a CAS ref move desynchronizes it) plus the measured pre-fix dirty-window
    baseline and the --no-optional-locks requirement for the acceptance poll'
  actor: logan
  at: '2026-08-27'
  old_length: 4298
  new_length: 6513
- mode: append
  reason: 'series BQ: settle the post-CAS root-resync mechanism and its failure semantics,
    as the ticket body demands before any code'
  actor: logan
  at: '2026-08-27'
  old_length: 6513
  new_length: 10042
designated_repro_test: null
acceptance:
- text: Given a concurrent git status poll during a real land, when the squash-apply
    stage runs, then no intermediate dirty state is observable before the final atomic
    publish
  evidence: []
- text: Given two lands racing the same base tip, when the second reaches publish,
    then it gets the existing DirtyMain-class refusal, not a corrupted ref
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
DECOMPOSITION CHILD 2 of T-3053 (parent epic). BLOCKED BY child 1
(_land_compose primitive must exist first).

Wire `compose_tree_out_of_tree` + `publish_ref_cas` (child 1) into the ONE
narrowest real stage that currently dirties root's shared working tree in a
way siblings can observe mid-land: `_squash_and_splice_ledger` /
`_land_squash_apply` in src/frob/tickets/_land_squash.py, which today runs
`git merge --squash --no-commit` directly against root then leaves it
staged-but-uncommitted while later stages (ledger splice, evidence checks,
REL001 bump) run -- exactly the window T-3066's land was observed staging
into the shared tree.

Replace that stage's mechanism only: compose the squash-merge result as a
tree object out-of-tree (against a scratch index seeded from root's current
HEAD, with the worktree branch's diff applied via `git read-tree`/`git
apply --cached` or equivalent plumbing -- no working-tree checkout), build
the commit object, then `publish_ref_cas` it onto main's branch ref in one
atomic step. If the CAS fails (main moved since land captured pre_land_tip),
refuse with the SAME `DirtyMain`-class error `land()` already raises for a
concurrently-moved tip -- do not invent a new error class for an old
condition.

Every existing guard stays wired unchanged: BUG002 repro ordering,
LAND-PROOF verification, the T-3050 non-QUEUED orphan refusal, the T-3061
pre-land lint gate, ledger splice conflict handling. This ticket changes
WHERE the tree is composed, not what content ends up in it or which checks
run over it.

ACCEPTANCE
- During a `frob ticket land --dry-run` (and a real land), `git -C <root>
  status --porcelain` observed from a SEPARATE process at any point during
  the run shows nothing beyond what was true before the land started, until
  the final atomic publish. Must-fire fixture: a concurrent `git status`
  poll during a land, asserting no intermediate dirty state is ever visible
  (this is the DirtyMain repro T-3066 hit -- reproduce it failing at the
  parent commit, per BUG002 test-first discipline, before the fix).
- A land whose main tip moved between preflight and publish gets the
  existing DirtyMain-class refusal, not a corrupted ref and not a silent
  overwrite of the sibling's commit. Must-fire fixture: two lands racing the
  same base tip.
- All pre-existing land test suites for BUG002/LAND-PROOF/T-3050/T-3061
  still pass unmodified -- must-stay-quiet fixture is the existing suite
  green with zero edits to its assertions.
- Measure land wall-clock before/after under comparable load; report it.


RE-SCOPE NOTICE (2026-08-27, series BM). The plan above is WRONG and must
not be executed as written. Three verified reasons, full detail in T-3107's
body:

1. `compose_tree_out_of_tree` (T-3088) is diff-and-apply against a scratch
   index; `_squash_and_splice_ledger` is a three-way merge whose conflict
   handling (`_check_squash_conflicted` ->
   `_auto_resolve_out_of_scope_conflicts`) carries T-0479 out-of-scope
   ours-resolution, T-1002 union zones, the T-1434 coverage-lock merge and
   T-1637's sibling carry-forward. Substituting one for the other silently
   deletes all of it. "Replace that stage's mechanism only" is not a
   substitution that exists.

2. Six downstream stages in `_land_squash_apply_finish` read root's WORKING
   TREE and INDEX (`_splice_and_stage`, `_apply_release_bump`,
   `_apply_gate_rule_sync`, `_assert_land_complete`/`_staged_files`,
   `_apply_pre_commit_sweep_or_unwind`, `_commit_squash_apply`). Composing
   only the squash out-of-tree leaves every one of them reading an index
   nothing populated -- a land that commits nothing while writing
   `state: done`.

3. This machine runs git 2.34.1. `git merge-tree --write-tree` needs 2.38+.
   There is NO plumbing path to an out-of-tree three-way merge here.

CORRECTED APPROACH: use T-3095's disposable-`git worktree` technique --
check out at `pre_land_tip` (never at the composed commit; that breaks
`_apply_release_bump`'s `_verified_reset_root` unwind invariant), run the
real `git merge --squash` there, reuse `_auto_resolve_out_of_scope_conflicts`
verbatim against that worktree, then write-tree/commit-tree/`publish_ref_cas`.
T-3107 builds that primitive; this ticket is now the WIRING of it and is
blocked on T-3107.


UNANSWERED DESIGN QUESTION the re-scoped plan must settle before any code
(series BM, recorded so the next agent does not rediscover it):

ROOT RESYNC AFTER THE CAS PUBLISH. Root is not a bare repo -- it is a
CHECKED-OUT worktree sitting on `main`. `publish_ref_cas` moves
`refs/heads/main` underneath it, which leaves root's HEAD, index and
working tree all still at `pre_land_tip`. The instant the CAS succeeds,
root's `git status` reports the ENTIRE landed changeset as reverted local
modifications -- which is a worse dirty-root than the one this epic exists
to remove, and it is the state every sibling agent's DirtyMain check would
then read.

So the transaction does not end at the publish. It needs a resync of root
onto the new tip immediately after (`git -C root reset --keep <new>` or
`read-tree -m -u`), and that resync:
  - is itself a working-tree mutation with a real, if short, window;
  - can FAIL if a concurrent agent has dirtied root in the meantime, and
    the failure happens AFTER the commit is already public, so it cannot
    unwind -- same posture as T-3111's post-publish rebuild: report
    loudly, never revert;
  - must not clobber a sibling's uncommitted work in root, which rules out
    `reset --hard` (the T-1740 lesson `_commit_squash_apply`'s own
    fallback already encodes).

Decide and write down the resync mechanism and its failure semantics
BEFORE retargeting the six index-consuming stages. An out-of-tree compose
that publishes and then leaves root desynchronized would trade a ~1.5s
staged window for a permanent one.

MEASURED BASELINE for comparison (2026-08-27, rapid profile, live fleet):
a concurrent `git --no-optional-locks -C <root> status --porcelain` poll at
0.5s during T-3107's real land read DIRTY at 3 of 97 samples -- a ~1.5s
window carrying 7 then 9 changed paths. Note the poll MUST use
`--no-optional-locks`: a plain `git status` poll takes `.git/index.lock`
and races the land's own commit. It did exactly that on the first attempt
here and killed the land with `CommitFailed: Unable to create index.lock`.
Also note a 0.5s poll in a live fleet cannot attribute a dirty sample to a
particular land; only a quiet-fleet measurement is attributable.


SETTLED: ROOT RESYNC AFTER THE CAS PUBLISH (2026-08-27, series BQ)

The open design question above is now answered. Mechanism, rationale and
failure semantics, all verified against this machine's git 2.34.1:

MECHANISM -- `git -C <root> read-tree -m -u <pre_land_tip> <composed_commit>`
(a two-tree "twoway_merge", the same plumbing `git checkout` uses), run
immediately after a successful `publish_ref_cas`, still holding the land
lock.

Why that and not the alternatives:

- Root's `HEAD` is a SYMREF to `refs/heads/main`, so the CAS publish moves
  HEAD as a side effect. Only the INDEX and WORKING TREE are left at
  `pre_land_tip`. The resync must therefore update index+worktree and must
  NOT touch any ref. `read-tree -m -u` touches no ref at all; `reset --keep`
  would re-point the branch ref it just published. Fewer moving parts on the
  post-publish side of an unwindable boundary wins.
- `reset --hard` is forbidden -- T-1740, already encoded in
  `_commit_squash_apply`'s own fallback. It would silently destroy a sibling
  agent's uncommitted work in root.

VERIFIED PROPERTIES (measured, git 2.34.1, disposable repos):
1. Resync applies the landed changeset to root's index and worktree: after
   `update-ref` left `M a.txt` outstanding, `read-tree -m -u OLD NEW` exited
   0 and `git status --porcelain` went clean for that path.
2. A sibling's uncommitted edit to an UNRELATED path survives untouched --
   `b.txt` kept its uncommitted line and stayed ` M` across the resync.
3. A sibling's uncommitted edit to a path the land ALSO changed causes an
   ATOMIC REFUSAL: `error: Entry 'a.txt' not uptodate. Cannot merge.`,
   exit 128, and the sibling's content is left byte-for-byte intact. No
   partial application. This is the property that makes the failure path
   safe to merely report.

FAILURE SEMANTICS -- post-publish, so it CANNOT unwind:
- The commit is already public and already correct. A resync failure is NOT
  a land failure. `land()` must still return `Ok(LandReport)`; the ticket is
  legitimately done.
- Posture is identical to T-3111's post-publish native rebuild: report
  loudly, never revert. Log at ERROR naming the ticket, the published sha,
  and the exact operator recovery command
  (`git -C <root> read-tree -m -u <pre_land_tip> <sha>` after the sibling's
  work is committed or stashed), and surface it as a non-fatal field on the
  `LandReport` so a coordinator sees it rather than discovering it as a
  mystery dirty root.
- Exactly ONE attempt, no retry loop. A retry races the same sibling that
  caused the refusal and only widens the window.
- Because the refusal is atomic, the failure state is "root's index and
  worktree still describe `pre_land_tip`" -- i.e. the ~1.5s dirty window
  degrades to a visible-and-loudly-reported dirty root, never to a
  half-applied tree. That is strictly better than the status quo, and it is
  bounded: the very next land, or the operator's one-line command, clears it.

CONSEQUENCE FOR THIS TICKET'S SEQUENCING. The resync is a primitive and it
belongs next to the other compose primitives in `src/frob/tickets/
_land_compose.py`, which is OUTSIDE this ticket's scope. It is therefore
decomposed out (see the child filed today) and built first, with both a
must-fire (conflicting dirty path -> refusal, sibling content intact) and a
must-stay-quiet (unrelated dirty path -> resync succeeds, sibling edit
preserved) fixture. T-3089 remains the WIRING of the six index-consuming
stages and stays blocked until that primitive exists.
