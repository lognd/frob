---
id: T-4303
title: WIRE001 fires on every new direct-dispatch verb's --help-only argparse dest
state: in-progress
kind: bug
origin: human
created: '2026-09-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_wire.py
- src/frob/_cli_parsers/_core.py
- tests/gates_suite/test_wire.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/_cli_parsers/_core.py
  reason: 'T-4303: discharge the whereis WIRE001 waiver (follow_up=T-4303) now that
    the real exemption lands -- the waiver''s own job is done'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: tests/gates_suite/test_wire.py
  reason: 'T-4303: new WIRE001 exemption tests for the bypass-verb fix live here'
  actor: logan
  at: '2026-09-08'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Discovered while working T-4299 (frob whereis). Every direct-dispatch verb (bind/agent/worktree/sync-skills, now whereis) registers a --help-only argparse parser whose dests are NEVER read through AppConfig by design -- the actual invocation bypasses AppConfig entirely (frob.__main__._dispatch's raw argv[0] scan). WIRE001 has no way to know this and flags the first NEW dest such a verb ever adds in a diff (pre-existing dests on bind/agent/worktree never got flagged only because they were never touched by a later diff). Right now this needs a per-verb frob:waive WIRE001 (see src/frob/_cli_parsers/_core.py::_add_whereis_parser's waiver for T-4299). Consider either: a WIRE001 exemption for parsers registered only for --help discoverability on a direct-dispatch verb (some structural marker), or documenting this as the expected/permanent posture so a waiver here does not need a fabricated follow_up ticket every time.