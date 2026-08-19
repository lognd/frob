---
id: T-2614
title: T-2450 scope is a single semicolon-joined glob string, not two scope entries
state: done
kind: bug
origin: human
created: '2026-08-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
scope:
- tickets/T-2450/**
- tickets/T-2450/ticket.md
- tests/unit/test_t2450_scope_repair.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: tickets/**
  reason: narrow to the ticket's own directory instead of the whole tickets tree
  actor: logan
  at: '2026-08-19'
- op: add
  glob: tickets/T-2450/**
  reason: narrow to the ticket's own directory instead of the whole tickets tree
  actor: logan
  at: '2026-08-19'
- op: add
  glob: tickets/T-2450/ticket.md
  reason: already covered by tickets/T-2450/**, no-op ack
  actor: logan
  at: '2026-08-19'
- op: add
  glob: tests/unit/test_t2450_scope_repair.py
  reason: T-2614 needs a designated FAILED_AT_PARENT repro test proving the scope
    fix; this ticket's bug kind requires a pytest node id, not a docs-only evidence-cmd
  actor: logan
  at: '2026-08-19'
evidence:
- tests/unit/test_t2450_scope_repair.py::TestT2450ScopeRepair::test_no_scope_entry_contains_a_semicolon
- tests/unit/test_t2450_scope_repair.py::TestT2450ScopeRepair::test_every_scope_entry_is_independently_matchable
designated_repro_test: tests/unit/test_t2450_scope_repair.py::TestT2450ScopeRepair::test_no_scope_entry_contains_a_semicolon
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while re-measuring T-2593 (over-broad scope enforcement). T-2450's
declared scope is a single ticket-frontmatter scope entry containing a
literal semicolon joining two globs:

    'src/frob/verify/**;src/frob/app/ticket_runner/**'

instead of two separate scope entries. As stored, that string is not a
valid glob pattern frob's scope matcher can meaningfully evaluate as
"src/frob/verify/** OR src/frob/app/ticket_runner/**" -- it is one
malformed pattern. This is a data/CLI-parsing defect in how the scope was
recorded (likely a `--scope` invocation that passed one semicolon-joined
argument instead of two separate `--scope` values or `--add` calls), not
an enforcement gap: large_glob_warnings/TICK009 correctly has nothing
sensible to say about a pattern that cannot be interpreted as a directory
glob in the first place.

Two things worth checking together:
1. Whether `frob ticket scope`/`new --scope` should validate/reject a
   semicolon (or other glob-illegal separator) inside a single scope
   entry at write time, rather than silently storing it.
2. T-2450's own scope should be split into two proper entries once
   someone picks it up (do not bulk-fix this from outside T-2450's own
   scope -- same over-broad-claim problem T-2593 was about).