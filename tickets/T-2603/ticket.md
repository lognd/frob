---
id: T-2603
title: 'three ledger-write patterns across two disjoint verb sets plus a special case:
  one table with a declared per-verb strategy'
state: done
kind: feature
origin: human
created: '2026-08-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
scope:
- src/frob/app/ticket_runner/_ledger_mirror.py
- docs/modules/tickets-lifecycle.md
- tests/unit/test_ticket_runner_ledger_mirror.py
- src/frob/app/ticket_runner/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/modules/tickets-lifecycle.md
  reason: T-2603 public symbols moved into _ledger_mirror.py doc into this file per
    COV/SCOPE002
  actor: logan
  at: '2026-08-19'
- op: add
  glob: tests/unit/test_ticket_runner_ledger_mirror.py
  reason: T-2603 adds new positive-control tests for the unified strategy table
  actor: logan
  at: '2026-08-19'
- op: add
  glob: src/frob/app/ticket_runner/__init__.py
  reason: T-2603 replaces _LEDGER_TRANSACTIONAL_VERBS declaration + _auto_commit_ledger_after_dispatch
    dispatch logic here with the unified table lookup
  actor: logan
  at: '2026-08-19'
evidence:
- tests/unit/test_ticket_runner_ledger_mirror.py::TestVerbStrategy::test_all_classified
- tests/unit/test_ticket_runner_ledger_mirror.py::TestVerbStrategy::test_derived_match
- tests/unit/test_ticket_runner_ledger_mirror.py::TestVerbStrategy::test_missing_raises
- tests/unit/test_ticket_runner_ledger_mirror.py::TestVerbStrategy::test_promote_kind
- tests/unit/test_ticket_runner_ledger_mirror.py::TestPromoteMirror::test_promote_from_worktree_is_visible_on_primary_without_a_land
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## State after T-2587

There are now THREE distinct ledger-write patterns spread across TWO
disjoint verb sets plus one special-case branch:

    _LEDGER_TRANSACTIONAL_VERBS  (T-1615)  "owns its own commit"
    MIRRORED_LEDGER_VERBS        (T-2563)  "is a single pathspec copy"
    promote                      (T-2587)  read-back, copy, then delete
                                           a stale draft dir -- a dedicated
                                           call from a new "promote" branch
                                           in _auto_commit_ledger_after_dispatch,
                                           a member of NEITHER set

## Why this is filed even though T-2587's narrow fix was correct

The agent that landed T-2587 considered unifying the two sets and
deliberately did not, reasoning that they answer orthogonal questions
(owns-its-own-commit vs. is-a-single-pathspec-copy) and that `promote`
needed a third write shape fitting neither -- so folding it into either
would "trade the current desync for a subtler one (a table whose entries
mean different things per key)".

That reasoning is SOUND and the narrow fix was the right call for that
ticket. It recorded the analysis in `docs/modules/tickets-lifecycle.md`
rather than filing, on the grounds that no other verb currently needs a
third pattern.

This ticket exists because the analysis being correct does not make the
debt tracked. Prose in a doc is not a queue entry: nothing surfaces it,
nothing schedules it, and the next person to add a ledger verb will not
read that paragraph before choosing which set to add it to. The measured
cost of exactly that is already on record -- `promote` sat in
`_LEDGER_TRANSACTIONAL_VERBS` and not in `MIRRORED_LEDGER_VERBS`, and that
desync IS the T-2197 bug, where a draft rename was left uncommitted in any
checkout.

Two sets governing overlapping concerns is one desync. Two sets plus a
special case is worse, and it got worse this week.

## What to build

A single verb table with an explicit per-verb mirror-strategy attribute,
replacing both frozensets and the `promote` special case. Every ledger verb
appears exactly once, and its write behaviour is a declared property rather
than a function of which set it was remembered into.

The agent's own caution applies and must be respected: a table whose
entries mean different things per key is WORSE than two honest sets. So the
strategy attribute must be an explicit enumerated value, not an implicit
"whatever this key happens to need". If the design cannot express all three
existing shapes cleanly as declared strategies, say so and close this
rather than forcing it -- a bad unification is worse than the status quo.

Enumerate the full current membership of both sets and the special case
FIRST, and state the strategy each one needs, before writing any code. If
that enumeration shows the three shapes do not generalise, that is a valid
outcome and worth reporting.

## Positive controls, both directions

- every verb previously in `_LEDGER_TRANSACTIONAL_VERBS` behaves
  identically after the change
- every verb previously in `MIRRORED_LEDGER_VERBS` behaves identically
- `promote` from a worktree is still visible on the primary checkout
  without a land (T-2587's own repro,
  `TestPromoteMirror::test_promote_from_worktree_is_visible_on_primary_without_a_land`,
  must still pass)
- adding a hypothetical new verb without declaring a strategy FAILS loudly
  rather than silently defaulting -- this is the whole point; a new verb
  that quietly picks a default recreates the T-2197 bug