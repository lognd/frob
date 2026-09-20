---
id: T-5075
title: same_worktree_lease rescans all leases on every ticket-holder pair
state: in-progress
kind: bug
origin: human
created: '2026-09-19'
priority: medium
parent: T-4806
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_leases.py
- src/frob/tickets/_doable.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_doable.py
  reason: 'coordinator design: thread a leases snapshot down from doable() to same_worktree_lease'
  actor: logan
  at: '2026-09-19'
- op: add
  glob: src/frob/tickets/_doable.py
  reason: 'coordinator design: thread a leases snapshot down from doable() to same_worktree_lease'
  actor: logan
  at: '2026-09-19'
- op: add
  glob: src/frob/tickets/_doable.py
  reason: 'coordinator design: thread a leases snapshot down from doable() to same_worktree_lease'
  actor: logan
  at: '2026-09-19'
- op: add
  glob: src/frob/tickets/_doable.py
  reason: 'coordinator design: thread a leases snapshot down from doable() to same_worktree_lease'
  actor: logan
  at: '2026-09-19'
- op: add
  glob: src/frob/tickets/_doable.py
  reason: 'coordinator design: thread a leases snapshot down from doable() to same_worktree_lease'
  actor: logan
  at: '2026-09-19'
- op: add
  glob: src/frob/tickets/_doable.py
  reason: 'coordinator design: thread a leases snapshot down from doable() to same_worktree_lease'
  actor: logan
  at: '2026-09-19'
- op: add
  glob: src/frob/tickets/_doable.py
  reason: 'coordinator design: thread a leases snapshot down from doable() to same_worktree_lease'
  actor: logan
  at: '2026-09-19'
- op: add
  glob: src/frob/tickets/_doable.py
  reason: 'coordinator design: thread a leases snapshot down from doable() to same_worktree_lease'
  actor: logan
  at: '2026-09-19'
designated_repro_test: null
acceptance:
- text: test_real_repo_ledger_is_tick008_clean completes well within its Windows CI
    timeout
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Follow-up to T-5036 (repo_root memoization): even after caching repo_root, tests/gates_suite/test_tick.py TestTick008UnknownLedgerFields test_real_repo_ledger_is_tick008_clean still runs for a very long time locally (reproduced with a faulthandler dump still showing the same doable -> leased_by -> _leased_by_one_holder -> same_worktree_lease call chain, now stuck resolving paths rather than spawning git). Root cause: same_worktree_lease (src/frob/tickets/_leases.py) calls read_all_leases(root) internally on EVERY invocation, and it is called once per (ticket, holder) pair inside frob.tickets._doable.leased_by's inner loop, itself called once per ticket inside doable()'s main loop -- against this repo's ~1171-ticket queue with a comparable number of leases, this is a full leases-directory rescan with a fresh os.stat-based liveness check per lease (frob.tickets._leases._probe_worktree_liveness) repeated on the order of tickets x holders x leases times. read_all_leases's own docstring explains liveness is deliberately NOT cached across calls for freshness against sibling processes/frob.serve's daemon loop -- so this needs a DESIGN decision, not a blind cache: either (a) same_worktree_lease should accept a precomputed leases snapshot from callers that already have one for the whole doable()/leased_by call (mirroring the existing all_leases threading T-0773 already established for the outer leased_by loop, but frob.tickets._doable.py is currently leased by T-4379 so the caller side cannot be touched until that clears), or (b) same_worktree_lease gains its own short-lived, explicitly-invalidated per-process cache (same shape as repo_root/git_common_dir) if a design call decides process-lifetime freshness is an acceptable tradeoff for this specific same-worktree-exclusion check. Do not cache liveness silently without that decision -- a stale-lease-not-detected bug here risks two agents editing the same file undetected.