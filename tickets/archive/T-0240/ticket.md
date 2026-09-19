---
id: T-0240
title: frob ticket sweep unbounded on real scopes -- ignores excludes, walks venvs,
  nonsense xref stems
state: done
kind: bug
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/**
- src/frob/gates/**
- src/frob/dup/**
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: moving DOCARCH001 change-narrative out of the test docstring per T-4420
  actor: logan
  at: '2026-09-19'
  old_length: 802
  new_length: 1498
evidence:
- tests/gates_suite/test_prework.py::TestPreworkSweepBounds::test_sweep_ticket_honors_graph_excludes
- tests/gates_suite/test_prework.py::TestPreworkSweepBounds::test_sweep_ticket_skips_builtin_skip_dirs
- tests/gates_suite/test_prework.py::TestPreworkSweepBounds::test_sweep_ticket_xref_hits_are_real_symbols
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Filed from malmberg pilot P3 (/mnt/c, 2026-07-18). Malmberg pilot (HIGH): sweep on an 8-glob scope never completed on /mnt/c across 5 attempts (>13 min; /proc fd sampling showed it inside .claude/worktrees/*/.venv site-packages); identical repo on Linux fs: 5.2s. It ignores [graph] exclude; xref_hits derives nonsense symbols from glob stems (**, __init__, README); SIGINT prints bare KeyboardInterrupt. Also fold in: PRE001 catch-22 on slow mounts (scope edit demands re-sweep which is this unbounded op) and scope_digest env-sensitivity (hashes snapshot file-hashes so a sweep record cannot be transplanted between identical-content checkouts -- consider content-digest keying). Fix: honor excludes + gitignore, cap/skip venv trees, derive xref terms from real symbols only, clean interrupt message.

DOCARCH001 cleanup note (T-4420): tests/gates_suite/test_prework.py::TestPreworkSweepBounds's class docstring used to say: 'T-0240: the sweep's xref half used to call xref(symbol, root) -- ALWAYS the full repo root, ignoring the per-pattern scan path it had already computed -- and derived its search term from a raw glob-syntax stem (Path(pattern).stem), producing nonsense terms like "**". Both made frob ticket start/sweep unbounded and slow on real scopes. These pin the fix: excludes/skip-dirs are honored (reusing frob.excludes, not a second copy of the rule) and every xref hit is a real, graph-known symbol name.' Moved here; the docstring now states only what the class's tests verify.