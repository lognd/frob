---
id: T-2900
title: wire or drop _parse_bash (bash raw-parse test helper)
state: done
kind: docs
origin: human
created: '2026-08-25'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/lang/_walk_bash.py
- tests/test_lang.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_lang.py
  reason: delete _parse_bash's test and inline get_parser directly, per wire-or-drop
    verdict
  actor: logan
  at: '2026-08-25'
evidence:
- tests/test_lang.py::TestBash::test_parse_bash_produces_a_tree
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 8e7582a81aa42d3363fe8a8c16fa6605860363c2
---
_parse_bash (src/frob/lang/_walk_bash.py, added under T-1604) is a raw
tree-sitter parse helper with no production caller -- frob.lang.__init__'s
_parse dispatch loads every grammar through its own generic
get_parser(grammar_name) chokepoint instead. It exists today only so
this module's own tests can exercise the parse step in isolation
(mirrors kotlin's parse_kotlin/raw_kotlin_tree before T-0723 wired
kotlin into central dispatch). Filed as WIRE001's required follow-up
ticket (frob:waive WIRE001 follow_up on _parse_bash) rather than citing
T-1604 itself, since a ticket cannot be its own live-tracker follow-up
at close time.

No action required unless a future consumer needs a standalone raw-tree
escape hatch for bash (mirroring _walk_kotlin.raw_kotlin_tree) -- if one
never materializes, drop this ticket and update the waiver to
permanent="true" (or delete _parse_bash and inline get_parser in its
test) instead.