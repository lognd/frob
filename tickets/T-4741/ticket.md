---
id: T-4741
title: 'Trunk-assigned ticket numbers: a branch never owns a T-#### number; frob ticket
  sync --base main absorbs, renumbers and rewrites citations'
state: queued
kind: feature
origin: human
created: '2026-09-19'
priority: critical
blocked_by:
- T-4657
- T-4658
parent: T-4652
tier: ticket
sprint: v0.535.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_sync.py
- src/frob/tickets/_land_ledger_merge.py
- tests/unit/test_ticket_sync_trunk_numbers.py
- docs/modules/tickets-merge-driver.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'read T-1608/T-1609/T-2202/T-3248: none is merge-driver renumbering work,
    every overlap is a wildcard-glob artifact, so none is adopted as a child; recorded
    as sequencing constraints instead'
  actor: logan
  at: '2026-09-19'
  old_length: 2476
  new_length: 4098
designated_repro_test: null
acceptance:
- text: Given two branches off the same main, when each files one draft ticket and
    one numbered ticket and then merges main, then both renumber without collision
    and every citation (frob:ticket, frob:todo, follow_up=, blocked_by, parent, done-report
    link) still resolves to the right ticket.
  evidence: []
- text: 'POSITIVE CONTROL: tests/unit/test_ticket_sync_trunk_numbers.py::test_two_branches_same_number_merge_without_collision
    builds exactly that two-branch scenario and asserts the merged ledger has no duplicate
    id and no dangling citation. It FAILS on dev today (both branches own the same
    T-#### and the merge is a ledger content conflict) and passes after this leaf.'
  evidence: []
- text: Given a PR whose ledger carries a numeric id not present on main, or one colliding
    with main, when the pre-merge check runs, then the PR is REFUSED with a named
    error telling the author to run the sync. Proven by ::test_branch_numbered_id_is_refused,
    which also asserts the check reports a nonzero number of ids EXAMINED -- never
    a bare zero.
  evidence: []
- text: Given `git merge main` on a branch with drafts, when the merge driver runs,
    then sync is applied automatically with no separate verb invoked by the user.
  evidence: []
- text: 'Given sync renumbers a ticket, when the rewrite completes, then it is ONE
    atomic ledger write: no state exists in which the ticket is renamed but its citations
    are not (this is T-3929''s failure mode).'
  evidence: []
- text: Given any refusal in the trunk-numbering flow, when it is shown to a user,
    then the message carries the EXACT next command to run, not a description of it.
    The PR check refusing a branch-minted id says "run `frob ticket sync --base main`,
    then push". No refusal in this flow may state a problem without stating its remedy.
  evidence: []
- text: Given `frob ticket sync`, when it runs, then it prints a before/after table
    of every renumbered id and every rewritten citation, and exits with a one-line
    summary of what changed. A sync that renumbered nothing says so on one line rather
    than printing an empty table.
  evidence: []
- text: Given `frob ticket new` on a non-trunk branch, when the ticket is created,
    then the author is told their id is a DRAFT that will be numbered when it reaches
    the trunk -- so nobody is surprised at merge by an id they had already written
    into a commit message or a doc.
  evidence: []
- text: 'Given docs/guides/collaborating.md (new), when a reader follows it, then
    it walks the two-collaborator, two-branch scenario end to end: both file tickets,
    both merge main, both renumber, every citation resolves. It is LINKED from the
    README section on tickets, so it is reachable without already knowing it exists.'
  evidence: []
- text: Given `frob doctor`, when it runs on a branch carrying numeric ids not present
    on main, then it reports them and names the sync command -- the problem is surfaced
    before the PR check refuses it, not after.
  evidence: []
- text: 'POSITIVE CONTROL: a scripted two-collaborator scenario asserts EVERY message
    a user sees, verbatim -- the `new` draft notice, the sync before/after table,
    the sync summary line, the doctor report, and the PR check refusal with its embedded
    command. It FAILS on dev today (none of these messages exist) and passes after
    this leaf. Asserting the text verbatim is the point: a test that only checks an
    exit code would pass against silent or unhelpful output, which is exactly the
    failure this criterion exists to prevent.'
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
LEDGER leaf (story T-4652), owner concern raised 2026-09-19. ~3 points.

Owner: "collaborators working on the same frob-enabled repository will overwrite each
other's tickets: ids carry no information, so we need a way to automatically update them
when we merge main (if main has tickets, absorb them and renumber branches), and with
branch protection there is no way to overwrite main's tickets."

The root cause is that a BRANCH currently owns a T-#### number. Two branches off the same
main both allocate T-4700 and neither is wrong; the collision is only discovered at merge,
when it is a content conflict in the ledger rather than a numbering question. Under branch
protection the usual escape (force the ledger onto main) is not available at all.

Target shape -- a branch NEVER owns a number:
- tickets are created as content-addressed T-draft-<hash> ids; a hash cannot collide across
  branches, so two collaborators filing simultaneously never conflict
- a number is assigned ONLY when a ticket reaches the trunk
- `frob ticket sync --base main` absorbs main's ledger, renumbers the branch's colliding or
  draft ids, and REWRITES EVERY CITATION: frob:ticket, frob:todo, follow_up=, blocked_by,
  parent, and done-report links. This subsumes T-3929's dangling-citation problem, which is
  the same rewrite performed at a different moment.
- the merge driver runs sync automatically on `git merge main`, building on the merge-driver
  work in T-draft-7b4d432f, so the common path needs no new verb (owner directive: prefer
  automatic behaviour to a new verb)
- a CI/pre-merge check REFUSES a PR whose ledger carries a numeric id not present on main or
  colliding with main -- so branch protection is never fought, it is satisfied by construction

This is the structural fix that T-4657's store API and T-4658's assign-once rule make
possible; both must land first.

SCOPE NOTES (planner):
- docs land in docs/modules/tickets-merge-driver.md, NOT docs/modules/tickets-lifecycle.md:
  that file is already declared in T-4659's scope (lease lifecycle) and would serialize the
  two leaves for no reason.
- the merge-driver module is src/frob/tickets/_land_ledger_merge.py. The CLI half lives in
  src/frob/app/ticket_runner/_land_cmd.py (7511 lines), deliberately NOT taken here: it is
  the hottest contended file in the repo and the T-3053 land leaves need it. Wire the CLI
  through the FEATURE-kind implicit CLI grant, or `scope --add` it only if genuinely needed.


SCOPE-OVERLAP RESOLUTION (planner, 2026-09-19, superseding the "KNOWN OVERLAP" note above).

The four queued tickets whose scopes this leaf's filing warned about were read. NONE of them
is a merge-driver renumbering ticket; every overlap is a WILDCARD-GLOB artifact, not shared
subject matter. None becomes a child of this leaf.

  T-1608  "Cross-language inspection stress test: one repo, every supported language, one
           obligation graph"  (feature, parent T-1597)  scope: tests/**, src/frob/**, docs/**
  T-1609  "Tail-end repo hygiene: docs completeness, detector-gap audit, vestigial cleanup,
           waiver audit"  (tier=epic)  scope: docs/**, src/frob/**, tests/**
  T-2202  "frob check --only cycle genuinely fails on frob's own repo -- real cyclic-import
           clusters"  (bug, tier=epic)  scope: src/frob/gates/**, src/frob/tickets/**, ...
  T-3248  "Migrate docstring archaeology into cited tickets (DOCARCH001 findings)"  (docs)
           scope: src/**/*.py

They collide with this leaf only because they declare `src/frob/**`-class globs that swallow
src/frob/tickets/_land_ledger_merge.py and docs/modules/tickets-merge-driver.md. They keep
their own life; this leaf names them as SEQUENCING CONSTRAINTS only, not blockers:
coordinate the write window on _land_ledger_merge.py if any of them is in progress
simultaneously.

NOTE FOR THE LAYERING STORY: T-2202 (cyclic-import clusters in src/frob/tickets) is the same
underlying fact as T-4656's "frob cycle clean on src/frob/tickets" criterion. It is left
under its own epic, but the two should be reconciled before T-4656 is called done.
