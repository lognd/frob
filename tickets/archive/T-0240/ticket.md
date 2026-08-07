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
scope:
- src/frob/tickets/**
- src/frob/gates/**
- src/frob/dup/**
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestPreworkSweepBounds::test_sweep_ticket_honors_graph_excludes
- tests/test_gates.py::TestPreworkSweepBounds::test_sweep_ticket_skips_builtin_skip_dirs
- tests/test_gates.py::TestPreworkSweepBounds::test_sweep_ticket_xref_hits_are_real_symbols
designated_repro_test: null
threat: null
component: null
---
Filed from malmberg pilot P3 (/mnt/c, 2026-07-18). Malmberg pilot (HIGH): sweep on an 8-glob scope never completed on /mnt/c across 5 attempts (>13 min; /proc fd sampling showed it inside .claude/worktrees/*/.venv site-packages); identical repo on Linux fs: 5.2s. It ignores [graph] exclude; xref_hits derives nonsense symbols from glob stems (**, __init__, README); SIGINT prints bare KeyboardInterrupt. Also fold in: PRE001 catch-22 on slow mounts (scope edit demands re-sweep which is this unbounded op) and scope_digest env-sensitivity (hashes snapshot file-hashes so a sweep record cannot be transplanted between identical-content checkouts -- consider content-digest keying). Fix: honor excludes + gitignore, cap/skip venv trees, derive xref terms from real symbols only, clean interrupt message.