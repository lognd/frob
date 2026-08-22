---
id: T-2641
title: clean up stray changelog.d/T-2593.md fragment left by the T-2615 bug
state: done
kind: docs
origin: human
created: '2026-08-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- changelog.d/T-2593.md
- CHANGELOG.md
- tests/test_release.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_release.py
  reason: 'T-2641: new repro test for the stray non-DONE fragment cleanup'
  actor: logan
  at: '2026-08-19'
evidence:
- tests/test_release.py::TestNoStrayFragmentForNonDoneTicket::test_every_changelog_fragment_belongs_to_a_done_ticket
designated_repro_test: tests/test_release.py::TestNoStrayFragmentForNonDoneTicket::test_every_changelog_fragment_belongs_to_a_done_ticket
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 7004e1fdc4c5f35d391c04f443d89dbc73aef470
---
T-2615 fixed the generator (src/frob/release/_fragments.py) so a
dropped ticket never again produces a changelog.d/T-####.md fragment or
a CHANGELOG.md entry. It deliberately did NOT touch the pre-existing
stray artifact this bug already produced on main:

- changelog.d/T-2593.md (tracked, announces "bump: minor" for a ticket
  that changed no code)
- CHANGELOG.md's line: "- T-2593: T-2593: over-broad scope is disclosed
  but never enforced: ..." (also carries the T-2615 defect-2 duplicated
  id, itself a data artifact -- the generator fix does not retroactively
  rewrite it)

Both are data cleanup, not code, and out of T-2615's single-file scope.
Now that the generator is fixed and will not recreate the fragment on
any future land, do the cleanup:

- Delete changelog.d/T-2593.md.
- Decide (and record the decision) whether to hand-edit the live
  CHANGELOG.md line, given T-2615's Done report already declined to
  retroactively rewrite the 101 historical duplicated-id lines as a
  matter of policy (released notes are a record). If that policy holds
  here too, leave the line as-is and just remove the stray fragment
  file; if it merits an explicit correction (the line describes a fix
  that never happened, which is a different class of problem than a
  cosmetic doubled id), say so and do it deliberately.