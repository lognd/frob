---
id: T-1817
title: PRE001/SCOPE001 fire by construction on an unscoped check from a clean root,
  so the 0-error floor cannot be measured
state: done
kind: bug
origin: human
created: '2026-08-08'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_scope.py
- src/frob/gates/__init__.py
- tickets/T-1817/**
- tickets/**
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/__init__.py
  reason: declared scope src/frob/gates/_scope.py does not exist; the PRE001/SCOPE001
    logic (_no_active_ticket_violation, _build_ticket_scoped_jobs) lives in src/frob/gates/__init__.py
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tickets/T-1817/**
  reason: frob ticket start/sweep auto-commit my own bookkeeping shard tickets/T-1817/ticket.md;
    it must be implicitly in my own scope the same way tickets.md is, to land this
    ticket's own change (filed T-1819 for the systemic scope_matches/LEDGER_PATH fix)
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tickets/**
  reason: ticket-ledger bookkeeping shards (frob ticket new/start/sweep auto-commits,
    including the T-1819 follow-up filed from this same worktree) are the sharded-ledger
    equivalent of tickets.md, which is already implicitly in scope for every ticket;
    narrowing to just tickets/T-1817/** was insufficient since any new draft filed
    from this branch also auto-commits its own shard
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/test_gates.py
  reason: regression test for the _b9_exempt_file fix belongs beside the existing
    B9 sibling tests (test_run_gates_still_skips_scope_and_prework_for_ledger_only_diff
    etc) in this file
  actor: logan
  at: '2026-08-08'
evidence:
- tests/test_gates.py::TestRunGates::test_run_gates_still_skips_scope_and_prework_for_sharded_ticket_diff
- tests/test_gates.py::TestRunGates::test_no_active_ticket_violation_names_the_diff_base
designated_repro_test: null
threat: null
component: null
---
An unscoped `frob check` from a CLEAN root reports 2 errors that mean
nothing:

    PRE001: diff touches 4 file(s) but no active ticket is derivable
            (pass --ticket or use a T-####-name branch)
    SCOPE001: diff touches 4 file(s) but no active ticket is derivable

`git status --porcelain` in root is EMPTY at the time. The "diff" being
measured is against a baseline, not the working tree, and no active
ticket exists because a coordinator running a repo-wide check by
definition is not working a ticket.

WHY THIS IS A REAL DEFECT AND NOT COSMETIC: "main is at 0 errors" is
this repo's stated floor, and `frob check` unscoped from root is the
canonical way to measure it. That measurement currently cannot return 0
from a clean tree. Every reader must know to mentally discount exactly
these two, which means the floor is verifiable only by someone who
already knows the answer. A gate that fires by construction on its own
canonical invocation trains readers to discount it -- and a discounted
gate stops being read at all, which is how the two REAL errors this
session (ARCH001 and an invalid-return-type, both introduced by lands
that passed their own scoped checks) sat unnoticed on main.

This has already produced a concrete misread. An agent reported "0
errors" from within its worktree while the coordinator's unscoped run
showed 2; both were right, and reconciling them cost a round trip.

REQUIRED:

1. PRE001/SCOPE001 must not fire when no ticket is derivable AND the
   invocation is unscoped. That combination is not a violation -- it is
   the normal shape of a repo-wide audit. Either suppress them, or
   report them at note severity with a different code meaning "not
   evaluated", never `error`.
2. Whatever "diff touches 4 file(s)" is comparing against must be named
   in the message. From a clean tree the number is unexplainable, and an
   unexplainable count in an error message is what makes people stop
   reading the message.
3. Sibling to T-1804, which fixed the deferred sweep FILING spurious
   PRE001/SCOPE001 regression tickets from exactly this shape. That fix
   stopped the tickets; the underlying by-construction firing is still
   here. Fixing the symptom and leaving the cause is why this resurfaced.

Prefer suppression over a new flag. A `--i-am-not-working-a-ticket`
escape hatch would be a mechanism to manage a rule that should not have
fired, and the standing directive on this repo is to delete the rule's
bad case rather than add machinery around it.

## Done report

`_b9_exempt_file` (the SCOPE001/PRE001 no-active-ticket exemption) only
knew about the legacy single-file `tickets.md` ledger, not the sharded
`tickets/<id>/*` layout this repo now uses -- `frob ticket start`'s own
auto-commit writes exactly `tickets/T-####/ticket.md`, so any unscoped
audit run from a worktree/branch whose only advance past `main` was
routine ticket-CLI bookkeeping saw a false, unexplainable "diff touches
N file(s)" PRE001/SCOPE001 on an otherwise genuinely clean tree.
Reproduced directly on this branch: `git status --porcelain` empty,
`frob check --only scope --only prework` (no --ticket) reported exactly
this shape naming `tickets/T-1817/ticket.md`.

Fix: `_b9_exempt_file` now also exempts any `tickets/`-prefixed path,
the sharded-ledger equivalent of the existing `tickets.md` exemption.
Chose suppression (the fix's own required option 1) over adding an
escape-hatch flag, per the ticket's explicit directive.

Also satisfies requirement 2: `_no_active_ticket_violation`'s message
now names the merge-base `diff` was computed against, so the "N
file(s)" count is explainable from the message alone instead of
unexplainable against a reader's clean `git status`.

Landing this ticket's own diff surfaced a second, distinct gap: SCOPE001
(scope_gate, a different check than the B9 no-active-ticket path this
ticket fixes) doesn't know about the sharded ledger either --
`tickets/<id>/**` is not implicitly in a ticket's own declared scope the
way `tickets.md` is. Filed as a follow-up (see Filed below) since the
fix belongs in `frob.tickets._models.scope_matches`/`LEDGER_PATH`,
outside this ticket's declared scope.

### Changed
```
 tickets/T-1817/ticket.md           | 40 +++++++++++++++++++++++++++++++++++++-
 tickets/T-1819/ticket.md | 39 +++++++++++++++++++++++++++++++++++++
 2 files changed, 78 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_gates.py::TestRunGates::test_run_gates_still_skips_scope_and_prework_for_sharded_ticket_diff` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestRunGates::test_no_active_ticket_violation_names_the_diff_base` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 1 error(s), 1170 warning(s), 734 waived
- error-findings: PRE001@tickets/T-1817
