---
id: T-3404
title: frob ticket scope applies the last --reason to every --add, silently mis-recording
  the scope audit trail
state: in-progress
kind: bug
origin: human
created: '2026-08-29'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_mutate.py
- src/frob/_cli_parsers/_ticket/_metadata.py
- tests/test_tickets_scope_mutation.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/app/ticket_runner/_mutate.py
  reason: the scope subcommand argv handling and its --reason pairing
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/_cli_parsers/_ticket/_metadata.py
  reason: the real defect is in argparse's --reason flag definition for the scope
    subcommand, not in _mutate.py which only consumes the already-collapsed value
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/test_tickets_scope_mutation.py
  reason: must-fire/must-stay-quiet fixtures for the --reason-collapse fix go here,
    alongside TestScopeCli's existing real-argv-parsing precedent
  actor: logan
  at: '2026-08-29'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
`frob ticket scope` does not pair each `--reason` with the `--add` it follows.
Every added glob is recorded with the LAST `--reason` on the command line, so
the scope_changes audit trail records a reason that is not the one the operator
gave for that glob.

MEASURED 2026-08-29 on T-3403. Command issued:

    frob ticket scope T-3403 \
      --add 'scripts/fleet_status.py' \
      --reason 'the disagreeing leak verdict and WORKTREES listing both live here' \
      --add 'tests/unit/test_fleet_status*.py' \
      --reason 'the two required fixtures'

Recorded in tickets/T-3403/ticket.md:

    - op: add
      glob: scripts/fleet_status.py
      reason: the two required fixtures        <-- WRONG, this is the tests reason
    - op: add
      glob: tests/unit/test_fleet_status*.py
      reason: the two required fixtures        <-- correct by coincidence

The first glob's real reason was silently discarded and replaced by the second's.

WHY THIS MATTERS. scope_changes is an audit trail; its whole purpose is to
answer "why is this file in this ticket's scope?" long after the fact. A wrong
reason is worse than a missing one, because it reads as authoritative. Scope is
also a write lease in this repo -- scope entries decide which agent may touch
which files -- so the recorded justification for a lease is load-bearing when
resolving a ScopeLeaseConflict, and it is currently unreliable for any
multi-`--add` invocation.

This is silent. Nothing warns that two `--add`s share one reason. The operator
sees the globs land correctly and has no signal that the reasons did not.

LIKELY SHAPE, confirm do not assume: argparse `--reason` declared as a single
scalar (last-one-wins) rather than paired positionally with `--add`, so all
`--add` values are collected into a list while `--reason` collapses to one
value which is then applied to every entry.

DESIGN QUESTION TO ANSWER EXPLICITLY: argparse cannot express "each --add takes
the --reason that follows it" without either (a) `--add GLOB:REASON` pair
syntax, (b) requiring one invocation per glob, or (c) manual argv scanning to
preserve order. Pick one and say why. Option (b) is the least clever and would
be a defensible answer; do not build argv-scanning machinery if a per-glob
invocation is acceptable. If a single shared reason for all globs in one
invocation IS the intended semantic, then the bug is that it is undocumented
and unsignalled -- say so, document it, and warn when multiple `--add`s are
given with a single `--reason`.

SECOND, SEPARATE FINDING observed in the same session, filed here only so it is
not lost -- triage it into its own ticket rather than fixing it under this one:
adding a documentation FILE to scope does not subsume that file's own anchors.
After `--add 'docs/guides/coordinator-scripts.md'`, scope closure still emitted
272 warnings of the form "doc anchor docs/guides/coordinator-scripts.md#X
describes docs/guides/coordinator-scripts.md#X in
'docs/guides/coordinator-scripts.md#X', not in scope -- consider --add
'docs/guides/coordinator-scripts.md#X'". A glob covering the file should cover
its anchors; as written the advice is unfollowable at any reasonable scale and
trains operators to ignore closure warnings, which is the real cost.

MUST-FIRE FIXTURE:   two `--add`s with two distinct `--reason`s record two
                     distinct, correctly-paired reasons (or, under whichever
                     design is chosen, the invocation is refused/warned).
MUST-STAY-QUIET:     a single `--add` with a single `--reason` is unchanged.

ACCEPTANCE
- The chosen semantic stated and documented, not just implemented.
- Existing mis-recorded scope_changes entries left alone; do NOT retroactively
  rewrite historical audit trails to match the new behaviour.
- Both fixtures committed.
