---
id: T-3792
title: 'win32: fix backslash-path bugs breaking arch gate / tickets / gates on Windows'
state: queued
kind: bug
origin: human
created: '2026-09-04'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/arch/__init__.py
- src/frob/tickets/_attach.py
- src/frob/tickets/_brief.py
- src/frob/gates/_tickets.py
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
winrun-confirmed: several node-ids fail on win32 because str(Path)/f'{path}' produce backslash-separated paths that downstream code compares against forward-slash prefixes (e.g. is_test_file's PurePosixPath parts check) or splits on '/'. Fix each site to use .as_posix(). Covers: tests/test_arch_gate.py::TestArchGateLargeFile::test_test_file_exempt_from_large001, tests/test_tickets.py::TestAttach::test_index_increments, tests/test_tickets_brief.py::TestInferVerifyCommands::test_matches_test_file_by_stem, tests/test_gates_tick009_tick010.py::TestTick010StaleLeaseReport::test_missing_worktree_reports_once_with_path_and_remedy (message truncation looked path-shape related; investigate).