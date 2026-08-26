---
id: T-2905
title: wire or drop _parse_csharp (csharp raw-parse test helper)
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
- src/frob/lang/_walk_csharp.py
- tests/test_lang.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_lang.py
  reason: delete _parse_csharp's test and inline get_parser directly, per wire-or-drop
    verdict
  actor: logan
  at: '2026-08-25'
evidence:
- tests/test_lang.py::TestCSharp::test_parse_csharp_produces_a_tree
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
_parse_csharp (src/frob/lang/_walk_csharp.py, added under T-1600) is a
raw tree-sitter parse helper with no production caller -- frob.lang.
__init__'s _parse dispatch loads every grammar through its own generic
get_parser(grammar_name) chokepoint instead. It exists today only so
this module's own tests can exercise the parse step in isolation
(mirrors kotlin's parse_kotlin/raw_kotlin_tree before T-0723 wired
kotlin into central dispatch, and bash's own identical T-2900). Filed
as WIRE001's required follow-up ticket (frob:waive WIRE001 follow_up
on _parse_csharp) rather than citing T-1600 itself, since a ticket
cannot be its own live-tracker follow-up at close time.

No action required unless a future consumer needs a standalone raw-tree
escape hatch for csharp (mirroring _walk_kotlin.raw_kotlin_tree) -- if
one never materializes, drop this ticket (and T-2900, its bash sibling)
and update both waivers to permanent="true" instead.