---
id: T-2615
title: changelog emits an entry for a DROPPED ticket and duplicates the ticket id
  on 101 lines
state: done
kind: bug
origin: human
created: '2026-08-19'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/release/_fragments.py
- tests/test_release.py
- docs/modules/release.md
- tickets/T-2642/ticket.md
- tickets/T-2641/ticket.md
evidence_scope:
- tests/test_release.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_release.py
  reason: 'SCOPE002: existing frob:doc/frob:tests edges on symbols touched by the
    T-2615 fix point at these two files'
  actor: logan
  at: '2026-08-19'
- op: add
  glob: docs/modules/release.md
  reason: 'SCOPE002: existing frob:doc/frob:tests edges on symbols touched by the
    T-2615 fix point at these two files'
  actor: logan
  at: '2026-08-19'
- op: add
  glob: tickets/T-2642/ticket.md
  reason: 'SCOPE001: this ticket''s own Done report files these two drafts as owed
    follow-up work'
  actor: logan
  at: '2026-08-19'
- op: add
  glob: tickets/T-2641/ticket.md
  reason: 'SCOPE001: this ticket''s own Done report files these two drafts as owed
    follow-up work'
  actor: logan
  at: '2026-08-19'
evidence:
- tests/test_release.py::TestChangelogFragments::test_write_refuses_for_a_dropped_ticket
- tests/test_release.py::TestChangelogFragments::test_write_still_succeeds_for_a_done_ticket
- tests/test_release.py::TestChangelogFragments::test_assemble_excludes_a_dropped_tickets_fragment
- tests/test_release.py::TestChangelogFragments::test_assemble_renders_the_ticket_id_exactly_once
designated_repro_test: tests/test_release.py::TestChangelogFragments::test_write_refuses_for_a_dropped_ticket
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Two defects in the changelog path, both measured on main

### Defect 1: a DROPPED ticket produced a release-notes entry (rare, just happened)

T-2593 was dropped -- correctly, as obsolete: the enforcement it proposed
already existed via T-1866 + T-2446, verified by the agent with 5 passing
positive-control tests. Its land still produced:

    changelog.d/T-2593.md   (tracked on main)
        bump: minor
        T-2593: over-broad scope is disclosed but never enforced: ...

    CHANGELOG.md
        - T-2593: T-2593: over-broad scope is disclosed but never
          enforced: 21 open tickets hold wildcard write leases, 0 acknowledged

So the release notes now announce a fix that was never made, and the
`bump: minor` will influence the next version. A reader of the changelog
learns that frob gained over-broad-scope enforcement in this release; it
did not -- it already had it, and this ticket changed no code at all (the
land commit contains only CHANGELOG.md, changelog.d/, and rapid-debt.jsonl).

Measured scope: 95 changelog fragments tracked, 1 belongs to a dropped
ticket. Rare, but it reached main today, so the path allows it.

A dropped ticket must not leave a changelog fragment or a CHANGELOG entry.
Drop should remove the fragment, or land should refuse to emit one for a
non-done ticket. Prefer whichever keeps a legitimately-dropped ticket from
needing manual cleanup.

### Defect 2: the id is duplicated on 101 lines (systematic)

    grep -cE "^- T-[0-9]+: T-[0-9]+:" CHANGELOG.md   ->  101

The rendered form is `- T-2593: T-2593: <title>`. The generator prefixes the
ticket id onto a fragment body that ALREADY begins with the id. 101 released
lines carry it.

### Defect 2b, worth deciding while in here

The entry text is the ticket TITLE, which by this repo's filing conventions
states the PROBLEM ("over-broad scope is disclosed but never enforced",
"frob cycle reports a false CLEAN"). A changelog should say what CHANGED.
Today every entry reads as a bug report rather than a release note.

This is a judgment call, not obviously a defect -- a problem-stated title is
often a serviceable changelog line for a bug fix. Decide deliberately and
record the decision. If a separate one-line "what changed" is wanted, that
is a bigger change: say so and file it rather than half-doing it here.

## Do not

- Do not retroactively rewrite the 101 historical CHANGELOG lines as part of
  the fix. Released notes are a record. Fix the GENERATOR, and decide
  separately (and explicitly) whether a historical cleanup is wanted.
- Do not delete `changelog.d/T-2593.md` by hand without fixing the path that
  created it, or the next dropped ticket recreates it.

## Positive controls, both directions

- a DONE ticket still produces exactly one changelog fragment and one
  CHANGELOG entry -- without this the fix is indistinguishable from
  disabling the changelog
- a DROPPED ticket produces NEITHER
- a newly generated entry contains the ticket id exactly ONCE
- the version bump computed for a release excludes dropped tickets'
  fragments