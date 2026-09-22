---
id: T-5289
title: 'TEST010 Tier-A fix deletes the wrong source lines: per-file line numbers come
  from the pre-fix snapshot, so every land''s pre-land pass corrupts files (lands
  refused by ty)'
state: queued
kind: bug
origin: human
created: '2026-09-22'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_fix_engine_text.py
- tests/test_gates_fix_engine.py
- tests/gates_suite/test_fix_engine.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Landed with T-5261 (e1ee0f1704). fix_test010_redundant_test_declaration iterates snapshot.malformed and calls _delete_redundant_test_declaration(root, md.file, md.line) per entry; after the first deletion in a file every later md.line is stale, so it deletes unrelated lines (observed in .claude/worktrees/t-5267 after a refused land: 'def _run_ruff(', '*,' and docstring lines removed from src/frob/check/_python.py, leaving invalid syntax). Every land since ~05:00 on 2026-09-22 runs this pass unscoped, corrupts the worktree tree, and is refused by ty with 1600-3300 'NEW errors' (T-5133, T-5267). Fix: group entries by file, delete from the highest line downward (or re-parse after each write), never apply a stale line index; add a positive-control test with two redundant declarations in one file above real code and assert the code survives byte-for-byte. Also: the pass must be scoped to the landing ticket's touched files (T-5106 note), and a Tier-A handler must refuse to write a file that no longer parses.