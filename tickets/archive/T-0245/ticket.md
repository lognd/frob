---
id: T-0245
title: 'mount-aware performance: per-file stat storms and sqlite contention on /mnt/c
  (13-60x tax)'
state: done
kind: bug
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/graph/**
- src/frob/gates/**
- src/frob/gitio.py
- tickets.md
- tests/test_graph.py
- docs/modules/graph.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: tests/**
  reason: 'scope hygiene (T-0455): narrow speculative tests/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/test_graph.py
  reason: T-0245 graph work maps to tests/test_graph.py
  actor: logan
  at: '2026-07-20'
- op: remove
  glob: docs/**
  reason: 'scope hygiene (T-0455): narrow speculative docs/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: docs/modules/graph.md
  reason: T-0245 graph work maps to docs/modules/graph.md
  actor: logan
  at: '2026-07-20'
evidence:
- tests/test_graph.py::TestBuildIncremental::test_touch_without_edit_skips_reparse
- tests/test_graph.py::TestLoadGraph::test_touch_without_edit_is_not_stale
- tests/test_graph.py::TestCacheModule::test_get_file_meta_and_touch_file_stat
designated_repro_test: null
threat: null
component: null
---
Filed from malmberg pilot P3 (/mnt/c, 2026-07-18). Malmberg pilot dedicated /mnt/c findings: same content, same machine -- graph cold 7.4s vs 1.1s, warm up to 31s vs 0.5s, gates-only 19-47s vs 7.9s; ~0.5ms/stat under load (11.3k stats in 90s of sweep strace); sqlite commit 8.2ms vs 2.3ms; concurrent frob processes drove D-state stalls with no lock feedback. Fixes: batch directory walks (os.scandir reuse), cut redundant per-file stats (trust one snapshot pass), sqlite busy_timeout + a visible waiting-on-lock message, and a docs page on WSL-mount expectations. Acceptance: measured cold graph build on the malmberg /mnt/c checkout under 3s.