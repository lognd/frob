---
id: T-3661
title: 'win32: lease records rejected by POSIX-only argv-safety regex'
state: in-progress
kind: bug
origin: human
created: '2026-09-01'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_leases.py
- tests/gates_suite/test_debt.py
- tests/gates_suite/test_fix_engine.py
- tests/test_tickets_leases.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_tickets_leases.py
  reason: unit tests for _looks_like_a_safe_worktree_path_operand/lease admission
    live here, not in gates_suite
  actor: logan
  at: '2026-09-01'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Windows CI run 33521416410 (tracked by T-3659): tests/gates_suite/test_debt.py::TestDebtGate::test_rel001_land_owned_via_ticket_lease and tests/gates_suite/test_fix_engine.py::TestFixEngineScopeLease::test_narrowed_live_lease_wins_over_stale_declared_scope_lease_filter both fail on win32 only.

Root cause: src/frob/tickets/_leases.py's _REF_ALLOWLIST_RE = re.compile(r"^[A-Za-z0-9._/-]+$"), used by _looks_like_a_safe_git_argv_operand/_lease_shape_is_safe to admit a parsed lease record's worktree field, only allows POSIX-shaped path characters. A Windows worktree path (e.g. D:\a\frob\frob\...\Temp\...) contains ':' (drive letter) and '\' (path separator), so it NEVER matches on win32. Every lease record's worktree field therefore fails _lease_shape_is_safe on Windows, and _read_one_lease/read_all_leases silently DROP the record (return None / omit it), exactly as if the ticket had never called frob ticket start.

This breaks two independent consumers:
1. _rel001_land_owned (src/frob/gates/__init__.py) calls resolve_lease, which reads the ticket's own lease via _read_one_lease -- on Windows this always comes back Err(NoLeaseForTicket) even when a lease genuinely exists, so REL001 is never suppressed as land-owned and fires as a plain-checkout ERROR.
2. _other_ticket_holding_live_lease (src/frob/gates/_fix_engine_scope.py) calls read_all_leases to get another ticket's LIVE (possibly narrowed) lease scope -- on Windows this always comes back empty, so it falls back to the ticket's STALE declared ledger scope instead, exactly the T-2328 staleness bug this fallback was supposed to fix. Confirmed via the "narrowed live lease wins" test: expects skipped==[] (kept) but gets a SkippedFix under the stale broader "design" scope, because the narrowing lease record itself got silently rejected.

Fix direction (product, not test): extend the worktree-field admission check to accept Windows absolute-path shapes (drive letter + backslash separators) while KEEPING the leading-dash rejection (the actual injection-guard property per this regex's own comment) intact -- e.g. a dedicated, more permissive pattern for the worktree field specifically (branch names never need ':'/'\' on any platform, so leave _REF_ALLOWLIST_RE itself unchanged for branch).

Traceback evidence: scratchpad/win-33521-failures.txt lines 2-1119 (test_debt.py) and lines 3317-4438 (test_fix_engine.py).

References T-3659 (tracking ticket for this campaign).
