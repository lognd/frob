---
id: T-3303
title: 'frob ticket show auto-commits: NOT_TICKET_SCOPED verbs fall through to the
  generic commit path when ticket_id is set'
state: done
kind: bug
origin: human
created: '2026-08-28'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/__init__.py
- src/frob/app/ticket_runner/_ledger_mirror.py
- tests/unit/test_ticket_runner_ledger_mirror.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_ticket_runner_ledger_mirror.py
  reason: T-3303's fix (an explicit NOT_TICKET_SCOPED branch) needs a structural test
    over the whole LedgerWriteStrategy dispatch table, added to this file
  actor: logan
  at: '2026-08-28'
body_changes:
- mode: append
  reason: 'coordinator directive: require a structural fixture over the LedgerWriteStrategy
    dispatch table, not a show-specific regression test'
  actor: logan
  at: '2026-08-28'
  old_length: 4124
  new_length: 5083
evidence:
- tests/unit/test_ticket_runner_ledger_mirror.py::TestAutoCommitDispatchCoversEveryStrategy::test_every_strategy_member_is_covered
- tests/unit/test_ticket_runner_ledger_mirror.py::TestAutoCommitDispatchCoversEveryStrategy::test_never_reaches_generic_commit_regardless_of_ticket_id
- tests/unit/test_ticket_runner_ledger_mirror.py::TestAutoCommitDispatchCoversEveryStrategy::test_generic_strategies_still_reach_the_generic_commit
designated_repro_test: tests/unit/test_ticket_runner_ledger_mirror.py::TestAutoCommitDispatchCoversEveryStrategy::test_never_reaches_generic_commit_regardless_of_ticket_id
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
REPORTED FROM REAL CONSUMER USE (../diax FROBLEMS.md F-019, F-024). Two
separate read/no-op verbs that should never write the ledger.

F-024 IS CONFIRMED IN CODE, PRECISELY. `frob ticket show <id>` produced a
real commit ("chore(tickets): show T-draft-4ff72519") after a batch of
`frob ticket new --no-commit` calls. Root cause, traced exactly:

  src/frob/app/ticket_runner/_ledger_mirror.py:235 correctly classifies
  "show" as `LedgerWriteStrategy.NOT_TICKET_SCOPED`.

  BUT the dispatcher that acts on that classification
  (src/frob/app/ticket_runner/__init__.py, `_auto_commit_ledger_after_dispatch`,
  around line 631 onward) only special-cases TWO of the three strategy
  values:

      if strategy is LedgerWriteStrategy.OWN_TRANSACTION_LEDGER_MIRROR:
          ...
          return
      if strategy is LedgerWriteStrategy.OWN_TRANSACTION:
          return
      if cfg.ticket_id is None:
          return
      # falls through to the generic auto-commit path below

  NOT_TICKET_SCOPED has NO early-return branch of its own. It falls into the
  generic `if cfg.ticket_id is None: return` check, which is FALSE whenever
  the verb happens to take a ticket id argument -- true for `show <id>`, even
  though "show" is a read verb. `list`/`doable`/`board`/etc. never set
  `cfg.ticket_id` so they accidentally skip the bug; `show` does set it, so
  it falls through into `commit_ticket_ledger_change`
  (src/frob/tickets/_leases.py:2719) and commits whatever the load path
  touched. The function's own docstring claims "NOT_TICKET_SCOPED... never
  dirties the ledger either way, so there is nothing to resolve a commit
  pathspec against" -- that claim is false for any NOT_TICKET_SCOPED verb
  that DOES take a ticket id, which is exactly the gap.

  (Whether the commit actually contains a real content change, or
  `commit_ticket_ledger_change` no-ops on a clean working tree, was not
  verified here -- confirm this as part of the fix; if it no-ops on truly
  unchanged content then the live repro depends on SOME load-time
  normalization touching the file, worth tracking down too.)

WHAT NOT TO DO: do not fix this by adding `show` to the OWN_TRANSACTION
branch (a no-op return) as a one-off patch -- the SAME gap exists for every
future NOT_TICKET_SCOPED verb that takes a ticket id, and the whole point of
the strategy-dispatch design (per its own docstring) is that a new verb is
covered "the instant it is added" by its LEDGER_VERB_STRATEGY entry alone.
Fix the dispatcher's fall-through, not just this one verb.

WHAT TO BUILD: give `LedgerWriteStrategy.NOT_TICKET_SCOPED` its own explicit
early-return branch in `_auto_commit_ledger_after_dispatch`, symmetric with
the other two strategies, so no NOT_TICKET_SCOPED verb can ever reach the
generic commit path regardless of whether `cfg.ticket_id` happens to be set.

F-019 (separate defect, same "ticket verbs write when they should not"
theme, NOT independently code-verified here -- confirm before fixing):
`frob ticket new` run with cwd outside any git repo / frob.toml tree
allegedly created a ledger there silently instead of refusing. Reported
scenario: a script ran it 49 times against a scratch dir under /tmp with no
git and no frob.toml; each call printed "created T-draft-..." (~12s/call)
and wrote tickets/ into the scratch dir. Expected: a hard error ("not a frob
repo") before any write. Locate the root-resolution path `frob ticket new`
uses and confirm whether it truly has no "no project root found" guard, or
whether it does and this was some other misconfiguration (e.g. a stray
frob.toml higher up the /tmp tree) -- state which in the Done report.

MUST-FIRE FIXTURE (F-024): `frob ticket new --no-commit` then `frob ticket
show <id>` in a clean tree -- must produce ZERO new commits.

MUST-FIRE FIXTURE (F-019, if confirmed): `frob ticket new` from a cwd with no
ancestor frob.toml and no ancestor .git -- must exit non-zero with a clear
"not a frob repo" error and write nothing.

MUST-STAY-QUIET FIXTURE: every OWN_TRANSACTION and OWN_TRANSACTION_LEDGER_MIRROR
verb (e.g. `close`, `promote`) keeps committing exactly as before.



COORDINATOR NOTE (2026-08-29): confirmed structural, not a one-off -- fix
the dispatch table's coverage, not just this one verb.

REQUIRED EVIDENCE SHAPE: a regression test must NOT be scoped to "show no
longer commits" alone -- that only proves this one instance is fixed and
would not catch the next NOT_TICKET_SCOPED verb reopening the same gap.
Required: a STRUCTURAL fixture that iterates every `LedgerWriteStrategy`
value (or at minimum every value currently mapped in LEDGER_VERB_STRATEGY)
and asserts `_auto_commit_ledger_after_dispatch` has an explicit,
early-returning branch for each -- e.g. by asserting NOT_TICKET_SCOPED
(and any future strategy) never reaches `commit_ticket_ledger_change`
regardless of whether `cfg.ticket_id` happens to be set, rather than
special-casing on a hardcoded verb name. A fixture keyed to the ENUM, not
to "show", is what keeps this fixed when the next NOT_TICKET_SCOPED verb
with a ticket-id argument is added.